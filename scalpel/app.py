import os
import re
import json
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


# ── Expose feature flags to every template ──
@app.context_processor
def inject_feature_flags():
    return {'scout_enabled': SCOUT_ENABLED, 'preflight_enabled': PREFLIGHT_ENABLED}


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
    'standard': {'monthly': 10.0, 'annual': 96.0},
    'premium':  {'monthly': 30.0, 'annual': 288.0},
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
    subject = f'[Trader Acelerator] Action needed — {event_type} failed'
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
PROJECT_LIMITS = {'free': 2, 'standard': 5, 'premium': 10}


def project_limit():
    """How many analysis projects the current user may save."""
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
    msg = Message('Trader Acelerator — Verify your email', recipients=[to_email])
    msg.body = (
        "Welcome to Trader Acelerator!\n\n"
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
    subject = f'[Trader Acelerator Contact] {category} — {sender_name}'
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

Concrete example of what ICT interpretation variance looks like:
- Some traders consider a FVG breached the moment any candle body closes inside it. Others require a full strong candle to close through it. Others will accept a partial entry even after a body has touched the FVG, as long as subsequent price action respects it. None of these is "wrong" — they reflect different personal rules.
- Some traders require a full MSS (with displacement candle) to confirm entry. Others enter on a soft CHoCH with no displacement. Both can be valid depending on the overall context and the trader's risk tolerance.
The AI must never pick one interpretation and label others as errors. Raise observations as things the trader may want to check against THEIR OWN rules — not against a universal standard.

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

ANALYSIS PROCESS:
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
    # Consume the pass so the next entry triggers the splash again.
    resp = make_response(render_template(
        'index.html',
        plan=current_plan(),
        is_admin=current_user.is_admin,
        username=current_user.username,
        is_guest=False,
        unlock_plan=unlock_plan,
        review_prompt=review_prompt,
        user_rank=current_user.rank or 1,
        user_xp=current_user.xp or 0,
    ))
    resp.delete_cookie('scalpel_splash_ts')
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

    return render_template(
        'admin.html', users=users, counts=counts,
        audit_events=audit_events, audit_failed_count=audit_failed_count,
        warn_counts=warn_counts, recent_warnings=recent_warnings, flagged=flagged,
        ban_queue=ban_queue, **revenue,
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
  <div class="cv-brand">Trader Acelerator</div>
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
        if current_user.is_authenticated:
            add_xp(current_user, 'analysis')
        return jsonify({'analysis': analysis})

    except Exception as e:
        error_msg = str(e)
        record_audit_event('analysis_error',
                            user_id=current_user.id if current_user.is_authenticated else None,
                            detail=error_msg[:300], success=False)
        if 'token' in error_msg.lower() or 'auth' in error_msg.lower() or '401' in error_msg:
            return jsonify({'error': 'Authentication failed. Check your GITHUB_TOKEN in the .env file.'}), 401
        if '429' in error_msg:
            return jsonify({'error': 'Rate limit reached. Please wait a moment and try again.'}), 429
        return jsonify({'error': f'Analysis failed: {error_msg}'}), 500


# ──────────────────────────────────────────────────────────────────────────
# TRADING FORUM (premium-only community)
# ──────────────────────────────────────────────────────────────────────────
EMOJI_SET = {'like', 'love', 'fire', 'chart', 'think'}
DAILY_POST_LIMIT = 2
FORUM_FEED_PAGE = 10


CONDUCT_BAN_THRESHOLD = 3   # warnings that trigger a ban *suggestion* (not a ban)


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
    if todays_post_count(current_user.id) >= DAILY_POST_LIMIT:
        return jsonify({'error': 'daily_limit', 'limit': DAILY_POST_LIMIT}), 429

    title = (request.form.get('title') or '').strip()
    body = (request.form.get('body') or '').strip()
    if len(title) < 4 or len(body) < 10:
        return jsonify({'error': 'too_short'}), 400
    title = title[:160]
    body = body[:8000]

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
    correct = bool((request.json or {}).get('correct')) and not timed_out

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
    st = _daily_state()
    if st.spins_available <= 0:
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
    """Award XP for a correctly answered quiz question. The quiz bank lives
    client-side, so the client reports (question_id, level); a question only
    ever pays once (dedup by ref) and the whole source is capped at 20 XP/day,
    so even a forged report can't farm faster than an honest user."""
    data = request.get_json(silent=True) or {}
    qid = str(data.get('question_id') or '').strip()[:60]
    level = str(data.get('level') or '').strip()
    if not qid or level not in ('beginner', 'intermediate', 'advanced'):
        return jsonify({'error': 'bad_request'}), 400
    amount = XP_PREMIUM.get(f'quiz_{level}', 0)
    awarded = add_xp(current_user, 'quiz', amount=amount, ref=f'q:{qid}')
    return jsonify({'ok': True, 'awarded': awarded, 'xp': current_user.xp,
                    'rank': current_user.rank})


def _rank_progress_payload(user):
    xp = user.xp or 0
    rank = rank_for_xp(xp)
    cur_floor = RANK_THRESHOLDS[rank - 1]
    next_floor = RANK_THRESHOLDS[rank] if rank < len(RANK_THRESHOLDS) else None
    plan = user.plan or 'free'
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
    return jsonify(_rank_progress_payload(current_user))


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
    """Mirror the Scout pattern: APIs answer 404 while the feature is disabled."""
    if not PREFLIGHT_ENABLED:
        return jsonify({'error': 'not_found'}), 404
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
    if stmts:
        with db.engine.begin() as conn:
            for s in stmts:
                conn.execute(text(s))
        app.logger.info('Migrated user table: added XP/Rank columns (%d).', len(stmts))


def init_db():
    with app.app_context():
        db.create_all()
        _migrate_user_verification_columns()
        # NOTE: these column migrations must run BEFORE the alt_id one — the
        # alt_id backfill issues an ORM query that SELECTs every User column,
        # so any column the model knows about must already exist.
        _migrate_user_review_column()
        _migrate_user_xp_columns()
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
    msg = (f"🚨 *Trader Acelerator — ERROR 500*\n"
           f"URL: {request.url}\n"
           f"Error: {str(e)[:200]}\n"
           f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    send_whatsapp_alert(msg)
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
