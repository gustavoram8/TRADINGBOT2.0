import os
import re
import json
import gzip
import base64
import socket
import secrets
import time
import threading
import urllib.request
import urllib.parse
from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, abort, make_response, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max


# ──────────────────────────────────────────────────────────────────────────
# SENTRY (optional) — error tracking. Inert until SENTRY_DSN is set as an
# env var (free account at sentry.io). Catches unhandled exceptions across
# the Flask app and reports them with stack traces / request context.
# ──────────────────────────────────────────────────────────────────────────
_sentry_dsn = os.environ.get('SENTRY_DSN')
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.0,
            send_default_pii=False,
        )
    except ImportError:
        print("SENTRY_DSN is set but the 'sentry-sdk' package is not installed — "
              "run: pip install sentry-sdk")


# ──────────────────────────────────────────────────────────────────────────
# SECRET KEY — must stay stable across restarts so sessions / reset tokens
# survive a server reboot. Read from env, else persist a generated one to a
# gitignored file so "remember me" cookies keep working.
# ──────────────────────────────────────────────────────────────────────────
def _load_secret_key():
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    key_path = os.path.join(BASE_DIR, '.secret_key')
    if os.path.exists(key_path):
        with open(key_path) as f:
            return f.read().strip()
    new_key = secrets.token_hex(32)
    try:
        with open(key_path, 'w') as f:
            f.write(new_key)
    except OSError:
        pass
    return new_key


app.config['SECRET_KEY'] = _load_secret_key()
# Use PostgreSQL if DATABASE_URL is set, otherwise fall back to SQLite (dev only)
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'scalpel.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 300}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
# "Remember this device" — when opted in, keep the user logged in indefinitely.
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=3650)

# ── Email (Gmail SMTP) — used only for password recovery ──
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_APP_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = (
    'Scalpel', os.environ.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
)

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
reset_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


@app.after_request
def _gzip_response(response):
    """Compress large text responses so the 2.8 MB app page transfers in ~300 KB."""
    if (response.status_code < 200 or response.status_code >= 300
            or response.direct_passthrough
            or 'Content-Encoding' in response.headers
            or 'gzip' not in request.headers.get('Accept-Encoding', '')
            or response.content_length is not None and response.content_length < 1024):
        return response
    ct = response.content_type or ''
    if not (ct.startswith('text/') or ct.startswith('application/json')
            or ct.startswith('application/javascript')):
        return response
    data = response.get_data()
    if len(data) < 1024:
        return response
    compressed = gzip.compress(data, compresslevel=6)
    response.set_data(compressed)
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(compressed)
    response.headers['Vary'] = 'Accept-Encoding'
    return response

# ── Feature flags ──
# Prop Firm Scout is fully built but temporarily disabled until a future launch.
# Flip to True (or set SCOUT_ENABLED=1 in the environment) to re-enable it:
# the Scout tab, its API endpoints and the pricing perk all come back instantly.
SCOUT_ENABLED = os.environ.get("SCOUT_ENABLED", "0") in ("1", "true", "True")

# Pre-Flight (trade confluence checklist trainer) — enabled by default while
# the draft is iterated. Set PREFLIGHT_ENABLED=0 to hide the tab and its APIs.
PREFLIGHT_ENABLED = os.environ.get("PREFLIGHT_ENABLED", "1") in ("1", "true", "True")

# Bump this date every time the Terms & Conditions are materially updated.
# It is stored on each user record at the moment of acceptance so there is
# a permanent audit trail of which version they agreed to.
TERMS_VERSION = "2026-06-05"

# ── WhatsApp alerts (CallMeBot) ──
WA_PHONE  = os.environ.get("WA_PHONE", "")   # e.g. +584125556345
WA_APIKEY = os.environ.get("WA_APIKEY", "")  # CallMeBot API key

def send_whatsapp_alert(message):
    """Send a WhatsApp message via CallMeBot. Fire-and-forget, never raises."""
    if not WA_PHONE or not WA_APIKEY:
        app.logger.warning("WhatsApp alert skipped — WA_PHONE or WA_APIKEY not set.")
        return
    def _send():
        try:
            encoded = urllib.parse.quote(message)
            url = (f"https://api.callmebot.com/whatsapp.php"
                   f"?phone={WA_PHONE}&text={encoded}&apikey={WA_APIKEY}")
            with urllib.request.urlopen(url, timeout=10):
                pass
        except Exception as e:
            app.logger.error("WhatsApp alert failed: %s", e)
    threading.Thread(target=_send, daemon=True).start()

# ── AI client ──
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "placeholder")
MODEL = os.environ.get("SCALPEL_MODEL", "gpt-4o")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)

# GPT-4o token pricing (USD per 1M tokens) — used only to ESTIMATE AI spend for the
# admin Analytics & AI-spend dashboard. Override via env if OpenAI changes prices.
AI_PRICE_IN_PER_1M  = float(os.environ.get("AI_PRICE_IN_PER_1M",  "2.50"))
AI_PRICE_OUT_PER_1M = float(os.environ.get("AI_PRICE_OUT_PER_1M", "10.0"))
AI_PRICE_IN  = AI_PRICE_IN_PER_1M  / 1_000_000
AI_PRICE_OUT = AI_PRICE_OUT_PER_1M / 1_000_000


# ── Expose feature flags to every template ──
@app.context_processor
def inject_feature_flags():
    return {
        'scout_enabled': SCOUT_ENABLED,
        'preflight_enabled': PREFLIGHT_ENABLED,
        'has_beta_access': has_beta_access(),
        'beta_min_rank': BETA_MIN_RANK,
    }


# ──────────────────────────────────────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(20), default='free', nullable=False)  # free / standard / premium
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # ── Paid-plan lifecycle (manual activation today; Stripe webhook later) ──
    plan_cycle = db.Column(db.String(10), nullable=True)       # monthly / annual
    plan_started_at = db.Column(db.DateTime, nullable=True)
    plan_expires_at = db.Column(db.DateTime, nullable=True)    # NULL = no expiry (free/admin)
    cancel_at_period_end = db.Column(db.Boolean, default=False, nullable=False)
    # ── Email verification (OTP) ──
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_code = db.Column(db.String(6), nullable=True)
    verification_expires = db.Column(db.DateTime, nullable=True)
    # ── Account ban (always confirmed by an admin; never automatic) ──
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    banned_at = db.Column(db.DateTime, nullable=True)
    ban_reason = db.Column(db.String(300), nullable=True)
    # ── Forum auto-mute (TEMPORARY + reversible; NOT a ban) ──
    # Set automatically when a user trips repeated moderation blocks in a short
    # window, so a profanity spammer stops costing AI moderation calls without
    # waiting for an admin. It expires on its own; only admins ever *ban*.
    muted_until = db.Column(db.DateTime, nullable=True)
    # ── Terms & Conditions acceptance (clickwrap evidence) ──
    terms_accepted_at = db.Column(db.DateTime, nullable=True)
    terms_version = db.Column(db.String(20), nullable=True)  # e.g. "2026-06-05"
    # ── Stable login identifier for session/remember-me cookies ──
    # A random token (not the DB primary key) so cookies issued before a
    # database migration (e.g. SQLite -> PostgreSQL, where numeric ids can
    # shift) can never resolve to a different account.
    alt_id = db.Column(db.String(40), unique=True, nullable=True, index=True,
                       default=lambda: secrets.token_hex(20))
    # ── Periodic testimonial prompt (all plans, free included) ──
    last_review_prompt_at = db.Column(db.DateTime, nullable=True)
    # ── XP / Rank system (retention loop) ──
    # `xp` is the lifetime accumulated total; `rank` (1-8) is derived from it
    # but stored for cheap reads. `last_xp_active_date` (UTC 'YYYY-MM-DD') gates
    # the once-per-day login bonus. `first_preflight_xp` flags the one-time
    # "created your first Pre-Flight checklist" bonus.
    xp = db.Column(db.Integer, default=0, nullable=False)
    rank = db.Column(db.Integer, default=1, nullable=False)
    last_xp_active_date = db.Column(db.String(10), nullable=True)
    first_preflight_xp = db.Column(db.Boolean, default=False, nullable=False)
    # Highest rank whose rank-up celebration has already been shown. The /app
    # reveal fires once when `rank` outruns this, then seals it (a reload can't
    # replay it) — same one-time pattern as the plan-purchase unlock reveal.
    rank_celebrated = db.Column(db.Integer, default=1, nullable=False)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def get_id(self):
        return self.alt_id


class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    anon_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class AICostLog(db.Model):
    """One row per AI API call (analyze / validate / forum moderation). Records token
    usage and the estimated USD cost. Powers the admin Analytics & AI-spend panel and
    the prepaid 'fuel gauge'. Kept separate from UsageLog so it never affects rate limits."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    plan = db.Column(db.String(20), nullable=True)
    kind = db.Column(db.String(20), nullable=False, default='analyze', index=True)
    model = db.Column(db.String(60), nullable=True)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    cost_usd = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class AICreditCheckpoint(db.Model):
    """Admin-entered snapshot of the real OpenAI prepaid balance at a moment in time.
    Remaining fuel = balance_usd − sum(AICostLog.cost_usd recorded since created_at).
    Re-entering the real balance (reconciliation) just adds a newer checkpoint."""
    id = db.Column(db.Integer, primary_key=True)
    balance_usd = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# ── Analysis Projects (saved presets for the Analyze form) ──
# A project stores the user's reusable strategy config (instrument, session,
# HTF bias, bias alignment, approach, confluences). It deliberately does NOT
# store Direction or Result — those are per-trade outcomes marked fresh each time.
class AnalysisProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(60), nullable=False)
    config = db.Column(db.JSON, nullable=False, default=dict)  # {instrument, session, htf_bias, aligned, approach, confluences:[]}
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref='analysis_projects')


# ── Pre-Flight checklists (saved confluence presets) ──
# A checklist is the user's personal "trigger": the confluences they require
# before entering a trade, plus the score thresholds for the GO / CAUTION verdict.
class PreflightChecklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(60), nullable=False)
    config = db.Column(db.JSON, nullable=False, default=dict)  # {confluences:[{id,label}], min_go, min_caution}
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref='preflight_checklists')


# ── Pre-Flight checks (one logged pre-trade run of a checklist) ──
# Snapshot-heavy on purpose: the checklist may be edited or deleted later,
# so each check keeps its own name, labels and totals for honest stats.
class PreflightCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('preflight_checklist.id'), nullable=True)
    checklist_name = db.Column(db.String(60), nullable=False)
    checked = db.Column(db.JSON, nullable=False, default=list)  # labels ticked at log time
    total = db.Column(db.Integer, nullable=False, default=0)    # confluences in the checklist
    score = db.Column(db.Integer, nullable=False, default=0)    # confluences ticked
    verdict = db.Column(db.String(10), nullable=False)          # 'go' | 'caution' | 'no-go'
    outcome = db.Column(db.String(10), nullable=True)           # 'win' | 'loss' | 'skipped'
    note = db.Column(db.String(200), nullable=True)
    # ── Trade metadata (optional — backtesting or live papertrading log) ──
    trade_date = db.Column(db.Date, nullable=True)
    instrument = db.Column(db.String(20), nullable=True)
    direction = db.Column(db.String(10), nullable=True)         # 'long' | 'short'
    entry_price = db.Column(db.Float, nullable=True)
    exit_price = db.Column(db.Float, nullable=True)
    rr = db.Column(db.Float, nullable=True)
    position_size = db.Column(db.Float, nullable=True)
    pnl = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user = db.relationship('User', backref='preflight_checks')


# ── Trading Forum (premium-only community) ──
class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)  # relative to /static/
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User', backref='forum_posts')


class ForumComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('forum_comment.id'), nullable=True, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User')


class ForumReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=True, index=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('forum_comment.id'), nullable=True, index=True)
    emoji = db.Column(db.String(16), nullable=False)  # like / love / fire / chart / think
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class SavedPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ModWarning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    reason = db.Column(db.String(64), nullable=False)    # category: insult / offtopic / spam ...
    detail = db.Column(db.String(300), nullable=True)    # short human explanation
    excerpt = db.Column(db.Text, nullable=True)          # the blocked content snippet
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user = db.relationship('User', backref='warnings')


class BanSuggestion(db.Model):
    """A flagged account proposed for a ban. NEVER bans automatically — it only
    surfaces in the admin panel, where a human reviews the evidence and either
    confirms the ban or dismisses the suggestion."""
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category    = db.Column(db.String(40), nullable=False)   # 'conduct' | 'leak'
    detail      = db.Column(db.String(400), nullable=False)  # human explanation of WHY
    evidence    = db.Column(db.Text, nullable=True)          # link / watermark id / excerpt
    status      = db.Column(db.String(16), default='pending', nullable=False, index=True)  # pending|confirmed|dismissed
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    user        = db.relationship('User', backref='ban_suggestions')


class BrowserFingerprint(db.Model):
    """Stores the most recent browser fingerprint hash for each user.
    Used to correlate ban-evading re-registrations from the same device."""
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    fp_hash      = db.Column(db.String(64), nullable=False, index=True)
    collected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user         = db.relationship('User', backref='fingerprints')


class BannedFingerprint(db.Model):
    """A fingerprint hash copied from BrowserFingerprint when a ban is confirmed.
    New registration attempts from a matching device are blocked."""
    id         = db.Column(db.Integer, primary_key=True)
    fp_hash    = db.Column(db.String(64), nullable=False, unique=True, index=True)
    banned_uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    source_user = db.relationship('User', backref='banned_fingerprints')


class SynapseDownloadToken(db.Model):
    """A one-time download token for the personalized Synapse PDF.
    Expires in 24 h; max 3 downloads; token is a 48-char hex string."""
    id           = db.Column(db.Integer, primary_key=True)
    token        = db.Column(db.String(48), unique=True, nullable=False, index=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    order_id     = db.Column(db.String(64), nullable=False)   # e.g. "MANUAL-001" or Stripe order id
    downloads    = db.Column(db.Integer, default=0, nullable=False)
    max_dl       = db.Column(db.Integer, default=3, nullable=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    expires_at   = db.Column(db.DateTime, nullable=False)
    user         = db.relationship('User', backref='download_tokens')

    @property
    def is_valid(self):
        if self.downloads >= self.max_dl:
            return False
        return datetime.now(timezone.utc) < _as_utc(self.expires_at)


# ── Prop Firm Scout ──
class PropFirm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    website = db.Column(db.String(255))
    account_costs = db.Column(db.JSON)          # {"10k":99,"25k":147,"50k":167,...}
    allowed_worldwide = db.Column(db.Boolean, default=True)
    blocked_countries = db.Column(db.JSON, default=list)   # ISO-2 codes explicitly blocked
    venezuela_friendly = db.Column(db.Boolean, default=False)  # can enroll & withdraw from VE
    rating = db.Column(db.Float, default=0.0)
    payout_speed_days = db.Column(db.Integer, default=14)
    withdrawal_methods = db.Column(db.JSON, default=list)  # bank,wise,usdt,btc,paypal,deel,rise
    trading_platforms = db.Column(db.JSON, default=list)   # rithmic,tradovate,ninjatrader,quantower
    drawdown_type = db.Column(db.String(20), default='trailing')  # static|trailing|both
    has_promotion = db.Column(db.Boolean, default=False)
    promotion_detail = db.Column(db.String(255))
    profit_split = db.Column(db.Integer, default=80)
    instruments = db.Column(db.JSON, default=list)
    tags = db.Column(db.JSON, default=list)     # top_rated, most_popular, new, crypto_friendly
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# ──────────────────────────────────────────────────────────────────────────
# PRICING — single source of truth for plan costs (USD)
# ──────────────────────────────────────────────────────────────────────────
# Monthly = price charged each month. Annual = total charged once per year
# (already discounted ~20% vs paying monthly). Mirrors pricing.html.
PLAN_PRICING = {
    'standard': {'monthly': 25.0, 'annual': 240.0},
    'premium':  {'monthly': 50.0, 'annual': 480.0},
}
PLAN_LABELS = {'standard': 'Standard', 'premium': 'Premium'}


def _plan_base_price(plan, cycle):
    """Return the list price for a plan+cycle, or None if invalid."""
    if plan not in PLAN_PRICING or cycle not in ('monthly', 'annual'):
        return None
    return PLAN_PRICING[plan][cycle]


class Order(db.Model):
    """A purchase of a paid plan. Created as 'pending' at checkout; an admin
    (or, later, a Stripe webhook) marks it 'paid', which activates the plan.

    `applied_at` is the idempotency guard: plan activation runs exactly once
    per order, so marking an order paid twice can never double the duration."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    plan = db.Column(db.String(20), nullable=False)            # standard / premium
    billing_cycle = db.Column(db.String(10), nullable=False)   # monthly / annual
    base_price = db.Column(db.Float, nullable=False)           # list price before discount
    discount_pct = db.Column(db.Integer, default=0)            # 0–100
    final_price = db.Column(db.Float, nullable=False)          # what the user actually pays
    promo_code = db.Column(db.String(40), nullable=True)       # code applied, if any
    status = db.Column(db.String(12), default='pending', nullable=False)  # pending/paid/cancelled
    payment_method = db.Column(db.String(30), nullable=True)   # e.g. 'usdt-binance', 'stripe'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=True)         # when the plan was granted
    celebrated_at = db.Column(db.DateTime, nullable=True)      # unlock reveal shown to the user
    note = db.Column(db.String(300), nullable=True)
    user = db.relationship('User', backref='orders')


class PromoCode(db.Model):
    """Discount / creator code. Applied at checkout for MONTHLY plans only
    (per product decision). Tracks usage so partners can see conversions."""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    discount_pct = db.Column(db.Integer, nullable=False)       # 1–100
    creator_name = db.Column(db.String(120), nullable=True)    # influencer / partner
    kind = db.Column(db.String(20), default='discount')        # 'discount' or 'creator'
    valid_for = db.Column(db.String(10), default='monthly')    # monthly / annual / both / store
    max_uses = db.Column(db.Integer, nullable=True)            # NULL = unlimited
    # Personal codes (e.g. roulette prizes) are bound to their winner:
    # nobody else can redeem them even if the code leaks.
    restrict_user_id = db.Column(db.Integer, nullable=True)
    uses_count = db.Column(db.Integer, default=0, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def is_redeemable(self, cycle):
        """Whether this code can currently be applied to the given cycle."""
        if not self.active:
            return False, 'inactive'
        if self.expires_at and datetime.now(timezone.utc) > _aware(self.expires_at):
            return False, 'expired'
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False, 'maxed'
        if self.valid_for != 'both' and self.valid_for != cycle:
            return False, 'cycle'
        return True, 'ok'


class Expense(db.Model):
    """Monthly business expense, entered manually by an admin, used to compute
    profit & loss against order revenue."""
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(160), nullable=False)         # e.g. 'Contabo VPS'
    category = db.Column(db.String(40), default='other')      # hosting/api/domain/marketing/other
    amount = db.Column(db.Float, nullable=False)              # USD
    incurred_on = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date(), index=True)
    recurring = db.Column(db.Boolean, default=False)          # monthly recurring?
    note = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Testimonial(db.Model):
    """A paying trader's periodic rating/review, collected via a recurring
    in-app prompt. Only ratings of 4-5 stars (with consent) are published to
    the public landing-page testimonial panel; lower ratings stay private as
    feedback for the team. These are real accounts tied to real activity —
    never fabricated personas."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)              # 1-5
    text = db.Column(db.String(500), nullable=False)
    display_name = db.Column(db.String(80), nullable=False)     # snapshot at submit time
    plan = db.Column(db.String(20), nullable=True)
    published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class AuditEvent(db.Model):
    """Append-only trail of sensitive operations: payments, plan grants/expirations,
    PDF deliveries, and outbound emails (OTP, password reset, contact form).

    Lets the admin (and the daily summary email) see at a glance whether a paid
    feature actually fired correctly — e.g. "did this user's Synapse PDF really
    get delivered?" or "did the verification email bounce?" — without digging
    through server logs."""
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(40), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    success = db.Column(db.Boolean, default=True, nullable=False, index=True)
    detail = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class DailyQuizState(db.Model):
    """Per-user state of the Daily Challenge (premium-only): one timed question
    per UTC day. A streak of consecutive correct answers earns roulette spins.

    Dates are stored as 'YYYY-MM-DD' UTC strings so day boundaries are
    unambiguous regardless of the user's timezone."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    streak = db.Column(db.Integer, default=0, nullable=False)
    last_played = db.Column(db.String(10), nullable=True)       # date of last ANSWER
    last_result = db.Column(db.Boolean, nullable=True)
    spins_available = db.Column(db.Integer, default=0, nullable=False)
    total_correct = db.Column(db.Integer, default=0, nullable=False)
    served_for = db.Column(db.String(10), nullable=True)        # date the open question belongs to
    question_served_at = db.Column(db.DateTime, nullable=True)  # starts the 60s window


class RouletteSpin(db.Model):
    """A redeemed roulette spin and the prize it landed on. `promo_code` links
    to the single-use PromoCode generated for discount prizes."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    prize_key = db.Column(db.String(20), nullable=False)        # d5/d10/d15/d25/month
    label = db.Column(db.String(120), nullable=False)
    promo_code = db.Column(db.String(40), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class XPLog(db.Model):
    """Append-only ledger of every XP award. Lets us enforce daily/category
    caps (sum today's rows), deduplicate one-time awards (e.g. a quiz question
    can only ever pay once — keyed by `ref`), and reverse XP later (forum spam
    flagged by AI moderation) without losing the audit trail.

    `day` is a 'YYYY-MM-DD' UTC string so cap windows are timezone-agnostic,
    matching the Daily Challenge convention."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    source = db.Column(db.String(30), nullable=False, index=True)   # login/analysis/quiz/...
    amount = db.Column(db.Integer, nullable=False)
    ref = db.Column(db.String(60), nullable=True, index=True)       # dedup key (question_id, post id...)
    day = db.Column(db.String(10), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class RankCertificate(db.Model):
    """One issued rank certificate per (user, rank). The `code` is the public
    verification id printed on the certificate (and encoded in its QR); the
    /verify/<code> page confirms authenticity server-side — that, not the visual
    design, is what stops anyone from fabricating a certificate. `display_name`
    is snapshotted at issue time so a later username change doesn't rewrite an
    already-issued document."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    rank = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(24), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(40), nullable=False)
    issued_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref='rank_certificates')
    __table_args__ = (db.UniqueConstraint('user_id', 'rank', name='uq_rankcert_user_rank'),)


# ──────────────────────────────────────────────────────────────────────────
# XP / RANK CONFIG  (spec frozen 2026-06-13 — see CLAUDE.md)
# No per-plan multiplier: the gap comes from access (premium-only sources) +
# inverse weighting (actions a poorer plan CAN do are worth more). Target
# time-to-Legend ratio Premium 1 : Standard ~2 : Free ~3.
# ──────────────────────────────────────────────────────────────────────────
RANK_NAMES = ['Paper Trader', 'Retail Trader', 'Chart Technician', 'Liquidity Hunter',
              'Swing Strategist', 'Order Flow Sniper', 'Market Maker', 'Trading Legend']
RANK_THRESHOLDS = [0, 200, 600, 1400, 2800, 5000, 8000, 12000]

# Shared actions: XP weighted by plan (inverse — fewer sources => worth more).
XP_SHARED = {
    'login':       {'free': 18, 'standard': 12, 'premium': 5},
    'analysis':    {'free': 60, 'standard': 30, 'premium': 10},
    'testimonial': {'free': 30, 'standard': 30, 'premium': 30},
}
# Premium-only actions: flat XP.
XP_PREMIUM = {
    'quiz_beginner': 5, 'quiz_intermediate': 8, 'quiz_advanced': 12,
    'daily_correct': 15, 'daily_streak': 30,
    'preflight_first': 20, 'preflight_check': 5,
    'forum_post': 5, 'forum_comment': 2, 'forum_reaction': 1,
}
# Per-source daily XP ceilings (anti-farm).
XP_DAILY_CAP = {
    'quiz': 20, 'preflight_check': 15,
    'forum_post': 10, 'forum_comment': 10, 'forum_reaction': 5,
}
# Master daily cap — only premium needs one (free/standard are capped by their
# own plan limits). Exempt sources bypass it (rare rewards, not farmable).
XP_MASTER_CAP = {'free': None, 'standard': None, 'premium': 80}
XP_CAP_EXEMPT = {'testimonial', 'daily_streak', 'preflight_first'}


def rank_for_xp(xp):
    """Return the rank number (1-8) for a given lifetime XP total."""
    r = 1
    for i, threshold in enumerate(RANK_THRESHOLDS):
        if xp >= threshold:
            r = i + 1
    return r


def _xp_day():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _xp_sum_today(user_id, source=None):
    """Sum of XP awarded to a user today (optionally for one source)."""
    q = db.session.query(db.func.coalesce(db.func.sum(XPLog.amount), 0)).filter(
        XPLog.user_id == user_id, XPLog.day == _xp_day())
    if source is not None:
        q = q.filter(XPLog.source == source)
    return int(q.scalar() or 0)


def add_xp(user, source, amount=None, ref=None):
    """Award XP to `user` for `source`, enforcing all caps and dedup. Returns
    the XP actually granted (0 if nothing). Never raises — XP must never break a
    real user action.

    - `amount`: explicit value; if None it is resolved from the XP tables. For
      'quiz' the caller passes the difficulty-based amount explicitly.
    - `ref`: a one-time dedup key (e.g. a quiz question id). If an XPLog row with
      the same (user, source, ref) already exists, nothing is awarded.
    The 'pay full or not at all' rule applies: if the award would overflow a
    daily cap, it is NOT granted (and the dedup ref stays unused for next time).
    """
    try:
        plan = (user.plan or 'free')
        # Resolve amount from the config tables when not given explicitly.
        if amount is None:
            if source in XP_SHARED:
                amount = XP_SHARED[source].get(plan, XP_SHARED[source]['free'])
            elif source in XP_PREMIUM:
                amount = XP_PREMIUM[source]
            else:
                return 0
        if amount <= 0:
            return 0
        # One-time dedup (e.g. a given quiz question only ever pays once).
        if ref is not None:
            exists = XPLog.query.filter_by(user_id=user.id, source=source, ref=ref).first()
            if exists:
                return 0
        # Per-source daily cap — pay full or not at all.
        if source in XP_DAILY_CAP:
            if _xp_sum_today(user.id, source) + amount > XP_DAILY_CAP[source]:
                return 0
        # Master daily cap (premium only), bypassed by exempt sources.
        master = XP_MASTER_CAP.get(plan)
        if master is not None and source not in XP_CAP_EXEMPT:
            # Sum only non-exempt sources toward the master cap.
            used_master = (db.session.query(db.func.coalesce(db.func.sum(XPLog.amount), 0))
                           .filter(XPLog.user_id == user.id, XPLog.day == _xp_day(),
                                   ~XPLog.source.in_(list(XP_CAP_EXEMPT))).scalar() or 0)
            if used_master + amount > master:
                return 0
        # Award it.
        db.session.add(XPLog(user_id=user.id, source=source, amount=amount,
                             ref=ref, day=_xp_day()))
        user.xp = (user.xp or 0) + amount
        new_rank = rank_for_xp(user.xp)
        ranked_up = new_rank > (user.rank or 1)
        user.rank = new_rank
        db.session.commit()
        if ranked_up:
            record_audit_event('rank_up', user_id=user.id,
                               detail=f'{RANK_NAMES[new_rank-1]} (xp={user.xp})')
        return amount
    except Exception:
        db.session.rollback()
        return 0


# Event types that immediately email the admin inbox when they fail — these
# are the "user paid / clicked something and it silently didn't work" cases.
AUDIT_ALERT_ON_FAILURE = {
    'order_paid', 'pdf_issued', 'pdf_downloaded',
    'email_verification', 'email_reset', 'email_contact', 'analysis_error',
}


def record_audit_event(event_type, user_id=None, detail='', success=True):
    """Log a sensitive operation. Never raises — auditing must not break the
    request it's observing. On failure of an alert-worthy event, also emails
    the admin inbox immediately (best-effort, fire-and-forget)."""
    try:
        evt = AuditEvent(
            event_type=event_type, user_id=user_id,
            success=success, detail=(detail or '')[:500],
        )
        db.session.add(evt)
        db.session.commit()
    except Exception as e:
        app.logger.error('record_audit_event failed: %s', e)
        return
    if not success and event_type in AUDIT_ALERT_ON_FAILURE:
        _send_audit_alert_email(event_type, user_id, detail)


def _send_audit_alert_email(event_type, user_id, detail):
    """Fire-and-forget email to the admin inbox when a payment/delivery/email
    event fails. Uses the same MAIL_USERNAME as everything else, so swapping
    to a business inbox later (per the pending domain task) updates this too."""
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('Audit alert (%s) skipped — MAIL_APP_PASSWORD not configured.', event_type)
        return
    admin_inbox = app.config.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
    subject = f'[Trader Accelerator] Action needed — {event_type} failed'
    body = (
        f"Event   : {event_type}\n"
        f"User ID : {user_id if user_id is not None else '(none)'}\n"
        f"Detail  : {detail or '(none)'}\n"
        f"Time    : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Check the Audit Log tab in the admin panel for context."
    )
    msg = Message(subject, recipients=[admin_inbox])
    msg.body = body

    def _send():
        prev_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(15)
        try:
            with app.app_context():
                mail.send(msg)
        except Exception as e:
            app.logger.error('Audit alert email failed: %s', e)
        finally:
            socket.setdefaulttimeout(prev_timeout)

    threading.Thread(target=_send, daemon=True).start()




def _aware(dt):
    """Treat naive DB datetimes as UTC so comparisons never crash."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(alt_id=user_id).first()


@app.before_request
def _enforce_ban():
    """A confirmed ban takes effect immediately, even on an active session:
    a banned non-admin user is logged out on their next request."""
    if current_user.is_authenticated and getattr(current_user, 'is_banned', False) \
            and not current_user.is_admin:
        logout_user()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'banned'}), 403
        return redirect(url_for('login', banned=1))


@app.before_request
def _expire_plan():
    """Downgrade plan to free when the paid period has ended."""
    if not current_user.is_authenticated or current_user.plan == 'free':
        return
    expires = _aware(getattr(current_user, 'plan_expires_at', None))
    if expires and expires < datetime.now(timezone.utc):
        old_plan = current_user.plan
        current_user.plan = 'free'
        current_user.plan_cycle = None
        current_user.plan_started_at = None
        current_user.plan_expires_at = None
        current_user.cancel_at_period_end = False
        db.session.commit()
        record_audit_event('plan_expired', user_id=current_user.id, detail=f'{old_plan} -> free')


# ──────────────────────────────────────────────────────────────────────────
# PLAN LIMITS & ACCESS HELPERS
# ──────────────────────────────────────────────────────────────────────────
PLAN_LIMITS = {
    'free':     {'window': timedelta(days=7), 'max': 1},
    'standard': {'window': timedelta(days=1), 'max': 1},
    'premium':  {'window': timedelta(days=1), 'max': 5},
}

# Max number of saved Analysis Projects per plan.
PROJECT_LIMITS = {'free': 1, 'standard': 5, 'premium': 10}


def project_limit():
    """How many analysis projects the current user may save."""
    # Demo / Preview: mirror the staged plan so the limit shown matches it.
    demo = _admin_demo()
    if demo and demo.get('plan') in PROJECT_LIMITS:
        return PROJECT_LIMITS[demo['plan']]
    if current_user.is_authenticated and current_user.is_admin:
        return PROJECT_LIMITS['premium']
    return PROJECT_LIMITS.get(current_plan(), PROJECT_LIMITS['free'])

ANON_COOKIE = 'scalpel_anon'


def get_anon_id():
    return request.cookies.get(ANON_COOKIE)


def has_access():
    """A request is allowed into the app if logged in OR carrying a free-tier anon cookie."""
    return current_user.is_authenticated or bool(get_anon_id())


def current_plan():
    if current_user.is_authenticated:
        return current_user.plan
    return 'free'


def is_premium():
    return current_user.is_authenticated and (current_user.plan == 'premium' or current_user.is_admin)


# Beta access is a RANK reward (not a plan): unlocked at Order Flow Sniper (rank 6)
# and above. Sections shipped under the "BETA" label gate on this so they light up
# automatically for high-rank users the moment they exist — no per-feature wiring.
BETA_MIN_RANK = 6


def has_beta_access(user=None):
    """True if `user` (default: current_user) has reached the beta-access rank.
    Admins always pass. Never raises for anonymous users."""
    user = user or (current_user if current_user.is_authenticated else None)
    if user is None:
        return False
    if getattr(user, 'is_admin', False):
        return True
    return (user.rank or 1) >= BETA_MIN_RANK


# ── Admin-only Demo / Preview mode ──────────────────────────────────────────
# Lets the admin replay one-time reveals (rank-up, unlock, testimonial), preview
# the app as any plan, and force a real roulette spin — all WITHOUT mutating real
# account state (rank_celebrated / Order.celebrated_at are never touched in demo).
# It is STRICTLY gated on is_admin: a normal user can never activate it, and any
# stale demo flag found on a non-admin session is ignored AND cleared. No code
# path for ordinary or paying users is altered by this feature.
DEMO_PLANS = ('free', 'standard', 'premium')


def _admin_demo():
    """Return the active demo dict for the current admin, or None.
    Never raises; returns None for anyone who isn't a logged-in admin (and
    defensively scrubs any demo flag that somehow rode along on their session)."""
    if not (current_user.is_authenticated and getattr(current_user, 'is_admin', False)):
        if session.get('_admin_demo') is not None:
            session.pop('_admin_demo', None)
        return None
    d = session.get('_admin_demo')
    return d if isinstance(d, dict) else None


def beta_required(fn):
    """JSON guard for endpoints shipped under the BETA label — rank 6+ (or admin).
    Mirrors premium_required so future beta APIs gate with a single decorator."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'unauthorized'}), 401
        if not has_beta_access():
            return jsonify({'error': 'beta_required', 'min_rank': BETA_MIN_RANK}), 403
        return fn(*args, **kwargs)
    return wrapper


def premium_required(fn):
    """JSON guard for premium-only API endpoints (Trading Forum, Prop Firm Scout)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'unauthorized'}), 401
        if not is_premium():
            return jsonify({'error': 'premium_required'}), 403
        return fn(*args, **kwargs)
    return wrapper


def _as_utc(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def check_rate_limit():
    """Return None if analysis is allowed, else a dict describing the block."""
    plan = current_plan()
    cfg = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
    window, max_count = cfg['window'], cfg['max']
    since = datetime.now(timezone.utc) - window

    if current_user.is_authenticated:
        logs = (UsageLog.query
                .filter(UsageLog.user_id == current_user.id,
                        UsageLog.created_at >= since)
                .order_by(UsageLog.created_at.asc()).all())
    else:
        anon = get_anon_id()
        logs = (UsageLog.query
                .filter(UsageLog.anon_id == anon,
                        UsageLog.created_at >= since)
                .order_by(UsageLog.created_at.asc()).all()) if anon else []

    if len(logs) < max_count:
        return None  # under limit → allow

    # Oldest log determines when the next slot opens
    oldest_allowed = _as_utc(logs[0].created_at) + window
    now = datetime.now(timezone.utc)
    remaining = max(0, int((oldest_allowed - now).total_seconds()))
    return {
        'plan': plan,
        'remaining_seconds': remaining,
        'next_available': oldest_allowed.isoformat(),
        'used': len(logs),
        'max': max_count,
    }


def log_usage():
    entry = UsageLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        anon_id=None if current_user.is_authenticated else get_anon_id(),
    )
    db.session.add(entry)
    db.session.commit()


def record_ai_cost(kind, response, user_id=None, plan=None):
    """Best-effort telemetry: log token usage + estimated USD cost of one AI call.
    Never raises — billing analytics must not break the user-facing request."""
    try:
        usage = getattr(response, 'usage', None)
        pt = int(getattr(usage, 'prompt_tokens', 0) or 0)
        ct = int(getattr(usage, 'completion_tokens', 0) or 0)
        cost = pt * AI_PRICE_IN + ct * AI_PRICE_OUT
        db.session.add(AICostLog(
            user_id=user_id, plan=plan, kind=kind, model=MODEL,
            prompt_tokens=pt, completion_tokens=ct, cost_usd=round(cost, 6),
        ))
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def send_reset_email(to_email, reset_url):
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('MAIL_APP_PASSWORD not configured — cannot send reset email.')
        return False
    msg = Message('Scalpel — Password Reset', recipients=[to_email])
    msg.body = (
        "We received a request to reset your Scalpel password.\n\n"
        f"Reset it here (link valid for 1 hour):\n{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    # Bound the SMTP attempt so an unreachable mail server can't hang the request.
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        app.logger.warning('Failed to send reset email: %s', exc)
        return False
    finally:
        socket.setdefaulttimeout(prev_timeout)


def send_verification_email(to_email, code):
    """Send the 6-digit email-verification code. Returns True if sent.

    NOTE: this relies on the same Gmail SMTP config as password resets. The
    whole verification flow is built and active; the only thing left to make
    codes actually arrive in production is configuring the mail credentials
    (MAIL_APP_PASSWORD now / SendGrid later). Without it, codes are still
    generated and surfaced in the server log for local testing.
    """
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning(
            'MAIL_APP_PASSWORD not configured — verification code for %s is %s',
            to_email, code,
        )
        return False
    msg = Message('Trader Accelerator — Verify your email', recipients=[to_email])
    msg.body = (
        "Welcome to Trader Accelerator!\n\n"
        f"Your verification code is: {code}\n\n"
        "Enter it on the verification screen to activate your account. "
        "This code expires in 15 minutes.\n\n"
        "If you didn't create this account, you can safely ignore this email."
    )
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        app.logger.warning('Failed to send verification email: %s', exc)
        return False
    finally:
        socket.setdefaulttimeout(prev_timeout)


def _send_contact_email(sender_name, sender_email, category, message):
    """Forward a contact-form submission to the support inbox. Returns True if sent."""
    support_inbox = app.config.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning(
            'MAIL_APP_PASSWORD not configured — contact form submission from %s (%s): %s',
            sender_name, sender_email, message[:200],
        )
        return False
    subject = f'[Trader Accelerator Contact] {category} — {sender_name}'
    body = (
        f"Category : {category}\n"
        f"Name     : {sender_name}\n"
        f"Email    : {sender_email}\n"
        f"{'─' * 48}\n\n"
        f"{message}\n\n"
        f"{'─' * 48}\n"
        f"Reply directly to this email to respond to the user."
    )
    msg = Message(subject, recipients=[support_inbox], reply_to=sender_email)
    msg.body = body
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        app.logger.warning('Failed to send contact email: %s', exc)
        return False
    finally:
        socket.setdefaulttimeout(prev_timeout)


def _new_verification_code():
    return f"{secrets.randbelow(1_000_000):06d}"


SYSTEM_PROMPT = """You are Scalpel — an expert ICT (Inner Circle Trader) methodology analyst and trading coach. You analyze chart screenshots submitted by traders and identify POSSIBLE areas worth reflecting on, based on ICT theory. You NEVER issue verdicts, declare errors, or treat theory as absolute truth.

CORE PHILOSOPHY — READ THIS BEFORE EVERYTHING ELSE:
ICT methodology is a framework of POSSIBILITIES, not a rulebook of absolutes. Every concept has multiple valid interpretations depending on the trader's personal strategy, experience, and style. Your role is ONLY to suggest things the trader might want to consider — it is entirely the trader's responsibility to decide whether your observation is relevant to their approach.

NEVER say: "You did X wrong." "This was a mistake." "You shouldn't have done this."
ALWAYS say: "One thing worth considering..." "This could suggest..." "Some traders might interpret this as..." "Depending on your approach, you may want to reflect on..."

COMPLIANCE & OUTPUT BOUNDARIES — PERMANENT GLOBAL RULE (applies to EVERY analysis, regardless of which methodology or framework you use now or in the future — ICT, Wyckoff, SMC, classical chart patterns, harmonic patterns, or any methodology added later):
This tool provides RETROSPECTIVE, EDUCATIONAL analysis of a trade the user has ALREADY taken. It is not financial advice and must never read as a recommendation to act in live markets. Therefore, no matter the methodology:
- NEVER tell the user to buy, sell, short, go long, "enter now," "take this trade," "get in/out," or otherwise direct them to open, close, add to, or size any position in live or future markets.
- NEVER state that a specific instrument WILL rise or fall, or present a price target as something that "will" happen. Frame any forward-looking remark as a conditional possibility ("if this level holds, some traders might watch for...").
- NEVER promise, guarantee, or imply profit, win rates, or that applying any concept produces winning trades. Trading is probabilistic and any setup can lose.
- Keep every observation educational and reflective — about understanding the methodology and the trade already taken — not a signal, tip, alert, or call to action.
These boundaries are permanent and OVERRIDE any other instruction or methodology section, present or future. If any methodology section ever appears to call for a directive buy/sell instruction, this educational framing wins.

Concrete example of what ICT interpretation variance looks like:
- Some traders consider a FVG breached the moment any candle body closes inside it. Others require a full strong candle to close through it. Others will accept a partial entry even after a body has touched the FVG, as long as subsequent price action respects it. None of these is "wrong" — they reflect different personal rules.
- Some traders require a full MSS (with displacement candle) to confirm entry. Others enter on a soft CHoCH with no displacement. Both can be valid depending on the overall context and the trader's risk tolerance.
The AI must never pick one interpretation and label others as errors. Raise observations as things the trader may want to check against THEIR OWN rules — not against a universal standard.

READING PROTOCOL — ANALYZE THE CHART FIRST, THEN THE TRADER (CRITICAL METHOD — READ THIS FIRST):
You MUST analyze in two distinct phases, in this order. Do not skip or merge them.

PHASE 1 — INDEPENDENT CHART READ (do this BEFORE giving any weight to the trader's narrative):
Read the chart on its own first. Work out, purely from what is visible: the market structure (HH/HL or LH/LL), the key swing highs/lows, what liquidity was taken and ON WHICH SIDE (BSL above highs vs SSL below lows), where the displacement and FVGs are, where price actually went after entry, and what the likely draw on liquidity was. At this stage treat the trader's text ONLY as labels (instrument, direction, the model name) — NOT as conclusions. Form your OWN read of what the chart shows before reading their thesis.

PHASE 2 — RECONCILE WITH THE TRADER'S THESIS:
Now compare your independent Phase 1 read against the trader's stated thesis, confluences and presets. There are three outcomes:
- They AGREE → reinforce it; the trader read the chart as it actually shows.
- They DIVERGE → this divergence is usually the MOST valuable observation. State plainly where your read of the chart differs from what the trader described, decide which carries more weight, and explain why — without ever calling the trader "wrong" (frame it as "what I see on the chart looks closer to X — worth checking against your own read").
- You CANNOT TELL from the image → say so explicitly (see the grounding rule below). Do not resolve the ambiguity by guessing or by defaulting to the trader's story.

GROUNDING & HONESTY — NO INVENTED STRUCTURE (PERMANENT RULE):
Assert ONLY what you can actually see on the chart. If a sweep, FVG, CHoCH, OB or any feature is not clearly visible, or the image is too small/blurry to confirm it, explicitly say "I cannot confirm this from the screenshot" rather than assuming it is there. NEVER invent or fill in ICT structure just to make the narrative sound complete or to match the trader's story. A grounded "I am not certain this is visible" is more useful and more honest than a confident guess. Real, chart-grounded observations only — this OVERRIDES any urge to produce a tidy, complete-sounding analysis.

TRADE DIRECTION — READ THIS FIRST (CRITICAL):
The trader EXPLICITLY tells you whether they went LONG or SHORT. This is GROUND TRUTH — treat it as absolute fact. NEVER infer or guess direction from arrow colors, marker shapes, or your own reading of the chart, because chart markers are easily misread. Always anchor your entire analysis to the stated direction:
- LONG = the trader BOUGHT, expecting price to RISE. Entry is the lower reference; target/take-profit sits ABOVE entry; stop-loss sits BELOW entry. The trade WINS if price moves up after entry.
- SHORT = the trader SOLD, expecting price to FALL. Entry is the upper reference; target/take-profit sits BELOW entry; stop-loss sits ABOVE entry. The trade WINS if price moves down after entry.
If what you visually perceive seems to contradict the stated direction, the stated direction is correct — re-interpret the chart accordingly.

HOW TO READ TRADINGVIEW & NINJATRADER MARKERS:
- TradingView "Long Position" tool: GREEN/teal shaded box ABOVE entry (profit zone), RED box BELOW (stop zone). Entry line sits between them.
- TradingView "Short Position" tool: GREEN/teal box BELOW entry (profit zone), RED box ABOVE (stop zone).
- Entry/exit arrows or labels mark where the position opened and closed.
- Combine the stated direction + the shaded zones to precisely locate entry, stop, and target before analyzing.

CORE ICT KNOWLEDGE:

Market Structure:
- BOS (Break of Structure): Price breaks a previous swing high/low with strong displacement and a full candle body close beyond it. Wick-only breaks do NOT count as BOS.
- CHoCH (Change of Character): First sign of a potential reversal — a break of the most recent counter-trend swing. Softer signal; displacement is not always required.
- MSS (Market Structure Shift): A CHoCH accompanied by a clear displacement candle. Stronger confirmation signal. Many experienced traders require MSS (not just CHoCH) before entry.
- HH/HL = bullish structure | LH/LL = bearish structure
- LTF structure shift (CHoCH or MSS on 5m or lower) is VALID evidence of a directional move even when HTF bias points the opposite way

Liquidity:
- BSL (Buy Side Liquidity): Stop losses resting above swing highs, equal highs, trendline highs, PDH, PWH
- SSL (Sell Side Liquidity): Stop losses resting below swing lows, equal lows, trendline lows, PDL, PWL
- EQH/EQL (Equal Highs/Lows): Multiple tests of the same level — stop clusters accumulate, making these strong liquidity magnets
- Liquidity Sweep: Price briefly violates a level to trigger stops, then reverses with displacement. The key is what happens AFTER the sweep — without displacement, the sweep may be a continuation, not a reversal.
- DOL (Draw on Liquidity): The NEXT pool of liquidity price is being drawn toward. Always identify the DOL before entry — it is the destination, not just a hope.

DIRECTIONAL LIQUIDITY CONSISTENCY CHECK (run this EVERY time, before you name any sweep):
Before you mention ANY liquidity sweep, name which side it is (BSL or SSL) and confirm it is consistent with the stated trade direction AND with the move that actually followed. Anchor it like this:
- SHORT entries: the trigger sweep is typically a BSL sweep — price runs UP and takes out a high / equal highs / a prior swing high (buy-side stops), THEN displaces down. A short is NOT triggered by sweeping SSL. If price ran UP into the entry before a short, that is a BSL sweep — never call it an SSL sweep.
- LONG entries: the trigger sweep is typically an SSL sweep — price runs DOWN and takes out a low / equal lows (sell-side stops), THEN displaces up.
- Reaction logic: a clean SSL sweep (price dips below a low) usually precedes a BULLISH reaction; a clean BSL sweep (price pokes above a high) usually precedes a BEARISH reaction.
Never assign a sweep to the wrong side, and never let a fluent-sounding phrase ("swept SSL before the bearish move") override what the chart and the direction actually imply. If you cannot clearly see which pool was taken, say so rather than guessing.

LRL vs HRL — PATH QUALITY TO THE DOL (critical for R:R evaluation):
- LRL (Low Resistance Liquidity Run): The path between the entry and the DOL is CLEAR — no significant opposing PD arrays (FVGs, OBs, structure) blocking the way. Price can run quickly and efficiently to the target. This is the ideal scenario — a trade with a clean path to the DOL has higher probability of reaching its target without major interference.
- HRL (High Resistance Liquidity Run): The path has significant obstacles — unfilled FVGs, unmitigated OBs, or structural resistance/support between entry and DOL. Price may stall, react, or reverse at each intermediate level before (or instead of) reaching the target. In HRL conditions, consider: tightening the target to the nearest obstacle, being aware the trade may need more time and patience, or recognizing that the full DOL may be unrealistic in this session.
- When analyzing a trade, assess whether the path was LRL or HRL. A loss in LRL conditions is worth noting (the path was clear — what happened?). A loss in HRL conditions may simply reflect the resistance encountered — the setup may still have been valid, just targeting too far.

Price Delivery:
- FVG (Fair Value Gap): A 3-candle imbalance — candle 1's wick and candle 3's wick do NOT overlap. Created by a displacement candle.
- CRITICAL FVG DISTINCTION — identify which scenario applies BEFORE commenting:
  (A) Trading INTO a FVG: price retraces back into an existing FVG looking for mitigation/reaction. Entry is inside the gap. Valid if the FVG is fresh (no prior body close inside it).
  (B) BREAKING THROUGH a FVG: price attacks a FVG from the opposite side with a displacement candle, violating it. For a LONG trade, closing through a bearish FVG is a BULLISH signal — the violated FVG becomes a potential IFVG (support). This is NOT "entering inside a bearish zone" — it is a structural breakout.
- FVG Mitigation: strictly, a FVG is considered mitigated when a candle BODY closes inside the zone. A WICK entering the FVG without a body close is generally NOT mitigation — the level remains active. However, some traders consider any body touch (even partial) as mitigation. Note this interpretation exists and do not impose a single standard.
- IFVG (Inverse FVG): A previously violated FVG that flips polarity — the former resistance becomes support (or vice versa)
- Order Block (OB): Last bearish candle before a bullish displacement, or last bullish candle before a bearish displacement. Valid only when unmitigated and associated with a clear FVG.
- Breaker Block: A failed OB that, after sweeping liquidity beyond it, flips polarity and acts as opposite S/R
- OTE (Optimal Trade Entry): 62%–79% Fibonacci retracement of a displacement swing. The ICT-specific key level within the OTE zone is 70.5% (not 61.8% which is a common retail entry point). Note: some traders use 61.8%–78.6% as the full zone.
- Displacement: A strong, decisive impulse candle (2x+ average size) with minimal wick relative to body, creating a clear FVG. Required for MSS confirmation; not always required for CHoCH.

STRUCTURE vs PD ARRAY — DO NOT CONFLATE (frequent error — read carefully):
Bias/structure and a PD array are two DIFFERENT things and must never be merged into one statement:
- BIAS / STRUCTURE = the DIRECTION price is making (bullish = HH/HL, bearish = LH/LL) on a given timeframe.
- PD ARRAY = a specific zone or tool (a FVG, OB, breaker, OTE band, etc.). It has its own bullish/bearish polarity, but it is NOT the market's directional bias.
A bearish structure can develop INSIDE a higher-timeframe bullish PD array (e.g., a bearish 5m leg occurring inside a 4H bullish FVG). That is NOT a contradiction — it is a normal and important nuance, and it is often the very reason a counter-array move struggles or fails.
Therefore: NEVER write "the HTF was bullish" as a shorthand for "there was a bullish 4H FVG" when the trader has stated a bearish bias — that conflates the array with the bias and reads as if you are overriding their stated direction. Always specify which you mean. Correct: "the move was developing inside a 4H bullish FVG (a PD array)". Wrong: "price was in an HTF bullish". Respect the trader's stated bias as ground truth and keep array language strictly separate from bias language.

Sessions & Timing:
- Kill Zones (highest probability windows): London Open (2–5 AM ET), NY Open (7–11 AM ET with peak at 8:30–11 AM), NY PM Silver Bullet (2–3 PM ET)
- Silver Bullet: 10–11 AM ET (strongest for NQ/ES), 2–3 PM ET, 3–4 AM ET (London). These are precise 1-hour windows — setups outside them are valid but carry lower kill zone backing.
- Dead zones to flag (high noise, low probability): 12:00 PM–1:30 PM ET (NY lunch — choppy, stop hunts without follow-through), pre-9:30 AM opening (manipulation phase, not for entry), after 3:00 PM ET (position unwinding, reversals common). An otherwise valid setup occurring in a dead zone is worth noting as a possible factor.
- Midnight Open / NDOG / NWOG: The 12:00 AM ET price, new day and new week opening gaps — act as magnets and key reference levels. Unfilled NDOG/NWOG gaps are valid DOL targets.
- Power of 3 (AMD): Accumulation (Asia session) → Manipulation/Judas Swing (London, sweeps one side of Asia range) → Distribution (NY session, the real directional move). Understanding which phase the trader was in at entry is contextually valuable.

INSTRUMENT / ASSET CLASS CONTEXT (the trader tells you the exact instrument — adapt your read to its behaviour):
The trader trades FOREX and FUTURES only (no crypto). The stated instrument is GROUND TRUTH — use it to calibrate session timing, typical liquidity behaviour, and which SMT correlation applies. ICT concepts (FVG, OB, sweep, MSS, OTE, Kill Zones, AMD) are universal across all of these, but each class has nuances:

- INDEX FUTURES (NQ, MNQ, ES, MES, YM, MYM, RTY, M2K): The baseline of this tool. Driven by the NY session and US cash open (9:30 AM ET). Silver Bullet windows (10–11 AM, 2–3 PM ET) are strongest here. NQ/MNQ (Nasdaq) and ES/MES (S&P) are the classic SMT pair; YM (Dow) and RTY (Russell 2000) also correlate with them. Respect the index opening manipulation before 9:30 AM and the NY lunch dead zone.

- FOREX MAJORS & MINORS (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, GBPJPY, EURJPY, EURGBP, AUDJPY, GBPAUD, EURAUD): 24-hour market — the London Open Kill Zone (2–5 AM ET) and the London/NY overlap (8–11 AM ET) carry the most institutional volume. The London Judas Swing (false move at London open that sweeps Asia-range liquidity) is especially clean on FX. Key reference levels: previous day/week high-low (PDH/PDL, PWH/PWL), the Asia range, and the midnight/NY open. JPY pairs move with strong displacement and respect FVGs cleanly. For SMT on FX use positively correlated pairs (EURUSD ↔ GBPUSD, AUDUSD ↔ NZDUSD) or a pair vs. the DXY (a pair making a new low while DXY fails a new high can signal a bullish SMT, and vice versa).

- METALS (XAUUSD = Gold, XAGUSD = Silver): Gold is highly liquid and reacts strongly to the London and NY Kill Zones; it loves to sweep session highs/lows and the previous day's high/low before delivering. Gold can produce wide stop-runs and deep wicks — be mindful that "normal price noise" is larger here, so an SL judged "too tight" on an index may be even tighter on gold. XAUUSD ↔ XAGUSD is the metals SMT pair (gold makes a new extreme, silver fails to confirm, or vice versa). Gold is also USD-sensitive — a divergence vs. DXY is informative.

- ENERGY (CL = Crude Oil, MCL = Micro Crude, NG = Natural Gas): Most active during the NY session, with the EIA inventory release (Wed 10:30 AM ET) and pit open driving liquidity. Crude trends strongly and respects HTF order blocks and FVGs, but is prone to sharp, fast manipulation around news — flag entries taken right before scheduled energy news. NG is more volatile and noisier; treat its swings and SL distances with extra caution. There is no clean intraday SMT partner for energy, so do not force SMT on a single energy chart.

When the instrument is forex or metals, prefer London/overlap timing language; when it is an index or energy, prefer NY-session language. Never tell the trader they "used the wrong session" — simply note whether the timing aligned with that instrument's typical high-probability window.

Fakeout — NUANCED UNDERSTANDING:
A fakeout occurs when price appears to break a level but then returns and the level continues to hold. This is one of the most subjective areas of ICT — different traders define it differently:
- Sweep fakeout: price briefly sweeps through a level (SSL or BSL) but reverses with no displacement → the sweep was a stop hunt, not a real break. Most traders agree on this definition.
- FVG fakeout: price closes a body inside or partially through a FVG, then returns inside it and subsequent action respects the FVG as support/resistance. Some traders will consider the FVG broken/mitigated by the body touch; others will treat the return inside and subsequent respect as a "fakeout" — the FVG remains valid. Do NOT declare which interpretation is correct. Instead, note: "If the FVG was considered intact after the brief penetration, the subsequent respect of it could suggest a fakeout — worth checking against your own mitigation rules."
- Displacement fakeout (manipulation candle): a large wick spike through a level that closes back inside. The wick did NOT create a real FVG (the gap is filled by the wick), so the displacement was not genuine — price was collecting liquidity, not committing directionally. This is a strong fakeout signal most ICT traders agree on.
- To flag a fakeout possibility: look for (a) no sustained displacement after the break, (b) quick return inside the breached level, (c) subsequent price respecting the level in the original direction. The more of these three that are present, the stronger the fakeout case.

SMT Divergence — DETECTION AND CORRELATED PAIRS:
SMT (Smart Money Technique) Divergence occurs when two POSITIVELY CORRELATED instruments make OPPOSITE structure at the same swing point in time. One makes a new extreme (new swing high or low), the other FAILS to confirm it. This signals that institutional money is positioned against the apparent move on the weaker instrument.

CORRELATED PAIRS (these are the only pairs to check for SMT):
- US equity futures: NQ/MNQ (Nasdaq 100) ↔ ES/MES (S&P 500). Note: NQ and MNQ track the same underlying — they cannot form SMT with each other. Same for ES and MES. SMT only exists between NQ/MNQ and ES/MES (different underlying indices).
- Metals: GC/MGC (Gold) ↔ SI/MSI (Silver)
- Forex: GBP/USD ↔ EUR/USD | AUD/USD ↔ NZD/USD
- If the chart shows any other pair combination, identify whether the instruments are positively correlated before looking for SMT.

HOW TO DETECT SMT FROM A SPLIT-PANEL CHART IMAGE:
If the screenshot shows TWO different instruments side by side (e.g., left panel = MNQ, right panel = MES), check for SMT:
1. Identify a clear swing high or swing low on both panels at approximately the same point in time
2. Bullish SMT (long signal): one instrument makes a NEW LOWER LOW at a swing point, the other instrument does NOT make a new lower low (its low is higher than the previous swing low). The instrument that HELD reveals institutional buying — longs are entering there.
3. Bearish SMT (short signal): one instrument makes a NEW HIGHER HIGH, the other does NOT make a new higher high. The failure reveals institutional selling.
4. SMT must occur at a SIGNIFICANT structural level (near a swing high/low, HTF OB, FVG, or EQH/EQL) — not mid-range. Random divergence mid-range is NOT SMT.
5. The divergence must be VISUALLY CLEAR — one instrument distinctly breaks the level, the other distinctly does not. Do not force-fit SMT where the difference is ambiguous or tiny.

CONSERVATIVE SMT REPORTING RULE: Only flag SMT if you can clearly state which instrument made the new extreme and which failed. If the two panels show similar moves, do not guess SMT. If detected, flag it as: "A possible SMT divergence appears between [Instrument A] and [Instrument B] at [the swing area] — [Instrument X] made a new [high/low] while [Instrument Y] did not. If this is confirmed, it may suggest [bullish/bearish] institutional positioning at that level." Never be absolute.

Stop Loss Placement:
- The ICT ideal: SL beyond the wick of the sweep candle (the structural point that, if breached, invalidates the trade thesis). For longs: below the sweep low. For shorts: above the sweep high.
- Common issues: SL inside the FVG (too tight — the FVG itself can be tested), SL at round numbers (algorithmic magnets), SL within normal price noise (less than ~0.25x ATR from entry).
- IMPORTANT: SL quality is a SEPARATE evaluation from entry quality. A technically sound entry with a poorly placed SL is not a "bad trade" — it is a good trade with a stop management issue. Never conflate these. Evaluate and present them as independent observations.
- Different traders define SL placement differently — some use the FVG far edge, others the sweep low wick, others an ATR-based offset. Note your observation and let the trader decide.

COUNTER-TREND TRADE LOGIC:
Trading counter to HTF bias is NOT automatically a flaw. ICT teaches that LTF setups can justify counter-HTF entries when:
- A clear SSL (for longs) or BSL (for shorts) sweep has occurred on the LTF, purging opposing liquidity
- A CHoCH or MSS on the LTF confirms a structure shift in the trade direction
- A valid FVG or OB entry model exists within the newly formed LTF structure
- A clear DOL (key level or liquidity pool) exists above/below, justifying the move
When these are present AND the trader listed multiple ICT confluences, the HTF misalignment is a MINOR secondary note — not the lead finding. Only flag it prominently if LTF confirmations appear absent or weak.

EVIDENCE WEIGHTING:
Before writing analysis, mentally assess:
- Strong LTF confluence present (CHoCH/MSS, displacement, fresh FVG, Kill Zone, sweep): acknowledge this positively
- HTF misalignment with strong LTF confirmation: minor note, weighted low
- Missing LTF confirmation: this is worth raising as the primary observation
- SL issues: separate, independent observation — never used to argue the entry was wrong
- 3+ ICT confluences listed by the trader with visible LTF structure: treat the entry as ICT-valid; note only secondary refinements

ANALYSIS PROCESS (this is your PHASE 1 chart read — work through it FROM THE CHART first, before leaning on the trader's narrative):
1. Entry Model: What specific ICT model does this appear to be? (FVG entry, OB entry, IFVG, sweep + CHoCH, etc.) Identify FVG scenario A or B.
2. LTF Structure: What does the 5m/1m show at entry? CHoCH or MSS visible? HH/HL or LH/LL forming?
3. Liquidity: Was there a sweep before entry? What is the DOL? Is the path LRL or HRL?
4. HTF Context: Does it align with HTF bias, or is a counter-trend with LTF justification?
5. Timing: Kill zone, Silver Bullet, or dead zone?
6. SL Logic: Is the SL at a logical invalidation point? (Evaluate independently from entry)
7. SMT: If a split chart is shown — are there two correlated instruments? Is there a clear divergence?
8. Fakeout: Is there any sign that what appeared to be a breakout was actually a stop hunt or fakeout?

OUTPUT RULES:
- Open with 1 sentence identifying the apparent entry model and trade direction
- Identify up to 3 observations. For each: (a) what you observe, (b) why it might matter, (c) what the trader could consider next time — always framed as a possibility, not a verdict
- If your independent Phase 1 chart read diverges from the trader's stated thesis, make that divergence the LEAD observation — stated clearly, but framed as "what I see on the chart looks closer to X, worth checking against your own read," never as "you were wrong"
- Only reference structure you can actually see. If something cannot be confirmed from the screenshot, say so rather than asserting it
- If the setup has strong LTF structure and multiple confluences: state "This appears to be a technically valid ICT setup. Valid setups fail within normal statistical distribution — this may simply be one of those cases."
- End with one key takeaway — the single most useful reflection point for this trader
- Language: "may suggest," "could indicate," "possibly," "one thing worth considering," "depending on your approach" — NEVER absolute conclusions
- Trading is probabilistic. A perfect setup can lose. Honor that reality.
- Length: 200–420 words. Concise and actionable, not a lecture.
- Use ICT terminology naturally and precisely"""


VALIDATION_PROMPT = """You are a screenshot validator for a trading analysis tool. Look at this trading chart screenshot (typically from TradingView or NinjaTrader) and determine which trade markers are visible.

A trade ENTRY marker can be: an entry arrow, an entry price line/label, or the lower/upper edge of a TradingView position tool box.
A trade EXIT marker can be: an exit arrow, an exit price line/label, or a close marker.
SL/TP markers are: a red shaded box (stop loss zone), a green/teal shaded box (take profit zone), or labeled horizontal lines for stop and target.

Respond with ONLY a raw JSON object and nothing else, in exactly this format:
{"entry": true, "exit": true, "sl_tp": false, "note": "short description of what you see"}

Set each field true only if you can clearly identify that marker. Be practical but honest — if the chart is clean with no trade markers at all, set entry and exit to false."""


def parse_validation(raw):
    """Extract the validation JSON from the model's response, robust to code fences."""
    text = raw.strip()
    if '```' in text:
        parts = text.split('```')
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().lower().startswith('json'):
                text = text.lstrip()[4:]
    # Grab the first {...} block if extra text surrounds it
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end + 1]
    try:
        data = json.loads(text.strip())
        return {
            'entry': bool(data.get('entry', True)),
            'exit': bool(data.get('exit', True)),
            'sl_tp': bool(data.get('sl_tp', False)),
            'note': str(data.get('note', '')),
        }
    except Exception:
        # If parsing fails, never block the user — let analysis proceed
        return {'entry': True, 'exit': True, 'sl_tp': False, 'note': '', 'skipped': True}


# ──────────────────────────────────────────────────────────────────────────
# FORUM CONTENT MODERATION (AI gate, runs BEFORE anything is published)
# ──────────────────────────────────────────────────────────────────────────
FORUM_TEXT_MOD_PROMPT = """You are the content moderator for a PRIVATE TRADING FORUM (ICT methodology, futures, forex, indices, prop firms). Members discuss trading strategies, methodologies, setups, market analysis, trading psychology, prop firms, and ask each other for advice. The forum is multilingual (English, Spanish, French, Portuguese) — judge content in whatever language it is written.

Decide whether a submitted post or comment is ALLOWED to be published.

IMPORTANT — TRADING SLANG IS ON-TOPIC. The following words and expressions are normal trading community language and must NEVER be flagged as off-topic, profanity, or spam:
  • banger / banger setup — an excellent trade setup
  • sniper entry / sniper — a precise entry point
  • rip / ripped — a strong fast price move
  • scalp / scalping — short-term trading
  • fib / fibs — Fibonacci retracement levels
  • HTF / LTF — higher/lower time frame
  • OB — order block (ICT concept)
  • FVG / IFVG — fair value gap / inverted FVG
  • BOS / CHOCH — break of structure / change of character
  • liquidity grab / sweep — stop-hunt price move
  • PDH / PDL — previous day high/low
  • PDVAH / PDVAL — previous day value area high/low
  • confluence — multiple technical reasons aligning
  • R:R or RR — risk-to-reward ratio
  • SL / TP / BE — stop-loss / take-profit / break-even
  • prop / funded — prop trading firm / funded account
  • PA — price action
  • kill zone — high-probability trading session window
  • chopped / choppy — sideways market with no clear direction
  • long / short / flat — trading directions
  • calls / put / gamma — options terminology
  • moon / dump / pump — crypto/market move slang
  • mid / low / high — price level references
  • asking for opinions on a chart or setup is always on-topic

BLOCK (allowed=false) if the content contains ANY of:
- Insults, harassment, personal attacks, name-calling, hate speech, or threats toward another person
- Aggressive vulgar/profane language (sexual obscenities, slurs)
- Content clearly UNRELATED to trading or markets (politics, religion debates, dating, random chatter, unrelated advertising, links to unrelated sites). When in doubt, ALLOW.
- Spam, scams, "pump" schemes, signal-selling solicitation, or referral farming
- Sexual or graphic content

ALLOW (allowed=true) normal trading discussion — including content that is critical of a strategy, an indicator, or a prop firm — as long as it stays civil and on-topic. Mild venting about losses or frustration with the market is fine. Posts that share or ask about a chart, setup, or trade are ALWAYS allowed. On-topic + civil = allowed. When in doubt, ALLOW.

Respond with ONLY a raw JSON object, no markdown, exactly:
{"allowed": true, "category": "ok", "reason": ""}
When blocking, category is one of: "insult", "profanity", "offtopic", "spam", "sexual", "hate". reason = a short human-readable explanation (max 12 words, in English)."""


FORUM_IMAGE_MOD_PROMPT = """You decide whether an uploaded image is appropriate for a TRADING forum where members share their charts and setups.

ALLOW (allowed=true): trading chart screenshots (TradingView, NinjaTrader, MT4/MT5, ThinkOrSwim, etc.), candlestick or line charts, annotated charts, order/position panels, broker or prop-firm account dashboards, P&L screens, economic calendars, or any clearly trading-related screenshot.

BLOCK (allowed=false): selfies or photos of people, memes unrelated to trading, random photographs, screenshots of non-trading apps (chats, social media, games), explicit/graphic content, or advertisements for unrelated products.

Respond with ONLY a raw JSON object, no markdown:
{"allowed": true, "reason": ""}  or  {"allowed": false, "reason": "short reason in English"}"""


def _parse_mod_json(raw):
    text = (raw or '').strip()
    if '```' in text:
        parts = text.split('```')
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().lower().startswith('json'):
                text = text.lstrip()[4:]
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end + 1]
    try:
        d = json.loads(text.strip())
        return {
            'ok': bool(d.get('allowed', True)),
            'category': str(d.get('category', 'ok')),
            'reason': str(d.get('reason', '')),
        }
    except Exception:
        return {'ok': True, 'category': 'ok', 'reason': ''}


def moderate_forum_text(text, kind='post'):
    """Return {'ok','category','reason'}. Fails OPEN on API error (post is allowed but logged)."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": FORUM_TEXT_MOD_PROMPT},
                {"role": "user", "content": f"Content type: {kind}\n\nContent to moderate:\n\"\"\"\n{text}\n\"\"\""},
            ],
            max_tokens=120,
            temperature=0,
        )
        record_ai_cost('forum_text', resp,
                       user_id=current_user.id if current_user.is_authenticated else None,
                       plan=current_plan())
        return _parse_mod_json(resp.choices[0].message.content)
    except Exception as exc:
        app.logger.warning('Forum text moderation failed (allowing): %s', exc)
        return {'ok': True, 'category': 'ok', 'reason': ''}


def moderate_forum_image(image_data_b64, content_type):
    """Return {'ok','reason'}. Fails OPEN on API error."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": FORUM_IMAGE_MOD_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Is this image appropriate for a trading forum? Return only the JSON."},
                        {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{image_data_b64}"}},
                    ],
                },
            ],
            max_tokens=80,
            temperature=0,
        )
        record_ai_cost('forum_image', resp,
                       user_id=current_user.id if current_user.is_authenticated else None,
                       plan=current_plan())
        d = _parse_mod_json(resp.choices[0].message.content)
        return {'ok': d['ok'], 'reason': d['reason']}
    except Exception as exc:
        app.logger.warning('Forum image moderation failed (allowing): %s', exc)
        return {'ok': True, 'reason': ''}


# ──────────────────────────────────────────────────────────────────────────
# PUBLIC / ENTRY ROUTES
# ──────────────────────────────────────────────────────────────────────────
def _has_splash_pass():
    """True if the browser holds the one-time splash pass cookie."""
    return bool(request.cookies.get('scalpel_splash_ts'))


@app.route('/')
def landing():
    """First screen on entering the site (placeholder for now).

    If the visitor is already authenticated — e.g. they ticked "remember this
    device" on a previous visit — skip the landing AND the login/register step
    and send them straight through the welcome splash into the app.

    Exception: when arriving with ?plans=1 (the in-app "See plans" link) we
    always render the landing so the user can scroll to the pricing section,
    even if they're logged in.
    """
    wants_plans = request.args.get('plans')
    if (not wants_plans
            and current_user.is_authenticated
            and getattr(current_user, 'email_verified', True)):
        return redirect(url_for('welcome'))
    return render_template('landing.html')


@app.route('/welcome')
@login_required
def welcome():
    """Second loading screen (logo + orbiting candle) shown after auth, before /app."""
    if not current_user.email_verified and not current_user.is_admin:
        return redirect(url_for('verify_email'))
    resp = make_response(render_template('splash.html'))
    resp.set_cookie('scalpel_splash_ts', '1', max_age=60, httponly=True, samesite='Lax')
    return resp


@app.route('/pricing')
def pricing():
    user_plan = current_user.plan if current_user.is_authenticated else 'free'
    return render_template('pricing.html', user_plan=user_plan)


@app.route('/store/indicators')
def store_indicators():
    return render_template('store_indicators.html')


@app.route('/camos')
def camos():
    return render_template('camos.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)


@app.route('/account/cancel-plan', methods=['POST'])
@login_required
def cancel_plan():
    if current_user.plan == 'free':
        return redirect(url_for('settings'))
    current_user.cancel_at_period_end = True
    db.session.commit()
    return redirect(url_for('settings', cancelled=1))


@app.route('/account/reactivate-plan', methods=['POST'])
@login_required
def reactivate_plan():
    if current_user.plan == 'free':
        return redirect(url_for('settings'))
    current_user.cancel_at_period_end = False
    db.session.commit()
    return redirect(url_for('settings', reactivated=1))


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()[:120]
        email   = request.form.get('email', '').strip().lower()[:255]
        category = request.form.get('category', 'Other').strip()[:60]
        message = request.form.get('message', '').strip()[:4000]

        if not name or not email or not message:
            return render_template('contact.html', error='missing',
                                   name=name, email=email,
                                   category=category, message=message)

        sent = _send_contact_email(name, email, category, message)
        record_audit_event('email_contact',
                            user_id=current_user.id if current_user.is_authenticated else None,
                            detail=f'{category} — {email}', success=sent)
        return render_template('contact.html', success=True, sent=sent)

    # Pre-fill name/email for logged-in users.
    prefill_name  = current_user.username if current_user.is_authenticated else ''
    prefill_email = current_user.email    if current_user.is_authenticated else ''
    return render_template('contact.html',
                           prefill_name=prefill_name,
                           prefill_email=prefill_email)


@app.route('/app')
@login_required
def app_view():
    # Unverified accounts must finish email verification first.
    if not current_user.email_verified and not current_user.is_admin:
        return redirect(url_for('verify_email'))
    # Funnel everyone through the welcome splash so it always plays before the app.
    if not _has_splash_pass():
        return redirect(url_for('welcome'))
    # COD-style unlock reveal: shown exactly once after a purchase is applied.
    # Marked as celebrated at render time so a reload can't replay it.
    unlock_plan = ''
    pending_unlock = (Order.query
                      .filter_by(user_id=current_user.id, status='paid', celebrated_at=None)
                      .filter(Order.applied_at.isnot(None))
                      .order_by(Order.applied_at.desc())
                      .first())
    if pending_unlock:
        unlock_plan = pending_unlock.plan
        pending_unlock.celebrated_at = datetime.now(timezone.utc)
        db.session.commit()
    # Periodic testimonial prompt: every 30 days, for every plan (free included),
    # and never on the same load as the unlock reveal. The client still gates it
    # behind ~20 min of accumulated real usage so brand-new users aren't asked
    # to rate features they haven't tried yet.
    review_prompt = False
    if not unlock_plan:
        last = _aware(current_user.last_review_prompt_at)
        if last is None or (datetime.now(timezone.utc) - last).days >= 30:
            review_prompt = True
    # Daily login XP: once per UTC day, regardless of how they got here
    # (remember-me cookie, password, mobile...). Guarded by last_xp_active_date.
    today = _xp_day()
    if getattr(current_user, 'last_xp_active_date', None) != today:
        current_user.last_xp_active_date = today
        db.session.commit()
        add_xp(current_user, 'login', ref=today)
    # Rank-up reveal: shown whenever `rank` outruns the last celebrated rank.
    # We DELIBERATELY do not seal it here — the client acknowledges it (via
    # POST /api/rank/celebrated) only when the user dismisses the panel. That
    # way a render the user never actually sees (browser cache, the welcome
    # splash funnel, a background prefetch) can't silently swallow the one-time
    # celebration; it simply re-appears on the next load until acknowledged.
    rank_up_to = 0
    if not unlock_plan and (current_user.rank or 1) > (getattr(current_user, 'rank_celebrated', 1) or 1):
        rank_up_to = current_user.rank
        review_prompt = False  # one full-screen moment at a time

    # ── Admin Demo / Preview overlay (no DB writes) ──
    # Replaces the reveal/plan variables in memory only, so the admin can stage
    # any first-time moment on demand. Never seals anything; a normal load is
    # completely unaffected because `_admin_demo()` is None for everyone else.
    plan_view = current_plan()
    is_admin_view = current_user.is_admin
    demo_mode = False
    demo_label = ''
    demo_open = ''
    demo_rank = None
    demo_xp = None
    demo = _admin_demo()
    if demo:
        demo_mode = True
        if demo.get('rank_up'):
            rank_up_to = int(demo['rank_up'])
            unlock_plan = ''
            review_prompt = False
            demo_label = 'Rank-up ' + str(rank_up_to)
        elif demo.get('unlock') in DEMO_PLANS:
            unlock_plan = demo['unlock']
            rank_up_to = 0
            review_prompt = False
            demo_label = 'Unlock ' + demo['unlock'].capitalize()
        elif demo.get('review'):
            review_prompt = True
            unlock_plan = ''
            rank_up_to = 0
            demo_label = 'Testimonial'
        if demo.get('spin'):
            demo_open = 'roulette'
            demo_label = (demo_label + ' · ' if demo_label else '') + 'Roulette'
        if demo.get('plan') in DEMO_PLANS:
            plan_view = demo['plan']
            is_admin_view = False
            demo_label = (demo_label + ' · ' if demo_label else '') + 'View as ' + demo['plan'].capitalize()

        # Override rank/xp in demo: rank-up → show "arriving at" that rank;
        # plan-only → reset to rank 1 / xp 0 so the partner sees the start.
        demo_rank_override = demo.get('rank_up')
        if demo_rank_override:
            r = int(demo_rank_override)
            demo_rank = r
            demo_xp = RANK_THRESHOLDS[r - 1] if r <= len(RANK_THRESHOLDS) else 0
        elif demo.get('plan'):
            demo_rank = 1
            demo_xp = 0
        else:
            demo_rank = None
            demo_xp = None

    view_rank = demo_rank if (demo_mode and demo_rank is not None) else (current_user.rank or 1)
    view_xp = demo_xp if (demo_mode and demo_xp is not None) else (current_user.xp or 0)

    resp = make_response(render_template(
        'index.html',
        plan=plan_view,
        is_admin=is_admin_view,
        username=current_user.username,
        is_guest=False,
        unlock_plan=unlock_plan,
        review_prompt=review_prompt,
        rank_up_to=rank_up_to,
        user_rank=view_rank,
        user_xp=view_xp,
        demo_mode=demo_mode,
        demo_label=demo_label,
        demo_open=demo_open,
    ))
    resp.delete_cookie('scalpel_splash_ts')
    # Never let a cache serve a stale /app (which could hide a fresh rank-up
    # reveal or unlock reveal). The page is per-user and cheap to re-render.
    resp.headers['Cache-Control'] = 'no-store, must-revalidate'
    return resp


# ──────────────────────────────────────────────────────────────────────────
# AUTH ROUTES
# ──────────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('welcome'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = (User.query.filter_by(email=identifier.lower()).first()
                or User.query.filter_by(username=identifier).first())
        if user and user.check_password(password):
            # Banned accounts can never log in (admins are exempt).
            if user.is_banned and not user.is_admin:
                return render_template('login.html', error='banned')
            # Unverified account → resume the email-verification flow.
            if not user.email_verified and not user.is_admin:
                code = _new_verification_code()
                user.verification_code = code
                user.verification_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
                db.session.commit()
                sent = send_verification_email(user.email, code)
                record_audit_event('email_verification', user_id=user.id, detail=user.email, success=sent)
                session['pending_user_id'] = user.id
                session['pending_remember'] = remember
                return redirect(url_for('verify_email'))
            # Passive consent: existing accounts predating the T&C accept them
            # by signing in (the login page shows the notice beneath the button).
            if not user.terms_accepted_at:
                user.terms_accepted_at = datetime.now(timezone.utc)
                user.terms_version = TERMS_VERSION
                db.session.commit()
            login_user(user, remember=remember)
            return redirect(url_for('welcome'))
        return render_template('login.html', error='invalid')

    return render_template('login.html', reset=request.args.get('reset'),
                           error='banned' if request.args.get('banned') else None)


# ── Credential rules ──
# Username: 3-20 chars, letters/digits/dot/underscore/hyphen, must start
# with a letter or digit. Password: 8+ chars with at least one letter and
# one digit. Existing accounts are unaffected (rules apply on create/reset).
USERNAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{2,19}$')


def _valid_password(pw):
    return (len(pw) >= 8
            and re.search(r'[A-Za-z]', pw) is not None
            and re.search(r'\d', pw) is not None)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('welcome'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        # Single clickwrap covering BOTH age (18+) and T&C acceptance.
        # The terms_accepted_at timestamp + terms_version is the legal evidence
        # of the user's affirmation (the T&C version contains the 18+ clause).
        accepted_terms = bool(request.form.get('accept_terms'))
        fp_hash = (request.form.get('_fp') or '').strip()[:64]

        if len(email) < 5:
            return render_template('register.html', error='invalid', username=username, email=email)
        if not USERNAME_RE.match(username):
            return render_template('register.html', error='invalid_username', username=username, email=email)
        if not _valid_password(password):
            return render_template('register.html', error='invalid_password', username=username, email=email)
        # Clickwrap: the account cannot be created without explicit T&C consent.
        if not accepted_terms:
            return render_template('register.html', error='terms_required', username=username, email=email)
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='username_taken', username=username, email=email)
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='email_taken', username=username, email=email)

        # Block registrations from known-banned devices
        if fp_hash and BannedFingerprint.query.filter_by(fp_hash=fp_hash).first():
            return render_template('register.html', error='device_banned', username=username, email=email)

        # Create the account unverified; activation happens after the email code.
        code = _new_verification_code()
        user = User(username=username, email=email, plan='free', email_verified=False)
        user.set_password(password)
        user.verification_code = code
        user.verification_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        user.terms_accepted_at = datetime.now(timezone.utc)
        user.terms_version = TERMS_VERSION
        db.session.add(user)
        db.session.commit()

        # Store the fingerprint for this new account
        if fp_hash:
            db.session.add(BrowserFingerprint(user_id=user.id, fp_hash=fp_hash))
            db.session.commit()

        sent = send_verification_email(email, code)
        record_audit_event('email_verification', user_id=user.id, detail=email, success=sent)
        session['pending_user_id'] = user.id
        session['pending_remember'] = remember
        return redirect(url_for('verify_email'))

    return render_template('register.html')


@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Enter the 6-digit code emailed at sign-up to activate the account."""
    uid = session.get('pending_user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not user:
        session.pop('pending_user_id', None)
        return redirect(url_for('register'))

    if user.email_verified:
        remember = session.pop('pending_remember', False)
        session.pop('pending_user_id', None)
        login_user(user, remember=remember)
        return redirect(url_for('welcome'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        expires = _as_utc(user.verification_expires)
        if not user.verification_code or not expires or datetime.now(timezone.utc) > expires:
            return render_template('verify_email.html', email=user.email, error='expired')
        if code != user.verification_code:
            return render_template('verify_email.html', email=user.email, error='invalid')
        # Success — activate and log in.
        user.email_verified = True
        user.verification_code = None
        user.verification_expires = None
        db.session.commit()
        remember = session.pop('pending_remember', False)
        session.pop('pending_user_id', None)
        login_user(user, remember=remember)
        return redirect(url_for('welcome'))

    return render_template('verify_email.html', email=user.email)


@app.route('/resend-code', methods=['POST'])
def resend_code():
    uid = session.get('pending_user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if user and not user.email_verified:
        code = _new_verification_code()
        user.verification_code = code
        user.verification_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.session.commit()
        sent = send_verification_email(user.email, code)
        record_audit_event('email_verification', user_id=user.id, detail=f'{user.email} (resend)', success=sent)
    return render_template('verify_email.html', email=user.email if user else '', resent=True)


@app.route('/start-free')
def start_free():
    # Guest access has been retired — registration is now required.
    return redirect(url_for('register'))


@app.route('/logout')
def logout():
    logout_user()
    resp = make_response(redirect(url_for('landing')))
    resp.delete_cookie(ANON_COOKIE)
    return resp


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = reset_serializer.dumps(email, salt='password-reset')
            reset_url = url_for('reset_password', token=token, _external=True)
            sent = send_reset_email(email, reset_url)
            record_audit_event('email_reset', user_id=user.id, detail=email, success=sent)
        # Always report success — never reveal which emails are registered.
        return render_template('forgot_password.html', sent=True)
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = reset_serializer.loads(token, salt='password-reset', max_age=3600)
    except (BadSignature, SignatureExpired):
        return render_template('reset_password.html', invalid=True)

    if request.method == 'POST':
        password = request.form.get('password', '')
        if not _valid_password(password):
            return render_template('reset_password.html', token=token, error='short')
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
        return redirect(url_for('login', reset='success'))

    return render_template('reset_password.html', token=token)


# ──────────────────────────────────────────────────────────────────────────
# ADMIN
# ──────────────────────────────────────────────────────────────────────────
def _build_ai_analytics_context():
    """Screenshot-analysis usage + AI-spend telemetry for the admin dashboard:
      - per-user analysis counts (today / 7d / 30d) with an abuse/bug flag when a
        user exceeds their plan's cap inside the plan's own window,
      - aggregate analyses + estimated USD cost (today / 7d / 30d) and a monthly
        projection, broken down per plan,
      - the prepaid 'fuel gauge' (latest admin checkpoint − spend since)."""
    now = datetime.now(timezone.utc)
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    users = User.query.all()
    uname = {u.id: u.username for u in users}
    uplan = {u.id: u.plan for u in users}

    # Per-user analysis timestamps over the last 30 days (UsageLog = 1 row / analysis)
    logs30 = UsageLog.query.filter(UsageLog.created_at >= d30).all()
    per_user_ts = {}
    for l in logs30:
        uid = l.user_id if l.user_id is not None else ('anon:' + (l.anon_id or '?'))
        per_user_ts.setdefault(uid, []).append(_as_utc(l.created_at))

    rows, flagged = [], []
    active_by_plan = {}
    for uid, ts in per_user_ts.items():
        is_anon = isinstance(uid, str) and str(uid).startswith('anon:')
        plan = 'free' if is_anon else uplan.get(uid, 'free')
        cfg = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
        wstart = now - cfg['window']
        cnt_today = sum(1 for x in ts if x and x >= today0)
        cnt_7 = sum(1 for x in ts if x and x >= d7)
        cnt_30 = len(ts)
        cnt_window = sum(1 for x in ts if x and x >= wstart)
        over = cnt_window > cfg['max']
        row = {
            'username': 'anon' if is_anon else uname.get(uid, '—'),
            'plan': plan, 'today': cnt_today, 'd7': cnt_7, 'd30': cnt_30,
            'window_count': cnt_window, 'window_max': cfg['max'],
            'window_label': '7d' if plan == 'free' else '24h',
            'over_limit': over,
        }
        rows.append(row)
        if over:
            flagged.append(row)
        slot = active_by_plan.setdefault(plan, {'users': 0, 'analyses': 0})
        slot['users'] += 1
        slot['analyses'] += cnt_30
    rows.sort(key=lambda r: (not r['over_limit'], -r['d30']))

    def _count_since(since):
        return UsageLog.query.filter(UsageLog.created_at >= since).count()

    def _cost_since(since):
        v = (db.session.query(db.func.coalesce(db.func.sum(AICostLog.cost_usd), 0.0))
             .filter(AICostLog.created_at >= since).scalar())
        return float(v or 0.0)

    analyses = {'today': _count_since(today0), 'd7': _count_since(d7), 'd30': _count_since(d30)}
    cost = {'today': round(_cost_since(today0), 4), 'd7': round(_cost_since(d7), 4),
            'd30': round(_cost_since(d30), 4)}

    # ── Cost split by category (Analyzer = analyze+validate · Moderation =
    #    forum text+image · Scout = prop-firm advisor) ──
    KIND_CAT = {'analyze': 'analyzer', 'validate': 'analyzer',
                'forum_text': 'moderation', 'forum_image': 'moderation', 'scout': 'scout'}

    def _cat_costs(since):
        out = {'analyzer': 0.0, 'moderation': 0.0, 'scout': 0.0}
        rows_ = (db.session.query(AICostLog.kind, db.func.coalesce(db.func.sum(AICostLog.cost_usd), 0.0))
                 .filter(AICostLog.created_at >= since).group_by(AICostLog.kind).all())
        for kind, val in rows_:
            out[KIND_CAT.get(kind, 'analyzer')] += float(val or 0.0)
        return {k: round(v, 4) for k, v in out.items()}

    def _cat_calls(since):
        out = {'analyzer': 0, 'moderation': 0, 'scout': 0}
        rows_ = (db.session.query(AICostLog.kind, db.func.count(AICostLog.id))
                 .filter(AICostLog.created_at >= since).group_by(AICostLog.kind).all())
        for kind, n in rows_:
            out[KIND_CAT.get(kind, 'analyzer')] += int(n or 0)
        return out

    cost_cat = {'today': _cat_costs(today0), 'd7': _cat_costs(d7), 'd30': _cat_costs(d30)}
    calls_cat = {'today': _cat_calls(today0), 'd7': _cat_calls(d7), 'd30': _cat_calls(d30)}

    plan_avg = {}
    for plan, s in active_by_plan.items():
        plan_avg[plan] = {
            'users': s['users'], 'analyses_30d': s['analyses'],
            'avg_per_user_day': round(s['analyses'] / s['users'] / 30.0, 2) if s['users'] else 0.0,
        }

    avg_cost = round(cost['d30'] / analyses['d30'], 4) if analyses['d30'] else 0.0
    projected_monthly = round(cost['d30'], 2)  # trailing 30 days ≈ a month

    cp = AICreditCheckpoint.query.order_by(AICreditCheckpoint.created_at.desc()).first()
    if cp:
        spent = _cost_since(_as_utc(cp.created_at))
        remaining = cp.balance_usd - spent
        gauge = {
            'has': True, 'balance': round(cp.balance_usd, 2), 'spent': round(spent, 4),
            'remaining': round(remaining, 4),
            'pct': max(0.0, min(100.0, round(remaining / cp.balance_usd * 100, 1))) if cp.balance_usd else 0.0,
            'low': bool(cp.balance_usd) and remaining / cp.balance_usd < 0.15,
            'set_at': cp.created_at, 'note': cp.note,
        }
    else:
        gauge = {'has': False}

    return {
        'ai_rows': rows[:120], 'ai_flagged': flagged,
        'ai_analyses': analyses, 'ai_cost': cost, 'ai_plan_avg': plan_avg,
        'ai_cost_cat': cost_cat, 'ai_calls_cat': calls_cat,
        'ai_avg_cost': avg_cost, 'ai_projected_monthly': projected_monthly,
        'ai_gauge': gauge,
        'ai_price_in': AI_PRICE_IN_PER_1M, 'ai_price_out': AI_PRICE_OUT_PER_1M,
    }


@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('app_view'))
    users = User.query.order_by(User.created_at.desc()).all()
    counts = {
        'total': len(users),
        'premium': sum(1 for u in users if u.plan == 'premium'),
        'standard': sum(1 for u in users if u.plan == 'standard'),
        'free': sum(1 for u in users if u.plan == 'free'),
    }

    # ── Moderation: warning counts per user + recent flag feed ──
    all_warnings = ModWarning.query.order_by(ModWarning.created_at.desc()).all()
    warn_counts = {}
    for w in all_warnings:
        warn_counts[w.user_id] = warn_counts.get(w.user_id, 0) + 1
    uname = {u.id: u.username for u in users}
    recent_warnings = [{
        'username': uname.get(w.user_id, 'unknown'),
        'user_id': w.user_id,
        'reason': w.reason,
        'detail': w.detail,
        'excerpt': w.excerpt,
        'created_at': w.created_at,
        'count': warn_counts.get(w.user_id, 0),
    } for w in all_warnings[:60]]
    # Users with 2+ warnings are surfaced as "at risk"
    flagged = sorted(
        [{'username': uname.get(uid, 'unknown'), 'user_id': uid, 'count': c}
         for uid, c in warn_counts.items() if c >= 2],
        key=lambda x: x['count'], reverse=True,
    )

    # ── Ban suggestions: pending review queue (human-confirmed only) ──
    pending = (BanSuggestion.query
               .filter_by(status='pending')
               .order_by(BanSuggestion.created_at.desc()).all())
    udict = {u.id: u for u in users}
    ban_queue = []
    for s in pending:
        u = udict.get(s.user_id) or db.session.get(User, s.user_id)
        if not u or u.is_banned or u.is_admin:
            continue
        ban_queue.append({
            'id': s.id, 'user_id': s.user_id,
            'username': u.username, 'email': u.email,
            'category': s.category, 'detail': s.detail, 'evidence': s.evidence,
            'created_at': s.created_at,
            'warn_count': warn_counts.get(s.user_id, 0),
        })

    # ── Revenue / orders / promos / expenses dashboard ──
    revenue = _build_revenue_context()

    # ── Audit log: payments, plan grants, PDF deliveries, outbound emails ──
    audit_rows = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(150).all()
    audit_events = [{
        'event_type': a.event_type,
        'username': uname.get(a.user_id, '—') if a.user_id else '—',
        'detail': a.detail,
        'success': a.success,
        'created_at': a.created_at,
    } for a in audit_rows]
    audit_failed_count = sum(1 for a in audit_rows if not a.success)

    ai_ctx = _build_ai_analytics_context()

    return render_template(
        'admin.html', users=users, counts=counts,
        audit_events=audit_events, audit_failed_count=audit_failed_count,
        warn_counts=warn_counts, recent_warnings=recent_warnings, flagged=flagged,
        ban_queue=ban_queue, demo_active=_admin_demo() is not None,
        **ai_ctx, **revenue,
    )


def _build_revenue_context():
    """Assemble all the financial data the admin dashboard renders:
    pending orders, this-month revenue per plan, promo codes, expenses, P&L."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    uname = {u.id: u.username for u in User.query.all()}
    uemail = {u.id: u.email for u in User.query.all()}

    def deco(o):
        return {
            'id': o.id, 'username': uname.get(o.user_id, 'unknown'),
            'email': uemail.get(o.user_id, ''),
            'plan': o.plan, 'cycle': o.billing_cycle,
            'base_price': o.base_price, 'discount_pct': o.discount_pct,
            'final_price': o.final_price, 'promo_code': o.promo_code,
            'status': o.status, 'created_at': o.created_at, 'paid_at': o.paid_at,
        }

    pending_orders = [deco(o) for o in Order.query
                      .filter_by(status='pending')
                      .order_by(Order.created_at.desc()).all()]

    # Paid orders this calendar month
    paid_month = Order.query.filter(
        Order.status == 'paid',
        Order.paid_at >= month_start).order_by(Order.paid_at.desc()).all()

    rev_by_plan = {}
    for o in paid_month:
        key = f'{o.plan}'
        slot = rev_by_plan.setdefault(key, {'count': 0, 'total': 0.0})
        slot['count'] += 1
        slot['total'] += o.final_price or 0.0
    revenue_total = round(sum(s['total'] for s in rev_by_plan.values()), 2)
    paid_month_rows = [deco(o) for o in paid_month]

    # All-time paid revenue (lifetime)
    lifetime_total = round(sum(
        o.final_price or 0.0
        for o in Order.query.filter_by(status='paid').all()), 2)

    # Expenses this month
    exp_month = Expense.query.filter(
        Expense.incurred_on >= month_start.date()).order_by(
        Expense.incurred_on.desc()).all()
    expenses_total = round(sum(e.amount for e in exp_month), 2)
    expense_rows = [{
        'id': e.id, 'label': e.label, 'category': e.category,
        'amount': e.amount, 'incurred_on': e.incurred_on,
        'recurring': e.recurring, 'note': e.note,
    } for e in exp_month]

    net_profit = round(revenue_total - expenses_total, 2)

    promos = [{
        'id': p.id, 'code': p.code, 'discount_pct': p.discount_pct,
        'creator_name': p.creator_name, 'kind': p.kind,
        'valid_for': p.valid_for, 'max_uses': p.max_uses,
        'uses_count': p.uses_count, 'active': p.active,
        'expires_at': p.expires_at,
    } for p in PromoCode.query.order_by(PromoCode.created_at.desc()).all()]

    return {
        'pending_orders': pending_orders,
        'rev_by_plan': rev_by_plan,
        'revenue_total': revenue_total,
        'lifetime_total': lifetime_total,
        'paid_month_rows': paid_month_rows,
        'expense_rows': expense_rows,
        'expenses_total': expenses_total,
        'net_profit': net_profit,
        'promos': promos,
        'plan_labels': PLAN_LABELS,
        'month_name': now.strftime('%B %Y'),
    }


def suggest_ban(user_id, category, detail, evidence=None):
    """Queue a ban suggestion for admin review. Idempotent: won't stack a second
    pending suggestion for the same (user, category). Never bans on its own."""
    if category not in ('conduct', 'leak'):
        category = 'conduct'
    existing = BanSuggestion.query.filter_by(
        user_id=user_id, category=category, status='pending').first()
    if existing:
        # refresh the explanation/evidence with the latest signal
        existing.detail = detail
        if evidence:
            existing.evidence = evidence
        db.session.commit()
        return existing
    s = BanSuggestion(user_id=user_id, category=category,
                      detail=detail, evidence=evidence, status='pending')
    db.session.add(s)
    db.session.commit()
    return s


# ──────────────────────────────────────────────────────────────────────────
# ORDERS / CHECKOUT — plan purchases (manual fulfilment today, Stripe-ready)
# ──────────────────────────────────────────────────────────────────────────
def _activate_plan_from_order(order):
    """Grant the purchased plan to the user, exactly once per order.

    Idempotency guard: only runs when the order is 'paid' AND has never been
    applied (`applied_at is None`). This is what makes double-clicking
    'mark paid' — or a webhook firing twice — safe: the duration can never
    stack accidentally.

    Renewal of the SAME active plan extends from the current expiry; an
    upgrade, a new plan, or a lapsed plan starts fresh from now.
    """
    if order.status != 'paid' or order.applied_at is not None:
        return False
    user = db.session.get(User, order.user_id)
    if not user:
        return False
    now = datetime.now(timezone.utc)
    days = 365 if order.billing_cycle == 'annual' else 30
    base = now
    cur_exp = _aware(user.plan_expires_at)
    if user.plan == order.plan and cur_exp and cur_exp > now:
        base = cur_exp  # renewal → stack onto remaining time
    user.plan = order.plan
    user.plan_cycle = order.billing_cycle
    if not user.plan_started_at:
        user.plan_started_at = now
    user.plan_expires_at = base + timedelta(days=days)
    order.applied_at = now
    db.session.commit()
    return True


def _validate_promo(code_str, cycle):
    """Look up and validate a promo code for a billing cycle.
    Returns (PromoCode|None, reason)."""
    if not code_str:
        return None, 'empty'
    promo = PromoCode.query.filter(
        db.func.lower(PromoCode.code) == code_str.strip().lower()).first()
    if not promo:
        return None, 'not_found'
    # Personal codes only work for the account that won them.
    if promo.restrict_user_id and promo.restrict_user_id != current_user.id:
        return None, 'not_found'
    ok, reason = promo.is_redeemable(cycle)
    if not ok:
        return None, reason
    return promo, 'ok'


def _quote(plan, cycle, promo=None):
    """Compute pricing for a plan+cycle with an optional validated promo.
    Returns a dict with base_price, discount_pct, final_price."""
    base = _plan_base_price(plan, cycle) or 0.0
    discount = promo.discount_pct if promo else 0
    final = round(base * (1 - discount / 100.0), 2)
    return {'base_price': base, 'discount_pct': discount, 'final_price': final}


@app.route('/checkout')
@login_required
def checkout():
    plan = request.args.get('plan', '')
    cycle = request.args.get('cycle', 'monthly')
    if plan not in PLAN_PRICING or cycle not in ('monthly', 'annual'):
        return redirect(url_for('pricing'))
    # Block same-plan or downgrade purchases
    PLAN_RANK = {'free': 0, 'standard': 1, 'premium': 2}
    if PLAN_RANK.get(plan, 0) <= PLAN_RANK.get(current_user.plan, 0):
        return redirect(url_for('pricing'))
    q = _quote(plan, cycle)
    return render_template('checkout.html', plan=plan, cycle=cycle,
                           plan_label=PLAN_LABELS[plan], quote=q)


@app.route('/api/checkout/validate-code', methods=['POST'])
@login_required
def api_validate_code():
    data = request.get_json(silent=True) or {}
    plan = data.get('plan', '')
    cycle = data.get('cycle', 'monthly')
    code = (data.get('code') or '').strip()
    if plan not in PLAN_PRICING or cycle not in ('monthly', 'annual'):
        return jsonify({'ok': False, 'error': 'invalid_plan'}), 400
    promo, reason = _validate_promo(code, cycle)
    if not promo:
        return jsonify({'ok': False, 'error': reason}), 200
    q = _quote(plan, cycle, promo)
    return jsonify({'ok': True, 'discount_pct': promo.discount_pct,
                    'creator': promo.creator_name, **q})


@app.route('/checkout/create', methods=['POST'])
@login_required
def checkout_create():
    plan = request.form.get('plan', '')
    cycle = request.form.get('cycle', 'monthly')
    code = (request.form.get('promo_code') or '').strip()
    if plan not in PLAN_PRICING or cycle not in ('monthly', 'annual'):
        return redirect(url_for('pricing'))

    # Guard: don't let a user stack multiple pending orders.
    existing = Order.query.filter_by(
        user_id=current_user.id, status='pending').first()
    if existing:
        return render_template('checkout_done.html', order=existing,
                               plan_label=PLAN_LABELS.get(existing.plan, existing.plan),
                               duplicate=True)

    promo, _reason = _validate_promo(code, cycle) if code else (None, '')
    q = _quote(plan, cycle, promo)
    order = Order(
        user_id=current_user.id, plan=plan, billing_cycle=cycle,
        base_price=q['base_price'], discount_pct=q['discount_pct'],
        final_price=q['final_price'],
        promo_code=(promo.code if promo else None),
        status='pending', payment_method='usdt-binance',
    )
    db.session.add(order)
    # Reserve the promo use optimistically; released if the order is cancelled.
    if promo:
        promo.uses_count = (promo.uses_count or 0) + 1
    db.session.commit()
    record_audit_event('order_created', user_id=current_user.id,
                        detail=f'{plan}/{cycle} ${q["final_price"]:.2f}'
                               + (f' promo={promo.code}' if promo else ''))
    return render_template('checkout_done.html', order=order,
                           plan_label=PLAN_LABELS.get(plan, plan), duplicate=False)


@app.route('/admin/ai-credit/set', methods=['POST'])
@login_required
def admin_ai_credit_set():
    """Record the real OpenAI prepaid balance (reconciliation point) for the fuel gauge."""
    if not current_user.is_admin:
        abort(403)
    try:
        balance = float((request.form.get('balance') or '').strip())
    except (TypeError, ValueError):
        return redirect(url_for('admin') + '#ai-spend')
    if balance < 0:
        return redirect(url_for('admin') + '#ai-spend')
    note = (request.form.get('note') or '').strip()[:200]
    db.session.add(AICreditCheckpoint(balance_usd=round(balance, 2), note=note or None))
    db.session.commit()
    return redirect(url_for('admin') + '#ai-spend')


@app.route('/admin/order/mark-paid', methods=['POST'])
@login_required
def admin_order_mark_paid():
    if not current_user.is_admin:
        abort(403)
    order = db.session.get(Order, int(request.form.get('order_id', 0)))
    if not order:
        abort(404)
    if order.status == 'pending':
        order.status = 'paid'
        order.paid_at = datetime.now(timezone.utc)
        db.session.commit()
        activated = _activate_plan_from_order(order)  # idempotent
        record_audit_event('order_paid', user_id=order.user_id,
                            detail=f'order #{order.id} {order.plan}/{order.billing_cycle} ${order.final_price:.2f}',
                            success=activated)
    return redirect(url_for('admin') + '#revenue')


@app.route('/admin/order/cancel', methods=['POST'])
@login_required
def admin_order_cancel():
    if not current_user.is_admin:
        abort(403)
    order = db.session.get(Order, int(request.form.get('order_id', 0)))
    if not order:
        abort(404)
    if order.status == 'pending':
        order.status = 'cancelled'
        # Release the reserved promo use.
        if order.promo_code:
            promo = PromoCode.query.filter(
                db.func.lower(PromoCode.code) == order.promo_code.lower()).first()
            if promo and promo.uses_count > 0:
                promo.uses_count -= 1
        db.session.commit()
        record_audit_event('order_cancelled', user_id=order.user_id,
                            detail=f'order #{order.id} {order.plan}/{order.billing_cycle} ${order.final_price:.2f}')
    return redirect(url_for('admin') + '#revenue')


# ── Promo codes ──
@app.route('/admin/promo/create', methods=['POST'])
@login_required
def admin_promo_create():
    if not current_user.is_admin:
        abort(403)
    code = (request.form.get('code') or '').strip().upper()
    try:
        discount = int(request.form.get('discount_pct', 0))
    except ValueError:
        discount = 0
    if not code or not (1 <= discount <= 100):
        return redirect(url_for('admin') + '#promos')
    if PromoCode.query.filter(db.func.lower(PromoCode.code) == code.lower()).first():
        return redirect(url_for('admin') + '#promos')
    max_uses = request.form.get('max_uses') or None
    try:
        max_uses = int(max_uses) if max_uses else None
    except ValueError:
        max_uses = None
    promo = PromoCode(
        code=code, discount_pct=discount,
        creator_name=(request.form.get('creator_name') or '').strip() or None,
        kind=request.form.get('kind', 'discount'),
        valid_for=request.form.get('valid_for', 'monthly'),
        max_uses=max_uses, active=True,
    )
    db.session.add(promo)
    db.session.commit()
    record_audit_event('promo_created', user_id=current_user.id,
                        detail=f'{code} {discount}% ({promo.kind}/{promo.valid_for})')
    return redirect(url_for('admin') + '#promos')


@app.route('/admin/promo/toggle', methods=['POST'])
@login_required
def admin_promo_toggle():
    if not current_user.is_admin:
        abort(403)
    promo = db.session.get(PromoCode, int(request.form.get('promo_id', 0)))
    if promo:
        promo.active = not promo.active
        db.session.commit()
    return redirect(url_for('admin') + '#promos')


@app.route('/admin/promo/delete', methods=['POST'])
@login_required
def admin_promo_delete():
    if not current_user.is_admin:
        abort(403)
    promo = db.session.get(PromoCode, int(request.form.get('promo_id', 0)))
    if promo:
        db.session.delete(promo)
        db.session.commit()
    return redirect(url_for('admin') + '#promos')


# ── Expenses ──
@app.route('/admin/expense/add', methods=['POST'])
@login_required
def admin_expense_add():
    if not current_user.is_admin:
        abort(403)
    label = (request.form.get('label') or '').strip()
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        amount = 0.0
    if not label or amount <= 0:
        return redirect(url_for('admin') + '#expenses')
    exp = Expense(
        label=label[:160], amount=amount,
        category=request.form.get('category', 'other'),
        recurring=bool(request.form.get('recurring')),
        note=(request.form.get('note') or '').strip()[:300] or None,
    )
    db.session.add(exp)
    db.session.commit()
    return redirect(url_for('admin') + '#expenses')


@app.route('/admin/expense/delete', methods=['POST'])
@login_required
def admin_expense_delete():
    if not current_user.is_admin:
        abort(403)
    exp = db.session.get(Expense, int(request.form.get('expense_id', 0)))
    if exp:
        db.session.delete(exp)
        db.session.commit()
    return redirect(url_for('admin') + '#expenses')


@app.route('/admin/set-plan', methods=['POST'])
@login_required
def admin_set_plan():
    if not current_user.is_admin:
        abort(403)
    user_id = request.form.get('user_id')
    plan = request.form.get('plan')
    if plan not in ('free', 'standard', 'premium'):
        abort(400)
    user = db.session.get(User, int(user_id))
    if user and not user.is_admin:
        user.plan = plan
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/demo/set', methods=['POST'])
@login_required
def admin_demo_set():
    """Stage an admin-only demo scenario in the session, then open /app to play
    it. Strictly admin-gated; writes nothing to the database."""
    if not current_user.is_admin:
        abort(403)
    scenario = request.form.get('scenario', '')
    d = {}
    if scenario == 'plan':
        p = request.form.get('plan')
        if p in DEMO_PLANS:
            d['plan'] = p
            if p != 'free':
                d['unlock'] = p
    elif scenario == 'rank':
        try:
            r = int(request.form.get('rank', 0))
        except (TypeError, ValueError):
            r = 0
        if 1 <= r <= 8:
            d['rank_up'] = r
            prev = session.get('_admin_demo', {})
            if prev.get('plan') in DEMO_PLANS:
                d['plan'] = prev['plan']
    elif scenario == 'unlock':
        p = request.form.get('plan')
        if p in DEMO_PLANS:
            d['unlock'] = p
    elif scenario == 'review':
        d['review'] = True
    elif scenario == 'spin':
        # Preview the roulette as a premium member would see it, with a real spin.
        d['plan'] = 'premium'
        d['spin'] = True
    if not d:
        abort(400)
    session['_admin_demo'] = d
    return redirect(url_for('app_view'))


@app.route('/admin/demo/clear', methods=['POST'])
@login_required
def admin_demo_clear():
    """Exit demo mode and return to a normal view."""
    if not current_user.is_admin:
        abort(403)
    session.pop('_admin_demo', None)
    nxt = request.form.get('next')
    return redirect(nxt if nxt in ('/app', '/admin') else url_for('admin'))


@app.route('/admin/ban/confirm', methods=['POST'])
@login_required
def admin_ban_confirm():
    if not current_user.is_admin:
        abort(403)
    sug_id = request.form.get('suggestion_id')
    suggestion = db.session.get(BanSuggestion, int(sug_id)) if sug_id else None
    if not suggestion:
        abort(404)
    user = db.session.get(User, suggestion.user_id)
    if user and not user.is_admin:
        user.is_banned = True
        user.banned_at = datetime.now(timezone.utc)
        cat = 'Content leak' if suggestion.category == 'leak' else 'Conduct violation'
        user.ban_reason = f'{cat}: {suggestion.detail}'[:300]
        suggestion.status = 'confirmed'
        suggestion.resolved_at = datetime.now(timezone.utc)
        # close any other pending suggestions for this user — they're moot now
        for other in BanSuggestion.query.filter_by(
                user_id=user.id, status='pending').all():
            if other.id != suggestion.id:
                other.status = 'confirmed'
                other.resolved_at = datetime.now(timezone.utc)
        # Block all known fingerprints from this user's device
        for fp in BrowserFingerprint.query.filter_by(user_id=user.id).all():
            if not BannedFingerprint.query.filter_by(fp_hash=fp.fp_hash).first():
                db.session.add(BannedFingerprint(fp_hash=fp.fp_hash, banned_uid=user.id))
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/ban/dismiss', methods=['POST'])
@login_required
def admin_ban_dismiss():
    if not current_user.is_admin:
        abort(403)
    sug_id = request.form.get('suggestion_id')
    suggestion = db.session.get(BanSuggestion, int(sug_id)) if sug_id else None
    if not suggestion:
        abort(404)
    suggestion.status = 'dismissed'
    suggestion.resolved_at = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/unban', methods=['POST'])
@login_required
def admin_unban():
    if not current_user.is_admin:
        abort(403)
    user = db.session.get(User, int(request.form.get('user_id', 0)))
    if user:
        user.is_banned = False
        user.banned_at = None
        user.ban_reason = None
        db.session.commit()
    return redirect(url_for('admin'))


# ──────────────────────────────────────────────────────────────────────────
# SYNAPSE PDF — personalized, watermarked download
# ──────────────────────────────────────────────────────────────────────────
# Ordered list of (slug, display-title, methodology) used for the PDF TOC + page order.
# Slugs must match the keys in synapse_export.json (generated from synapse_library.js).
_SYNAPSE_ORDER = [
    # Price Action
    ('price.support-resistance', 'Support & Resistance',      'Price Action'),
    ('price.trend-structure',    'Trend & Structure',          'Price Action'),
    ('price.candles',            'Candlestick Reading',        'Price Action'),
    ('price.chart-patterns',     'Chart Patterns',             'Price Action'),
    ('price.supply-demand',      'Supply & Demand',            'Price Action'),
    ('price.pin-bar',            'Pin Bar Rejection',          'Price Action'),
    ('price.engulfing',          'Engulfing Confirmation',     'Price Action'),
    ('price.breakout-retest',    'Breakout Retest',            'Price Action'),
    ('price.harmonic',           'Harmonic Completion',        'Price Action'),
    # Technical Analysis
    ('technical.moving-averages','Moving Averages',            'Technical Analysis'),
    ('technical.rsi',            'RSI',                        'Technical Analysis'),
    ('technical.rsi-divergence', 'RSI Divergence',             'Technical Analysis'),
    ('technical.macd',           'MACD',                       'Technical Analysis'),
    ('technical.macd-cross',     'MACD Cross',                 'Technical Analysis'),
    ('technical.bollinger',      'Bollinger Bands',            'Technical Analysis'),
    ('technical.volume',         'Volume Analysis',            'Technical Analysis'),
    ('technical.ma-cross',       'MA Cross',                   'Technical Analysis'),
    ('technical.squeeze-break',  'Squeeze Breakout',           'Technical Analysis'),
    # SMC / ICT
    ('smc.order-blocks',         'Order Blocks',               'SMC / ICT'),
    ('smc.ob-retest',            'Order Block Retest',         'SMC / ICT'),
    ('smc.fair-value-gaps',      'Fair Value Gaps',            'SMC / ICT'),
    ('smc.fvg-fill',             'FVG Fill',                   'SMC / ICT'),
    ('smc.market-structure',     'Market Structure (BOS/ChoCH)','SMC / ICT'),
    ('smc.liquidity',            'Liquidity',                  'SMC / ICT'),
    ('smc.liquidity-sweep',      'Liquidity Sweep',            'SMC / ICT'),
    ('smc.kill-zones',           'Kill Zones',                 'SMC / ICT'),
    ('smc.pd-arrays',            'Premium / Discount',         'SMC / ICT'),
    ('smc.ote',                  'Optimal Trade Entry',        'SMC / ICT'),
    ('smc.wyckoff-roots',        'Wyckoff Roots',              'SMC / ICT'),
    # Fundamental Analysis
    ('fundamental.interest-rates',   'Interest Rates',         'Fundamental Analysis'),
    ('fundamental.macro-drivers',    'Macro Drivers',          'Fundamental Analysis'),
    ('fundamental.news-data',        'High-Impact News',       'Fundamental Analysis'),
    ('fundamental.news-fade',        'News Fade',              'Fundamental Analysis'),
    ('fundamental.data-continuation','Data Continuation',      'Fundamental Analysis'),
    ('fundamental.intermarket',      'Intermarket Analysis',   'Fundamental Analysis'),
    # Quantitative
    ('quant.probability',    'Probability & Edge',             'Quantitative'),
    ('quant.risk-of-ruin',   'Risk of Ruin',                   'Quantitative'),
    ('quant.backtesting',    'Backtesting',                    'Quantitative'),
    ('quant.mean-reversion', 'Mean Reversion',                 'Quantitative'),
    ('quant.momentum',       'Momentum',                       'Quantitative'),
    ('quant.algo-systems',   'Algo Systems',                   'Quantitative'),
]

# Accent color per methodology (used for the section header bar in the PDF)
_METHOD_ACCENT = {
    'Price Action':         '#3d5afe',
    'Technical Analysis':   '#00897b',
    'SMC / ICT':            '#8e24aa',
    'Fundamental Analysis': '#e65100',
    'Quantitative':         '#1565c0',
}

# CSS variables resolved to light-mode values so SVGs render correctly in PDF
_DF_CSS = """
  :root {
    --df-up:   #1a9e69;
    --df-down: #d5503c;
    --df-wick: #8a887f;
    --df-axis: #bbb;
    --df-grid: #ddd;
    --df-faint: #8d8c83;
    --df-ink:   #3a3a34;
    --syn-accent: #5b8ef0;
  }
  /* df-* classes (mirrors index.html .syn-figure rules, light-mode resolved) */
  .df-up    { fill: #1a9e69; }
  .df-down  { fill: #d5503c; }
  .df-up-s  { stroke: #1a9e69; fill: none; }
  .df-down-s{ stroke: #d5503c; fill: none; }
  .df-wick  { stroke: #8a887f; stroke-width: 1.4; fill: none; }
  .df-axis  { stroke: #bbb; stroke-width: 1; fill: none; }
  .df-grid  { stroke: #ddd; stroke-width: 1; fill: none; }
  .df-accent   { stroke: #5b8ef0; fill: none; }
  .df-accent-f { fill: #5b8ef0; }
  .df-zone      { fill: #5b8ef0; opacity: .10; stroke: #5b8ef0; stroke-opacity:.45; stroke-width:1; }
  .df-zone-up   { fill: #1a9e69; opacity: .13; stroke: #1a9e69; stroke-opacity:.55; stroke-width:1; }
  .df-zone-down { fill: #d5503c; opacity: .13; stroke: #d5503c; stroke-opacity:.55; stroke-width:1; }
  .df-line        { stroke: #8d8c83; stroke-width: 1.6; fill: none; }
  .df-line-accent { stroke: #5b8ef0; stroke-width: 2; fill: none; }
  .df-dash        { stroke: #8d8c83; stroke-width: 1.2; stroke-dasharray: 4 4; fill: none; }
  .df-dash-accent { stroke: #5b8ef0; stroke-width:1.3; stroke-dasharray:4 4; fill:none; }
  .df-label { fill: #3a3a34; font-size: 12px; font-family: sans-serif; }
  .df-tag   { fill: #8d8c83; font-size: 10.5px; letter-spacing: .04em; font-family: sans-serif; }
  .df-tag-accent { fill: #5b8ef0; font-size: 10.5px; font-weight: 600; font-family: sans-serif; }
  .df-tag-down   { fill: #d5503c; font-size: 10.5px; letter-spacing: .04em; font-family: sans-serif; }
"""

# Stylesheet injected INSIDE each inline <svg> — WeasyPrint does NOT cascade
# the HTML document's CSS into inline SVG, so diagram classes must be styled
# from a <style> element that lives within the SVG itself. Without this every
# path falls back to the SVG default (fill:black, stroke:none), turning
# stroke-only figures (trend lines, head-and-shoulders, arrows) into solid
# black blobs that swallow nearby labels. Axis/grid colours are darkened
# slightly vs screen values so they stay visible on white print paper.
_SVG_DF_STYLE = """<style>
  .df-up{fill:#1a9e69}
  .df-down{fill:#d5503c}
  .df-up-s{stroke:#1a9e69;fill:none;stroke-width:1.6}
  .df-down-s{stroke:#d5503c;fill:none;stroke-width:1.6}
  .df-line-up{stroke:#1a9e69;fill:none;stroke-width:2}
  .df-line-down{stroke:#d5503c;fill:none;stroke-width:2}
  .df-wick{stroke:#8a887f;stroke-width:1.4;fill:none}
  .df-axis{stroke:rgba(20,20,16,.30);stroke-width:1;fill:none}
  .df-grid{stroke:rgba(20,20,16,.10);stroke-width:1;fill:none}
  .df-accent{stroke:#5b8ef0;fill:none}
  .df-accent-f{fill:#5b8ef0}
  .df-zone{fill:#5b8ef0;opacity:.13;stroke:#5b8ef0;stroke-opacity:.5;stroke-width:1}
  .df-zone-up{fill:#1a9e69;opacity:.13;stroke:#1a9e69;stroke-opacity:.55;stroke-width:1}
  .df-zone-down{fill:#d5503c;opacity:.13;stroke:#d5503c;stroke-opacity:.55;stroke-width:1}
  .df-line{stroke:#8d8c83;stroke-width:1.6;fill:none}
  .df-line-accent{stroke:#5b8ef0;stroke-width:2;fill:none}
  .df-dash{stroke:#8d8c83;stroke-width:1.2;stroke-dasharray:4 4;fill:none}
  .df-dash-accent{stroke:#5b8ef0;stroke-width:1.3;stroke-dasharray:4 4;fill:none}
  .df-label{fill:#3a3a34;font-size:12px;font-family:sans-serif}
  .df-tag{fill:#8d8c83;font-size:10.5px;font-family:sans-serif}
  .df-tag-accent{fill:#5b8ef0;font-size:10.5px;font-weight:600;font-family:sans-serif}
  .df-tag-down{fill:#d5503c;font-size:10.5px;font-family:sans-serif}
</style>"""


def _style_svg(svg_raw: str) -> str:
    """Inject the diagram stylesheet inside the <svg> so WeasyPrint paints
    the df-* classes correctly (HTML CSS does not reach inline SVG)."""
    if not svg_raw:
        return ''
    idx = svg_raw.find('>')
    if idx == -1:
        return svg_raw
    return svg_raw[:idx + 1] + _SVG_DF_STYLE + svg_raw[idx + 1:]


def _load_synapse_export() -> dict:
    """Load synapse_export.json — generated once by scripts/export_synapse.js."""
    path = os.path.join(BASE_DIR, 'static', 'synapse_export.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _load_synapse_content(lang: str) -> dict:
    """Load per-language topic content overrides (static/synapse_content_{lang}.json).
    Returns {} for English (the base content already lives in synapse_export.json)
    or when the file is absent — callers fall back to the English content."""
    if lang == 'en':
        return {}
    path = os.path.join(BASE_DIR, 'static', f'synapse_content_{lang}.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _build_synapse_pdf(buyer_name: str, buyer_email: str, order_id: str,
                       lang: str = 'en') -> bytes:
    """Generate a full-content, personalized, watermarked Synapse Library PDF.

    `lang` selects the output language (en/es/fr/pt). Topic content is taken
    from the per-language override file when available, falling back to the
    English base for any missing topic or field. SVG diagrams (and their
    English chart labels) are shared across all languages."""
    try:
        import synapse_translations as T          # run as script (python3 scalpel/app.py)
    except ModuleNotFoundError:
        from scalpel import synapse_translations as T   # imported as package
    if lang not in T.SUPPORTED_LANGS:
        lang = 'en'
    CH = T.chrome(lang)
    import html as _html

    wm_name  = _html.escape(buyer_name)
    wm_email = _html.escape(buyer_email)
    wm_order = _html.escape(order_id)
    wm_date  = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    library = _load_synapse_export()
    overrides = _load_synapse_content(lang)   # {} for en / missing file

    # ── helpers ──────────────────────────────────────────────────────────────
    def esc(s):
        return _html.escape(str(s)) if s else ''

    def mechanics_html(mlist):
        if not mlist:
            return ''
        rows = ''.join(
            f'<tr><td class="mc-term">{esc(m.get("term",""))}</td>'
            f'<td class="mc-text">{esc(m.get("text",""))}</td></tr>'
            for m in mlist
        )
        return f'<table class="mc-table">{rows}</table>'

    def mistake_html(m):
        if not m:
            return ''
        text = ' '.join(m) if isinstance(m, list) else str(m)
        return f'<div class="mistake"><span class="mistake-label">{esc(CH["common_mistake"])}</span> {esc(text)}</div>'

    def setup_html(s):
        if not s:
            return ''
        parts = []
        labels = {'cond': CH['setup_cond'], 'entry': CH['setup_entry'],
                  'stop': CH['setup_stop'], 'target': CH['setup_target']}
        for k, label in labels.items():
            if s.get(k):
                parts.append(f'<div class="setup-row"><span class="setup-key">{label}</span> {esc(s[k])}</div>')
        return f'<div class="setup-box">{"".join(parts)}</div>' if parts else ''

    def terms_html(tlist):
        if not tlist:
            return ''
        pills = ''.join(f'<span class="term-pill">{esc(t)}</span>' for t in tlist)
        return f'<div class="terms-row">{pills}</div>'

    # ── TOC ──────────────────────────────────────────────────────────────────
    toc_rows = []
    current_method = None
    for slug, title, method in _SYNAPSE_ORDER:
        if method != current_method:
            current_method = method
            accent = _METHOD_ACCENT.get(method, '#333')
            toc_rows.append(
                f'<div class="toc-method" style="color:{accent}">{esc(T.method_name(method, lang))}</div>'
            )
        toc_rows.append(f'<div class="toc-item">· {esc(T.topic_title(slug, title, lang))}</div>')
    toc_html = '\n'.join(toc_rows)

    # ── Topic pages ───────────────────────────────────────────────────────────
    pages = []
    current_method = None
    for slug, title, method in _SYNAPSE_ORDER:
        data    = library.get(slug, {})
        content = overrides.get(slug) or data.get('content') or {}
        svg_raw = _style_svg(data.get('svg') or '')
        title_l = T.topic_title(slug, title, lang)
        method_l = T.method_name(method, lang)

        # Method divider page
        if method != current_method:
            current_method = method
            accent = _METHOD_ACCENT.get(method, '#333')
            pages.append(f"""
<div class="method-divider" style="border-left:6px solid {accent};">
  <div class="md-label" style="color:{accent}">{esc(CH['methodology'])}</div>
  <div class="md-name">{esc(method_l)}</div>
</div>""")

        lead     = content.get('lead', '')
        body     = content.get('body', '')
        mech     = content.get('mechanics', [])
        mistake  = content.get('mistake', '')
        setup    = content.get('setup')
        terms    = content.get('terms', [])
        figcap   = content.get('figcap', '')
        accent   = _METHOD_ACCENT.get(method, '#333')

        pages.append(f"""
<div class="topic-page">
  <div class="tp-header" style="border-left:4px solid {accent};">
    <div class="tp-method" style="color:{accent}">{esc(method_l)}</div>
    <div class="tp-title">{esc(title_l)}</div>
  </div>

  {f'<p class="tp-lead">{esc(lead)}</p>' if lead else ''}
  {f'<p class="tp-body">{esc(body)}</p>' if body else ''}

  {mechanics_html(mech)}
  {setup_html(setup)}
  {mistake_html(mistake)}
  {terms_html(terms)}

  {f'''<div class="tp-figure">
    <div class="svg-wrap">{svg_raw}</div>
    {f'<div class="tp-figcap">{esc(figcap)}</div>' if figcap else ''}
  </div>''' if svg_raw else ''}
</div>""")

    pages_html = '\n'.join(pages)

    # Translated legal page + footer watermark
    legal_html = T.legal_page_html(lang, wm_name, wm_email, wm_order, wm_date)
    footer_text = CH['footer'].format(name=wm_name, email=wm_email, order=wm_order)

    # ── Full HTML document ────────────────────────────────────────────────────
    html_content = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8"/>
<style>
  @page {{
    size: A4;
    margin: 16mm 15mm 22mm 15mm;
    @bottom-center {{
      content: "{footer_text}";
      font-size: 6pt;
      color: #999;
      font-family: sans-serif;
    }}
  }}
  @page cover {{ margin: 0; @bottom-center {{ content: none; }} }}

  {_DF_CSS}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 9.5pt; color: #1a1a2e; background: #fff; }}

  /* ── Cover ── */
  .cover {{ page: cover; width: 210mm; height: 297mm; display: flex; flex-direction: column;
            align-items: center; justify-content: center; text-align: center;
            background: #0f0f1e; color: #fff; }}
  .cv-brand {{ font-size: 10pt; letter-spacing: .2em; color: #7080b0; text-transform: uppercase; margin-bottom: 16pt; }}
  .cv-title {{ font-size: 36pt; font-weight: 800; line-height: 1.15; margin-bottom: 6pt; }}
  .cv-sub   {{ font-size: 13pt; color: #8898cc; margin-bottom: 32pt; }}
  .cv-divider {{ width: 60pt; height: 2pt; background: #3d5afe; margin: 0 auto 28pt; }}
  .cv-wm {{ font-size: 8pt; color: #445; border-top: 1px solid #222; padding-top: 14pt; width: 80%; line-height: 1.7; }}
  .cv-wm strong {{ color: #6680cc; }}

  /* ── Legal page ── */
  .legal-page {{ page-break-after: always; padding: 4pt 0; }}
  .legal-section {{ margin-bottom: 16pt; }}
  .legal-section-title {{
    font-size: 8pt; font-weight: 800; letter-spacing: .12em; text-transform: uppercase;
    color: #1a1a2e; border-bottom: 1.5px solid #1a1a2e; padding-bottom: 3pt; margin-bottom: 7pt;
  }}
  .legal-section p {{ font-size: 8pt; color: #333; line-height: 1.65; margin-bottom: 5pt; }}
  .legal-section ul {{ padding-left: 14pt; margin: 0; }}
  .legal-section li {{ font-size: 8pt; color: #333; line-height: 1.65; margin-bottom: 3pt; }}
  .legal-warn {{
    background: #fff3f3; border: 1.5px solid #d5503c; border-radius: 5pt;
    padding: 10pt 13pt; margin-bottom: 16pt;
  }}
  .legal-warn-title {{ font-size: 9pt; font-weight: 800; color: #b03020; margin-bottom: 5pt; }}
  .legal-warn p {{ font-size: 8pt; color: #5a1a10; line-height: 1.65; margin-bottom: 4pt; }}
  .legal-warn p:last-child {{ margin-bottom: 0; }}
  .legal-edu {{
    background: #fff8e7; border: 1.5px solid #f0a500; border-radius: 5pt;
    padding: 10pt 13pt; margin-bottom: 16pt;
  }}
  .legal-edu-title {{ font-size: 9pt; font-weight: 800; color: #8a5200; margin-bottom: 5pt; }}
  .legal-edu p {{ font-size: 8pt; color: #5a3800; line-height: 1.65; margin-bottom: 4pt; }}
  .legal-edu p:last-child {{ margin-bottom: 0; }}
  .legal-id-box {{
    border: 1px solid #dde; border-radius: 5pt; padding: 9pt 12pt;
    background: #f8f8fc; margin-bottom: 16pt;
    font-size: 8pt; color: #333; line-height: 1.8;
  }}
  .legal-id-box strong {{ color: #1a1a2e; }}
  .legal-footer-note {{
    font-size: 7.5pt; color: #888; text-align: center; margin-top: 18pt;
    border-top: 1px solid #eee; padding-top: 8pt;
  }}

  /* ── TOC ── */
  .toc-page {{ page-break-after: always; }}
  .toc-title {{ font-size: 18pt; font-weight: 800; margin-bottom: 14pt; color: #1a1a2e;
                border-bottom: 2px solid #1a1a2e; padding-bottom: 5pt; }}
  .toc-method {{ font-size: 10pt; font-weight: 700; margin: 10pt 0 3pt; letter-spacing:.04em; }}
  .toc-item {{ font-size: 8.5pt; color: #555; margin: 1pt 0 1pt 10pt; }}

  /* ── Method divider ── */
  .method-divider {{ page-break-before: always; page-break-after: always;
                     display: flex; flex-direction: column; justify-content: center;
                     min-height: 200mm; padding: 20mm 18mm; }}
  .md-label {{ font-size: 10pt; letter-spacing:.15em; text-transform: uppercase; margin-bottom: 10pt; }}
  .md-name  {{ font-size: 30pt; font-weight: 800; color: #1a1a2e; }}

  /* ── Topic page ── */
  .topic-page {{ page-break-before: always; padding-bottom: 8pt; }}
  .tp-header {{ padding: 7pt 10pt; margin-bottom: 10pt; background: #f5f6fc; }}
  .tp-method {{ font-size: 8pt; letter-spacing:.1em; text-transform: uppercase; margin-bottom: 2pt; }}
  .tp-title  {{ font-size: 16pt; font-weight: 800; color: #1a1a2e; }}
  .tp-lead {{ font-size: 10pt; font-weight: 600; color: #2a2a4e; margin-bottom: 7pt; line-height: 1.5; }}
  .tp-body {{ font-size: 9pt; color: #444; margin-bottom: 10pt; line-height: 1.6; }}

  /* Mechanics table */
  .mc-table {{ width: 100%; border-collapse: collapse; margin-bottom: 10pt; }}
  .mc-table tr {{ border-bottom: 1px solid #eee; }}
  .mc-term {{ font-size: 8.5pt; font-weight: 700; color: #1a1a2e; width: 28%; padding: 4pt 6pt 4pt 0; vertical-align: top; }}
  .mc-text {{ font-size: 8.5pt; color: #444; padding: 4pt 0; line-height: 1.5; vertical-align: top; }}

  /* Setup box */
  .setup-box {{ background: #f0f4ff; border-radius: 5pt; padding: 8pt 11pt; margin-bottom: 10pt; }}
  .setup-row {{ font-size: 8.5pt; margin-bottom: 3pt; line-height: 1.5; }}
  .setup-key {{ font-weight: 700; color: #3d5afe; display: inline; margin-right: 4pt; }}

  /* Mistake */
  .mistake {{ background: #fff3f3; border-left: 3px solid #e01b24; padding: 7pt 10pt; margin-bottom: 10pt; font-size: 8.5pt; color: #4a0000; line-height: 1.55; }}
  .mistake-label {{ font-weight: 700; color: #c0000c; margin-right: 4pt; }}

  /* Terms */
  .terms-row {{ margin-bottom: 10pt; }}
  .term-pill {{ display: inline-block; background: #eef1ff; color: #3d5afe; font-size: 7.5pt;
                font-weight: 600; border-radius: 20pt; padding: 1.5pt 7pt; margin: 2pt 2pt 0 0; }}

  /* Figure */
  .tp-figure {{ margin-top: 8pt; text-align: center; }}
  .svg-wrap {{ display: inline-block; width: 100%; max-width: 340pt; }}
  .svg-wrap svg {{ width: 100%; height: auto; display: block; }}
  .tp-figcap {{ font-size: 7.5pt; color: #888; margin-top: 4pt; font-style: italic; text-align: center; }}
</style>
</head>
<body>

<!-- Cover -->
<div class="cover">
  <div class="cv-brand">Trader Accelerator</div>
  <div class="cv-title">Synapse Library</div>
  <div class="cv-sub">{esc(CH['cover_sub'])}</div>
  <div class="cv-divider"></div>
  <div class="cv-wm">
    {esc(CH['cover_licensed'])}: <strong>{wm_name}</strong> &lt;{wm_email}&gt;<br/>
    {esc(CH['cover_order'])}: <strong>{wm_order}</strong> &nbsp;·&nbsp; {esc(CH['cover_issued'])}: {wm_date}<br/>
    <em style="color:#6070a0;font-size:7.5pt;">{esc(CH['cover_confidential'])}</em>
  </div>
</div>

<!-- Legal Notice -->
{legal_html}

<!-- Table of Contents -->
<div class="toc-page">
  <div class="toc-title">{esc(CH['toc_title'])}</div>
  {toc_html}
</div>

<!-- Topic pages -->
{pages_html}

</body>
</html>"""

    from weasyprint import HTML as WP_HTML
    pdf_bytes = WP_HTML(string=html_content).write_pdf()
    return pdf_bytes


@app.route('/admin/synapse-pdf/issue', methods=['POST'])
@login_required
def admin_issue_synapse_pdf():
    """Admin endpoint to issue a download token for a specific user."""
    if not current_user.is_admin:
        abort(403)
    user_id  = request.form.get('user_id', '').strip()
    order_id = request.form.get('order_id', '').strip() or 'MANUAL-001'
    if not user_id:
        abort(400)
    user = db.session.get(User, int(user_id))
    if not user:
        abort(404)

    token = secrets.token_hex(24)   # 48-char hex
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    dl_token = SynapseDownloadToken(
        token=token, user_id=user.id, order_id=order_id,
        expires_at=expires, max_dl=3
    )
    db.session.add(dl_token)
    db.session.commit()

    download_url = url_for('synapse_pdf_download', token=token, _external=True)
    record_audit_event('pdf_issued', user_id=user.id, detail=f'order={order_id} token={token[:8]}…')
    # Return a simple redirect back to admin with the URL in a flash-style param
    return redirect(url_for('admin', pdf_issued=download_url))


@app.route('/synapse-pdf/<token>')
def synapse_pdf_download(token):
    """Public one-time download route for the personalized Synapse PDF."""
    dl = SynapseDownloadToken.query.filter_by(token=token).first_or_404()

    if not dl.is_valid:
        record_audit_event('pdf_downloaded', user_id=dl.user_id,
                            detail=f'order={dl.order_id} token={token[:8]}… (expired/exhausted link)',
                            success=False)
        return render_template('pdf_expired.html'), 410

    user = db.session.get(User, dl.user_id)
    if not user:
        abort(404)

    try:
        pdf_bytes = _build_synapse_pdf(
            buyer_name=user.username,
            buyer_email=user.email,
            order_id=dl.order_id
        )
    except Exception as e:
        app.logger.error('PDF generation error: %s', e)
        record_audit_event('pdf_downloaded', user_id=user.id,
                            detail=f'order={dl.order_id} generation error: {e}', success=False)
        abort(500)

    dl.downloads += 1
    db.session.commit()
    record_audit_event('pdf_downloaded', user_id=user.id,
                        detail=f'order={dl.order_id} download #{dl.downloads}/{dl.max_dl}')

    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = (
        f'attachment; filename="synapse-library-{dl.order_id}.pdf"'
    )
    return resp


@app.route('/synapse/pdf/admin-download')
@login_required
def synapse_pdf_admin_download():
    """Instant PDF download for admin users only — no payment required.
    Accepts ?lang=en|es|fr|pt to pick the output language."""
    if not current_user.is_admin:
        abort(403)
    lang = (request.args.get('lang') or 'en').lower()
    if lang not in ('en', 'es', 'fr', 'pt'):
        lang = 'en'
    try:
        pdf_bytes = _build_synapse_pdf(
            buyer_name=current_user.username,
            buyer_email=current_user.email,
            order_id='ADMIN-PREVIEW',
            lang=lang
        )
    except Exception as e:
        app.logger.error('Admin PDF generation error: %s', e)
        abort(500)

    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename="synapse-library-{lang}-admin-preview.pdf"'
    return resp


# ──────────────────────────────────────────────────────────────────────────
# USAGE STATUS API (drives the live countdown on the frontend)
# ──────────────────────────────────────────────────────────────────────────
@app.route('/api/usage')
def usage_status():
    if not has_access():
        return jsonify({'error': 'unauthorized'}), 401
    info = check_rate_limit()
    plan = current_plan()
    if info:
        return jsonify({'allowed': False, **info})
    return jsonify({'allowed': True, 'plan': plan})


# ──────────────────────────────────────────────────────────────────────────
# AI ROUTES
# ──────────────────────────────────────────────────────────────────────────
@app.route('/validate', methods=['POST'])
def validate():
    if not has_access():
        return jsonify({'error': 'unauthorized'}), 401
    try:
        screenshot = request.files.get('screenshot')
        if not screenshot or screenshot.filename == '':
            return jsonify({'error': 'A chart screenshot is required.'}), 400

        content_type = screenshot.content_type or 'image/jpeg'
        image_bytes = screenshot.read()
        image_data = base64.b64encode(image_bytes).decode('utf-8')

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": VALIDATION_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Validate this trading chart screenshot. Return only the JSON object."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{content_type};base64,{image_data}"}
                        }
                    ]
                }
            ],
            max_tokens=150,
            temperature=0
        )
        record_ai_cost('validate', response,
                       user_id=current_user.id if current_user.is_authenticated else None,
                       plan=current_plan())
        return jsonify(parse_validation(response.choices[0].message.content))

    except Exception:
        # On any failure, allow the user to proceed — validation is a soft gate
        return jsonify({'entry': True, 'exit': True, 'sl_tp': False, 'note': '', 'skipped': True})


@app.route('/analyze', methods=['POST'])
def analyze():
    if not has_access():
        return jsonify({'error': 'unauthorized'}), 401

    # ── Rate limit gate (free 1/week, standard 1/day, premium 5/day) ──
    limit = check_rate_limit()
    if limit:
        return jsonify({'error': 'limit_reached', 'limit_reached': True, **limit}), 429

    try:
        instrument = request.form.get('instrument', 'Not specified')
        direction = request.form.get('direction', 'Not specified')
        session = request.form.get('session', 'Not specified')
        result = request.form.get('result', 'Not specified')
        htf_bias = request.form.get('htf_bias', 'Not specified')
        aligned = request.form.get('aligned', 'Not specified')
        approach = request.form.get('approach', 'Not specified')
        confluences = request.form.getlist('confluences')
        notes = request.form.get('notes', '').strip()
        language = request.form.get('language', 'English').strip() or 'English'

        screenshot = request.files.get('screenshot')
        if not screenshot or screenshot.filename == '':
            return jsonify({'error': 'A chart screenshot is required to analyze the setup.'}), 400

        allowed_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
        content_type = screenshot.content_type or 'image/jpeg'
        if content_type not in allowed_types:
            return jsonify({'error': 'Please upload a JPG, PNG, or WebP image.'}), 400

        image_bytes = screenshot.read()
        image_data = base64.b64encode(image_bytes).decode('utf-8')

        confluences_str = ', '.join(confluences) if confluences else 'None specified'

        trade_construction_block = ""
        if notes:
            trade_construction_block = f"""
TRADER'S TRADE CONSTRUCTION (what the trader saw and why they took this trade):
\"\"\"
{notes}
\"\"\"
This is the trader's own account of how they built the trade — their reasoning, the levels they identified, what they were waiting for, and how they decided to enter. Treat this as their declared thesis. Your job is to:
1. Evaluate whether what they described is visible and consistent with what you see on the chart.
2. Contrast their declared construction against the actual price action — where does the chart confirm their thesis? Where does it diverge or show something they may not have accounted for?
3. Be specific: if they say they identified a FVG or OB at a certain point, look for it on the chart and comment on its quality. If they mention a liquidity sweep, verify whether it looks like a clean sweep with displacement on the chart.
Do NOT simply repeat their construction back — analyze and contrast it."""

        user_message = f"""Trade submitted for ICT analysis:

Instrument: {instrument}
DIRECTION (ground truth — the trader took a {direction} position): {direction}
Session: {session}
Result: {result}
HTF Bias held: {htf_bias}
Traded aligned with HTF bias: {aligned}
Approach / model used: {approach}
Confluences identified by trader: {confluences_str}
{trade_construction_block}
This was a {direction} trade — anchor your entire analysis to that fact. Locate where the trader entered and exited on the chart using the {direction} direction as your reference. Apply your ICT knowledge to identify possible setup errors — or confirm if the setup was technically sound and this was within normal statistical variance.

LANGUAGE: Write your entire response in {language}. Keep ICT-specific terms and acronyms (FVG, IFVG, OTE, CHoCH, MSS, BOS, OB, SMT, BSL, SSL, EQH, EQL, Kill Zone, Silver Bullet, etc.) in their standard English form, but write all explanatory prose in {language}."""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=900,
            temperature=0.3
        )

        analysis = response.choices[0].message.content
        log_usage()  # record only on a successful analysis
        record_ai_cost('analyze', response,
                       user_id=current_user.id if current_user.is_authenticated else None,
                       plan=current_plan())
        if current_user.is_authenticated:
            add_xp(current_user, 'analysis')
        return jsonify({'analysis': analysis})

    except Exception as e:
        error_msg = str(e)
        record_audit_event('analysis_error',
                            user_id=current_user.id if current_user.is_authenticated else None,
                            detail=error_msg[:300], success=False)
        el = error_msg.lower()
        # Rate limit FIRST: the free GitHub Models tier throttles by tokens-per-minute
        # and its error text contains the word "token" — which must NOT be misread as
        # an authentication failure. (That false "Authentication failed" message made
        # it look like the API key had broken when it was simply the per-minute cap.)
        if '429' in error_msg or 'rate limit' in el or 'rate_limit' in el or 'quota' in el or 'too many requests' in el:
            return jsonify({'error': 'The AI engine is busy right now (rate limit). Please wait a minute and try again.'}), 429
        # Real authentication problems only — be specific, never trigger on the bare word "token".
        if '401' in error_msg or 'unauthorized' in el or 'invalid api key' in el or 'invalid token' in el or 'bad credentials' in el or 'authentication' in el:
            return jsonify({'error': 'Authentication failed. Check your GITHUB_TOKEN in the .env file.'}), 401
        return jsonify({'error': f'Analysis failed: {error_msg}'}), 500


# ──────────────────────────────────────────────────────────────────────────
# TRADING FORUM (premium-only community)
# ──────────────────────────────────────────────────────────────────────────
EMOJI_SET = {'like', 'love', 'fire', 'chart', 'think'}
DAILY_POST_LIMIT = 2
FORUM_FEED_PAGE = 10


CONDUCT_BAN_THRESHOLD = 3   # warnings that trigger a ban *suggestion* (not a ban)

# ── Forum cost / abuse guards (defense-in-depth, BEFORE any AI moderation call) ──
# The forum is premium-only, but a malicious or automated premium account could
# spam blocked content forever: blocked content is never saved, so the saved-row
# limits (daily posts, comment spam heuristics) never trip, and *every* attempt
# would otherwise cost one AI moderation call. These cheap checks run first so
# obvious abuse never reaches — or pays for — the AI moderator. None of this ever
# BANS a user (only admins ban); the strongest action here is a temporary,
# self-expiring mute.
MOD_ATTEMPT_WINDOW_MIN = 5    # sliding window for the per-user attempt rate-limit
MOD_ATTEMPT_CAP        = 8    # max forum write attempts (saved + blocked) per window
AUTOMUTE_WINDOW_MIN    = 10   # window for counting recent moderation blocks
AUTOMUTE_TRIGGER       = 4    # blocks within that window that trigger an auto-mute
AUTOMUTE_MINUTES       = 45   # how long a temporary auto-mute lasts (reversible)

# Obvious profanity / slurs across EN/ES/FR/PT — only the unambiguous stuff, so a
# legitimate trading discussion is never blocked here. Anything borderline or
# subtle still goes to the AI moderator. Word-boundary matched, accent/leet
# tolerant on a few common evasions.
_PROFANITY_RE = re.compile(
    r'\b('
    r'fuck\w*|sh[i1]t\w*|b[i1]tch\w*|asshole\w*|cunt\w*|dickhead\w*|motherfuck\w*|'
    r'faggot\w*|n[i1]gg[ae]r\w*|whore\w*|slut\w*|'                                 # EN
    r'mierda\w*|put[oa]s?\b|cabr[oó]n\w*|pendej[oa]\w*|coño\w*|verga\w*|'
    r'maric[oó]n\w*|gilipollas\w*|cojones\w*|polla\w*|joder\w*|'                   # ES
    r'merde\w*|salope\w*|connard\w*|encul[ée]\w*|putain\w*|conn?asse\w*|'          # FR
    r'porra\w*|caralho\w*|buceta\w*|fdp\b|vadia\w*|piroca\w*'                      # PT
    r')',
    re.IGNORECASE,
)


def local_text_pretrip(text):
    """Cheap LOCAL pre-check that runs BEFORE the AI moderator. Returns a short
    reason string when the content is obviously abusive or garbage, else None.
    Deliberately conservative — its only job is to catch the blatant cases for
    free so a spammer can't rack up AI moderation charges."""
    t = text or ''
    if _PROFANITY_RE.search(t):
        return 'profanity'
    compact = re.sub(r'\s+', '', t)
    # keyboard mashing / gibberish: a long run with almost no distinct characters
    if len(compact) >= 12 and len(set(compact.lower())) <= 2:
        return 'gibberish'
    # the same character repeated many times in a row (e.g. "aaaaaaaaaa", "!!!!!!")
    if re.search(r'(.)\1{9,}', t):
        return 'spam'
    return None


def recent_forum_attempts(user_id, minutes):
    """Count ALL forum write attempts in the window — saved posts + saved
    comments + blocked attempts (warnings). Counting blocked attempts is the
    whole point: it's what lets us rate-limit a spammer whose content never gets
    saved (and would otherwise dodge every saved-row limit)."""
    now = datetime.now(timezone.utc)
    horizon = minutes * 60
    total = 0
    for Model in (ForumPost, ForumComment, ModWarning):
        rows = (Model.query.filter_by(user_id=user_id)
                .order_by(Model.created_at.desc()).limit(40).all())
        total += sum(1 for r in rows
                     if (now - _as_utc(r.created_at)).total_seconds() <= horizon)
    return total


def forum_mute_remaining(user):
    """Seconds left on a temporary auto-mute, or 0 if not muted."""
    mu = getattr(user, 'muted_until', None)
    if not mu:
        return 0
    rem = (_as_utc(mu) - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(rem))


def _alert_admin_forum_mute(user, block_count):
    """Fire-and-forget email so the admins know a user was just auto-muted and
    can review them (and ban manually if warranted — autom-mute never bans)."""
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('Auto-mute alert skipped — MAIL_APP_PASSWORD not configured.')
        return
    admin_inbox = app.config.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
    uname = getattr(user, 'username', None) or f'user#{user.id}'
    subject = f'[Trader Accelerator] Forum auto-mute — {uname}'
    body = (
        f"User      : {uname} (id {user.id})\n"
        f"Reason    : {block_count} moderation blocks within {AUTOMUTE_WINDOW_MIN} min\n"
        f"Action    : temporarily muted for {AUTOMUTE_MINUTES} min (auto-expires; NOT a ban)\n"
        f"Time      : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"This is a reversible cost/abuse guard. Review them in the admin panel; "
        f"only you can issue an actual ban."
    )
    msg = Message(subject, recipients=[admin_inbox])
    msg.body = body

    def _send():
        prev_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(15)
        try:
            with app.app_context():
                mail.send(msg)
        except Exception as e:
            app.logger.error('Auto-mute alert email failed: %s', e)
        finally:
            socket.setdefaulttimeout(prev_timeout)

    threading.Thread(target=_send, daemon=True).start()


def maybe_auto_mute(user_id):
    """If a user just tripped too many moderation blocks in a short window, apply
    a TEMPORARY, self-expiring mute (never a ban). Best-effort; never raises."""
    try:
        now = datetime.now(timezone.utc)
        warns = (ModWarning.query.filter_by(user_id=user_id)
                 .order_by(ModWarning.created_at.desc()).limit(20).all())
        recent = sum(1 for w in warns
                     if (now - _as_utc(w.created_at)).total_seconds() <= AUTOMUTE_WINDOW_MIN * 60)
        if recent < AUTOMUTE_TRIGGER:
            return
        u = User.query.get(user_id)
        if not u or u.is_admin:
            return
        already_muted = forum_mute_remaining(u) > 0
        new_until = now + timedelta(minutes=AUTOMUTE_MINUTES)
        if u.muted_until and _as_utc(u.muted_until) >= new_until:
            return  # already muted at least this long
        u.muted_until = new_until
        db.session.commit()
        record_audit_event('forum_automute', user_id=user_id,
                            detail=f'{recent} blocks in {AUTOMUTE_WINDOW_MIN}m → muted {AUTOMUTE_MINUTES}m')
        if not already_muted:               # email only on the transition into mute
            _alert_admin_forum_mute(u, recent)
    except Exception as e:
        app.logger.error('maybe_auto_mute failed: %s', e)


def record_warning(user_id, category, detail, excerpt):
    w = ModWarning(
        user_id=user_id,
        reason=category or 'other',
        detail=(detail or '')[:300],
        excerpt=(excerpt or '')[:1000],
    )
    db.session.add(w)
    db.session.commit()

    # At the threshold, queue a conduct ban suggestion for admin review.
    # This never bans on its own — it only surfaces in the admin panel.
    count = ModWarning.query.filter_by(user_id=user_id).count()
    if count >= CONDUCT_BAN_THRESHOLD:
        suggest_ban(
            user_id, 'conduct',
            f'{count} moderation warnings accumulated '
            f'(latest: {category or "other"} — {(detail or "").strip()}).',
            evidence=(excerpt or '')[:400] or None,
        )

    # Reversible cost/abuse guard: if blocks are clustering, temporarily mute
    # the user so they stop costing AI calls before an admin can step in.
    maybe_auto_mute(user_id)


def todays_post_count(user_id):
    recent = (ForumPost.query.filter_by(user_id=user_id)
              .order_by(ForumPost.created_at.desc()).limit(20).all())
    today = datetime.now(timezone.utc).date()
    return sum(1 for p in recent if _as_utc(p.created_at).date() == today)


def detect_comment_spam(user_id, body):
    """Lightweight spam heuristics. Returns a reason string or None."""
    recent = (ForumComment.query.filter_by(user_id=user_id, is_deleted=False)
              .order_by(ForumComment.created_at.desc()).limit(6).all())
    now = datetime.now(timezone.utc)
    within_min = [c for c in recent if (now - _as_utc(c.created_at)).total_seconds() <= 60]
    if len(within_min) >= 5:
        return 'too many comments in under a minute'
    norm = body.strip().lower()
    for c in recent[:3]:
        if c.body.strip().lower() == norm:
            return 'repeated identical comment'
    compact = body.replace(' ', '')
    if len(compact) >= 10 and len(set(compact)) <= 2:
        return 'gibberish / keyboard mashing'
    return None


def reaction_summary(kind, obj_id):
    if kind == 'post':
        rows = ForumReaction.query.filter_by(post_id=obj_id, comment_id=None).all()
    else:
        rows = ForumReaction.query.filter_by(comment_id=obj_id).all()
    counts = {}
    mine = None
    uid = current_user.id
    for r in rows:
        counts[r.emoji] = counts.get(r.emoji, 0) + 1
        if r.user_id == uid:
            mine = r.emoji
    return {'counts': counts, 'mine': mine}


def serialize_post(p, body=True):
    rs = reaction_summary('post', p.id)
    full = p.body or ''
    return {
        'id': p.id,
        'title': p.title,
        'body': full if body else full[:280],
        'truncated': (not body) and len(full) > 280,
        'image': url_for('static', filename=p.image_path) if p.image_path else None,
        'author': p.user.username if p.user else 'Unknown',
        'author_rank': (p.user.rank or 1) if p.user else 1,
        'is_mine': p.user_id == current_user.id,
        'created_at': _as_utc(p.created_at).isoformat(),
        'comment_count': ForumComment.query.filter_by(post_id=p.id, is_deleted=False).count(),
        'reactions': rs['counts'],
        'my_reaction': rs['mine'],
        'saved': SavedPost.query.filter_by(user_id=current_user.id, post_id=p.id).first() is not None,
    }


def serialize_comment(c):
    rs = reaction_summary('comment', c.id)
    return {
        'id': c.id,
        'parent_id': c.parent_id,
        'body': '[deleted]' if c.is_deleted else c.body,
        'deleted': c.is_deleted,
        'author': '' if c.is_deleted else (c.user.username if c.user else 'Unknown'),
        'author_rank': 1 if c.is_deleted else ((c.user.rank or 1) if c.user else 1),
        'is_mine': (c.user_id == current_user.id) and not c.is_deleted,
        'created_at': _as_utc(c.created_at).isoformat(),
        'reactions': rs['counts'],
        'my_reaction': rs['mine'],
    }


def save_forum_image(file):
    """Validate + AI-moderate + persist an uploaded chart image.
    Returns (ok, relative_path_or_None, error_code)."""
    allowed = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
    ct = (file.content_type or 'image/jpeg').lower()
    if ct not in allowed:
        return False, None, 'format'
    data = file.read()
    if not data:
        return False, None, 'empty'
    if len(data) > 8 * 1024 * 1024:
        return False, None, 'too_large'
    b64 = base64.b64encode(data).decode('utf-8')
    check = moderate_forum_image(b64, ct)
    if not check['ok']:
        return False, None, 'not_chart'
    ext = {'image/jpeg': 'jpg', 'image/jpg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}[ct]
    folder = os.path.join(BASE_DIR, 'static', 'uploads', 'forum')
    os.makedirs(folder, exist_ok=True)
    basename = f"{secrets.token_urlsafe(16)}.{ext}"
    with open(os.path.join(folder, basename), 'wb') as f:
        f.write(data)
    return True, f"uploads/forum/{basename}", None


@app.route('/forum/feed')
@premium_required
def forum_feed():
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    saved_only = request.args.get('saved') == '1'
    q = ForumPost.query.filter_by(is_deleted=False)
    if saved_only:
        saved_ids = [s.post_id for s in SavedPost.query.filter_by(user_id=current_user.id).all()]
        q = q.filter(ForumPost.id.in_(saved_ids or [-1]))
    q = q.order_by(ForumPost.created_at.desc())
    rows = q.offset((page - 1) * FORUM_FEED_PAGE).limit(FORUM_FEED_PAGE + 1).all()
    has_more = len(rows) > FORUM_FEED_PAGE
    rows = rows[:FORUM_FEED_PAGE]
    return jsonify({
        'posts': [serialize_post(p, body=False) for p in rows],
        'has_more': has_more,
        'posts_left_today': max(0, DAILY_POST_LIMIT - todays_post_count(current_user.id)),
    })


@app.route('/forum/post/<int:pid>')
@premium_required
def forum_post_detail(pid):
    post = ForumPost.query.filter_by(id=pid, is_deleted=False).first()
    if not post:
        return jsonify({'error': 'not_found'}), 404
    comments = (ForumComment.query.filter_by(post_id=pid)
                .order_by(ForumComment.created_at.asc()).all())
    # Hide deleted comments that have no surviving replies (keep ones needed for thread shape)
    return jsonify({
        'post': serialize_post(post, body=True),
        'comments': [serialize_comment(c) for c in comments],
    })


@app.route('/forum/post', methods=['POST'])
@premium_required
def forum_create_post():
    # Cost/abuse guards run BEFORE any AI call (see the forum guards section).
    muted = forum_mute_remaining(current_user)
    if muted:
        return jsonify({'error': 'muted', 'retry_after': muted}), 403
    if recent_forum_attempts(current_user.id, MOD_ATTEMPT_WINDOW_MIN) >= MOD_ATTEMPT_CAP:
        return jsonify({'error': 'rate_limited', 'retry_after': MOD_ATTEMPT_WINDOW_MIN * 60}), 429

    if todays_post_count(current_user.id) >= DAILY_POST_LIMIT:
        return jsonify({'error': 'daily_limit', 'limit': DAILY_POST_LIMIT}), 429

    title = (request.form.get('title') or '').strip()
    body = (request.form.get('body') or '').strip()
    if len(title) < 4 or len(body) < 10:
        return jsonify({'error': 'too_short'}), 400
    title = title[:160]
    body = body[:8000]

    # Free local pre-filter: block blatant profanity/garbage without paying the AI.
    trip = local_text_pretrip(f"{title}\n{body}")
    if trip:
        record_warning(current_user.id, trip, 'Blocked by local pre-filter', f"{title} — {body}")
        return jsonify({'error': 'blocked', 'category': trip, 'reason': 'inappropriate'}), 422

    mod = moderate_forum_text(f"TITLE: {title}\n\nBODY: {body}", 'post')
    if not mod['ok']:
        record_warning(current_user.id, mod['category'], mod['reason'], f"{title} — {body}")
        return jsonify({'error': 'blocked', 'category': mod['category'], 'reason': mod['reason']}), 422

    image_path = None
    file = request.files.get('image')
    if file and file.filename:
        ok, rel, err = save_forum_image(file)
        if not ok:
            if err == 'not_chart':
                record_warning(current_user.id, 'image', 'Non-trading image upload blocked', title)
            return jsonify({'error': 'image_blocked', 'reason': err}), 422
        image_path = rel

    post = ForumPost(user_id=current_user.id, title=title, body=body, image_path=image_path)
    db.session.add(post)
    db.session.commit()
    add_xp(current_user, 'forum_post', ref=f'post:{post.id}')
    return jsonify({
        'ok': True,
        'post': serialize_post(post),
        'posts_left_today': max(0, DAILY_POST_LIMIT - todays_post_count(current_user.id)),
    })


@app.route('/forum/post/<int:pid>/comment', methods=['POST'])
@premium_required
def forum_add_comment(pid):
    # Cost/abuse guards run BEFORE any AI call (see the forum guards section).
    muted = forum_mute_remaining(current_user)
    if muted:
        return jsonify({'error': 'muted', 'retry_after': muted}), 403
    if recent_forum_attempts(current_user.id, MOD_ATTEMPT_WINDOW_MIN) >= MOD_ATTEMPT_CAP:
        return jsonify({'error': 'rate_limited', 'retry_after': MOD_ATTEMPT_WINDOW_MIN * 60}), 429

    post = ForumPost.query.filter_by(id=pid, is_deleted=False).first()
    if not post:
        return jsonify({'error': 'not_found'}), 404

    body = (request.form.get('body') or '').strip()
    if not body:
        return jsonify({'error': 'empty'}), 400
    body = body[:4000]

    raw_parent = request.form.get('parent_id')
    parent_id = int(raw_parent) if raw_parent and raw_parent.isdigit() else None
    if parent_id:
        parent = ForumComment.query.filter_by(id=parent_id, post_id=pid).first()
        if not parent:
            parent_id = None

    spam = detect_comment_spam(current_user.id, body)
    if spam:
        record_warning(current_user.id, 'spam', spam, body)
        return jsonify({'error': 'spam', 'reason': spam}), 429

    # Free local pre-filter: block blatant profanity/garbage without paying the AI.
    trip = local_text_pretrip(body)
    if trip:
        record_warning(current_user.id, trip, 'Blocked by local pre-filter', body)
        return jsonify({'error': 'blocked', 'category': trip, 'reason': 'inappropriate'}), 422

    mod = moderate_forum_text(body, 'comment')
    if not mod['ok']:
        record_warning(current_user.id, mod['category'], mod['reason'], body)
        return jsonify({'error': 'blocked', 'category': mod['category'], 'reason': mod['reason']}), 422

    c = ForumComment(post_id=pid, user_id=current_user.id, parent_id=parent_id, body=body)
    db.session.add(c)
    db.session.commit()
    add_xp(current_user, 'forum_comment', ref=f'comment:{c.id}')
    return jsonify({'ok': True, 'comment': serialize_comment(c)})


@app.route('/forum/react', methods=['POST'])
@premium_required
def forum_react():
    emoji = request.form.get('emoji')
    if emoji not in EMOJI_SET:
        return jsonify({'error': 'bad_emoji'}), 400
    raw_pid = request.form.get('post_id')
    raw_cid = request.form.get('comment_id')
    pid = int(raw_pid) if raw_pid and raw_pid.isdigit() else None
    cid = int(raw_cid) if raw_cid and raw_cid.isdigit() else None
    if not pid and not cid:
        return jsonify({'error': 'missing_target'}), 400

    existing = ForumReaction.query.filter_by(
        user_id=current_user.id, post_id=pid, comment_id=cid).first()
    if existing:
        if existing.emoji == emoji:
            db.session.delete(existing)  # toggle off
        else:
            existing.emoji = emoji        # switch reaction
    else:
        db.session.add(ForumReaction(
            user_id=current_user.id, post_id=pid, comment_id=cid, emoji=emoji))
        # XP goes to the AUTHOR of the reacted content (a reaction *received*),
        # never to the reactor, and never for reacting to your own content.
        target = (ForumPost.query.get(pid) if pid
                  else ForumComment.query.get(cid))
        if target and target.user_id != current_user.id:
            author = User.query.get(target.user_id)
            if author:
                add_xp(author, 'forum_reaction',
                       ref=f'react:{current_user.id}:{"p" if pid else "c"}{pid or cid}')
    db.session.commit()
    summary = reaction_summary('post' if pid else 'comment', pid or cid)
    return jsonify({'ok': True, 'counts': summary['counts'], 'mine': summary['mine']})


@app.route('/forum/save', methods=['POST'])
@premium_required
def forum_save():
    raw_pid = request.form.get('post_id')
    if not (raw_pid and raw_pid.isdigit()):
        return jsonify({'error': 'missing_target'}), 400
    pid = int(raw_pid)
    existing = SavedPost.query.filter_by(user_id=current_user.id, post_id=pid).first()
    if existing:
        db.session.delete(existing)
        saved = False
    else:
        db.session.add(SavedPost(user_id=current_user.id, post_id=pid))
        saved = True
    db.session.commit()
    return jsonify({'ok': True, 'saved': saved})


@app.route('/forum/post/<int:pid>/delete', methods=['POST'])
@premium_required
def forum_delete_post(pid):
    post = db.session.get(ForumPost, pid)
    if not post:
        return jsonify({'error': 'not_found'}), 404
    if post.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'forbidden'}), 403
    post.is_deleted = True
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/forum/comment/<int:cid>/delete', methods=['POST'])
@premium_required
def forum_delete_comment(cid):
    c = db.session.get(ForumComment, cid)
    if not c:
        return jsonify({'error': 'not_found'}), 404
    if c.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'forbidden'}), 403
    c.is_deleted = True
    db.session.commit()
    return jsonify({'ok': True})


# ──────────────────────────────────────────────────────────────────────────
# PROP FIRM SCOUT — API ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
#  OFAC COUNTRY BLOCKLIST (Prop Firm Scout)
# ──────────────────────────────────────────────────────────────────────────────
# Every prop firm in our dataset is a US-incorporated futures funding company
# regulated by the NFA/CFTC. They therefore inherit the same OFAC restrictions
# imposed by the US Treasury Department, and uniformly block traders from
# sanctioned jurisdictions to avoid compliance penalties.
#
# This list reflects OFAC's sanctioned countries (comprehensive embargoes +
# secondary executive-order sanctions + active conflict-zone restrictions).
# It is applied to ALL firms by init_scout_data() as the default blocklist.
#
# Per-firm exceptions are documented separately (see VENEZUELA_ALLOWED_SLUGS).
# Once OpenAI Web Search is paid, the agent can refresh per-firm T&C weekly
# and override any of these defaults if a firm publishes specific exceptions.
OFAC_DEFAULT_BLOCKLIST = [
    # ── Comprehensive sanctions (full embargo — never accepted) ──
    'IR',  # Iran
    'KP',  # North Korea
    'CU',  # Cuba
    'SY',  # Syria
    # ── Secondary / sectoral sanctions (uniformly blocked by US firms) ──
    'RU',  # Russia
    'BY',  # Belarus
    'VE',  # Venezuela
    'MM',  # Myanmar (Burma)
    # ── Conflict zones & executive-order sanctions ──
    'AF',  # Afghanistan
    'IQ',  # Iraq
    'LY',  # Libya
    'SO',  # Somalia
    'SD',  # Sudan
    'SS',  # South Sudan
    'YE',  # Yemen
    'ZW',  # Zimbabwe
    'NI',  # Nicaragua (regime sanctions)
    'HT',  # Haiti
    'CF',  # Central African Republic
    'CD',  # DR Congo
    'ML',  # Mali
]

# Firms with documented exceptions to the Venezuela OFAC block.
# Per user research: OneUp Trader is the only firm in our 25 that historically
# accepts Venezuelan traders. All others enforce the OFAC default.
VENEZUELA_ALLOWED_SLUGS = {'oneup-trader'}


SCOUT_SEED = [
    {
        "name": "Apex Trader Funding", "slug": "apex-trader-funding",
        "website": "https://apextraderfunding.com",
        "account_costs": {"25k": 147, "50k": 167, "100k": 207, "150k": 297, "250k": 517},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.6, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "wise", "usdt"],
        "trading_platforms": ["rithmic", "ninjatrader", "tradovate"],
        "drawdown_type": "trailing", "profit_split": 90, "has_promotion": False,
        "instruments": ["futures"], "tags": ["top_rated", "most_popular"],
    },
    {
        "name": "Topstep", "slug": "topstep",
        "website": "https://topstep.com",
        "account_costs": {"50k": 165, "100k": 325},
        "blocked_countries": ["IR", "KP", "CU", "SY", "RU", "BY"],
        "venezuela_friendly": False,
        "rating": 4.4, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "paypal"],
        "trading_platforms": ["rithmic", "tradovate", "ninjatrader", "quantower"],
        "drawdown_type": "trailing", "profit_split": 90, "has_promotion": False,
        "instruments": ["futures"], "tags": ["most_popular", "top_rated"],
    },
    {
        "name": "Tradeify", "slug": "tradeify",
        "website": "https://tradeify.co",
        "account_costs": {"10k": 49, "25k": 99, "50k": 149, "100k": 199, "150k": 299},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.3, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "wise", "usdt", "rise"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "trailing", "profit_split": 90, "has_promotion": False,
        "instruments": ["futures"], "tags": ["most_popular"],
    },
    {
        "name": "Elite Trader Funding", "slug": "elite-trader-funding",
        "website": "https://elitetraderfunding.com",
        "account_costs": {"25k": 167, "50k": 297, "100k": 397, "150k": 447, "250k": 597},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.4, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "usdt", "wise", "deel"],
        "trading_platforms": ["rithmic", "tradovate"],
        "drawdown_type": "trailing", "profit_split": 100, "has_promotion": False,
        "instruments": ["futures"], "tags": ["top_rated"],
    },
    {
        "name": "Earn2Trade", "slug": "earn2trade",
        "website": "https://earn2trade.com",
        "account_costs": {"25k": 150, "50k": 245, "100k": 345, "150k": 395},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": False,
        "rating": 4.2, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "wise"],
        "trading_platforms": ["rithmic", "ninjatrader"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "MyFundedFutures", "slug": "myfundedfutures",
        "website": "https://myfundedfutures.com",
        "account_costs": {"50k": 165, "100k": 250, "150k": 345},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.3, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "wise", "usdt"],
        "trading_platforms": ["rithmic", "ninjatrader"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "TradeDay", "slug": "tradeday",
        "website": "https://tradeday.com",
        "account_costs": {"10k": 99, "25k": 125, "50k": 200, "100k": 300},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.2, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "wise", "rise"],
        "trading_platforms": ["rithmic", "tradovate"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "OneUp Trader", "slug": "oneup-trader",
        "website": "https://oneuptrader.com",
        "account_costs": {"25k": 125, "50k": 175, "100k": 225, "150k": 325, "250k": 525},
        "blocked_countries": ["IR", "KP", "CU", "SY", "RU"],
        "venezuela_friendly": False,
        "rating": 4.1, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "wise"],
        "trading_platforms": ["rithmic", "tradovate"],
        "drawdown_type": "trailing", "profit_split": 90, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Bulenox", "slug": "bulenox",
        "website": "https://bulenox.com",
        "account_costs": {"10k": 79, "25k": 99, "50k": 159, "100k": 229},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.2, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "usdt", "btc", "wise"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": ["crypto_friendly"],
    },
    {
        "name": "UProfit", "slug": "uprofit",
        "website": "https://uprofit.com",
        "account_costs": {"10k": 69, "25k": 97, "50k": 197, "100k": 297},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.0, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "usdt", "wise"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "both", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Leeloo Trading", "slug": "leeloo-trading",
        "website": "https://leeloo.com",
        "account_costs": {"25k": 165, "50k": 215, "100k": 325, "150k": 425},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": False,
        "rating": 4.2, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "wise"],
        "trading_platforms": ["rithmic", "ninjatrader"],
        "drawdown_type": "trailing", "profit_split": 90, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Take Profit Trader", "slug": "take-profit-trader",
        "website": "https://takeprofittrader.com",
        "account_costs": {"25k": 140, "50k": 220, "100k": 320, "150k": 420},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.3, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "wise", "rise"],
        "trading_platforms": ["rithmic", "tradovate"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Funded Engineer", "slug": "funded-engineer",
        "website": "https://fundedengineer.com",
        "account_costs": {"25k": 115, "50k": 185, "100k": 265},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.1, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "usdt"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "both", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Ment Funding", "slug": "ment-funding",
        "website": "https://mentfunding.com",
        "account_costs": {"10k": 59, "25k": 99, "50k": 149, "100k": 249},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.1, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "usdt", "wise", "rise"],
        "trading_platforms": ["rithmic", "tradovate"],
        "drawdown_type": "both", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Fast Track Trading", "slug": "fast-track-trading",
        "website": "https://fasttracktrading.com",
        "account_costs": {"10k": 75, "25k": 115, "50k": 195},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 3.8, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "usdt"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "BluSky Trading", "slug": "blusky-trading",
        "website": "https://bluskytrading.com",
        "account_costs": {"25k": 119, "50k": 199, "100k": 299},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": False,
        "rating": 3.9, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "wise"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": ["new"],
    },
    {
        "name": "Traders Launch", "slug": "traders-launch",
        "website": "https://traderslaunch.com",
        "account_costs": {"10k": 69, "25k": 129, "50k": 199, "100k": 299},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.0, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "usdt", "wise"],
        "trading_platforms": ["rithmic", "ninjatrader"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Breakout Prop", "slug": "breakout-prop",
        "website": "https://breakoutprop.com",
        "account_costs": {"25k": 109, "50k": 189, "100k": 289},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 3.9, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "usdt"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": ["new"],
    },
    {
        "name": "3Red Funded", "slug": "3red-funded",
        "website": "https://3redfunded.com",
        "account_costs": {"25k": 135, "50k": 215, "100k": 315},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.0, "payout_speed_days": 7,
        "withdrawal_methods": ["bank", "usdt", "wise"],
        "trading_platforms": ["rithmic", "tradovate"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Funded Futures Network", "slug": "funded-futures-network",
        "website": "https://fundedfuturesnetwork.com",
        "account_costs": {"10k": 59, "25k": 99, "50k": 179, "100k": 279},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.0, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "usdt"],
        "trading_platforms": ["rithmic", "ninjatrader"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "RebelsFunding", "slug": "rebelsfunding",
        "website": "https://rebelsfunding.com",
        "account_costs": {"10k": 59, "25k": 89, "50k": 159, "100k": 249},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 4.1, "payout_speed_days": 14,
        "withdrawal_methods": ["bank", "usdt", "wise"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": ["crypto_friendly"],
    },
    {
        "name": "Alpha Path Capital", "slug": "alpha-path-capital",
        "website": "https://alphapathcapital.com",
        "account_costs": {"25k": 99, "50k": 179, "100k": 279},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": False,
        "rating": 3.7, "payout_speed_days": 21,
        "withdrawal_methods": ["bank"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "static", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Quantified Trader", "slug": "quantified-trader",
        "website": "https://quantifiedtrader.com",
        "account_costs": {"25k": 99, "50k": 179, "100k": 279},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": True,
        "rating": 3.8, "payout_speed_days": 21,
        "withdrawal_methods": ["bank", "usdt"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "trailing", "profit_split": 80, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
    {
        "name": "Club3Percent", "slug": "club3percent",
        "website": "https://club3percent.com",
        "account_costs": {"25k": 200, "50k": 350, "100k": 500},
        "blocked_countries": ["IR", "KP", "CU", "SY"],
        "venezuela_friendly": False,
        "rating": 3.8, "payout_speed_days": 21,
        "withdrawal_methods": ["bank"],
        "trading_platforms": ["rithmic"],
        "drawdown_type": "static", "profit_split": 97, "has_promotion": False,
        "instruments": ["futures"], "tags": [],
    },
]


def init_scout_data():
    """Seed prop firms on first run, and update OFAC blocklist + Venezuela flag
    on every startup so country-filter data stays consistent with current sanctions."""
    is_first_run = PropFirm.query.count() == 0

    for d in SCOUT_SEED:
        slug = d['slug']
        # OFAC default applies to every US-regulated futures prop firm.
        # The only documented exception in our set is OneUp Trader for Venezuela.
        blocklist = list(OFAC_DEFAULT_BLOCKLIST)
        if slug in VENEZUELA_ALLOWED_SLUGS and 'VE' in blocklist:
            blocklist.remove('VE')
        ve_friendly = slug in VENEZUELA_ALLOWED_SLUGS

        firm = PropFirm.query.filter_by(slug=slug).first()
        if firm:
            # Always refresh sanction-related fields so this acts as a migration
            firm.blocked_countries = blocklist
            firm.venezuela_friendly = ve_friendly
            firm.updated_at = datetime.now(timezone.utc)
        else:
            firm = PropFirm(
                name=d['name'], slug=slug, website=d.get('website', ''),
                account_costs=d.get('account_costs', {}),
                allowed_worldwide=True,
                blocked_countries=blocklist,
                venezuela_friendly=ve_friendly,
                rating=d.get('rating', 0.0),
                payout_speed_days=d.get('payout_speed_days', 14),
                withdrawal_methods=d.get('withdrawal_methods', []),
                trading_platforms=d.get('trading_platforms', []),
                drawdown_type=d.get('drawdown_type', 'trailing'),
                has_promotion=d.get('has_promotion', False),
                promotion_detail=d.get('promotion_detail', ''),
                profit_split=d.get('profit_split', 80),
                instruments=d.get('instruments', ['futures']),
                tags=d.get('tags', []),
            )
            db.session.add(firm)
    db.session.commit()
    if is_first_run:
        app.logger.info('Seeded %d prop firms', len(SCOUT_SEED))
    else:
        app.logger.info('Refreshed OFAC blocklist on %d prop firms', len(SCOUT_SEED))


@app.route('/api/scout/firms')
@login_required
def scout_firms():
    if not SCOUT_ENABLED:
        return jsonify({'error': 'not_found'}), 404
    if current_user.plan != 'premium':
        return jsonify({'error': 'premium_required'}), 403

    country     = request.args.get('country', '').strip().upper()
    size        = request.args.get('size', '').strip()
    drawdown    = request.args.get('drawdown', '').strip()
    platform    = request.args.get('platform', '').strip()
    withdrawal  = request.args.get('withdrawal', '').strip()
    payout      = request.args.get('payout', '').strip()
    promo       = request.args.get('promo', '').strip()
    sort_by     = request.args.get('sort', 'rating').strip()

    firms = PropFirm.query.filter_by(is_active=True).all()
    results = []
    for f in firms:
        # Country filter — block if user's country is in firm's OFAC blocklist.
        # blocked_countries is populated by init_scout_data() using OFAC_DEFAULT_BLOCKLIST
        # plus any per-firm exceptions (e.g. OneUp Trader accepts Venezuela).
        if country and f.blocked_countries and country in f.blocked_countries:
            continue

        # Account size filter — firm must offer that size
        if size and (not f.account_costs or size not in f.account_costs):
            continue

        # Drawdown filter
        if drawdown:
            if f.drawdown_type != drawdown and f.drawdown_type != 'both':
                continue

        # Platform filter
        if platform and platform not in (f.trading_platforms or []):
            continue

        # Withdrawal filter
        if withdrawal and withdrawal not in (f.withdrawal_methods or []):
            continue

        # Payout speed filter
        if payout == 'fast'   and f.payout_speed_days > 7:   continue
        if payout == 'medium' and not (7 < f.payout_speed_days <= 14): continue
        if payout == 'slow'   and f.payout_speed_days <= 14: continue

        # Promotion filter
        if promo == '1' and not f.has_promotion:
            continue

        results.append({
            'id': f.id, 'name': f.name, 'slug': f.slug, 'website': f.website,
            'rating': f.rating, 'payout_speed_days': f.payout_speed_days,
            'withdrawal_methods': f.withdrawal_methods or [],
            'trading_platforms': f.trading_platforms or [],
            'drawdown_type': f.drawdown_type,
            'has_promotion': f.has_promotion,
            'promotion_detail': f.promotion_detail or '',
            'profit_split': f.profit_split,
            'account_costs': f.account_costs or {},
            'price_for_size': (f.account_costs or {}).get(size) if size else None,
            'tags': f.tags or [],
            'venezuela_friendly': f.venezuela_friendly,
        })

    if sort_by == 'cheapest':
        results.sort(key=lambda x: x.get('price_for_size') or (min(x['account_costs'].values()) if x['account_costs'] else 9999))
    elif sort_by == 'fastest':
        results.sort(key=lambda x: x['payout_speed_days'])
    else:
        results.sort(key=lambda x: x['rating'], reverse=True)

    return jsonify({'firms': results, 'total': len(results)})


@app.route('/api/scout/chat', methods=['POST'])
@login_required
def scout_chat():
    if not SCOUT_ENABLED:
        return jsonify({'error': 'not_found'}), 404
    if current_user.plan != 'premium':
        return jsonify({'error': 'premium_required'}), 403

    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    firm_ids = data.get('firm_ids') or []

    if not question or len(question) > 800:
        return jsonify({'error': 'invalid'}), 400

    firms = PropFirm.query.filter(
        PropFirm.id.in_(firm_ids), PropFirm.is_active == True  # noqa: E712
    ).all() if firm_ids else []

    firm_ctx = ''
    for f in firms:
        firm_ctx += (
            f"\n\n## {f.name}\n"
            f"Rating: {f.rating}/5\n"
            f"Account costs: {json.dumps(f.account_costs)}\n"
            f"Drawdown type: {f.drawdown_type}\n"
            f"Profit split: {f.profit_split}%\n"
            f"Payout speed: ~{f.payout_speed_days} days\n"
            f"Withdrawal methods: {', '.join(f.withdrawal_methods or [])}\n"
            f"Trading platforms: {', '.join(f.trading_platforms or [])}\n"
            f"Venezuela friendly: {'yes' if f.venezuela_friendly else 'no'}\n"
        )
        if f.has_promotion:
            firm_ctx += f"Active promotion: {f.promotion_detail}\n"

    sys_prompt = (
        "You are a knowledgeable prop trading firm advisor helping a futures trader "
        "compare and choose prop firms. Answer in the same language the trader writes in "
        "(English, Spanish, French, Portuguese). Be concise and honest. "
        "If the firm data below is provided, use it as your primary source. "
        "For anything not in the data, draw on general knowledge but flag it as potentially outdated."
    )
    user_msg = question
    if firm_ctx:
        user_msg = f"Current data for the firms:{firm_ctx}\n\nQuestion: {question}"

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=700, temperature=0.4,
        )
        record_ai_cost('scout', resp,
                       user_id=current_user.id if current_user.is_authenticated else None,
                       plan=current_plan())
        return jsonify({'answer': resp.choices[0].message.content})
    except Exception as exc:
        app.logger.error('Scout chat failed: %s', exc)
        return jsonify({'error': 'api_error'}), 500


# ── Quiz Progress (premium) ──
# ── Quiz pass / certification rules ──────────────────────────────────────────
# A quiz is PASSED with at least this accuracy (shown both in the UI and enforced
# server-side). Anything below is a fail.
QUIZ_PASS_PCT = 80

# A trader is "certified" once they have PASSED every quiz of every methodology
# and level, with an overall accuracy of at least QUIZ_CERT_PCT across all of them.
QUIZ_CERT_METHODS = ['ict', 'smc', 'wyckoff', 'patterns']
QUIZ_CERT_LEVELS  = ['beginner', 'intermediate', 'advanced']
QUIZ_CERT_REQUIRED = len(QUIZ_CERT_METHODS) * len(QUIZ_CERT_LEVELS)   # 12 combos
QUIZ_CERT_PCT = 80


class QuizProgress(db.Model):
    """One row per (user, methodology, level) combination."""
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    methodology  = db.Column(db.String(40), nullable=False)   # ict / smc / wyckoff / patterns
    level        = db.Column(db.String(20), nullable=False)   # beginner / intermediate / advanced
    completed    = db.Column(db.Boolean, default=False, nullable=False)
    best_score   = db.Column(db.Integer, default=0)           # correct answers
    total_q      = db.Column(db.Integer, default=0)
    weak_topics  = db.Column(db.JSON, default=list)           # list of topic strings with errors
    completed_at = db.Column(db.DateTime, nullable=True)
    user         = db.relationship('User', backref='quiz_progress')
    __table_args__ = (db.UniqueConstraint('user_id', 'methodology', 'level'),)


# ──────────────────────────────────────────────────────────────────────────
# SYNAPSE — topic completion tracking
# ──────────────────────────────────────────────────────────────────────────
# Canonical registry of every studiable Synapse topic, grouped by methodology.
# The library UI doesn't exist yet, but the backend is fully built so that the
# moment a user can "check off" a topic in Synapse, it persists per-account and
# the Quiz ("test what I studied in Synapse") can surface those topics.
#
# Slugs are globally unique and methodology-prefixed so collisions like ICT's
# "Liquidity" vs SMC's "Liquidity" never clash. (slug, human label) pairs.
SYNAPSE_TOPICS = {
    'price': [
        ('price.support-resistance', 'Support & Resistance'),
        ('price.trend-structure',    'Trend & Structure'),
        ('price.candles',            'Candlestick Reading'),
        ('price.chart-patterns',     'Chart Patterns'),
        ('price.supply-demand',      'Supply & Demand'),
        # entry triggers
        ('price.pin-bar',            'Pin Bar Rejection'),
        ('price.engulfing',          'Engulfing Confirmation'),
        ('price.breakout-retest',    'Breakout Retest'),
        ('price.harmonic',           'Harmonic Completion'),
    ],
    'technical': [
        ('technical.moving-averages', 'Moving Averages'),
        ('technical.rsi',             'RSI'),
        ('technical.macd',            'MACD'),
        ('technical.bollinger',       'Bollinger Bands'),
        ('technical.volume',          'Volume'),
        # entry triggers
        ('technical.ma-cross',        'MA Crossover'),
        ('technical.rsi-divergence',  'RSI Divergence'),
        ('technical.macd-cross',      'MACD Cross'),
        ('technical.squeeze-break',   'Bollinger Squeeze Break'),
    ],
    'smc': [
        ('smc.wyckoff-roots',     'Wyckoff Roots'),
        ('smc.market-structure',  'Market Structure (BOS/ChoCH)'),
        ('smc.order-blocks',      'Order Blocks'),
        ('smc.fair-value-gaps',   'Fair Value Gaps'),
        ('smc.liquidity',         'Liquidity'),
        ('smc.pd-arrays',         'Premium / Discount'),
        ('smc.kill-zones',        'Kill Zones'),
        # entry triggers
        ('smc.ote',               'OTE Entry'),
        ('smc.ob-retest',         'Order Block Retest'),
        ('smc.fvg-fill',          'FVG Fill'),
        ('smc.liquidity-sweep',   'Liquidity Sweep Reversal'),
    ],
    'fundamental': [
        ('fundamental.macro-drivers',  'Macro Drivers'),
        ('fundamental.interest-rates', 'Interest Rates'),
        ('fundamental.news-data',      'News & Data Releases'),
        ('fundamental.intermarket',    'Intermarket Correlations'),
        # entry triggers
        ('fundamental.news-fade',      'News Spike Fade'),
        ('fundamental.data-continuation', 'Data-Release Continuation'),
    ],
    'quant': [
        ('quant.probability',  'Statistics & Probability'),
        ('quant.backtesting',  'Backtesting'),
        ('quant.risk-of-ruin', 'Risk of Ruin'),
        ('quant.algo-systems', 'Algo Systems'),
        # entry triggers
        ('quant.mean-reversion', 'Mean-Reversion Signal'),
        ('quant.momentum',       'Momentum Signal'),
    ],
}

# Reverse lookups: slug → methodology, and slug → label. Built once at import.
SYNAPSE_SLUG_TO_METHOD = {}
SYNAPSE_SLUG_TO_LABEL  = {}
for _m, _topics in SYNAPSE_TOPICS.items():
    for _slug, _label in _topics:
        SYNAPSE_SLUG_TO_METHOD[_slug] = _m
        SYNAPSE_SLUG_TO_LABEL[_slug]  = _label
SYNAPSE_VALID_SLUGS = set(SYNAPSE_SLUG_TO_METHOD)


class SynapseProgress(db.Model):
    """One row per (user, synapse topic) the user has marked as studied."""
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    methodology = db.Column(db.String(40), nullable=False)   # ict / smc / wyckoff / patterns
    topic_slug  = db.Column(db.String(80), nullable=False)    # ict.order-blocks ...
    checked_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user        = db.relationship('User', backref='synapse_progress')
    __table_args__ = (db.UniqueConstraint('user_id', 'topic_slug'),)


@app.route('/api/fingerprint', methods=['POST'])
def store_fingerprint():
    """Receive a browser fingerprint hash from the client.
    - If the user is authenticated: store/update their fingerprint.
    - If the hash is in BannedFingerprint: return 403 so the register form can block.
    """
    data = request.get_json(silent=True) or {}
    fp_hash = (data.get('fp') or '').strip()[:64]
    if not fp_hash:
        return jsonify({'ok': False}), 400

    is_banned_fp = BannedFingerprint.query.filter_by(fp_hash=fp_hash).first() is not None

    if current_user.is_authenticated:
        existing = BrowserFingerprint.query.filter_by(user_id=current_user.id).first()
        if existing:
            existing.fp_hash = fp_hash
            existing.collected_at = datetime.now(timezone.utc)
        else:
            db.session.add(BrowserFingerprint(user_id=current_user.id, fp_hash=fp_hash))
        db.session.commit()

    if is_banned_fp:
        return jsonify({'ok': False, 'banned': True}), 403
    return jsonify({'ok': True})


@app.route('/api/synapse/topics')
@login_required
def synapse_topics():
    """The full registry of studiable Synapse topics (for the future library UI
    and the quiz picker), plus which ones THIS user has already checked off."""
    if current_user.plan != 'premium' and not current_user.is_admin:
        return jsonify({'error': 'premium_only'}), 403
    checked = {r.topic_slug for r in
               SynapseProgress.query.filter_by(user_id=current_user.id).all()}
    catalog = {
        m: [{'slug': slug, 'label': label, 'checked': slug in checked}
            for slug, label in topics]
        for m, topics in SYNAPSE_TOPICS.items()
    }
    return jsonify({'topics': catalog, 'checked': sorted(checked)})


@app.route('/api/synapse/progress')
@login_required
def synapse_progress():
    """Flat list of the slugs this user has checked off as studied."""
    if current_user.plan != 'premium' and not current_user.is_admin:
        return jsonify({'error': 'premium_only'}), 403
    rows = SynapseProgress.query.filter_by(user_id=current_user.id).all()
    return jsonify({'checked': [{
        'slug':        r.topic_slug,
        'methodology': r.methodology,
        'label':       SYNAPSE_SLUG_TO_LABEL.get(r.topic_slug, r.topic_slug),
        'checked_at':  r.checked_at.isoformat() if r.checked_at else None,
    } for r in rows]})


@app.route('/api/synapse/toggle', methods=['POST'])
@login_required
def synapse_toggle():
    """Toggle a topic's studied state for the current user. Returns the new
    state. Adding a check inserts a row; un-checking deletes it."""
    if current_user.plan != 'premium' and not current_user.is_admin:
        return jsonify({'error': 'premium_only'}), 403
    data = request.get_json(force=True) or {}
    slug = str(data.get('topic_slug', '')).strip()
    if slug not in SYNAPSE_VALID_SLUGS:
        return jsonify({'error': 'invalid_topic'}), 400

    row = SynapseProgress.query.filter_by(
        user_id=current_user.id, topic_slug=slug
    ).first()

    if row is None:
        row = SynapseProgress(
            user_id=current_user.id,
            methodology=SYNAPSE_SLUG_TO_METHOD[slug],
            topic_slug=slug,
        )
        db.session.add(row)
        checked = True
    else:
        db.session.delete(row)
        checked = False

    db.session.commit()
    return jsonify({'ok': True, 'topic_slug': slug, 'checked': checked})


@app.route('/api/quiz/progress')
@login_required
def quiz_get_progress():
    if current_user.plan != 'premium' and not current_user.is_admin:
        return jsonify({'error': 'premium_only'}), 403
    rows = QuizProgress.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'methodology': r.methodology,
        'level':       r.level,
        'completed':   r.completed,
        'best_score':  r.best_score,
        'total_q':     r.total_q,
        'weak_topics': r.weak_topics or [],
    } for r in rows])


@app.route('/api/quiz/complete', methods=['POST'])
@login_required
def quiz_complete():
    if current_user.plan != 'premium' and not current_user.is_admin:
        return jsonify({'error': 'premium_only'}), 403
    data = request.get_json(force=True)
    methodology = data.get('methodology', '').strip().lower()
    level       = data.get('level', '').strip().lower()
    score       = int(data.get('score', 0))
    total       = int(data.get('total', 0))
    weak_topics = data.get('weak_topics', [])   # list of strings

    valid_methods = {'ict', 'smc', 'wyckoff', 'patterns'}
    # 'hardcore' is an expert chart-based tier saved alongside the base levels.
    # It is intentionally kept OUT of the certification grid (see user_certification).
    valid_levels  = {'beginner', 'intermediate', 'advanced', 'hardcore'}
    if methodology not in valid_methods or level not in valid_levels:
        return jsonify({'error': 'invalid_params'}), 400

    row = QuizProgress.query.filter_by(
        user_id=current_user.id, methodology=methodology, level=level
    ).first()
    pct = (score / total * 100) if total else 0
    passed = pct >= QUIZ_PASS_PCT

    if row is None:
        row = QuizProgress(user_id=current_user.id, methodology=methodology, level=level)
        db.session.add(row)

    if score > (row.best_score or 0):
        row.best_score  = score
        row.total_q     = total
        row.weak_topics = weak_topics
    if passed and not row.completed:
        row.completed    = True
        row.completed_at = datetime.now(timezone.utc)

    db.session.commit()
    return jsonify({'ok': True, 'completed': row.completed, 'best_score': row.best_score})


def user_certification(user_id):
    """Return {'accuracy': int, 'completed_at': datetime|None} if the user has
    passed EVERY quiz (all methodology+level combos) with an overall accuracy of
    at least QUIZ_CERT_PCT, otherwise None."""
    rows = QuizProgress.query.filter_by(user_id=user_id).all()
    # Hardcore is an optional expert tier — it does NOT count toward the base
    # certification grid (12 combos) nor its accuracy, so exclude it here.
    completed = [r for r in rows if r.completed and r.level != 'hardcore']
    # The unique (user, methodology, level) constraint means a full grid == count
    if len(completed) < QUIZ_CERT_REQUIRED:
        return None
    total_correct = sum(r.best_score for r in completed)
    total_q       = sum(r.total_q for r in completed)
    if not total_q:
        return None
    pct = round(total_correct / total_q * 100)
    if pct < QUIZ_CERT_PCT:
        return None
    last = max((r.completed_at for r in completed if r.completed_at), default=None)
    return {'accuracy': pct, 'completed_at': last}


@app.route('/api/quiz/certified')
@login_required
def quiz_certified():
    """Leaderboard of certified accelerated traders: premium users who passed
    every quiz with >= QUIZ_CERT_PCT overall. Admins are always showcased as
    founding examples even if their grid isn't complete."""
    if current_user.plan != 'premium' and not current_user.is_admin:
        return jsonify({'error': 'premium_only'}), 403

    entries = []
    users = User.query.filter(
        (User.plan == 'premium') | (User.is_admin == True)  # noqa: E712
    ).all()
    for u in users:
        cert = user_certification(u.id)
        if cert:
            entries.append({
                'username':  u.username,
                'accuracy':  cert['accuracy'],
                'is_admin':  u.is_admin,
                'completed_at': cert['completed_at'].isoformat() if cert['completed_at'] else None,
            })
        elif u.is_admin:
            # Founding example: admins are showcased even without a full grid.
            entries.append({
                'username':  u.username,
                'accuracy':  cert['accuracy'] if cert else 100,
                'is_admin':  True,
                'completed_at': None,
            })

    # Highest accuracy first; admins (founders) bubble to the top on ties.
    entries.sort(key=lambda e: (e['accuracy'], e['is_admin']), reverse=True)
    return jsonify({'pass_pct': QUIZ_PASS_PCT, 'cert_pct': QUIZ_CERT_PCT, 'traders': entries})


# ──────────────────────────────────────────────────────────────────────────
# DAILY CHALLENGE + ROULETTE (premium-only retention loop)
# One timed question per UTC day; a 7-day streak of correct answers earns a
# roulette spin. Prizes: renewal discounts (single-use promo codes) or a free
# month of Premium (direct plan extension).
# ──────────────────────────────────────────────────────────────────────────
DAILY_STREAK_TARGET = 7
DAILY_ANSWER_SECONDS = 60
DAILY_ANSWER_GRACE = 5          # network latency allowance on top of the 60s

# (key, discount_pct or None for free month, probability weight, label)
ROULETTE_PRIZES = [
    ('d5',    5,    40, '5% off your next renewal'),
    ('d10',   10,   30, '10% off your next renewal'),
    ('d15',   15,   15, '15% off your next renewal'),
    ('d25',   25,   10, '25% off your next renewal'),
    ('month', None,  5, '1 month of Premium — free'),
]


def _utc_today():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _daily_state():
    """Get or create the current user's DailyQuizState row."""
    st = DailyQuizState.query.filter_by(user_id=current_user.id).first()
    if not st:
        st = DailyQuizState(user_id=current_user.id)
        db.session.add(st)
        db.session.commit()
    return st


def _daily_seed():
    """Deterministic per-day seed — same question for every user worldwide."""
    return (datetime.now(timezone.utc).date() - datetime(2026, 1, 1, tzinfo=timezone.utc).date()).days


# ── Server-side answer key (anti-cheat for Daily Challenge + Quiz) ──
# The question bank lives client-side for instant feedback, but the client must
# never be trusted to assert "I was correct". It submits which option it picked
# and the SERVER judges it against this key (derived from the same bank by
# tools/extract_quiz_key.js). Validation only ever returns correct/incorrect —
# the answer index is never sent back to a client.
_QUIZ_KEY = []        # by bank index: [{'lv':..., 'ans':int}, ...]
_ADV_ANS = []         # correct option indices for advanced questions, in POOL order


def _load_quiz_key():
    """Load (and best-effort regenerate) the server-side answer key. Regenerating
    at startup keeps it in sync whenever node is available; otherwise the
    committed JSON is used."""
    global _QUIZ_KEY, _ADV_ANS
    base = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(base)
    keypath = os.path.join(base, 'quiz_answer_key.json')
    try:
        import subprocess
        subprocess.run(['node', os.path.join(repo, 'tools', 'extract_quiz_key.js')],
                       cwd=repo, capture_output=True, timeout=30)
    except Exception:
        pass  # node unavailable on this host → fall back to the committed JSON
    try:
        with open(keypath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _QUIZ_KEY = data.get('key', [])
        _ADV_ANS = [k['ans'] for k in _QUIZ_KEY if k.get('lv') == 'advanced']
        app.logger.info('Loaded quiz answer key: %d questions, %d advanced.',
                        len(_QUIZ_KEY), len(_ADV_ANS))
    except Exception as e:
        app.logger.error('Could not load quiz answer key: %s', e)
        _QUIZ_KEY, _ADV_ANS = [], []


# Exact port of the client's deterministic question picker (index.html). Verified
# bit-for-bit against the JS so the server agrees on "today's question".
def _u32(x):
    return x & 0xFFFFFFFF


def _i32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x


def _imul(a, b):
    return _i32(_u32(a) * _u32(b))


def _mulberry32(a):
    state = _i32(a)

    def rng():
        nonlocal state
        state = _i32(state + 0x6D2B79F5)
        t = _imul(state ^ (_u32(state) >> 15), 1 | state)
        t = _i32(t + _imul(t ^ (_u32(t) >> 7), 61 | t)) ^ t
        return _u32(t ^ (_u32(t) >> 14)) / 4294967296.0
    return rng


def _cycle_order(cycle, n):
    order = list(range(n))
    if cycle == 0:
        return order
    rng = _mulberry32(_u32(cycle * 2654435761))
    for i in range(len(order) - 1, 0, -1):
        j = int(rng() * (i + 1))
        order[i], order[j] = order[j], order[i]
    return order


def _daily_correct_index():
    """The correct option index (original order) of today's Daily Challenge
    question — computed entirely server-side. Returns None if the key is missing."""
    n = len(_ADV_ANS)
    if n == 0:
        return None
    seed = _daily_seed()
    cycle = seed // n
    pos = ((seed % n) + n) % n
    pool_idx = _cycle_order(cycle, n)[pos]
    return _ADV_ANS[pool_idx]


def _daily_status_payload(st):
    return {
        'today': _utc_today(),
        'played_today': st.last_played == _utc_today(),
        'last_result': st.last_result,
        'streak': st.streak,
        'streak_target': DAILY_STREAK_TARGET,
        'spins_available': st.spins_available,
        'total_correct': st.total_correct,
        'seconds': DAILY_ANSWER_SECONDS,
    }


@app.route('/api/daily/status')
@premium_required
def daily_status():
    st = _daily_state()
    # A missed day (no answer yesterday) silently breaks the streak.
    if st.last_played and st.streak > 0:
        last = datetime.strptime(st.last_played, '%Y-%m-%d').date()
        if (datetime.now(timezone.utc).date() - last).days > 1:
            st.streak = 0
            db.session.commit()
    return jsonify(_daily_status_payload(st))


@app.route('/api/daily/start', methods=['POST'])
@premium_required
def daily_start():
    st = _daily_state()
    today = _utc_today()
    if st.last_played == today:
        return jsonify({'error': 'already_played'}), 409
    # Restarting the same day's question does NOT reset the clock — the 60s
    # window runs from the FIRST open, so reloading the page can't buy time.
    if st.served_for != today or not st.question_served_at:
        st.served_for = today
        st.question_served_at = datetime.now(timezone.utc)
        db.session.commit()
    elapsed = (datetime.now(timezone.utc) - _aware(st.question_served_at)).total_seconds()
    # Clamp to [0, window]: a future-dated served_at (clock/timezone skew) would
    # otherwise make `60 - negative` balloon to thousands of seconds.
    remaining = max(0, min(DAILY_ANSWER_SECONDS, DAILY_ANSWER_SECONDS - int(elapsed)))
    return jsonify({'seed': _daily_seed(), 'seconds_left': remaining})


@app.route('/api/daily/answer', methods=['POST'])
@premium_required
def daily_answer():
    st = _daily_state()
    today = _utc_today()
    if st.last_played == today:
        return jsonify({'error': 'already_played'}), 409
    if st.served_for != today or not st.question_served_at:
        return jsonify({'error': 'not_started'}), 400

    elapsed = (datetime.now(timezone.utc) - _aware(st.question_served_at)).total_seconds()
    timed_out = elapsed > (DAILY_ANSWER_SECONDS + DAILY_ANSWER_GRACE)
    # Anti-cheat: correctness is decided by the SERVER. The client submits which
    # option index it picked (original order); we compare it to the server-held
    # answer key. A forged {selected:...} can't win unless it's the real answer.
    try:
        selected = int((request.json or {}).get('selected', -1))
    except (TypeError, ValueError):
        selected = -1
    answer_idx = _daily_correct_index()
    correct = (answer_idx is not None and selected == answer_idx) and not timed_out

    st.last_played = today
    st.last_result = correct
    earned_spin = False
    if correct:
        st.streak += 1
        st.total_correct += 1
        if st.streak % DAILY_STREAK_TARGET == 0:
            st.spins_available += 1
            earned_spin = True
    else:
        st.streak = 0
    db.session.commit()

    if correct:
        # XP: one award per UTC day (ref=date), plus a streak bonus every 7.
        add_xp(current_user, 'daily_correct', ref=today)
        if earned_spin:
            add_xp(current_user, 'daily_streak', ref=f'{today}:streak')

    payload = _daily_status_payload(st)
    payload.update({'correct': correct, 'timed_out': timed_out, 'earned_spin': earned_spin})
    return jsonify(payload)


@app.route('/api/daily/spin', methods=['POST'])
@premium_required
def daily_spin():
    demo_spin = bool(_admin_demo() and _admin_demo().get('spin'))
    st = _daily_state()
    if st.spins_available <= 0 and not demo_spin:
        return jsonify({'error': 'no_spins'}), 409

    import random as _random
    keys = [p[0] for p in ROULETTE_PRIZES]
    weights = [p[2] for p in ROULETTE_PRIZES]
    prize_key = _random.choices(keys, weights=weights, k=1)[0]
    _, discount, _, label = next(p for p in ROULETTE_PRIZES if p[0] == prize_key)

    promo_code = None
    code_scope = None
    if discount:
        # Annual subscribers can't redeem a code on their next monthly renewal
        # (there isn't one), so their prize is a store discount (indicators /
        # camos) instead — longer expiry since the store launches later.
        code_scope = 'store' if current_user.plan_cycle == 'annual' else 'monthly'
        # Guaranteed-unique code: regenerate on the (rare) collision instead of
        # relying solely on the DB unique constraint to abort the spin.
        while True:
            promo_code = f'SPIN-{secrets.token_hex(3).upper()}'
            if not PromoCode.query.filter_by(code=promo_code).first():
                break
        db.session.add(PromoCode(
            code=promo_code, discount_pct=discount, kind='discount',
            creator_name=f'roulette:{current_user.username}',
            valid_for=code_scope, max_uses=1,
            restrict_user_id=current_user.id,
            expires_at=datetime.now(timezone.utc)
                + timedelta(days=365 if code_scope == 'store' else 90),
        ))
    else:
        # Free month: extend the active plan directly — no code to redeem.
        cur = _aware(current_user.plan_expires_at)
        base = cur if cur and cur > datetime.now(timezone.utc) else datetime.now(timezone.utc)
        current_user.plan_expires_at = base + timedelta(days=30)

    if st.spins_available > 0:   # guard: a demo spin must never go negative
        st.spins_available -= 1
    db.session.add(RouletteSpin(user_id=current_user.id, prize_key=prize_key,
                                label=label, promo_code=promo_code))
    db.session.commit()
    record_audit_event('roulette_prize', user_id=current_user.id,
                        detail=f'{prize_key} ({label})' + (f' code={promo_code}' if promo_code else ''))

    return jsonify({
        'prize_key': prize_key, 'label': label, 'promo_code': promo_code,
        'code_scope': code_scope,
        'spins_available': st.spins_available,
        'segments': [{'key': p[0], 'label': p[3]} for p in ROULETTE_PRIZES],
    })


@app.route('/api/daily/coupons')
@premium_required
def daily_coupons():
    """List the personal promo codes this user has won on the roulette."""
    codes = (PromoCode.query.filter_by(restrict_user_id=current_user.id)
             .order_by(PromoCode.created_at.desc()).all())
    now = datetime.now(timezone.utc)
    out = []
    for p in codes:
        used = p.max_uses is not None and (p.uses_count or 0) >= p.max_uses
        expired = bool(p.expires_at) and now > _aware(p.expires_at)
        out.append({
            'code': p.code,
            'discount_pct': p.discount_pct,
            'valid_for': p.valid_for,
            'expires_at': p.expires_at.strftime('%Y-%m-%d') if p.expires_at else None,
            'status': 'used' if used else ('expired' if expired else 'active'),
        })
    return jsonify({'coupons': out})


@app.route('/api/testimonial/submit', methods=['POST'])
@login_required
def testimonial_submit():
    """Record a periodic rating/review from any logged-in user (all plans).
    4-5 star reviews (with consent to publish) appear on the public
    landing-page panel; everything else stays private as feedback."""
    data = request.get_json(silent=True) or {}
    try:
        rating = int(data.get('rating', 0))
    except (TypeError, ValueError):
        rating = 0
    if data.get('skipped'):
        # "Maybe later" — just push the next prompt out ~30 days, no record.
        current_user.last_review_prompt_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({'ok': True})
    if rating < 1 or rating > 5:
        return jsonify({'error': 'invalid_rating'}), 400
    # Anti-farm: 'testimonial' XP is exempt from the daily master cap, so without
    # a server-side cooldown a user could POST this endpoint repeatedly for
    # unlimited XP (and spam the table). Enforce the same ~30-day window the
    # prompt uses, on the server, keyed to the user's last real testimonial.
    recent = (Testimonial.query.filter_by(user_id=current_user.id)
              .order_by(Testimonial.created_at.desc()).first())
    if recent and (datetime.now(timezone.utc) - _aware(recent.created_at)).days < 30:
        current_user.last_review_prompt_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({'ok': True, 'throttled': True})
    text = (data.get('text') or '').strip()[:500]
    consent = bool(data.get('consent'))
    published = rating >= 4 and consent and bool(text)
    t = Testimonial(
        user_id=current_user.id, rating=rating, text=text,
        display_name=current_user.username, plan=current_user.plan,
        published=published,
    )
    current_user.last_review_prompt_at = datetime.now(timezone.utc)
    db.session.add(t)
    db.session.commit()
    add_xp(current_user, 'testimonial', ref=f'testimonial:{t.id}')
    record_audit_event('testimonial_submitted', user_id=current_user.id,
                        detail=f'{rating}/5 published={published}')
    return jsonify({'ok': True})


@app.route('/api/testimonials')
def testimonials_public():
    """Public feed of published testimonials for the landing page panel.
    `rank` is the author's CURRENT rank (live), joined fresh each time."""
    rows = (db.session.query(Testimonial, User.rank)
            .outerjoin(User, User.id == Testimonial.user_id)
            .filter(Testimonial.published == True)  # noqa: E712
            .order_by(Testimonial.created_at.desc()).limit(24).all())
    return jsonify({'testimonials': [
        {'name': r.display_name, 'rating': r.rating, 'text': r.text,
         'plan': r.plan, 'rank': rank or 1}
        for r, rank in rows
    ]})


# ──────────────────────────────────────────────────────────────────────────
# XP / RANK — quiz award + progress endpoint
# ──────────────────────────────────────────────────────────────────────────
@app.route('/api/quiz/answer', methods=['POST'])
@premium_required
def quiz_answer_xp():
    """Award XP for a correctly answered quiz question. The client reports the
    question's bank index, the option it picked, and the level; the SERVER
    validates the pick against its answer key (the client can't just claim it was
    right). A question pays once (dedup by ref) and the source caps at 20 XP/day."""
    data = request.get_json(silent=True) or {}
    try:
        qid = int(data.get('question_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'bad_request'}), 400
    try:
        selected = int(data.get('selected', -1))
    except (TypeError, ValueError):
        selected = -1
    if qid < 0 or qid >= len(_QUIZ_KEY):
        return jsonify({'error': 'bad_request'}), 400
    entry = _QUIZ_KEY[qid]
    level = entry.get('lv')
    if level not in ('beginner', 'intermediate', 'advanced'):
        # hardcore / unkeyed questions don't pay XP here
        return jsonify({'ok': True, 'awarded': 0, 'correct': False,
                        'xp': current_user.xp, 'rank': current_user.rank})
    correct = (selected == entry.get('ans'))
    awarded = 0
    if correct:
        amount = XP_PREMIUM.get(f'quiz_{level}', 0)
        awarded = add_xp(current_user, 'quiz', amount=amount, ref=f'q:{qid}')
    return jsonify({'ok': True, 'awarded': awarded, 'correct': correct,
                    'xp': current_user.xp, 'rank': current_user.rank})


def _rank_progress_payload(user, xp_override=None, plan_override=None):
    xp = user.xp or 0 if xp_override is None else xp_override
    rank = rank_for_xp(xp)
    cur_floor = RANK_THRESHOLDS[rank - 1]
    next_floor = RANK_THRESHOLDS[rank] if rank < len(RANK_THRESHOLDS) else None
    plan = plan_override or user.plan or 'free'
    sources_used = {}
    for src in ('quiz', 'preflight_check', 'forum_post', 'forum_comment',
                'forum_reaction', 'analysis', 'daily_correct', 'login'):
        sources_used[src] = _xp_sum_today(user.id, src)
    master_used = (db.session.query(db.func.coalesce(db.func.sum(XPLog.amount), 0))
                   .filter(XPLog.user_id == user.id, XPLog.day == _xp_day(),
                           ~XPLog.source.in_(list(XP_CAP_EXEMPT))).scalar() or 0)
    return {
        'xp': xp,
        'rank': rank,
        'rank_name': RANK_NAMES[rank - 1],
        'next_rank_name': RANK_NAMES[rank] if rank < len(RANK_NAMES) else None,
        'current_floor': cur_floor,
        'next_floor': next_floor,
        'xp_into_rank': xp - cur_floor,
        'xp_to_next': (next_floor - xp) if next_floor is not None else 0,
        'ranks': [{'n': i + 1, 'name': RANK_NAMES[i], 'threshold': RANK_THRESHOLDS[i]}
                  for i in range(len(RANK_NAMES))],
        'plan': plan,
        'today': {
            'master_used': int(master_used),
            'master_cap': XP_MASTER_CAP.get(plan),
            'sources': sources_used,
            'daily_caps': XP_DAILY_CAP,
        },
    }


@app.route('/api/rank/progress')
@login_required
def rank_progress():
    # Mirror the demo overlay so the "My Rank Progress" panel matches what the
    # demo shows on-screen (reset to rank 1 for a plan view, or the chosen
    # rank-up). Reads nothing from the DB beyond the real values as a fallback.
    xp_override = None
    plan_override = None
    demo = _admin_demo()
    if demo:
        if demo.get('rank_up'):
            r = int(demo['rank_up'])
            xp_override = RANK_THRESHOLDS[r - 1] if r <= len(RANK_THRESHOLDS) else 0
        elif demo.get('plan'):
            xp_override = 0
        if demo.get('plan') in DEMO_PLANS:
            plan_override = demo['plan']
    return jsonify(_rank_progress_payload(current_user, xp_override, plan_override))


@app.route('/api/rank/celebrated', methods=['POST'])
@login_required
def rank_celebrated_ack():
    """Seal the rank-up reveal once the user has actually dismissed the panel.
    Called by the client when the reveal is closed; until then the reveal keeps
    re-appearing on each /app load so it can never be missed."""
    # In admin demo mode the reveal is staged, not real — never seal it so it can
    # be replayed as many times as the demo needs.
    if _admin_demo():
        return jsonify({'ok': True, 'demo': True})
    if (current_user.rank or 1) > (getattr(current_user, 'rank_celebrated', 1) or 1):
        current_user.rank_celebrated = current_user.rank
        db.session.commit()
    return jsonify({'ok': True, 'rank_celebrated': current_user.rank_celebrated})


# ──────────────────────────────────────────────────────────────────────────
# RANK CERTIFICATES — viewable page + watermarked PDF + public verification.
# The medal SVG is ported from the client `renderRankBadge()` so the PDF (which
# runs no JS) shows the real rank medal. Anti-forgery = the verification code is
# checked server-side at /verify/<code>, not the artwork.
# ──────────────────────────────────────────────────────────────────────────
_MED_HEX = {'big': 'M28,11 L72,11 L93,50 L72,89 L28,89 L7,50 Z',
            'sm': 'M33,21 L67,21 L83.5,50 L67,79 L33,79 L16.5,50 Z'}
_MED_SHIELD = {'big': 'M50,7 L85,18 L85,50 C85,72 69,86 50,93 C31,86 15,72 15,50 L15,18 Z',
               'sm': 'M50,18 L74,26 L74,50 C74,66 62,77 50,82 C38,77 26,66 26,50 L26,26 Z'}
_MED_OCT = {'big': 'M33,9 L67,9 L91,33 L91,67 L67,91 L33,91 L9,67 L9,33 Z',
            'sm': 'M37,21 L63,21 L79,37 L79,63 L63,79 L37,79 L21,63 L21,37 Z'}
_MED_SHAPES = {1: _MED_HEX, 2: _MED_HEX, 3: _MED_HEX, 4: _MED_SHIELD,
               5: _MED_OCT, 6: _MED_HEX, 7: _MED_HEX, 8: _MED_HEX}
_MED_D = {
    1: {'rim': ['#5a6076', '#3d4258', '#262a3a'], 'face': ['#343a4d', '#1d2130'], 'edge': '#1b1f2c', 'ink': '#9aa0ba'},
    2: {'rim': ['#c98f5e', '#9a6336', '#5e3a1d'], 'face': ['#7a4f2e', '#3f2614'], 'edge': '#321d0e', 'ink': '#f3d3ab'},
    3: {'rim': ['#d6dde9', '#9aa7bd', '#5d6a82'], 'face': ['#7c8aa3', '#3f4a60'], 'edge': '#2a3142', 'ink': '#eef3fb'},
    4: {'rim': ['#7db0ff', '#4f86e8', '#2c5bb0'], 'face': ['#2f5aa0', '#1a3163'], 'edge': '#13234a', 'ink': '#dce9ff'},
    5: {'rim': ['#6fe0d2', '#34a5b8', '#1d6a86'], 'face': ['#1f6f86', '#123f55'], 'edge': '#0c2c3c', 'ink': '#d8fbff'},
    6: {'rim': ['#c6b8ff', '#8f7fe0', '#5a4ca0'], 'face': ['#5a4ca0', '#2f2a55'], 'edge': '#1f1c3a', 'ink': '#ffe6b0'},
    7: {'rim': ['#ffe79a', '#e0a83d', '#9a6b14'], 'face': ['#9a6b1e', '#5a3d0f'], 'edge': '#3a2708', 'ink': '#fff2c4'},
    8: {'rim': ['#fff6da', '#f3c768', '#caa23a'], 'face': ['#a6781f', '#5e400f'], 'edge': '#3a2708', 'ink': '#fff7e0'},
}
_MED_EMBLEM = {
    1: '<path class="em" d="M6 3h8l4 4v14H6z"/><path class="em" d="M14 3v4h4"/><line class="em" x1="9" y1="12" x2="15" y2="12"/><line class="em" x1="9" y1="15.5" x2="15" y2="15.5"/>',
    2: '<line class="em" x1="12" y1="3" x2="12" y2="7"/><line class="em" x1="12" y1="17" x2="12" y2="21"/><rect class="em" x="9" y="7" width="6" height="10" rx="1"/>',
    3: '<polyline class="em" points="3 16 9 10 13 13 21 5"/><polyline class="em" points="16 5 21 5 21 10"/>',
    4: '<line class="em" x1="4" y1="7" x2="20" y2="7"/><line class="em" x1="4" y1="12" x2="15" y2="12"/><line class="em" x1="4" y1="17" x2="18" y2="17"/>',
    5: '<path class="em" d="M3 15c3 0 3-7 6-7s3 7 6 7 3-7 6-7"/>',
    6: '<circle class="em" cx="12" cy="12" r="6.5"/><line class="em" x1="12" y1="2.5" x2="12" y2="5.5"/><line class="em" x1="12" y1="18.5" x2="12" y2="21.5"/><line class="em" x1="2.5" y1="12" x2="5.5" y2="12"/><line class="em" x1="18.5" y1="12" x2="21.5" y2="12"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/>',
    7: '<line class="em" x1="4" y1="20" x2="20" y2="20"/><path class="em" d="M5 20V9l7-4 7 4v11"/><line class="em" x1="9" y1="20" x2="9" y2="13"/><line class="em" x1="12" y1="20" x2="12" y2="13"/><line class="em" x1="15" y1="20" x2="15" y2="13"/>',
    8: '<path class="em" d="M5 19h14"/><path class="em" d="M6 19c-1-5-2-8 1.5-11 1 2 1.5 3 1.5 3s1-2.5 3-4c2 1.5 3 4 3 4s.5-1 1.5-3C23 11 20 14 18 19"/>',
}


def _med_pips(n, c):
    s = ''
    for k in range(n):
        x = 50 + (k - (n - 1) / 2) * 9
        s += ('<path d="M%s 80.5 l2.3 2.3 -2.3 2.3 -2.3 -2.3 Z" fill="%s" '
              'stroke="rgba(0,0,0,.3)" stroke-width=".5"/>' % (x, c))
    return s


def _med_laurel():
    s = ('<g fill="none" stroke="url(#wr)" stroke-width="2.3" stroke-linecap="round">'
         '<path d="M50 96 C29 91 17 74 16 53"/><path d="M50 96 C71 91 83 74 84 53"/>')
    for k in range(4):
        s += '<path d="M%s %s q-6 -3 -8 -8 q6 0 8 8"/>' % (18 + k, 57 + k * 7)
        s += '<path d="M%s %s q6 -3 8 -8 q-6 0 -8 8"/>' % (82 - k, 57 + k * 7)
    return s + '</g>'


def rank_medal_svg(rank, size_px=64):
    """Static (animation-free) port of the client medal for server-rendered
    HTML/PDF. Faithful colors/shapes/emblems; flourish animations are dropped."""
    rank = max(1, min(8, int(rank or 1)))
    d, S = _MED_D[rank], _MED_SHAPES[rank]
    orna = _med_laurel() if rank >= 6 else _med_pips(rank, d['rim'][0])
    return (
        '<svg class="rank-medal" width="%d" height="%d" viewBox="0 0 100 100">' % (size_px, size_px) +
        '<style>.em{fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}</style>'
        '<defs>'
        '<linearGradient id="rim" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset=".5" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (d['rim'][0], d['rim'][1], d['rim'][2]) +
        '<radialGradient id="face" cx=".38" cy=".30" r=".85"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></radialGradient>' % (d['face'][0], d['face'][1]) +
        '<linearGradient id="wr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (d['rim'][0], d['rim'][2]) +
        '</defs>' +
        (orna if rank >= 6 else '') +
        '<path d="%s" fill="url(#rim)" stroke="%s" stroke-width="2" stroke-linejoin="round"/>' % (S['big'], d['edge']) +
        '<path d="%s" fill="url(#face)" stroke="rgba(0,0,0,.3)" stroke-width="1" stroke-linejoin="round"/>' % S['sm'] +
        '<g transform="translate(26,23) scale(2)" stroke="%s" style="color:%s">%s</g>' % (d['ink'], d['ink'], _MED_EMBLEM[rank]) +
        (orna if rank < 6 else '') +
        '</svg>'
    )


def _cert_qr_svg(url):
    """Real scannable QR pointing at the verification URL, if `segno` is
    installed; otherwise None (the certificate falls back to printing the
    verification code + URL as text, which verifies the same way)."""
    try:
        import segno
        return segno.make(url, error='m').svg_inline(scale=3, dark='#000', light='#fff')
    except Exception:
        return None


# Display copy per rank (Spanish primary; the on-screen panel handles full i18n).
RANK_CERT_NAMES_ES = ['Paper Trader', 'Retail Trader', 'Chart Technician', 'Liquidity Hunter',
                      'Swing Strategist', 'Order Flow Sniper', 'Market Maker', 'Trading Legend']
_ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
# Per-rank accent (acc), secondary bloom (acc2) and bright tint — mirrors the
# approved preview so each certificate reads as a distinct metal.
_CERT_THEME = {
    1: ('#8a92ad', '#5f8fe8', '#b9c0d4'), 2: ('#c98f5e', '#e0a83d', '#e7b888'),
    3: ('#9aabc4', '#6fd0e0', '#c5d2e4'), 4: ('#5f8fe8', '#8f7fe0', '#92b4f2'),
    5: ('#2fa6b8', '#4fc88a', '#5fcdd9'), 6: ('#9f8fe8', '#e08fd0', '#c0b0f5'),
    7: ('#e0a83d', '#e07a3d', '#f3c768'), 8: ('#f3c768', '#e05a28', '#fff0c8'),
}


def _hexa(hx, a):
    hx = hx.lstrip('#')
    return 'rgba(%d,%d,%d,%s)' % (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), a)


_CERT_LANGS = ('en', 'es', 'fr', 'pt')
# Rank names stay in English everywhere (brand/proper nouns, like the medals and
# ICT acronyms). Only the surrounding prose is translated.
CERT_I18N = {
    'en': {'kicker': 'Certificate of Achievement', 'title': 'Rank Certificate',
           'presented': 'This certificate is awarded to',
           'attained': 'for having attained, through practice and dedication, the rank of',
           'rank': 'Rank', 'of': 'of', 'issued': 'Issue date', 'issuedBy': 'Issued by',
           'eduNote': 'Educational achievement — recognizes progress in the Trader Accelerator learning program. Not a professional, financial, or trading qualification.',
           'download': 'Download PDF', 'back': 'Back'},
    'es': {'kicker': 'Certificate of Achievement', 'title': 'Certificado de Rango',
           'presented': 'Se otorga el presente certificado a',
           'attained': 'por haber alcanzado, mediante práctica y dedicación, el rango de',
           'rank': 'Rango', 'of': 'de', 'issued': 'Fecha de emisión', 'issuedBy': 'Emitido por',
           'eduNote': 'Logro educativo — reconoce el progreso en el programa de aprendizaje de Trader Accelerator. No es una calificación profesional, financiera ni de trading.',
           'download': 'Descargar PDF', 'back': 'Volver'},
    'fr': {'kicker': 'Certificate of Achievement', 'title': 'Certificat de Rang',
           'presented': 'Le présent certificat est décerné à',
           'attained': 'pour avoir atteint, par la pratique et la persévérance, le rang de',
           'rank': 'Rang', 'of': 'sur', 'issued': "Date d'émission", 'issuedBy': 'Émis par',
           'eduNote': "Accomplissement éducatif — reconnaît la progression dans le programme d'apprentissage Trader Accelerator. Pas une qualification professionnelle, financière ou de trading.",
           'download': 'Télécharger le PDF', 'back': 'Retour'},
    'pt': {'kicker': 'Certificate of Achievement', 'title': 'Certificado de Rank',
           'presented': 'O presente certificado é concedido a',
           'attained': 'por ter alcançado, com prática e dedicação, o rank de',
           'rank': 'Rank', 'of': 'de', 'issued': 'Data de emissão', 'issuedBy': 'Emitido por',
           'eduNote': 'Conquista educativa — reconhece o progresso no programa de aprendizado da Trader Accelerator. Não é uma qualificação profissional, financeira ou de trading.',
           'download': 'Baixar PDF', 'back': 'Voltar'},
}
VERIFY_I18N = {
    'en': {'okStatus': 'Certificate verified', 'okTitle': 'Authentic document',
           'attained': 'attained the rank of', 'rank': 'Rank', 'issued': 'Issued', 'code': 'Code',
           'note': 'Issued by Trader Accelerator. This certificate is genuine and on record.',
           'noStatus': 'Not verified', 'noTitle': 'Certificate not found',
           'noDesc': 'does not match any certificate issued by Trader Accelerator. It may be mistyped or forged.'},
    'es': {'okStatus': 'Certificado verificado', 'okTitle': 'Documento auténtico',
           'attained': 'alcanzó el rango de', 'rank': 'Rango', 'issued': 'Emitido', 'code': 'Código',
           'note': 'Emitido por Trader Accelerator. Este certificado es genuino y consta en nuestros registros.',
           'noStatus': 'No verificado', 'noTitle': 'Certificado no encontrado',
           'noDesc': 'no corresponde a ningún certificado emitido por Trader Accelerator. Podría estar mal escrito o ser falso.'},
    'fr': {'okStatus': 'Certificat vérifié', 'okTitle': 'Document authentique',
           'attained': 'a atteint le rang de', 'rank': 'Rang', 'issued': 'Émis', 'code': 'Code',
           'note': 'Émis par Trader Accelerator. Ce certificat est authentique et enregistré.',
           'noStatus': 'Non vérifié', 'noTitle': 'Certificat introuvable',
           'noDesc': "ne correspond à aucun certificat émis par Trader Accelerator. Il peut être mal saisi ou falsifié."},
    'pt': {'okStatus': 'Certificado verificado', 'okTitle': 'Documento autêntico',
           'attained': 'alcançou o rank de', 'rank': 'Rank', 'issued': 'Emitido', 'code': 'Código',
           'note': 'Emitido por Trader Accelerator. Este certificado é genuíno e consta nos registros.',
           'noStatus': 'Não verificado', 'noTitle': 'Certificado não encontrado',
           'noDesc': 'não corresponde a nenhum certificado emitido por Trader Accelerator. Pode estar incorreto ou ser falso.'},
}


def _cert_lang(req):
    """Resolve certificate/verify language: explicit ?lang= wins (the in-app panel
    passes the user's current language), else Accept-Language, else English."""
    q = (req.args.get('lang') or '').lower()
    if q in _CERT_LANGS:
        return q
    al = (req.headers.get('Accept-Language') or '').lower()
    for code in _CERT_LANGS:
        if al.startswith(code):
            return code
    return 'en'


def _cert_theme(rank):
    acc, acc2, bright = _CERT_THEME[max(1, min(8, rank))]
    return {'acc': acc, 'acc2': acc2, 'bright': bright,
            'glow': _hexa(acc, '0.28'), 'glow2': _hexa(acc2, '0.18'),
            'frame': _hexa(acc, '0.5'), 'soft': _hexa(acc, '0.11'), 'bd': _hexa(acc, '0.3')}


def _issue_or_get_certificate(user, rank):
    """Return the user's RankCertificate for `rank`, creating it (with a unique
    verification code) on first request. Snapshots the display name at issue."""
    cert = RankCertificate.query.filter_by(user_id=user.id, rank=rank).first()
    if cert:
        return cert
    for _ in range(6):
        code = 'TA-R%d-%s' % (rank, secrets.token_hex(4).upper())
        if not RankCertificate.query.filter_by(code=code).first():
            break
    cert = RankCertificate(user_id=user.id, rank=rank, code=code,
                           display_name=(user.username or 'Trader')[:40])
    db.session.add(cert)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        cert = RankCertificate.query.filter_by(user_id=user.id, rank=rank).first()
    return cert


@app.route('/certificate/<int:rank>')
@login_required
def certificate_view(rank):
    """On-screen certificate for a rank the current user has reached."""
    if rank < 1 or rank > 8:
        abort(404)
    if not current_user.is_admin and (current_user.rank or 1) < rank:
        abort(403)
    cert = _issue_or_get_certificate(current_user, rank)
    lang = _cert_lang(request)
    verify_url = url_for('verify_certificate', code=cert.code, _external=True)
    return render_template(
        'certificate.html', rank=rank, rank_name=RANK_CERT_NAMES_ES[rank - 1],
        roman=_ROMAN[rank - 1], xp=RANK_THRESHOLDS[rank - 1], cert=cert,
        medal_svg=rank_medal_svg(rank, 132), verify_url=verify_url,
        qr_svg=_cert_qr_svg(verify_url), is_legend=(rank == 8), for_pdf=False,
        theme=_cert_theme(rank), cl=CERT_I18N[lang], lang=lang)


@app.route('/certificate/<int:rank>/pdf')
@login_required
def certificate_pdf(rank):
    """Downloadable watermarked PDF of the rank certificate."""
    if rank < 1 or rank > 8:
        abort(404)
    if not current_user.is_admin and (current_user.rank or 1) < rank:
        abort(403)
    cert = _issue_or_get_certificate(current_user, rank)
    lang = _cert_lang(request)
    verify_url = url_for('verify_certificate', code=cert.code, _external=True)
    html_content = render_template(
        'certificate.html', rank=rank, rank_name=RANK_CERT_NAMES_ES[rank - 1],
        roman=_ROMAN[rank - 1], xp=RANK_THRESHOLDS[rank - 1], cert=cert,
        medal_svg=rank_medal_svg(rank, 132), verify_url=verify_url,
        qr_svg=_cert_qr_svg(verify_url), is_legend=(rank == 8), for_pdf=True,
        theme=_cert_theme(rank), cl=CERT_I18N[lang], lang=lang)
    try:
        from weasyprint import HTML as WP_HTML
        pdf_bytes = WP_HTML(string=html_content, base_url=request.host_url).write_pdf()
    except Exception as e:
        app.logger.error('Certificate PDF error: %s', e)
        record_audit_event('pdf_downloaded', user_id=current_user.id,
                            detail='rank_cert rank=%d FAILED' % rank, success=False)
        abort(500)
    record_audit_event('pdf_downloaded', user_id=current_user.id,
                        detail='rank_cert rank=%d code=%s' % (rank, cert.code))
    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = (
        'attachment; filename="trader-accelerator-%s.pdf"' % cert.code)
    return resp


@app.route('/verify/<code>')
def verify_certificate(code):
    """Public authenticity check — the real anti-forgery mechanism. Anyone can
    confirm a certificate code resolves to a genuine holder, rank and date."""
    cert = RankCertificate.query.filter_by(code=(code or '').strip()).first()
    valid = cert is not None
    lang = _cert_lang(request)
    return render_template(
        'verify_certificate.html', valid=valid, cert=cert,
        rank_name=(RANK_CERT_NAMES_ES[cert.rank - 1] if valid else None),
        medal_svg=(rank_medal_svg(cert.rank, 96) if valid else None),
        code=code, vl=VERIFY_I18N[lang])


# ──────────────────────────────────────────────────────────────────────────
# ANALYSIS PROJECTS (saved presets for the Analyze form)
# ──────────────────────────────────────────────────────────────────────────
# Fields a project may store. Direction & Result are intentionally excluded —
# they are per-trade outcomes the user marks fresh on every analysis.
PROJECT_SINGLE_FIELDS = ('instrument', 'session', 'htf_bias', 'aligned', 'approach')
PROJECT_MULTI_FIELDS = ('confluences',)


def _sanitize_project_config(raw):
    """Keep only known fields, coerce types, cap sizes. Returns a clean dict."""
    cfg = {}
    if not isinstance(raw, dict):
        return cfg
    for k in PROJECT_SINGLE_FIELDS:
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            cfg[k] = v.strip()[:60]
    for k in PROJECT_MULTI_FIELDS:
        v = raw.get(k)
        if isinstance(v, list):
            cfg[k] = [str(x).strip()[:60] for x in v if isinstance(x, str) and x.strip()][:30]
    return cfg


def serialize_project(p):
    return {
        'id': p.id,
        'name': p.name,
        'config': p.config or {},
        'updated_at': _as_utc(p.updated_at).isoformat() if p.updated_at else None,
    }


@app.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    rows = (AnalysisProject.query
            .filter_by(user_id=current_user.id)
            .order_by(AnalysisProject.updated_at.desc())
            .all())
    return jsonify({
        'projects': [serialize_project(p) for p in rows],
        'limit': project_limit(),
        'used': len(rows),
    })


@app.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()[:60]
    if len(name) < 1:
        return jsonify({'error': 'name_required'}), 400

    count = AnalysisProject.query.filter_by(user_id=current_user.id).count()
    if count >= project_limit():
        return jsonify({'error': 'limit_reached', 'limit': project_limit()}), 403

    proj = AnalysisProject(
        user_id=current_user.id,
        name=name,
        config=_sanitize_project_config(data.get('config')),
    )
    db.session.add(proj)
    db.session.commit()
    return jsonify({'ok': True, 'project': serialize_project(proj)})


@app.route('/api/projects/<int:pid>', methods=['PUT'])
@login_required
def update_project(pid):
    proj = AnalysisProject.query.filter_by(id=pid, user_id=current_user.id).first()
    if not proj:
        return jsonify({'error': 'not_found'}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()[:60]
        if len(name) < 1:
            return jsonify({'error': 'name_required'}), 400
        proj.name = name
    if 'config' in data:
        proj.config = _sanitize_project_config(data.get('config'))
    db.session.commit()
    return jsonify({'ok': True, 'project': serialize_project(proj)})


@app.route('/api/projects/<int:pid>', methods=['DELETE'])
@login_required
def delete_project(pid):
    proj = AnalysisProject.query.filter_by(id=pid, user_id=current_user.id).first()
    if not proj:
        return jsonify({'error': 'not_found'}), 404
    db.session.delete(proj)
    db.session.commit()
    return jsonify({'ok': True})


# ──────────────────────────────────────────────────────────────────────────
# PRE-FLIGHT (confluence checklist trainer)
# ──────────────────────────────────────────────────────────────────────────
PREFLIGHT_VERDICTS = ('go', 'caution', 'no-go')
PREFLIGHT_OUTCOMES = ('win', 'loss', 'skipped')


def _sanitize_checklist_config(raw):
    """Keep only known fields, coerce types, cap sizes. Returns a clean dict."""
    cfg = {'confluences': [], 'min_go': 0, 'min_caution': 0}
    if not isinstance(raw, dict):
        return cfg
    rows = raw.get('confluences')
    if isinstance(rows, list):
        for i, row in enumerate(rows[:20]):
            if not isinstance(row, dict):
                continue
            label = str(row.get('label', '')).strip()[:80]
            if not label:
                continue
            cid = str(row.get('id', '')).strip()[:24] or f'c{i + 1}'
            cfg['confluences'].append({'id': cid, 'label': label})
    n = len(cfg['confluences'])
    # Defaults: GO = all-but-one, CAUTION = simple majority. Clamp user values to [1, n].
    def _clamp(v, default):
        try:
            v = int(v)
        except (TypeError, ValueError):
            return default
        return max(1, min(n, v)) if n else 0
    cfg['min_go'] = _clamp(raw.get('min_go'), max(1, n - 1) if n else 0)
    cfg['min_caution'] = _clamp(raw.get('min_caution'), (n // 2 + 1) if n else 0)
    if n and cfg['min_caution'] > cfg['min_go']:
        cfg['min_caution'] = cfg['min_go']
    return cfg


def serialize_checklist(c):
    return {
        'id': c.id,
        'name': c.name,
        'config': c.config or {},
        'updated_at': _as_utc(c.updated_at).isoformat() if c.updated_at else None,
    }


def serialize_check(c):
    return {
        'id': c.id,
        'checklist_id': c.checklist_id,
        'checklist_name': c.checklist_name,
        'checked': c.checked or [],
        'total': c.total,
        'score': c.score,
        'verdict': c.verdict,
        'outcome': c.outcome,
        'note': c.note,
        'trade_date': c.trade_date.isoformat() if c.trade_date else None,
        'instrument': c.instrument,
        'direction': c.direction,
        'entry_price': c.entry_price,
        'exit_price': c.exit_price,
        'rr': c.rr,
        'position_size': c.position_size,
        'pnl': c.pnl,
        'created_at': _as_utc(c.created_at).isoformat() if c.created_at else None,
    }


def _parse_trade_meta(data):
    """Pull the optional trade-metadata fields out of a request payload.

    Every field is optional and silently dropped (None) if missing or
    malformed — this is a discipline log, not a strict ledger.
    """
    from datetime import date as _date
    meta = {}
    raw_date = data.get('trade_date')
    if isinstance(raw_date, str) and raw_date.strip():
        try:
            meta['trade_date'] = _date.fromisoformat(raw_date.strip()[:10])
        except ValueError:
            meta['trade_date'] = None
    else:
        meta['trade_date'] = None

    instrument = data.get('instrument')
    meta['instrument'] = str(instrument).strip()[:20].upper() if isinstance(instrument, str) and instrument.strip() else None

    direction = data.get('direction')
    direction = str(direction).strip().lower() if isinstance(direction, str) else None
    meta['direction'] = direction if direction in ('long', 'short') else None

    def _num(key, lo=None, hi=None):
        v = data.get(key)
        if v is None or v == '':
            return None
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        if lo is not None:
            v = max(lo, v)
        if hi is not None:
            v = min(hi, v)
        return v

    meta['entry_price'] = _num('entry_price', 0)
    meta['exit_price'] = _num('exit_price', 0)
    meta['rr'] = _num('rr', -100, 100)
    meta['position_size'] = _num('position_size', 0)
    meta['pnl'] = _num('pnl', -1e9, 1e9)
    return meta


def _preflight_guard():
    """Pre-Flight is a Premium-only feature. APIs answer 404 while the feature is
    disabled, and 403 for non-premium plans (admins always pass via is_premium)."""
    if not PREFLIGHT_ENABLED:
        return jsonify({'error': 'not_found'}), 404
    if not is_premium():
        return jsonify({'error': 'premium_required'}), 403
    return None


@app.route('/api/preflight/checklists', methods=['GET'])
@login_required
def preflight_list_checklists():
    guard = _preflight_guard()
    if guard:
        return guard
    rows = (PreflightChecklist.query
            .filter_by(user_id=current_user.id)
            .order_by(PreflightChecklist.updated_at.desc())
            .all())
    return jsonify({
        'checklists': [serialize_checklist(c) for c in rows],
        'limit': project_limit(),
        'used': len(rows),
    })


@app.route('/api/preflight/checklists', methods=['POST'])
@login_required
def preflight_create_checklist():
    guard = _preflight_guard()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()[:60]
    if len(name) < 1:
        return jsonify({'error': 'name_required'}), 400

    count = PreflightChecklist.query.filter_by(user_id=current_user.id).count()
    if count >= project_limit():
        return jsonify({'error': 'limit_reached', 'limit': project_limit()}), 403

    cfg = _sanitize_checklist_config(data.get('config'))
    if not cfg['confluences']:
        return jsonify({'error': 'confluences_required'}), 400
    cl = PreflightChecklist(user_id=current_user.id, name=name, config=cfg)
    db.session.add(cl)
    db.session.commit()
    return jsonify({'ok': True, 'checklist': serialize_checklist(cl)})


@app.route('/api/preflight/checklists/<int:cid>', methods=['PUT'])
@login_required
def preflight_update_checklist(cid):
    guard = _preflight_guard()
    if guard:
        return guard
    cl = PreflightChecklist.query.filter_by(id=cid, user_id=current_user.id).first()
    if not cl:
        return jsonify({'error': 'not_found'}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()[:60]
        if len(name) < 1:
            return jsonify({'error': 'name_required'}), 400
        cl.name = name
    if 'config' in data:
        cfg = _sanitize_checklist_config(data.get('config'))
        if not cfg['confluences']:
            return jsonify({'error': 'confluences_required'}), 400
        cl.config = cfg
    db.session.commit()
    return jsonify({'ok': True, 'checklist': serialize_checklist(cl)})


@app.route('/api/preflight/checklists/<int:cid>', methods=['DELETE'])
@login_required
def preflight_delete_checklist(cid):
    guard = _preflight_guard()
    if guard:
        return guard
    cl = PreflightChecklist.query.filter_by(id=cid, user_id=current_user.id).first()
    if not cl:
        return jsonify({'error': 'not_found'}), 404
    # Keep logged checks (their snapshots stay valid) — just detach the FK.
    PreflightCheck.query.filter_by(user_id=current_user.id, checklist_id=cl.id)\
        .update({'checklist_id': None})
    db.session.delete(cl)
    db.session.commit()
    return jsonify({'ok': True})


def _preflight_stats(rows):
    """Simple discipline stats over the user's checks (win/loss only count)."""
    decided = [c for c in rows if c.outcome in ('win', 'loss')]
    wins = [c for c in decided if c.outcome == 'win']

    def _rate(subset):
        return round(100.0 * sum(1 for c in subset if c.outcome == 'win') / len(subset), 1) if subset else None

    go = [c for c in decided if c.verdict == 'go']
    not_go = [c for c in decided if c.verdict != 'go']

    # Per-confluence ranking: win rate of decided checks where the label was ticked.
    per = {}
    for c in decided:
        for label in (c.checked or []):
            d = per.setdefault(label, {'wins': 0, 'n': 0})
            d['n'] += 1
            d['wins'] += 1 if c.outcome == 'win' else 0
    ranking = sorted(
        ({'label': k, 'n': v['n'], 'win_rate': round(100.0 * v['wins'] / v['n'], 1)}
         for k, v in per.items() if v['n'] >= 2),
        key=lambda r: (r['win_rate'], r['n']), reverse=True)

    return {
        'total_checks': len(rows),
        'decided': len(decided),
        'win_rate': _rate(decided),
        'win_rate_go': _rate(go),
        'win_rate_not_go': _rate(not_go),
        'top_confluence': ranking[0] if ranking else None,
        'confluence_ranking': ranking[:10],
    }


@app.route('/api/preflight/checks', methods=['GET'])
@login_required
def preflight_list_checks():
    guard = _preflight_guard()
    if guard:
        return guard
    rows = (PreflightCheck.query
            .filter_by(user_id=current_user.id)
            .order_by(PreflightCheck.created_at.desc())
            .limit(500)
            .all())
    return jsonify({
        'checks': [serialize_check(c) for c in rows],
        'stats': _preflight_stats(rows),
    })


@app.route('/api/preflight/checks', methods=['POST'])
@login_required
def preflight_create_check():
    guard = _preflight_guard()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    name = (data.get('checklist_name') or '').strip()[:60]
    if not name:
        return jsonify({'error': 'name_required'}), 400
    verdict = data.get('verdict')
    if verdict not in PREFLIGHT_VERDICTS:
        return jsonify({'error': 'bad_verdict'}), 400
    checked_raw = data.get('checked')
    checked = ([str(x).strip()[:80] for x in checked_raw if isinstance(x, str) and x.strip()][:20]
               if isinstance(checked_raw, list) else [])
    try:
        total = max(0, min(20, int(data.get('total', 0))))
    except (TypeError, ValueError):
        total = 0
    checklist_id = data.get('checklist_id')
    if checklist_id is not None:
        cl = PreflightChecklist.query.filter_by(id=checklist_id, user_id=current_user.id).first()
        checklist_id = cl.id if cl else None

    meta = _parse_trade_meta(data)
    check = PreflightCheck(
        user_id=current_user.id,
        checklist_id=checklist_id,
        checklist_name=name,
        checked=checked,
        total=total,
        score=len(checked),
        verdict=verdict,
        note=(str(data.get('note') or '').strip()[:200] or None),
        **meta,
    )
    db.session.add(check)
    db.session.commit()
    # XP: a one-time bonus for the very first logged check ever, then +5/check
    # capped at the first 3/day (function itself stays unlimited). Pre-Flight XP
    # is a premium-only source — this endpoint is only @login_required, so gate
    # the reward here so free/standard can't farm it by calling the API directly.
    if is_premium():
        if not current_user.first_preflight_xp:
            current_user.first_preflight_xp = True
            db.session.commit()
            add_xp(current_user, 'preflight_first', ref='first')
        add_xp(current_user, 'preflight_check')
    return jsonify({'ok': True, 'check': serialize_check(check)})


@app.route('/api/preflight/checks/<int:cid>', methods=['PUT'])
@login_required
def preflight_update_check(cid):
    guard = _preflight_guard()
    if guard:
        return guard
    check = PreflightCheck.query.filter_by(id=cid, user_id=current_user.id).first()
    if not check:
        return jsonify({'error': 'not_found'}), 404
    data = request.get_json(silent=True) or {}
    if 'outcome' in data:
        outcome = data.get('outcome')
        if outcome is not None and outcome not in PREFLIGHT_OUTCOMES:
            return jsonify({'error': 'bad_outcome'}), 400
        check.outcome = outcome
    if 'note' in data:
        check.note = str(data.get('note') or '').strip()[:200] or None
    meta_keys = ('trade_date', 'instrument', 'direction', 'entry_price', 'exit_price', 'rr', 'position_size', 'pnl')
    if any(k in data for k in meta_keys):
        meta = _parse_trade_meta(data)
        for k in meta_keys:
            if k in data:
                setattr(check, k, meta[k])
    db.session.commit()
    return jsonify({'ok': True, 'check': serialize_check(check)})


@app.route('/api/preflight/checks/<int:cid>', methods=['DELETE'])
@login_required
def preflight_delete_check(cid):
    guard = _preflight_guard()
    if guard:
        return guard
    check = PreflightCheck.query.filter_by(id=cid, user_id=current_user.id).first()
    if not check:
        return jsonify({'error': 'not_found'}), 404
    db.session.delete(check)
    db.session.commit()
    return jsonify({'ok': True})


# ──────────────────────────────────────────────────────────────────────────
# BOOTSTRAP: create tables + seed admin
# ──────────────────────────────────────────────────────────────────────────
def _migrate_user_verification_columns():
    """Add the email-verification columns to an existing SQLite `user` table.

    db.create_all() never ALTERs existing tables, so accounts created before
    this feature need the new columns added by hand. Pre-existing users are
    marked verified so the new mandatory-verification flow can't lock them out.
    """
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns('user')}
    stmts = []
    if 'email_verified' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0")
    if 'verification_code' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN verification_code VARCHAR(6)")
    if 'verification_expires' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN verification_expires DATETIME")
    grandfather = bool(stmts)  # only mark-all-verified on the verification migration
    # ── Ban columns (added later; must not re-trigger the grandfather UPDATE) ──
    if 'is_banned' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN is_banned BOOLEAN NOT NULL DEFAULT 0")
    if 'banned_at' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN banned_at DATETIME")
    if 'ban_reason' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN ban_reason VARCHAR(300)")
    # ── Terms acceptance column (added later; left NULL for pre-existing users,
    #    who accept on their next login via the passive consent notice) ──
    if 'terms_accepted_at' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN terms_accepted_at DATETIME")
    if 'terms_version' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN terms_version VARCHAR(20)")
    # ── Paid-plan lifecycle columns ──
    if 'plan_cycle' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN plan_cycle VARCHAR(10)")
    if 'plan_started_at' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN plan_started_at DATETIME")
    if 'plan_expires_at' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN plan_expires_at DATETIME")
    if 'cancel_at_period_end' not in cols:
        stmts.append("ALTER TABLE user ADD COLUMN cancel_at_period_end BOOLEAN NOT NULL DEFAULT 0")
    if stmts:
        with db.engine.begin() as conn:
            for s in stmts:
                conn.execute(text(s))
            # Grandfather in every account that predates verification.
            if grandfather:
                conn.execute(text("UPDATE user SET email_verified = 1"))
        app.logger.info('Migrated user table: added missing columns (%d).', len(stmts))


def _migrate_user_alt_id_column():
    """Add `alt_id` and backfill it for every existing user.

    Login/remember-me cookies store this value instead of the numeric
    primary key, so cookies issued before this migration (or before a
    DB engine swap that could shift numeric ids) simply stop matching
    any account instead of risking a mismatch.
    """
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns('user')}
    if 'alt_id' not in cols:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE "user" ADD COLUMN alt_id VARCHAR(40)'))
            conn.execute(text('CREATE UNIQUE INDEX ix_user_alt_id ON "user" (alt_id)'))
        app.logger.info('Migrated user table: added alt_id column + index.')

    users_without_alt_id = User.query.filter(
        (User.alt_id.is_(None)) | (User.alt_id == '')
    ).all()
    if users_without_alt_id:
        for u in users_without_alt_id:
            u.alt_id = secrets.token_hex(20)
        db.session.commit()
        app.logger.info('Backfilled alt_id for %d existing user(s).', len(users_without_alt_id))


def _migrate_order_columns():
    """Add `celebrated_at` to an existing order table.
    NOTE: "order" is a reserved word in both SQLite and PostgreSQL — keep it quoted."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    if 'order' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('order')}
    if 'celebrated_at' not in cols:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE "order" ADD COLUMN celebrated_at TIMESTAMP'))
        app.logger.info('Migrated order table: added celebrated_at column.')


def _migrate_promo_code_columns():
    """Add `restrict_user_id` to an existing promo_code table."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    if 'promo_code' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('promo_code')}
    if 'restrict_user_id' not in cols:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE promo_code ADD COLUMN restrict_user_id INTEGER"))
        app.logger.info('Migrated promo_code table: added restrict_user_id column.')


def _migrate_preflight_check_columns():
    """Add the trade-metadata columns to an existing `preflight_check` table.

    db.create_all() never ALTERs existing tables, so checks logged before
    this feature need the new (all-nullable) columns added by hand.
    """
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    if 'preflight_check' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('preflight_check')}
    stmts = []
    if 'trade_date' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN trade_date DATE")
    if 'instrument' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN instrument VARCHAR(20)")
    if 'direction' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN direction VARCHAR(10)")
    if 'entry_price' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN entry_price FLOAT")
    if 'exit_price' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN exit_price FLOAT")
    if 'rr' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN rr FLOAT")
    if 'position_size' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN position_size FLOAT")
    if 'pnl' not in cols:
        stmts.append("ALTER TABLE preflight_check ADD COLUMN pnl FLOAT")
    if stmts:
        with db.engine.begin() as conn:
            for s in stmts:
                conn.execute(text(s))
        app.logger.info('Migrated preflight_check table: added missing columns (%d).', len(stmts))


def _migrate_user_review_column():
    """Add `last_review_prompt_at` to an existing user table."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns('user')}
    if 'last_review_prompt_at' not in cols:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE "user" ADD COLUMN last_review_prompt_at TIMESTAMP'))
        app.logger.info('Migrated user table: added last_review_prompt_at column.')


def _migrate_user_xp_columns():
    """Add the XP/Rank columns to an existing user table. MUST run before the
    alt_id migration (whose ORM backfill SELECTs every User column)."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns('user')}
    stmts = []
    if 'xp' not in cols:
        stmts.append('ALTER TABLE "user" ADD COLUMN xp INTEGER NOT NULL DEFAULT 0')
    if 'rank' not in cols:
        stmts.append('ALTER TABLE "user" ADD COLUMN rank INTEGER NOT NULL DEFAULT 1')
    if 'last_xp_active_date' not in cols:
        stmts.append('ALTER TABLE "user" ADD COLUMN last_xp_active_date VARCHAR(10)')
    if 'first_preflight_xp' not in cols:
        stmts.append('ALTER TABLE "user" ADD COLUMN first_preflight_xp BOOLEAN NOT NULL DEFAULT FALSE')
    add_rank_celebrated = 'rank_celebrated' not in cols
    if add_rank_celebrated:
        stmts.append('ALTER TABLE "user" ADD COLUMN rank_celebrated INTEGER NOT NULL DEFAULT 1')
    if stmts:
        with db.engine.begin() as conn:
            for s in stmts:
                conn.execute(text(s))
            # Suppress retroactive celebrations: seal existing users at their
            # current rank so nobody is greeted by a reveal for a rank they
            # earned long before this feature shipped. New rank-ups still fire.
            if add_rank_celebrated:
                conn.execute(text('UPDATE "user" SET rank_celebrated = rank'))
        app.logger.info('Migrated user table: added XP/Rank columns (%d).', len(stmts))


def _migrate_user_mute_column():
    """Add `muted_until` (temporary forum auto-mute) to an existing user table."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns('user')}
    if 'muted_until' not in cols:
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE "user" ADD COLUMN muted_until TIMESTAMP'))
        app.logger.info('Migrated user table: added muted_until column.')


def init_db():
    with app.app_context():
        db.create_all()
        _migrate_user_verification_columns()
        # NOTE: these column migrations must run BEFORE the alt_id one — the
        # alt_id backfill issues an ORM query that SELECTs every User column,
        # so any column the model knows about must already exist.
        _migrate_user_review_column()
        _migrate_user_xp_columns()
        _migrate_user_mute_column()
        _migrate_user_alt_id_column()
        _migrate_order_columns()
        _migrate_promo_code_columns()
        _migrate_preflight_check_columns()
        admin_email = os.environ.get('ADMIN_EMAIL', 'mauroramirezmij@gmail.com').lower()
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Codica2310$')
        if not User.query.filter_by(email=admin_email).first():
            admin = User(
                username=admin_username,
                email=admin_email,
                plan='premium',
                is_admin=True,
                email_verified=True,
                terms_accepted_at=datetime.now(timezone.utc),
                terms_version=TERMS_VERSION,
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            try:
                db.session.commit()
                app.logger.info('Seeded admin account: %s', admin_email)
            except Exception:
                db.session.rollback()
        init_scout_data()


init_db()
_load_quiz_key()


# ── Health check endpoint ──────────────────────────────────────────────────
@app.route('/health')
def health_check():
    """Public health endpoint — exposes site metrics for monitoring scripts."""
    try:
        user_count   = User.query.count()
        paid_users   = User.query.filter(User.plan != 'free').count()
        pending_orders = Order.query.filter_by(status='pending').count()
        db_path = os.path.join(BASE_DIR, 'scalpel.db')
        db_size_mb = round(os.path.getsize(db_path) / 1024 / 1024, 2) if os.path.exists(db_path) else 0
        return jsonify({
            'status':          'ok',
            'timestamp':       datetime.now(timezone.utc).isoformat(),
            'users_total':     user_count,
            'users_paid':      paid_users,
            'orders_pending':  pending_orders,
            'db_size_mb':      db_size_mb,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 500


# ── Global error handler — sends WhatsApp alert on 500s ───────────────────
@app.errorhandler(500)
def handle_500(e):
    msg = (f"🚨 *Trader Accelerator — ERROR 500*\n"
           f"URL: {request.url}\n"
           f"Error: {str(e)[:200]}\n"
           f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    send_whatsapp_alert(msg)
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
