import os
import re
import json
import hmac
import hashlib
import gzip
import base64
import socket
import secrets
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import (
    Flask, render_template, request, jsonify, send_file,
    redirect, url_for, abort, make_response, session, has_request_context
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
# Display name on every outbound email. Was still the old "Scalpel" brand;
# env-driven so a domain mailbox only needs MAIL_* variables, no code change.
app.config['MAIL_DEFAULT_SENDER'] = (
    os.environ.get('MAIL_SENDER_NAME', 'Tradeable Academy'),
    os.environ.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
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

# Indicators store/library — fully built but HIDDEN until a viable delivery model
# exists (TradingView invite-only needs a Premium author + Pro customers, which
# kills it). Flip to True / set INDICATORS_ENABLED=1 to bring back the in-app tab,
# the /store/indicators route, the products-dropdown item and every pricing/landing
# mention instantly. Nothing was deleted.
INDICATORS_ENABLED = os.environ.get("INDICATORS_ENABLED", "0") in ("1", "true", "True")

# Mentorship funnel ("Find New Ways to Improve") — under construction. Hidden from
# the public while we build it: the funnel routes 404 for everyone EXCEPT admins
# (so we can preview by URL). Flip to True / set MENTORSHIP_ENABLED=1 to open it.
MENTORSHIP_ENABLED = os.environ.get("MENTORSHIP_ENABLED", "0") in ("1", "true", "True")

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
# By default the app talks to GitHub Models (free, rate-limited) via GITHUB_TOKEN.
# If OPENAI_API_KEY is set, it switches to the PAID OpenAI API instead — same
# model, same prompts, only the endpoint + key change. Fully reversible: unset the
# key and it falls back to GitHub Models on the next restart. This powers BOTH the
# analyzer and every other AI call (validation, forum moderation) since they all
# share this one client.
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "placeholder")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL          = os.environ.get("SCALPEL_MODEL", "gpt-4o")

if OPENAI_API_KEY:
    # Paid OpenAI — omitting base_url uses the SDK's default OpenAI endpoint.
    client = OpenAI(api_key=OPENAI_API_KEY)
    AI_BACKEND = "openai"
else:
    # Free GitHub Models (default).
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN,
    )
    AI_BACKEND = "github"

# Logged once at startup so the active backend is greppable in the stdout log
# (never prints the key itself).
print(f"[AI] backend={AI_BACKEND} model={MODEL}", flush=True)

# GPT-4o token pricing (USD per 1M tokens) — used only to ESTIMATE AI spend for the
# admin Analytics & AI-spend dashboard. Override via env if OpenAI changes prices.
AI_PRICE_IN_PER_1M  = float(os.environ.get("AI_PRICE_IN_PER_1M",  "2.50"))
AI_PRICE_OUT_PER_1M = float(os.environ.get("AI_PRICE_OUT_PER_1M", "10.0"))
AI_PRICE_IN  = AI_PRICE_IN_PER_1M  / 1_000_000
AI_PRICE_OUT = AI_PRICE_OUT_PER_1M / 1_000_000

# ── Vision image normalization ──
# Every chart screenshot is downscaled to a fixed max long-side BEFORE it reaches
# the vision API, so the per-analysis image cost stays bounded no matter what the
# trader uploads (a 4K screenshot and a Full-HD one both land at the same size).
# A trading chart stays fully legible at ~1280px, so this trims image tokens with
# no loss of analytic detail. Small images are never upscaled (that is the cost
# FLOOR); the fixed max is the cost CEILING. All tunable via env.
#   ANALYZE_IMG_MAX_PX=0 disables the resize entirely (send original).
#   ANALYZE_IMG_DETAIL: "high" (sharp, recommended) | "low" (flat min cost) | "auto".
#   ANALYZE_IMG_HARD_PX: reject absurd dimensions before decoding (RAM guard).
ANALYZE_IMG_MAX_PX  = int(os.environ.get("ANALYZE_IMG_MAX_PX", "1280"))
ANALYZE_IMG_DETAIL  = os.environ.get("ANALYZE_IMG_DETAIL", "high").strip().lower()
ANALYZE_IMG_HARD_PX = int(os.environ.get("ANALYZE_IMG_HARD_PX", "8000"))


class ImageTooLarge(Exception):
    """Raised when an upload's pixel dimensions exceed the hard RAM guard."""


def normalize_chart_image(raw_bytes, content_type):
    """Downscale a chart screenshot to ANALYZE_IMG_MAX_PX on its long side so the
    per-analysis vision cost is bounded regardless of the uploaded resolution.
    Never upscales (small images keep their size → cost floor). Flattens any
    transparency onto white and re-encodes as JPEG. Raises ImageTooLarge for
    absurd dimensions (RAM guard). On any OTHER decode/encode failure it returns
    the original bytes unchanged, so an edge-case image never blocks an analysis."""
    if ANALYZE_IMG_MAX_PX <= 0:
        return raw_bytes, content_type
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes))
        w, h = img.size  # available without a full decode
        if ANALYZE_IMG_HARD_PX and (w > ANALYZE_IMG_HARD_PX or h > ANALYZE_IMG_HARD_PX):
            raise ImageTooLarge(f"{w}x{h} exceeds {ANALYZE_IMG_HARD_PX}px guard")
        long_side = max(w, h)
        if long_side <= ANALYZE_IMG_MAX_PX:
            return raw_bytes, content_type  # already within the cap → cost floor
        img.load()
        # Flatten transparency onto white (charts are opaque) so JPEG is safe.
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA')
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        scale = ANALYZE_IMG_MAX_PX / float(long_side)
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85, optimize=True)
        return buf.getvalue(), 'image/jpeg'
    except ImageTooLarge:
        raise
    except Exception as exc:  # decode/encode edge case → never block the analysis
        app.logger.warning('Image normalization failed (sending original): %s', exc)
        return raw_bytes, content_type


# ── Stripe (optional) — card payments. Fully inert until STRIPE_SECRET_KEY is
# set, so production keeps using the manual USDT/bank flow until you flip it on.
# Test mode: create a free Stripe account, grab the sk_test_… key, set it here
# (and STRIPE_WEBHOOK_SECRET if you run the webhook), then use test card
# 4242 4242 4242 4242 to walk the whole flow without moving real money.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
try:
    import stripe as _stripe          # optional dependency; app runs fine without it
except ImportError:
    _stripe = None
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY) and _stripe is not None
if STRIPE_ENABLED:
    _stripe.api_key = STRIPE_SECRET_KEY


# ── Crypto checkout (USDT) — the live rail while there is no company bank ──
# Same conditional pattern as Stripe and OpenAI: entirely inert until the keys
# are set, so nothing changes in production until you flip it on.
#   CRYPTO_API_KEY      — processor API key
#   CRYPTO_IPN_SECRET   — shared secret used to sign the payment notification
#   CRYPTO_PAY_CURRENCY — what the buyer sends (default USDT on TRON: cheap fees,
#                         the most widely used rail in Latin America)
# Prices are ALWAYS quoted in USD; the crypto is only the rail.
CRYPTO_API_KEY = os.environ.get("CRYPTO_API_KEY", "")
CRYPTO_IPN_SECRET = os.environ.get("CRYPTO_IPN_SECRET", "")
CRYPTO_API_BASE = os.environ.get("CRYPTO_API_BASE", "https://api.nowpayments.io/v1")
CRYPTO_PAY_CURRENCY = os.environ.get("CRYPTO_PAY_CURRENCY", "usdttrc20")
CRYPTO_ENABLED = bool(CRYPTO_API_KEY)
# What we promise publicly when the automatic path fails (hours).
CRYPTO_SLA_HOURS = 24


# ── PayPal (optional) — the card/PayPal-balance rail ──────────────────────
# Reaches the buyers USDT cannot: the United States, Canada and Europe, where
# almost nobody holds crypto. Same conditional pattern as everything else —
# without the keys nothing about production changes.
#   PAYPAL_CLIENT_ID / PAYPAL_SECRET — REST app credentials
#   PAYPAL_ENV       — 'sandbox' to rehearse with fake money, 'live' to charge
#   PAYPAL_WEBHOOK_ID— id of the webhook created in the PayPal dashboard; it is
#                      what lets us verify a notification really came from them
# Prices are always in USD here — PayPal settles in USD directly.
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET = os.environ.get("PAYPAL_SECRET", "")
PAYPAL_ENV = os.environ.get("PAYPAL_ENV", "live").strip().lower()
PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")
PAYPAL_API_BASE = ("https://api-m.sandbox.paypal.com" if PAYPAL_ENV == "sandbox"
                   else "https://api-m.paypal.com")
PAYPAL_ENABLED = bool(PAYPAL_CLIENT_ID and PAYPAL_SECRET)
# Shown to the buyer on PayPal's own page and on their receipt. Keeping it equal
# to the trade name in the Terms is what stops "I don't recognise this charge"
# disputes when the receiving account is held under a different name.
PAYPAL_BRAND_NAME = os.environ.get("PAYPAL_BRAND_NAME", "Tradeable Academy")


# ── Expose feature flags to every template ──
@app.before_request
def _mentorship_kill_switch():
    """One switch that darkens the whole programme.

    It runs BEFORE authentication, so a logged-out visitor gets a plain 404
    instead of being bounced to the login page — from the outside the feature
    simply does not exist. Nothing is deleted: flip MENTORSHIP_ENABLED back on
    and every route, page and legal clause returns exactly as it was."""
    if MENTORSHIP_ENABLED:
        return
    p = request.path
    if not (p.startswith('/improve') or p.startswith('/mentorship')
            or p.startswith('/api/ment/') or p.startswith('/api/improve')):
        return
    if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
        return          # the owner keeps the preview
    abort(404)


@app.context_processor
def inject_feature_flags():
    return {
        'scout_enabled': SCOUT_ENABLED,
        'indicators_enabled': INDICATORS_ENABLED,
        'mentorship_enabled': MENTORSHIP_ENABLED,
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

    # ── Camos (purchasable website skins) ──
    # active_camo: slug of the currently applied skin ('' / None = default theme).
    # owned_camos: JSON list of purchased skin slugs. Plan camos are owned via the
    # plan (not stored here); admins own everything (see owns_camo()).
    active_camo = db.Column(db.String(40), nullable=True, default='')
    owned_camos = db.Column(db.Text, nullable=True, default='')

    def camos_owned(self):
        try:
            return set(json.loads(self.owned_camos or '[]'))
        except Exception:
            return set()

    def add_camo(self, slug):
        owned = self.camos_owned()
        owned.add(slug)
        self.owned_camos = json.dumps(sorted(owned))

    def owns_camo(self, slug):
        """True if this user may activate the given camo.

        Admins own everything. Anything recorded in `owned_camos` is theirs for
        good — that covers both purchases and the camo granted with a plan,
        which the Terms promise stays with the account even if the plan later
        lapses. The plan checks below are what keep an active subscriber's camo
        working on accounts that predate that grant.
        """
        if self.is_admin:
            return True
        if slug in self.camos_owned():
            return True
        if slug == 'standard':
            return self.plan in ('standard', 'premium')
        if slug == 'premium':
            return self.plan == 'premium'
        return False

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
    community_id = db.Column(db.Integer, db.ForeignKey('forum_community.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User', backref='forum_posts')
    community = db.relationship('ForumCommunity', foreign_keys=[community_id])


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


class ForumCommunity(db.Model):
    """A user-created trading community (group) inside the forum. Posts can be
    published into a community; members browse it as a filtered feed."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    description = db.Column(db.String(240), nullable=True)
    emoji = db.Column(db.String(8), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    creator = db.relationship('User')


class ForumCommunityMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey('forum_community.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ForumFollow(db.Model):
    """follower_id follows followed_id (trader-to-trader, Instagram-style)."""
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ForumDM(db.Model):
    """Private 1-to-1 message between forum members (Standard+)."""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])


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

# ── Welcome offer ──────────────────────────────────────────────────────────
# A discount on a buyer's FIRST paid month. Deliberately open-ended: it stays
# up until switched off by hand (LAUNCH_DISCOUNT_PCT=0 + restart), so nothing
# expires on its own and surprises someone mid-purchase.
#
# First payment only, not a standing price cut. A discount that also applied to
# renewals would mean every monthly subscriber pays it forever — and switching
# it off later would hand every existing customer a price RISE, which is how
# you lose the people you already convinced.
#
# Monthly only, on purpose. The annual plan already costs ~20% less than twelve
# monthly payments, and taking 15% off its list price would land ABOVE what the
# annual already costs — an "offer" that made the plan dearer.
LAUNCH_DISCOUNT_PCT = int(os.environ.get("LAUNCH_DISCOUNT_PCT", "15"))
LAUNCH_DISCOUNT_CYCLES = ('monthly',)


def has_paid_before(user=None):
    """Whether this account has ever completed a purchase.

    Tied to the account, not to a cookie or a device: the welcome price is a
    property of the customer, so it survives a new browser and cannot be
    re-claimed by clearing storage.
    """
    u = user
    if u is None:
        u = current_user if current_user and current_user.is_authenticated else None
    if u is None or not getattr(u, 'is_authenticated', False):
        return False          # anonymous visitor — quote them the newcomer price
    try:
        return db.session.query(Order.id).filter(
            Order.user_id == u.id, Order.status == 'paid').first() is not None
    except Exception:
        return False


def launch_discount_for(cycle, user=None):
    """Percentage the welcome offer takes off this cycle (0 = none)."""
    if cycle not in LAUNCH_DISCOUNT_CYCLES or LAUNCH_DISCOUNT_PCT <= 0:
        return 0
    if has_paid_before(user):
        return 0
    return max(0, min(100, LAUNCH_DISCOUNT_PCT))

# ── Mentorship price book (SERVER-SIDE SOURCE OF TRUTH) ────────────────────
# The mentorship offer (/improve/plans) is a SEPARATE product line from the
# site subscription plans. The browser only ever sends a SKU key; the price is
# looked up HERE, never trusted from the client — so a package can never be
# charged the wrong amount, and a mentorship purchase can never touch
# `user.plan` (they go through their own MentorshipOrder + activation path).
# `kind` groups the SKU; `meetings` = number of 30-min 1-on-1 meetings bundled.
MENTORSHIP_SKUS = {
    'meet_single': {'label': 'Single meeting',        'price': 100.0, 'kind': 'meetings', 'meetings': 1},
    'meet3':       {'label': '3 meetings / month',    'price': 270.0, 'kind': 'meetings', 'meetings': 3},
    'meet6':       {'label': '6 meetings / month',    'price': 480.0, 'kind': 'meetings', 'meetings': 6},
    'library':     {'label': 'Recorded library',      'price': 350.0, 'kind': 'library',  'meetings': 0},
    'combo3':      {'label': 'Library + 3 meetings',  'price': 533.0, 'kind': 'combo',    'meetings': 3},
    'combo6':      {'label': 'Library + 6 meetings',  'price': 743.0, 'kind': 'combo',    'meetings': 6},
}


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
    # ── crypto rail ──────────────────────────────────────────────────────
    # `provider_ref` is the processor's invoice id: it is what lets us ASK the
    # processor about this order later, which is how a lost notification is
    # recovered without the buyer having to do anything.
    provider_ref = db.Column(db.String(80), nullable=True, index=True)
    pay_status = db.Column(db.String(24), nullable=True)       # waiting/confirming/finished/partial…
    paid_amount = db.Column(db.Float, nullable=True)           # what actually arrived (in pay currency)
    pay_currency = db.Column(db.String(20), nullable=True)
    tx_hash = db.Column(db.String(120), nullable=True)         # buyer-supplied or processor-reported
    alerted_at = db.Column(db.DateTime, nullable=True)         # problem alert already emailed
    user = db.relationship('User', backref='orders')


class MentorshipOrder(db.Model):
    """A purchase from the mentorship offer (/improve/plans).

    Deliberately a SEPARATE table from `Order`: a mentorship purchase must never
    be able to touch `user.plan` (site subscription), and a plan purchase must
    never grant mentorship. `price`/`label` are SNAPSHOTS taken server-side from
    MENTORSHIP_SKUS at creation, so the amount is fixed by the SKU, never the
    client. `applied_at` is the idempotency guard for fulfilment (notify once),
    mirroring Order — marking paid twice can never double-fire."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    sku = db.Column(db.String(20), nullable=False)            # meet3 / meet6 / combo6 / library / meet_single
    kind = db.Column(db.String(12), nullable=False)           # meetings / library / combo
    label = db.Column(db.String(80), nullable=False)          # snapshot at purchase
    price = db.Column(db.Float, nullable=False)               # snapshot (from SKU table, server-side)
    currency = db.Column(db.String(3), default='usd', nullable=False)
    status = db.Column(db.String(12), default='pending', nullable=False)  # pending/paid/cancelled
    payment_method = db.Column(db.String(30), nullable=True)  # 'stripe' / 'manual'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=True)        # fulfilment/notify ran (idempotency)
    note = db.Column(db.String(300), nullable=True)
    user = db.relationship('User', backref='mentorship_orders')


# ═══ Mentorship MEMBERS AREA (post-purchase) ═══════════════════════════════
class MentorshipFolder(db.Model):
    """A module/folder of the members video library."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    emoji = db.Column(db.String(8), nullable=True)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class MentorshipVideo(db.Model):
    """Library video metadata. The stream itself is hosted externally
    (Bunny / unlisted embed / direct mp4) — we store only the URL."""
    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('mentorship_folder.id'), nullable=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(500), nullable=False)
    duration_min = db.Column(db.Integer, nullable=True)
    kind = db.Column(db.String(12), default='class', nullable=False)  # class / live / backtest
    position = db.Column(db.Integer, default=0)
    # Where the stream lives. Derived from the URL on save, never typed by hand.
    # Today: youtube (unlisted embed) / file (direct mp4-webm-m3u8) / embed (other
    # iframe). Adding 'bunny' later only means a new value here + a branch in the
    # player — the rest of the library keeps working untouched.
    source = db.Column(db.String(12), default='embed', nullable=True)
    thumb_url = db.Column(db.String(500), nullable=True)     # cover shown before play
    provider_id = db.Column(db.String(120), nullable=True)   # youtube id / future bunny guid
    # JSON list of {"t": seconds, "label": "..."} — makes a 90-minute recording
    # navigable instead of a wall of video.
    chapters = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class MentorshipVideoComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('mentorship_video.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    body = db.Column(db.String(1000), nullable=False)
    # Second of the video this comment is about. The whole point of the feature:
    # "why did you exit at 12:30?" is answerable, "why did you exit?" is not.
    at_sec = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user = db.relationship('User')


class MentorshipNote(db.Model):
    """One private notebook per member per class. Never shown to anyone else,
    not even the mentor — it is the student's own scratchpad."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('mentorship_video.id'), nullable=False, index=True)
    body = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class MentorshipAttachment(db.Model):
    """Support material hanging off a class or a whole module: a PDF, an image,
    an external link, or a Chalkboard project the student can copy into their own
    board. Files are stored OUTSIDE /static and served through a member-gated
    route, so a leaked path is not a public download."""
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('mentorship_video.id'), nullable=True, index=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('mentorship_folder.id'), nullable=True, index=True)
    kind = db.Column(db.String(10), nullable=False)          # file / image / link / board
    title = db.Column(db.String(160), nullable=False)
    filename = db.Column(db.String(200), nullable=True)      # stored name (file/image)
    mime = db.Column(db.String(80), nullable=True)
    size = db.Column(db.Integer, nullable=True)
    url = db.Column(db.String(500), nullable=True)           # kind=link
    payload = db.Column(db.Text, nullable=True)              # kind=board: the board JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class MentorshipQuestion(db.Model):
    """Question box to the mentor; the mentor answers from the same page."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    body = db.Column(db.String(1000), nullable=False)
    answer = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    answered_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User')


class MentorshipChannel(db.Model):
    """A chat channel of the private members community. locked=True means an
    announcement channel where only the mentor/admin can post."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    emoji = db.Column(db.String(8), nullable=True)
    description = db.Column(db.String(200), nullable=True)
    locked = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class MentorshipMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('mentorship_channel.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    body = db.Column(db.String(2000), nullable=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('mentorship_message.id'), nullable=True)
    pinned = db.Column(db.Boolean, default=False, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user = db.relationship('User')


class MentorshipMsgReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('mentorship_message.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    emoji = db.Column(db.String(16), nullable=False)


class MentorshipProgress(db.Model):
    """Per-user watch progress: lets the area show 'continue watching' and a
    completion ring per folder."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('mentorship_video.id'), nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class MentorshipLiveState(db.Model):
    """Single-row switch the mentor flips when streaming live (plus the link),
    so the area shows the ON AIR banner instantly."""
    id = db.Column(db.Integer, primary_key=True)
    is_live = db.Column(db.Boolean, default=False, nullable=False)
    title = db.Column(db.String(160), nullable=True)
    url = db.Column(db.String(500), nullable=True)
    note = db.Column(db.String(300), nullable=True)
    # Area-wide settings live on this same singleton row (id=1) so we don't need
    # a second one-row table. `watermark_on` floats the viewer's username over
    # every video: it doesn't stop a determined ripper, it stops the casual
    # screen-recorder from reselling it anonymously. NULL (legacy row) = on.
    watermark_on = db.Column(db.Boolean, nullable=True, default=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


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


class BugReport(db.Model):
    """A user-submitted bug report. Kept in the DB (not just email) so nothing is
    lost and the admin can triage with status + notes. Technical context (page,
    browser, plan, recent console errors) is captured automatically so a real
    bug is verifiable without trusting the description — which also makes reports
    that just fish for a reward easy to dismiss."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    username = db.Column(db.String(40), nullable=True)              # snapshot (survives account changes)
    kind = db.Column(db.String(20), default='other', nullable=False)  # visual/broken/data/other
    description = db.Column(db.String(4000), nullable=False)
    page_url = db.Column(db.String(500), nullable=True)             # auto-captured
    user_agent = db.Column(db.String(400), nullable=True)          # auto-captured (server-side)
    plan = db.Column(db.String(20), nullable=True)                 # auto-captured
    console_log = db.Column(db.Text, nullable=True)                # recent client console errors
    status = db.Column(db.String(14), default='new', nullable=False)  # new/reviewing/resolved/not_repro
    admin_note = db.Column(db.String(600), nullable=True)
    rewarded = db.Column(db.Boolean, default=False, nullable=False)
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


class MentorshipApplication(db.Model):
    """One mentorship application ("The Great Filter", /improve/apply). Stored
    for manual review — nothing is auto-accepted; the mentor reveal and the
    pricing pages only come AFTER a human reviews the application. `user_id` is
    optional: the funnel is public, so visitors can apply with just an email.
    The waiver flags snapshot that the applicant explicitly acknowledged the
    educational nature of the program at submit time."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    name = db.Column(db.String(80), nullable=False)               # full legal name
    username = db.Column(db.String(40), nullable=True)            # account username (separate from full name)
    email = db.Column(db.String(255), nullable=False, index=True)
    experience = db.Column(db.String(20), nullable=False)     # lt1 / y1_3 / y3p
    situation = db.Column(db.String(20), nullable=False)      # demo / live / funded / inconsistent
    program = db.Column(db.String(12), nullable=True)         # rec / calls / both
    struggle = db.Column(db.String(600), nullable=False)      # legacy free text (now unused, '')
    why = db.Column(db.String(600), nullable=False)           # legacy free text (now unused, '')
    hours_week = db.Column(db.String(20), nullable=False)     # lt5 / h5_10 / h10p
    # FAQ-style profile (2026-07 form rework — all click-based, all required):
    goals = db.Column(db.String(200), nullable=True)          # CSV of goal keys
    strength = db.Column(db.String(20), nullable=True)        # strongest area
    weakness = db.Column(db.String(20), nullable=True)        # weakest area
    assets = db.Column(db.String(120), nullable=True)         # CSV: futures/forex
    country = db.Column(db.String(80), nullable=True)
    tzname = db.Column(db.String(60), nullable=True)          # browser IANA timezone (auto-captured)
    call_lang = db.Column(db.String(10), nullable=True)       # es / en / both (programs are ES/EN only)
    call_slot = db.Column(db.String(12), nullable=True)       # morning / afternoon / evening
    source = db.Column(db.String(20), nullable=True)          # how they found us
    age_range = db.Column(db.String(10), nullable=True)       # 18_24 / 25_34 / 35_44 / 45p
    waiver_accepted_at = db.Column(db.DateTime, nullable=False)
    lang = db.Column(db.String(5), nullable=True)             # UI language at submit time
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending/accepted/rejected
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Anti-spam bookkeeping (2026-07-26): a resubmit UPDATES the pending row, so
    # `created_at` alone can't throttle. `last_submit_at` is the real clock for
    # the 1-per-24h rule; `submit_ip` backs the per-device cap; `submit_count`
    # is audit only (how many times this profile was re-sent).
    last_submit_at = db.Column(db.DateTime, nullable=True, index=True)
    submit_ip = db.Column(db.String(45), nullable=True, index=True)   # IPv6-safe length
    submit_count = db.Column(db.Integer, default=1, nullable=True)
    user = db.relationship('User', backref='mentorship_applications')


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
    subject = f'[Tradeable] Action needed — {event_type} failed'
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

# Hard character ceiling for the analyzer's free-text Trade Construction. ~200
# real words fit well under this; the cap exists to stop a space-less spam blob
# (which a word count reads as one "word") from inflating the token bill.
NOTES_MAX_CHARS = 2000

# ── Camos (purchasable website skins) ──
# Every camo slug the store knows about (mirrors the cards in camos.html; the
# client maps each card's cm-<x> swatch class to one of these slugs).
CAMO_SLUGS = {
    'standard', 'premium',                                   # bundled with plan
    'naval', 'highnoon', 'rising-sun', 'mission', 'blackflag',
    'alchemist', 'shadow', 'pole', 'arcade', 'cyber',        # themes
    'santa', 'hallow', 'fourth', 'lucky', 'valentine',
    'easter', 'newyear', 'muertos',                          # seasonal
}
# Camos that actually have a theme built and can be activated today. The rest
# still render as "Coming soon" in the store. Add a slug here once its CSS ships.
CAMO_READY = {'rising-sun', 'pole', 'premium', 'fourth', 'naval', 'mission', 'blackflag'}

# The camo that ships with each paid plan. Granting it is part of what the
# buyer paid for, so it is written into the account (see grant_plan_camo).
PLAN_CAMOS = {'standard': 'standard', 'premium': 'premium'}

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
    """JSON guard for premium-only API endpoints (Daily Challenge, Prop Firm Scout)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'unauthorized'}), 401
        if not is_premium():
            return jsonify({'error': 'premium_required'}), 403
        return fn(*args, **kwargs)
    return wrapper


def is_standard_up():
    """True for any PAID plan (standard or premium) or admin."""
    return current_user.is_authenticated and (
        current_user.plan in ('standard', 'premium') or current_user.is_admin)


def standard_required(fn):
    """JSON guard for paid-plan API endpoints (Trading Forum: Standard + Premium
    since 2026-07-25 — it was premium-only before)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'unauthorized'}), 401
        if not is_standard_up():
            return jsonify({'error': 'standard_required'}), 403
        return fn(*args, **kwargs)
    return wrapper


def is_mentorship_member():
    """Members area access: the mentor/admin, or any user with a PAID mentorship
    order that includes the Classes Program (library / combo SKUs)."""
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, 'is_admin', False):
        return True
    return MentorshipOrder.query.filter(
        MentorshipOrder.user_id == current_user.id,
        MentorshipOrder.status == 'paid',
        MentorshipOrder.kind.in_(('library', 'combo'))).first() is not None


def mentorship_member_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # While the programme is shelved the whole surface is dark for everyone
        # but the admin — the data stays, only the door closes.
        if not MENTORSHIP_ENABLED and not (current_user.is_authenticated
                                           and getattr(current_user, 'is_admin', False)):
            return jsonify({'error': 'unavailable'}), 404
        if not current_user.is_authenticated:
            return jsonify({'error': 'unauthorized'}), 401
        if not is_mentorship_member():
            return jsonify({'error': 'membership_required'}), 403
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


# ── Email i18n ──────────────────────────────────────────────────────────────
# Emails are sent from the server, but the chosen UI language lives in the
# browser (localStorage `scalpel_lang`). The client mirrors that choice into a
# `scalpel_lang` cookie, which we read here to pick the email language.
# EN/ES/FR/PT are all filled.
EMAIL_I18N = {
    'reset': {
        'en': {
            'subject': 'Tradeable — Password Reset',
            'body': (
                "We received a request to reset your Tradeable password.\n\n"
                "Reset it here (link valid for 1 hour):\n{reset_url}\n\n"
                "If you didn't request this, you can safely ignore this email."
            ),
        },
        'es': {
            'subject': 'Tradeable — Restablecer contraseña',
            'body': (
                "Recibimos una solicitud para restablecer tu contraseña de Tradeable.\n\n"
                "Restablécela aquí (el enlace es válido por 1 hora):\n{reset_url}\n\n"
                "Si no solicitaste esto, puedes ignorar este correo sin problema."
            ),
        },
        'fr': {
            'subject': 'Tradeable — Réinitialisation du mot de passe',
            'body': (
                "Nous avons reçu une demande de réinitialisation de votre mot de passe Tradeable.\n\n"
                "Réinitialisez-le ici (lien valable 1 heure) :\n{reset_url}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet e-mail."
            ),
        },
        'pt': {
            'subject': 'Tradeable — Redefinição de senha',
            'body': (
                "Recebemos uma solicitação para redefinir sua senha do Tradeable.\n\n"
                "Redefina-a aqui (o link é válido por 1 hora):\n{reset_url}\n\n"
                "Se você não solicitou isto, pode ignorar este e-mail com segurança."
            ),
        },
    },
    'verify': {
        'en': {
            'subject': 'Tradeable — Verify your email',
            'body': (
                "Welcome to Tradeable!\n\n"
                "Your verification code is: {code}\n\n"
                "Enter it on the verification screen to activate your account. "
                "This code expires in 15 minutes.\n\n"
                "If you didn't create this account, you can safely ignore this email."
            ),
        },
        'es': {
            'subject': 'Tradeable — Verifica tu correo',
            'body': (
                "¡Bienvenido a Tradeable!\n\n"
                "Tu código de verificación es: {code}\n\n"
                "Ingrésalo en la pantalla de verificación para activar tu cuenta. "
                "Este código expira en 15 minutos.\n\n"
                "Si no creaste esta cuenta, puedes ignorar este correo sin problema."
            ),
        },
        'fr': {
            'subject': 'Tradeable — Vérifiez votre e-mail',
            'body': (
                "Bienvenue sur Tradeable !\n\n"
                "Votre code de vérification est : {code}\n\n"
                "Saisissez-le sur l'écran de vérification pour activer votre compte. "
                "Ce code expire dans 15 minutes.\n\n"
                "Si vous n'êtes pas à l'origine de ce compte, vous pouvez ignorer cet e-mail."
            ),
        },
        'pt': {
            'subject': 'Tradeable — Verifique seu e-mail',
            'body': (
                "Bem-vindo ao Tradeable!\n\n"
                "Seu código de verificação é: {code}\n\n"
                "Digite-o na tela de verificação para ativar sua conta. "
                "Este código expira em 15 minutos.\n\n"
                "Se você não criou esta conta, pode ignorar este e-mail com segurança."
            ),
        },
    },
}


def _email_lang():
    """Pick the email language from the `scalpel_lang` cookie. EN/ES/FR/PT are
    all available; anything else falls back to English."""
    if has_request_context():
        lang = request.cookies.get('scalpel_lang', 'en')
        if lang in ('en', 'es', 'fr', 'pt'):
            return lang
    return 'en'


def send_reset_email(to_email, reset_url):
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('MAIL_APP_PASSWORD not configured — cannot send reset email.')
        return False
    strings = EMAIL_I18N['reset'][_email_lang()]
    msg = Message(strings['subject'], recipients=[to_email])
    msg.body = strings['body'].format(reset_url=reset_url)
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
    strings = EMAIL_I18N['verify'][_email_lang()]
    msg = Message(strings['subject'], recipients=[to_email])
    msg.body = strings['body'].format(code=code)
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
    subject = f'[Tradeable Contact] {category} — {sender_name}'
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


def _send_bug_email(report):
    """Notify the admin inbox about a new bug report (best-effort). Returns True
    if sent. The report is already saved in the DB, so email is only a heads-up."""
    inbox = app.config.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('MAIL_APP_PASSWORD not set — bug report #%s not emailed.', report.id)
        return False
    subject = f'[Tradeable BUG] {report.kind} — #{report.id} ({report.username or "guest"})'
    body = (
        f"Bug #{report.id}\n"
        f"User     : {report.username or '—'} (id {report.user_id}, plan {report.plan or '—'})\n"
        f"Kind     : {report.kind}\n"
        f"Page     : {report.page_url or '—'}\n"
        f"Browser  : {report.user_agent or '—'}\n"
        f"{'─' * 48}\n\n{report.description}\n\n"
        f"{'─' * 48}\nRecent console errors:\n{report.console_log or '(none captured)'}\n"
        f"{'─' * 48}\nReview & triage in the admin panel → Bug Reports."
    )
    msg = Message(subject, recipients=[inbox])
    msg.body = body
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        app.logger.warning('Failed to send bug email: %s', exc)
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

@@SEC:ICT@@
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

OTE / STANDARD DEVIATION — A SELF-CONTAINED FIB-DRIVEN ENTRY STRATEGY (conceptual lens = ICT). This is the dedicated framework when the trader's approach is OTE / Std Dev — treat it as its OWN entry model, NOT as "ICT with a fib drawn on top." The trader THINKS in ICT terms (liquidity, displacement, premium/discount, PD arrays), but the ENTRY TRIGGER is fib-driven and distinct from a plain return-to-an-OB/FVG entry. Purpose reminder: you are explaining, retrospectively and educationally, a trade the user has ALREADY taken — help them understand what may have supported or hurt the entry and target, never issue a verdict or a live signal. Different traders mark this differently and none is "wrong": read what the trader actually marked, evaluate the confluences supporting it, and judge it against THEIR own rules — never impose one single version as the standard.

OTE — the entry (fib retracement):
- After a displacement that produces a BOS or MSS, price retraces into the fib of THAT impulse leg. Anchor the fib to the impulse/displacement leg that shifted structure — NOT to a random or corrective leg.
- ANCHOR POINTS VARY and BOTH are valid: some draw from the extreme WICK of the origin to the end of the move (wick-to-wick), others body-to-body. Wick-anchoring is common and fully legitimate — never "correct" a wick-drawn fib into a body one or treat it as an error.
- THE LEVELS VARY BETWEEN TRADERS AND NONE IS "THE STANDARD." A very common fib configuration is 1 / 0.79 / 0.705 / 0.62 / 0.5 / 0.25 / 0 — here 0.62–0.79 is the OTE band, 0.705 the classic sweet spot, and 0.5 the equilibrium that divides premium from discount. Others legitimately use 0.618 / 0.786, add 0.886, or run their own set, and many enter shallower (at 0.5) depending on confluence and context. For a true discount (longs) / premium (shorts) entry, price should retrace PAST the 0.5 equilibrium — an entry that never reached discount/premium may explain, in hindsight, why a "textbook OTE" behaved more like a shallow pullback. NEVER treat a different level set, a non-0.705 entry, or a 0.5 / sub-62% entry, as "shallow," "wrong," or a defect. A 0.5 entry backed by strong confluence is a valid context decision. Read the level the trader chose and evaluate the confluence supporting THAT level — not the number in isolation.
- CONFLUENCES that strengthen an OTE (recognize when visible): an FVG and/or Order Block nested INSIDE the OTE band (both stacked together = the A+ case), a Breaker Block overlapping the zone, HTF trendline alignment, STACKED FVGs, a BOS/MSS aligned with HTF bias, the zone sitting in discount (longs) / premium (shorts), Kill-Zone timing (London / NY), SMT divergence, and a LIQUIDITY SWEEP into the level. When NONE of these support the fib level, the OTE alone is a weak basis — noting that (gently, in hindsight) is often the single most useful reflection for the trader.
- THE DISTINCT ENTRY TRIGGER (what sets OTE / Std Dev apart from a plain imbalance entry): reaching the fib level is necessary but NOT sufficient — the entry is armed by price tagging the level on the correct side of equilibrium and FIRED by a confirmation AT that level. Confirmation forms are all valid and trader-dependent: a liquidity SWEEP into the fib level then reversal (many use the sweep itself as the trigger), a rejection/reaction wick, a clean opposing candle close, or an LTF break-and-retest / micro-CHoCH. A fib tag with no confirmation is not yet a trigger — if the trade was entered on the bare tag, that is a fair, useful retrospective observation, never a verdict.
- KNOWN OTE VARIANTS / SUB-STYLES (this is the whole landscape — recognize whichever the trader actually marked; never assume your own): (a) CONTINUATION OTE — retrace into the fib of an in-trend displacement leg and continue with the trend; (b) REVERSAL OTE — after a liquidity sweep + MSS, take the OTE of the NEW leg against the prior move; (c) 2022 MODEL — sweep → displacement → enter the FVG nearest ~50% of the setup range (usually inside the OTE band), targeting opposing liquidity; (d) UNICORN MODEL — entry at the OVERLAP of a Breaker Block + FVG, where the fib zone commonly coincides (bullish/bearish variants, entered on the retest); (e) SILVER BULLET — a session FVG (10–11 AM / 2–3 PM ET) aligned with HTF bias, frequently sitting in the OTE band; (f) DEALING-RANGE OTE — mark the dealing range, use its 0.5 equilibrium to split premium/discount, and enter the OTE within discount (longs) / premium (shorts). These all share the fib + confluence DNA but differ in TRIGGER and BIAS. Identify which one the chart + the trader's construction point to; if it is ambiguous, say so rather than forcing one, and NEVER label the trader's chosen variant "wrong" because it is not the one you would use.
- TARGETS: negative extensions (-0.62, -1, -2) of the same leg project the DOL. Tie targets to a liquidity pool or PD array, not to the extension number alone, and assess whether the path is LRL or HRL.
- EVALUATION (work it from the chart): (1) is the fib anchored to a valid impulse leg that actually broke structure? (2) what level did the trader enter and what confluence supports it? (3) is direction consistent with premium/discount? (4) was there a sweep trigger? (5) is SL beyond the swing origin or a structural point? Frame every observation as a possibility to check against their own rules — never a verdict.

STDV — the projection (fib extension for targets / reversals):
- Standard Deviation projects a defined range or the manipulation leg OUTWARD by fib multiples ("standard deviations") to forecast where price is likely to REACH (target/DOL) or REVERSE (exhaustion). It is a projection tool, not a standalone entry — it usually pairs with an entry (often the OTE) to set objectives.
- It is only relevant when there is a clear MANIPULATION LEG, or a defined range to anchor to (CBDR = Central Bank Dealing Range, or the Asian range / Flout). If no manipulation leg or valid anchor is visible, STDV does not apply — say so plainly rather than forcing a projection.
- ANCHOR STYLES VARY (recognize which one the trader used): (i) the DISPLACEMENT / MANIPULATION LEG projected outward by SD multiples; (ii) the CBDR — the ~2:00–8:00 PM ET range — projected by 1/2/3 SD above/below as Judas-swing limits and the projected daily high/low, valid ONLY when the range is TIGHT (roughly under 40 pips); (iii) the ASIAN RANGE (~8:00 PM–12:00 AM ET, ideally 20–30 pips) used when the CBDR is too wide; (iv) any other defined dealing range. The SAME projection is read three ways depending on the trader's intent — as a TARGET (where price is drawn to), as a REVERSAL / exhaustion zone (extreme bands into opposing HTF liquidity), or as the manipulation LIMIT of a Judas swing. Identify which reading the trader intended before evaluating whether price respected it.
- Bands: -1, -2, -2.5, -3, -4 deviations (and the positive side) — these are ZONES, not hard lines. A healthy expansion commonly delivers to roughly the -2 to -2.5 band; -3/-4 mark stretched / exhaustion zones. Range-based (CBDR / Asian) projections are only trustworthy when the anchor range is TIGHT — a wide anchor gives unreliable bands, so note that.
- Require the projected band to CONFLUENCE with a liquidity pool or PD array; do not trust an SD level in isolation. For a reversal read, price reaching an extreme band (-3/-4) into opposing HTF structure or liquidity is the strongest case.

GROUNDING FOR OTE/STDV: traders often do NOT leave the fib tool or the SD projection drawn on the screenshot. When they are not drawn, reconstruct the LIKELY impulse leg / anchor range from the visible structure and SAY you are doing so — e.g. "reconstructing the fib on the displacement leg, the entry looks to sit near the 0.5–0.62 area, though I cannot confirm the exact level without the drawn fib." Never assert precise fib percentages or SD bands you cannot actually see or safely reconstruct from visible price action.

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

@@SEC:ROUTER@@
METHODOLOGY ROUTER — ANALYZE THROUGH THE TRADER'S CHOSEN FRAMEWORK (read this before the ANALYSIS PROCESS):
The trader states their Approach/Model. Everything above, and the ICT ANALYSIS PROCESS below, is the ICT lens (SMC is treated as part of it — same order-block / FVG / liquidity vocabulary). OTE / STD DEV, however, is its OWN fib-driven entry strategy: the trader's CONCEPTUAL lens is ICT, but the entry trigger is distinct, so when that is the stated approach, lead with the dedicated OTE / STANDARD DEVIATION block above (its levels, its distinct trigger, its STDV projection) rather than defaulting to a generic ICT read. If the stated approach is instead OTE / STD DEV, WYCKOFF, CHART PATTERNS, HARMONIC, ELLIOTT WAVE, or TECHNICAL ANALYSIS, analyze the SAME chart through THAT framework using the matching block — the two-phase reading (chart first, then thesis), the grounding rule (assert only what you can see), the interpretation-variance rule (judge against the trader's OWN rules, never one universal standard), and the compliance boundaries ALL still apply unchanged. Read what the trader marked, evaluate the confluences that support it, and frame every observation as a possibility, never a verdict. If the chart plainly belongs to a different framework than the one stated, note that gently as your Phase-1-vs-thesis divergence rather than forcing the wrong lens.

@@SEC:WYCKOFF@@
WYCKOFF (when approach = Wyckoff): read the chart as a campaign staged by a Composite Operator (a modelling lens, not a literal single actor). Purpose reminder: you are explaining, retrospectively and educationally, a Wyckoff trade the user has ALREADY taken — where the campaign read may have supported or hurt it, which phase/event they may have misjudged, what the volume was telling them — never a verdict or a live call. Wyckoff traders LABEL the events on the chart (PS, SC, AR, ST, Spring, LPS, SOS, UTAD, etc.) and lean heavily on VOLUME — read those annotations and the volume bars as their "marks," the way you read a drawn fib for OTE. Much of Wyckoff is unconfirmable without volume; if the volume panel is not visible on the screenshot, SAY SO rather than assuming it.
CORE READ: locate price within a trading RANGE and decide ACCUMULATION (bottoming) vs DISTRIBUTION (topping) by the CHARACTER of its tests, not the calendar. Accumulation leaves springs that hold, shallow reactions on drying volume, rallies that strengthen; distribution leaves upthrusts that fail and reactions that deepen with effort.
- EVENT GLOSSARY (recognize whichever the trader marked): Accumulation Phase A — PS (Preliminary Support), SC (Selling Climax, wide spread + high volume), AR (Automatic Rally, defines the range top), ST (Secondary Test). Distribution Phase A — PSY (Preliminary Supply), BC (Buying Climax), AR, ST. Phase B — builds the CAUSE (the "boring" absorption/distribution middle, repeated STs). Phase C — the TEST: a SPRING / shakeout (dip below support that snaps back inside) in accumulation, an UTAD / UT (upthrust that fails) in distribution. A spring/UTAD is NOT required (Accumulation Schematic #1 has a spring, Schematic #2 has none) — its absence is not a defect. Phase D — SOS (Sign of Strength) / SOW (Sign of Weakness), LPS (Last Point of Support) / LPSY (Last Point of Supply), the JUMP ACROSS THE CREEK (JAC) + Back-Up (BU/BUEC) to the edge (creek / ice = the range boundary). Phase E — the trend outside the range (markup / markdown).
- THREE LAWS: (1) Supply & Demand — which side owns the imbalance = DIRECTION. (2) Cause & Effect — the horizontal Point & Figure count across the range sizes the target = MAGNITUDE (the longer the range/cause, the larger the effect); never treat a P&F target as a debt the market owes. (3) Effort vs Result — volume (effort) vs price spread (result); a divergence (huge volume, tiny progress) warns of ABSORPTION. Bar reading = spread + close position + volume.
- VOLUME / VSA (Wyckoff's confirmation layer): climactic volume at the SC/BC, drying volume through Phase B, LOW volume on a spring (bullish) vs high volume that fails to reverse (weak), a NO-DEMAND bar (up bar, narrow spread, low volume) or NO-SUPPLY bar, stopping volume, and effort-vs-result divergence. When the trader's read hinges on volume you cannot see, say so plainly.
- VARIANTS / SUB-STYLES (recognize which the trader used, never impose one): accumulation vs distribution; Schematic #1 (with spring) vs #2 (no spring); RE-ACCUMULATION (a pause inside an uptrend) vs RE-DISTRIBUTION (a pause inside a downtrend) — misreading a re-accumulation as a top (or vice versa) is a classic cause of a failed Wyckoff trade and a high-value thing to check; and pure VSA/volume readers vs schematic/structure readers.
- SANCTIONED ENTRIES sit NEXT TO their invalidation: the spring (stop below the shaken low), the test of the spring, the LPS/LPSY, the back-up to the creek/edge after a SOS. The naked breakout is the same campaign at its worst price (furthest from any structural stop) — treat the jump as confirmation to hold/add, not the core entry.
- EVALUATION (Phase 1, from the chart, for a trade already taken): (1) is a clear range present, and is it accumulation or distribution by test character (and re-accumulation vs re-distribution)? (2) which phase and which event was the entry taken at? (3) was the entry at a sanctioned point with nearby invalidation, or chasing the breakout? (4) does VOLUME confirm the read (climax, drying, spring signature, effort vs result) — or is volume not visible? (5) is the P&F cause big enough for the stated target, and did the path face opposing HTF structure (LRL vs HRL)? Frame everything as a possibility to check against the trader's own rules — never a verdict; a valid Wyckoff read can still fail within normal variance.

@@SEC:PATTERNS@@
CHART PATTERNS (when approach = Chart Patterns): classical patterns are context-dependent STATISTICS, not verdicts — the SAME shape means opposite things depending on WHERE it forms (a wide-range high-volume bar out of a completed base is initiation; the same bar late in a trend into old supply is a climax candidate). Purpose reminder: you are explaining, retrospectively and educationally, a pattern trade the user has ALREADY taken — which part of the pattern / breakout / volume / context may have supported or hurt it — never a verdict or a live call. The trader's "marks" are the DRAWN pattern: the trendlines, neckline and measured-move projection — read those the way you read a fib for OTE; if the pattern is not drawn, reconstruct the likely boundaries from the swings and SAY you are doing so.
- Reversals: Head & Shoulders (+ inverse), Double/Triple Top & Bottom, Rounding Top/Bottom, Diamond, Island Reversal. Continuations: Triangles (symmetrical = compression, usually resolves with the prior trend; ascending/descending carry a bias), Wedges (rising = bearish, falling = bullish; within a pullback they are continuation), Flags & Pennants (brief, project the flagpole), Rectangles/Channels, Cup & Handle.
- IDENTIFY THE SPECIFIC VARIANT: the trader now tags a SPECIFIC variant (e.g. "Ascending Triangle", "Rising Wedge", "Double Bottom", "Bull Flag"). Confirm that exact variant on the chart and judge its own bias, volume signature and measured move.
- CONFLUENCE HANDLING — when the trader tags a specific pattern, treat it as their THESIS, not as ground truth, and resolve it three ways: (1) if you can CONFIRM it on the chart, use it and analyze it fully. (2) If you can clearly SEE that it is absent, or that the shape is actually a DIFFERENT pattern than the one tagged, that divergence is often the single MOST useful lesson — say it gently: e.g. "what you marked as an ascending triangle looks closer to a symmetrical one on the chart (the support line isn't flat), and that mismatch may itself be part of why the trade didn't behave as expected." NEVER blindly accept a pattern you can actually see is wrong. (3) If you genuinely CANNOT tell from the screenshot (too small, blurry, cropped, the pattern isn't fully in frame), SAY SO explicitly, proceed on the trader's read for the rest of the analysis, but flag the limit honestly: you cannot assess the pattern's exact level, its breakout quality, or precisely how it influenced the trade, and invite a clearer / zoomed-out chart. NEVER fabricate the pattern's location or measured move just to honour the tag. The distinction that matters: "I cannot confirm this from the image" (a vision limit — proceed on the trader's read, with the caveat) is DIFFERENT from "I can see this is not what you marked" (a real divergence — surface it).
- ENTRY VARIANTS / SUB-STYLES (recognize which the trader used — none is "wrong"): (a) AGGRESSIVE breakout — enter on the close beyond the boundary/neckline; carries the highest FALSE-breakout risk; (b) CONSERVATIVE retest — wait for the throwback (tops) / pullback (bottoms) to the broken level and enter on the re-rejection (best R:R; ~60% of H&S do throw back); (c) ANTICIPATION — enter inside the pattern at the far trendline before the break (best price, needs confirmation). The FALSE / FAILED breakout (breaks then closes back inside) is the single most common reason these trades fail — check it FIRST in hindsight.
- CONFIRMATION: a neckline/boundary CLOSE matters more than an intraday wick — a spike that pierces and closes back inside did NOT complete the pattern. An up-breakout needs EXPANDING volume as fuel; a down-break can fall on its own weight with ordinary volume. In an H&S, volume should shrink left-shoulder → head → right-shoulder; a heavy right shoulder contradicts the top. The Edwards-&-Magee penetration filter (ignore a break until ~3% or ~2 sessions beyond) guards against false breaks.
- MEASURED MOVE / TARGET = the pattern's height projected from the breakout — geometry blind to context, so an opposing HTF level in the path re-evaluates it (LRL vs HRL). Watch neckline/trendline slope, apex proximity (triangle breaks that drift to the apex are weak), and THROWBACK HEALTH (quiet & shallow that holds the broken level = healthy; heavy & deep back inside = the failure dressed as a retest).
- CONTEXT OUTRANKS SHAPE: the HTF trend, nearby support/resistance, volume behaviour and news can override a textbook-looking formation. A continuation pattern WITH the trend is higher-odds than the same shape fighting it.
- CANDLESTICKS (Engulfing, Morning/Evening Star, Hammer, Doji, Marubozu, Three White Soldiers vs Advance Block, Harami/Inside Bar, Piercing, Kicker, Abandoned Baby) are defined on CLOSED candles; meaning = WHAT IT INTERRUPTS + its location + its volume — the same shape at a tested level with follow-through outranks it mid-range.
- EVALUATION (Phase 1, from the chart, for a trade already taken): (1) which exact variant, and does the trend stage / HTF context support its textbook reading? (2) volume confirmation on the break? (3) breakout quality — a real CLOSE beyond, or just a wick / false break? (4) which entry variant was used, and was the throwback healthy or a failure? (5) is the measured target realistic given obstacles in the path, and where was invalidation placed? Frame everything as a possibility to check against the trader's own rules — never a verdict; a valid pattern can still fail within normal variance.

@@SEC:HARMONIC@@
HARMONIC (when approach = Harmonic): Fibonacci-defined XABCD geometries that project a Potential Reversal Zone (PRZ) at point D — probabilistic ZONES that need reactive confirmation, never blind limit triggers. Purpose reminder: you are explaining, retrospectively and educationally, a harmonic trade the user has ALREADY taken — where the ratios, the PRZ, or the confirmation may have supported or hurt it — never a verdict or a live call. The trader's "marks" are the drawn XABCD pivots, the leg fib ratios, and the PRZ box — read those the way you read a fib for OTE; if the pattern is not drawn, reconstruct the likely XABCD from the visible swings and SAY you are doing so, and never assert exact ratios you cannot measure from the image.
- THE PATTERNS & RATIOS (tolerance BANDS, not exact numbers): RETRACEMENT patterns complete D INSIDE the XA leg — GARTLEY (B ≈ 0.618 of XA → D ≈ 0.786), BAT (B ≈ 0.382–0.50 → D ≈ 0.886). EXTENSION patterns complete D BEYOND X — BUTTERFLY (B ≈ 0.786 → D ≈ 1.27–1.618), CRAB (D ≈ 1.618 extension of XA — the most extreme, tightest stop, most violent reactions), DEEP CRAB (B ≈ 0.886). Also CYPHER (C beyond A, D ≈ 0.786 of the XC leg), SHARK (the 5-0 relation), ABCD (CD = AB, or a 1.272/1.618 extension), THREE DRIVES.
- THE B POINT IS THE CLASSIFIER: it decides WHICH pattern is forming and therefore where D sits — moving B moves the PRZ, the stop and the whole risk geometry. A common failure worth checking in hindsight is a MISLABELED B (e.g. a "Gartley" whose B is really 0.786 makes it a Butterfly, so the true D/PRZ sat somewhere else and the entry was early).
- THE PRZ IS A CONFLUENCE ZONE, not a line: it is strongest where SEVERAL independent fib projections converge in a tight area — the XA retracement/extension, the BC projection, and the AB=CD completion all landing together. A PRZ resting on a single ratio is weaker; it is stronger still when it overlaps OUTSIDE confluence (an HTF S/R level, a structural swing, a liquidity pool).
- ARRIVAL & CONFIRMATION (sub-styles vary — recognize which the trader used): HOW price arrives matters — a chain of displacement candles INTO the PRZ is initiative momentum (caution: the reversal needs EXHAUSTION, not momentum); a tiring, overlapping arrival favours the reversal. Entry styles: (a) AGGRESSIVE — a limit order in the PRZ (higher risk if price runs through it); (b) CONFIRMED — wait for a reversal signal IN the PRZ: a rejection candle, a CHoCH / structure shift, a liquidity sweep, or an oscillator divergence (RSI/MACD). Neither is "wrong" — judge against the trader's own rule.
- STOP & TARGETS: stop just beyond X (Gartley / Bat) or just beyond D (Butterfly / Crab, since D is already an extension). Targets at fib retracements of the AD leg (commonly 0.382 and 0.618), then point C, then beyond — tie them to structure / liquidity, not the ratio alone (LRL vs HRL path).
- EVALUATION (Phase 1, from the chart, for a trade already taken): (1) are the leg ratios within tolerance, and is the pattern correctly classified by its B point? (2) is the PRZ a real MULTI-fib confluence, and does it align with outside S/R / liquidity? (3) did price actually REACT at D (confirmation candle / structure shift / sweep), or was it entered on a bare limit while price was still arriving with momentum? (4) was the stop beyond X or D per the pattern, and were targets tied to the AD-leg fibs / structure? (5) never absolute — the PRZ is a zone and a valid harmonic can still fail within normal variance. Frame everything as a possibility to check against the trader's own rules — never a verdict.

@@SEC:ELLIOTT@@
ELLIOTT WAVE (when approach = Elliott Wave): price unfolds in FRACTAL waves — a five-wave IMPULSE in the direction of the larger trend (1-2-3-4-5), then a three-wave CORRECTION against it (A-B-C), the same shape repeating across degrees. Purpose reminder: you are explaining, retrospectively and educationally, an Elliott trade the user has ALREADY taken — whether the count held up, which rule/relationship it may have broken, why the wave may not have played out — never a verdict or a live call. The count is SUBJECTIVE (two analysts label differently), so the trader's WAVE LABELS on the chart (1-5, A-B-C, and the degree) are their "marks" — read them; if unlabeled, propose the most likely count from the visible swings and SAY it is your read. Because it is subjective, almost always NAME a viable ALTERNATE count as well.
- THREE INVIOLABLE RULES (your objective anchor): (1) wave 2 never retraces more than 100% of wave 1; (2) wave 3 is never the shortest of waves 1/3/5 (usually the longest, strongest, most momentum); (3) wave 4 never enters the price territory of wave 1 (in an impulse). If a labelled count breaks any rule the count is INVALID — say so gently as your Phase-1 divergence and offer the corrected count.
- GUIDELINES (tendencies, not rules): ALTERNATION (a sharp wave 2 pairs with a sideways/flat wave 4, and vice versa); wave 3 often ~1.618 of wave 1 (extensions common); wave 4 often retraces ~0.382 of wave 3 and holds above wave-1 territory; waves 1 & 5 often reach equality; channelling contains the impulse.
- CORRECTIVE TAXONOMY (name the form): ZIGZAG (5-3-5, sharp; B shorter than A, C beyond A), FLAT (3-3-5, sideways; regular, or expanded/irregular where B exceeds the start of A), TRIANGLE (3-3-3-3-3, contracting or expanding; appears in wave 4, B, or X — NEVER in wave 2), COMBINATIONS (double/triple three, joined by an X wave; never more than one zigzag or triangle in one). DIAGONALS: LEADING (wave 1 or A) and ENDING (wave 5 or C — signals exhaustion of the move).
- ENTRIES & INVALIDATION (sub-styles vary): the highest-probability entries are the start of wave 3 (after a valid 1-2) or the end of a correction into the next impulse; some enter aggressively at a fib of the expected corrective end, others wait for a lower-degree 5-wave to confirm the turn. Invalidation sits at the EXACT rule-breaking level (e.g. below the start of wave 1 for a wave-2 entry; the wave-1 territory for a wave-4 entry).
- EVALUATION (Phase 1, from the chart, for a trade already taken): (1) does the labelled count obey all THREE rules? (2) was the entry at a high-probability wave with invalidation at the rule-breaking level, or mid-wave / against the count? (3) do the fib relationships (wave-3 extension, wave-4 retrace, 1=5) support the count? (4) is wave DEGREE consistent (not mixing a 5m sub-wave with a daily wave)? (5) is there a viable ALTERNATE count that was actually more likely — often the very reason the trade failed? Frame everything as a possibility to check against the trader's own rules — never a verdict; Elliott is a probability roadmap, not a certainty.

@@SEC:TA@@
TECHNICAL ANALYSIS (when approach = Technical Analysis):
Signals derived from mathematical transforms of price and volume, plotted on the chart. Purpose reminder: you are explaining, retrospectively and educationally, an indicator-based trade the user has ALREADY taken — whether the signals truly aligned, which one was over-trusted, why it may have failed — never a verdict or a live call. The edge is the CONFLUENCE of conditions plus context (trend, support/resistance), never a single indicator in isolation; and do NOT count two indicators of the SAME family as confluence (RSI + Stochastic both oversold is ONE reading, not two) — real confluence pulls from different categories (a momentum read + a trend read + a volume read). Because most indicators are DERIVED from price they LAG it, so they confirm and filter rather than lead — divergence is the closest thing to a leading read.
- Momentum oscillators: RSI (overbought/oversold — but these can stay PINNED for long stretches in a strong trend, so they are not standalone signals; RSI is far more valuable as DIVERGENCE), Stochastic (similar), MACD (signal-line cross, zero-line cross, histogram divergence). DIVERGENCE TYPE matters: REGULAR divergence (price makes a new extreme, the oscillator does not) signals a REVERSAL; HIDDEN divergence (the oscillator retraces deeper than price on a pullback) signals CONTINUATION with the trend — fading a strong trend with regular divergence is a classic loser, while hidden divergence aligns with it. A "Class A" divergence has its first RSI peak above 70 (bearish) / trough below 30 (bullish). A clean divergence at a structural level, confirmed by a second family (e.g. MACD agreeing with RSI), is the strongest oscillator signal.
- Trend / volatility: Moving Averages (fast/slow cross = trend change; price above/below a key MA = bias; the 50/200 "golden/death" cross; MA slope), ADX (trend STRENGTH only, NOT direction — under ~20 = weak/ranging, over ~25 = trending, over ~50 = strong; a signal taken in sub-20 ADX chop is lower-odds), Bollinger Bands (reaction at the bands = mean reversion; a squeeze = volatility contraction that precedes expansion), Ichimoku (cloud as dynamic S/R and bias).
- Volume tools: raw Volume (confirmation — genuine breakouts expand volume), VWAP (intraday institutional mean — rejection or reversion at VWAP), and Volume Profile / VPVR (the VPOC / point of control, the value-area high and low, and high/low-volume nodes: price tends to rotate toward the VPOC and react at value-area edges; low-volume nodes get traversed quickly).
- EVALUATION (Phase 1, from the chart, for a trade already taken): (1) what exact indicator setup did the trader use, and is it real cross-category confluence or one lagging signal (or two of the same family) alone? (2) is there a divergence — is it clean, the right TYPE (regular vs hidden) for the context, and at a meaningful level? (3) does the indicator condition ALIGN with price structure / trend / S-R, or fight it (e.g. fading a strong trend)? (4) volume confirmation on the move? (5) indicators confirm, they do not override the chart — judge the entry against price action, not just the oscillator reading. Frame every observation as a possibility to check against the trader's own rules — never a verdict.
- GROUNDING FOR INDICATORS (critical — indicators are easy to MISREAD from a screenshot, so never fake precision): state plainly what you can and cannot see. You CAN read the qualitative picture when it is clearly drawn — two moving averages visibly crossing, an oscillator sitting in overbought/oversold, a MACD flip, a Bollinger squeeze, an obvious divergence, a VWAP/VPOC rejection. You CANNOT reliably (a) read exact numeric values — NEVER assert "RSI was 68" or a precise level unless the number is printed and legible; (b) confirm bar-precise ALIGNMENT such as "the EMA cross landed exactly on your entry candle"; (c) tell which periods overlapping MAs are, unless the legend is legible. When the trader's conjecture hinges on precision you cannot verify — e.g. "the 9/21 EMA crossed right at my entry" — CONFIRM what is visually clear ("two MAs do appear to cross upward near that area"), EXPLICITLY flag what you cannot confirm from the image (the exact candle, the MA periods, the value), give any estimate AS an estimate, and invite the trader to confirm or point to it — never invent the detail. A grounded "I can see X but cannot confirm Y from this screenshot" is always better and more useful than a confident guess. If the indicator the trader names is not visibly present on the chart at all, say that directly rather than pretending to read it.

@@SEC:ICTPROCESS@@
ANALYSIS PROCESS (this is your PHASE 1 chart read for ICT — work through it FROM THE CHART first, before leaning on the trader's narrative; for Wyckoff / Chart Patterns / Harmonic / Elliott Wave / Technical Analysis use that framework's EVALUATION checklist above instead):
1. Entry Model: What specific ICT model does this appear to be? (FVG entry, OB entry, IFVG, sweep + CHoCH, etc.) Identify FVG scenario A or B.
2. LTF Structure: What does the 5m/1m show at entry? CHoCH or MSS visible? HH/HL or LH/LL forming?
3. Liquidity: Was there a sweep before entry? What is the DOL? Is the path LRL or HRL?
4. HTF Context: Does it align with HTF bias, or is a counter-trend with LTF justification?
5. Timing: Kill zone, Silver Bullet, or dead zone?
6. SL Logic: Is the SL at a logical invalidation point? (Evaluate independently from entry)
7. SMT: If a split chart is shown — are there two correlated instruments? Is there a clear divergence?
8. Fakeout: Is there any sign that what appeared to be a breakout was actually a stop hunt or fakeout?

@@SEC:OUTPUT@@
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


# Compact shared-market primer sent with NON-ICT methodologies so they still
# "see" liquidity / structure / sessions without carrying the full ICT mechanics.
SP_CORE_LITE = """SHARED MARKET CONCEPTS (baseline context — the trader may reference these regardless of their chosen methodology):
- MARKET STRUCTURE: HH/HL = bullish, LH/LL = bearish. BOS (Break of Structure) = a swing high/low broken with a decisive body close (wick-only breaks do not count). CHoCH (Change of Character) = the first break of the most recent counter-trend swing — an early reversal hint.
- LIQUIDITY: resting stops pool above highs / below lows. Buy-side liquidity (BSL) sits above swing highs, equal highs, trendline highs and the previous day/week high (PDH/PWH); sell-side (SSL) below swing lows, equal lows, PDL/PWL. A LIQUIDITY SWEEP = price briefly runs a level to trigger those stops, then reverses — what matters is what happens AFTER the sweep. DOL (Draw on Liquidity) = the next pool price is likely drawn toward.
- PREMIUM / DISCOUNT: the working range's 50% is equilibrium; above it = premium (favours selling), below = discount (favours buying).
- PATH QUALITY (LRL vs HRL): LRL (Low-Resistance) = a clear path to target with no major opposing levels in the way (higher odds of reaching it); HRL (High-Resistance) = unfilled gaps / untested levels / structure block the path, so price may stall or reverse before the target.
- SESSIONS: the London (~2–5 AM ET) and New York (~8–11 AM ET) windows carry the most institutional volume; NY lunch (~12–1:30 PM ET) is typically choppy. A setup in a high-participation window has more backing than one in a dead zone.
- INSTRUMENT: the trader states the exact instrument (index futures NQ/ES/YM, forex majors, metals XAU/XAG, energy CL/NG). Calibrate typical volatility, session timing and stop distances to it — gold and NQ produce wider stop-runs than a quiet FX pair."""


def build_system_prompt(approach):
    """Assemble the system prompt with ONLY the sections relevant to the trader's
    chosen approach, to avoid paying for methodology blocks that don't apply.
    ICT and OTE/Std Dev travel together (OTE is a fib entry within the ICT lens);
    every other methodology gets the compact shared core + its own block only.
    The global scaffolding (compliance, two-phase reading, grounding, direction)
    and the OUTPUT rules are ALWAYS included."""
    raw = SYSTEM_PROMPT
    parts = re.split(r'@@SEC:([A-Z]+)@@\n', raw)
    global_top = parts[0]
    sec = {}
    for i in range(1, len(parts) - 1, 2):
        sec[parts[i]] = parts[i + 1]

    def strip_markers(t):
        return re.sub(r'@@SEC:[A-Z]+@@\n?', '', t)

    a = (approach or '').strip().lower()
    out = [global_top]
    ict_family = a.startswith('ict') or a.startswith('ote') or 'smc' in a
    method_map = {
        'wyckoff': 'WYCKOFF', 'chart patterns': 'PATTERNS', 'harmonic': 'HARMONIC',
        'elliott wave': 'ELLIOTT', 'technical analysis': 'TA',
    }
    if ict_family:
        # Full ICT knowledge (already contains the OTE/Std Dev block) + the router
        # (so an OTE approach still leads with the dedicated OTE block) + ICT process.
        out.append(sec.get('ICT', ''))
        out.append(sec.get('ROUTER', ''))
        out.append(sec.get('ICTPROCESS', ''))
    elif a in method_map:
        out.append(SP_CORE_LITE)
        out.append(sec.get(method_map[a], ''))
    else:
        # Unknown / unspecified approach → safe fallback: send everything.
        return strip_markers(raw)
    out.append(sec.get('OUTPUT', ''))
    return strip_markers('\n'.join(p for p in out if p))


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
                        {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{image_data_b64}", "detail": "low"}},
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
    if not INDICATORS_ENABLED:
        abort(404)
    return render_template('store_indicators.html')


def _mentorship_gate():
    """The mentorship funnel is hidden while under construction: 404 for everyone
    except admins (who can preview by URL). Once MENTORSHIP_ENABLED is on it's
    open to all visitors."""
    if MENTORSHIP_ENABLED:
        return
    if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
        return
    abort(404)


# ── Mentorship funnel ("Find New Ways to Improve") — step 1: the hook ──
@app.route('/improve')
def improve_intro():
    _mentorship_gate()
    return render_template('improve.html')


@app.route('/improve/mindset')
def improve_mindset():
    _mentorship_gate()
    return render_template('improve_mindset.html')


@app.route('/improve/gap')
def improve_gap():
    _mentorship_gate()
    return render_template('improve_gap.html')


@app.route('/improve/inside')
def improve_inside():
    _mentorship_gate()
    return render_template('improve_inside.html')


# ── Mentorship funnel — step 5: how it works + "The Great Filter" (application) ──
_APPLY_EXPERIENCE = {'lt1', 'y1_3', 'y3p'}
_APPLY_SITUATION = {'demo', 'live', 'funded', 'inconsistent'}
_APPLY_HOURS = {'lt5', 'h5_10', 'h10p'}
_APPLY_PROGRAM = {'rec', 'calls', 'both'}
_APPLY_GOALS = {'study', 'errors', 'consistency', 'plan', 'psych', 'validate'}
_APPLY_SKILL = {'strategy', 'ta', 'psych', 'risk', 'theory', 'discipline'}
_APPLY_ASSETS = {'futures', 'forex'}
_APPLY_CLANG = {'es', 'en', 'both'}
_APPLY_SLOT = {'morning', 'afternoon', 'evening'}
_APPLY_SOURCE = {'tiktok', 'youtube', 'x', 'friend', 'google', 'other'}
_APPLY_AGE = {'18_24', '25_34', '35_44', '45p'}


def send_mentorship_application_email(a):
    """Email the freshly submitted mentorship application to the company inbox
    (current Gmail until the business domain mail exists). Non-fatal: the
    application is already stored in DB, so a mail hiccup only logs a warning."""
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('MAIL_APP_PASSWORD not configured — mentorship application email not sent.')
        return False
    to_addr = os.environ.get('ADMIN_EMAIL', 'mauroramirezmij@gmail.com')
    label = {
        'rec': 'Biblioteca grabada', 'calls': 'Calls 1-1', 'both': 'Ambos programas',
        'lt1': 'Menos de 1 año', 'y1_3': '1–3 años', 'y3p': '3+ años',
        'demo': 'Demo / paper', 'live': 'Real, tamaño chico', 'funded': 'Fondeo / prop', 'inconsistent': 'Real pero inconsistente',
        'lt5': '<5 h/semana', 'h5_10': '5–10 h/semana', 'h10p': '10+ h/semana',
        'study': 'Estudiar con estructura', 'errors': 'Corregir errores recurrentes',
        'consistency': 'Acercarse a la consistencia', 'plan': 'Construir plan de trading',
        'psych': 'Psicotrading', 'validate': 'Validar su estrategia',
        'strategy': 'Estrategia', 'ta': 'Análisis técnico', 'risk': 'Gestión de riesgo',
        'theory': 'Teoría', 'discipline': 'Disciplina/consistencia',
        'futures': 'Futuros', 'forex': 'Forex', 'crypto': 'Cripto', 'stocks': 'Acciones/otros', 'mixed': 'Varios/definiendo',
        'es': 'Español', 'en': 'English', 'both': 'Ambos programas',
        'morning': 'Mañana', 'afternoon': 'Tarde', 'evening': 'Noche',
        'tiktok': 'TikTok/Instagram', 'youtube': 'YouTube', 'x': 'X (Twitter)',
        'friend': 'Amigo/referido', 'google': 'Google', 'other': 'Otro',
        '18_24': '18–24', '25_34': '25–34', '35_44': '35–44', '45p': '45+',
    }
    def lab(v):
        return label.get(v, v or '—')
    def labs(csv):
        return ', '.join(lab(x) for x in (csv or '').split(',') if x) or '—'
    # 'both' collides between program and call_lang labels — resolve per-field:
    call_lang_lab = {'es': 'Español', 'en': 'English', 'both': 'Español e inglés'}.get(a.call_lang, '—')
    body = (
        'Nueva aplicación de mentoría — Tradeable Academy\n'
        '================================================\n\n'
        f'Nombre completo:      {a.name}\n'
        f'Usuario:              {a.username or "—"}\n'
        f'Email:                {a.email}\n'
        f'Programa de interés:  {lab(a.program)}\n\n'
        f'Tiempo operando:      {lab(a.experience)}\n'
        f'Etapa actual:         {lab(a.situation)}\n'
        f'Horas por semana:     {lab(a.hours_week)}\n'
        f'Objetivos:            {labs(a.goals)}\n'
        f'Fortaleza:            {lab(a.strength)}\n'
        f'Debilidad:            {lab(a.weakness)}\n'
        f'Activos que opera:    {labs(a.assets)}\n\n'
        f'País:                 {a.country or "—"}\n'
        f'Zona horaria (auto):  {a.tzname or "—"}\n'
        f'Idioma para calls:    {call_lang_lab}\n'
        f'Franja para calls:    {lab(a.call_slot)}\n'
        f'Nos conoció por:      {lab(a.source)}\n'
        f'Rango de edad:        {lab(a.age_range)}\n\n'
        f'Idioma de la web:     {a.lang or "—"}\n'
        f'Usuario registrado:   {"sí (id %s)" % a.user_id if a.user_id else "no"}\n'
        f'Waiver aceptado:      {a.waiver_accepted_at:%Y-%m-%d %H:%M} UTC\n'
    )
    msg = Message('Nueva aplicación de mentoría — ' + a.name, recipients=[to_addr])
    msg.body = body
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        app.logger.warning('Failed to send mentorship application email: %s', exc)
        return False
    finally:
        socket.setdefaulttimeout(prev_timeout)


def send_mentorship_order_email(order):
    """Notify the company inbox of a PAID mentorship purchase. Best-effort —
    the MentorshipOrder row is the source of truth."""
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('MAIL_APP_PASSWORD not configured — mentorship order email not sent.')
        return False
    to_addr = os.environ.get('ADMIN_EMAIL', 'mauroramirezmij@gmail.com')
    u = db.session.get(User, order.user_id)
    body = (
        'Nueva COMPRA de mentoría — Tradeable Academy\n'
        '============================================\n\n'
        f'Paquete:   {order.label} ({order.sku})\n'
        f'Monto:     ${order.price:.2f} {order.currency.upper()}\n'
        f'Pago:      {order.payment_method or "—"}\n'
        f'Usuario:   {(u.username if u else "?")} / {(u.email if u else "?")} (id {order.user_id})\n'
        f'Pagada:    {order.paid_at:%Y-%m-%d %H:%M} UTC\n' if order.paid_at else ''
    )
    msg = Message('Nueva compra de mentoría — ' + order.label, recipients=[to_addr])
    msg.body = body
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        app.logger.warning('Failed to send mentorship order email: %s', exc)
        return False
    finally:
        socket.setdefaulttimeout(prev_timeout)


def _activate_mentorship_order(order):
    """Fulfil a PAID mentorship order exactly once. Deliberately does NOT touch
    `user.plan` — mentorship is a separate product line. For now fulfilment =
    record + notify the company; granting actual access (library / booking) is a
    later task once the member area exists. Idempotent via `applied_at`."""
    if order.status != 'paid' or order.applied_at is not None:
        return False
    order.applied_at = datetime.now(timezone.utc)
    db.session.commit()
    try:
        send_mentorship_order_email(order)
    except Exception as exc:
        app.logger.warning('mentorship order email raised: %s', exc)
    return True


@app.route('/improve/apply')
def improve_apply():
    _mentorship_gate()
    prefill_email = current_user.email if current_user.is_authenticated else ''
    prefill_username = (current_user.username or '') if current_user.is_authenticated else ''
    return render_template('improve_apply.html',
                           prefill_email=prefill_email,
                           prefill_username=prefill_username, prefill_name='')


@app.route('/improve/plans')
def improve_plans():
    """Step 6 — the offer. Only reachable after submitting the application
    (session flag), so the funnel order holds: filter first, then the mentor
    reveal + prices. Admins can always preview directly."""
    _mentorship_gate()
    is_admin = current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    if not session.get('improve_applied') and not is_admin:
        return redirect(url_for('improve_apply'))
    return render_template('improve_plans.html',
                           authed=current_user.is_authenticated)


# ═══ Mentorship MEMBERS AREA — page + JSON APIs ════════════════════════════
MENT_REACTIONS = ('👍', '🔥', '📈', '❤️', '🤝')


def _ment_live_state():
    row = db.session.get(MentorshipLiveState, 1)
    if not row:
        row = MentorshipLiveState(id=1, is_live=False)
        db.session.add(row)
        db.session.commit()
    return row


def _ment_live_dict(row):
    return {'is_live': bool(row.is_live), 'title': row.title or '', 'url': row.url or '',
            'note': row.note or '', 'watermark': row.watermark_on is not False,
            'updated_at': _as_utc(row.updated_at).isoformat() if row.updated_at else None}


_YT_RE = re.compile(r'(?:youtube\.com/(?:watch\?v=|embed/|live/)|youtu\.be/)([\w-]{6,})')


def _video_meta_from_url(url):
    """Classify a pasted video URL once, at save time.

    Returns (source, provider_id, auto_thumb). Keeping this server-side means the
    player never has to guess, and swapping in a new host later is a change here
    plus one branch in the client — not a rewrite of every stored row."""
    u = (url or '').strip()
    m = _YT_RE.search(u)
    if m:
        vid = m.group(1)
        return 'youtube', vid, 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % vid
    if re.search(r'\.(mp4|webm|m3u8)(\?|$)', u, re.I):
        return 'file', None, None
    return 'embed', None, None


MENT_ATTACH_DIR = os.path.join(BASE_DIR, 'private_uploads', 'mentorship')
MENT_ATTACH_MIME = {'application/pdf': ('file', 'pdf'), 'image/png': ('image', 'png'),
                    'image/jpeg': ('image', 'jpg'), 'image/jpg': ('image', 'jpg'),
                    'image/webp': ('image', 'webp')}
MENT_ATTACH_MAX = 10 * 1024 * 1024
MENT_BOARD_MAX = 2 * 1024 * 1024          # a Chalkboard project as JSON


def _fmt_ts(sec):
    sec = max(0, int(sec or 0))
    h, rem = divmod(sec, 3600)
    m, sc = divmod(rem, 60)
    return ('%d:%02d:%02d' % (h, m, sc)) if h else ('%d:%02d' % (m, sc))


def _parse_ts(txt):
    """'4:12' / '1:04:12' / '92' -> seconds, or None."""
    txt = (txt or '').strip()
    if not txt:
        return None
    parts = txt.split(':')
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums) or len(nums) > 3:
        return None
    total = 0
    for n in nums:
        total = total * 60 + n
    return total if total < 24 * 3600 else None


def _parse_chapters(raw):
    """Free text, one chapter per line: '4:12 Entrada'. Anything unparseable is
    skipped rather than rejected, so a stray blank line can't lose the lot."""
    out = []
    for line in (raw or '').splitlines():
        line = line.strip()
        if not line:
            continue
        bits = line.split(None, 1)
        t = _parse_ts(bits[0])
        if t is None:
            continue
        label = (bits[1].strip() if len(bits) > 1 else '')[:80]
        out.append({'t': t, 'label': label})
    out.sort(key=lambda c: c['t'])
    return out[:80]


def _ment_chapters(v):
    try:
        data = json.loads(v.chapters) if v.chapters else []
    except (ValueError, TypeError):
        return []
    return [{'t': int(c['t']), 'label': c.get('label') or '', 'ts': _fmt_ts(c['t'])}
            for c in data if isinstance(c, dict) and 't' in c]


def _attach_dict(a):
    return {'id': a.id, 'kind': a.kind, 'title': a.title, 'mime': a.mime or '',
            'size': a.size or 0, 'url': a.url or '',
            'created_at': _as_utc(a.created_at).isoformat() if a.created_at else None}


def _ment_attachments(video_id=None, folder_id=None):
    q = MentorshipAttachment.query
    q = q.filter_by(video_id=video_id) if video_id else q.filter_by(folder_id=folder_id)
    return [_attach_dict(a) for a in q.order_by(MentorshipAttachment.id.asc()).all()]


def _ment_video_dict(v, with_desc=False):
    done = MentorshipProgress.query.filter_by(user_id=current_user.id, video_id=v.id, completed=True).first() is not None
    d = {'id': v.id, 'title': v.title, 'kind': v.kind, 'duration_min': v.duration_min,
         'folder_id': v.folder_id, 'done': done, 'thumb': v.thumb_url or '',
         'comment_count': MentorshipVideoComment.query.filter_by(video_id=v.id).count(),
         'created_at': _as_utc(v.created_at).isoformat()}
    if with_desc:
        d['description'] = v.description or ''
        d['video_url'] = v.video_url
        d['source'] = v.source or 'embed'
        d['provider_id'] = v.provider_id or ''
        d['chapters'] = _ment_chapters(v)
        d['attachments'] = _ment_attachments(video_id=v.id)
    return d


def _ment_msg_dict(m):
    counts = {}
    mine = None
    for r in MentorshipMsgReaction.query.filter_by(message_id=m.id).all():
        counts[r.emoji] = counts.get(r.emoji, 0) + 1
        if r.user_id == current_user.id:
            mine = r.emoji
    reply = None
    if m.reply_to_id:
        rm = db.session.get(MentorshipMessage, m.reply_to_id)
        if rm and not rm.is_deleted:
            reply = {'author': rm.user.username if rm.user else '—', 'body': (rm.body or '')[:90]}
    return {'id': m.id, 'body': m.body, 'author': m.user.username if m.user else '—',
            'is_mentor': bool(m.user and m.user.is_admin), 'is_mine': m.user_id == current_user.id,
            'pinned': bool(m.pinned), 'reply_to': reply,
            'reactions': counts, 'my_reaction': mine,
            'created_at': _as_utc(m.created_at).isoformat()}


@app.route('/mentorship/area')
@login_required
def mentorship_area():
    _mentorship_gate()
    if not is_mentorship_member():
        return redirect(url_for('improve_plans'))
    return render_template('mentorship_area.html', is_mentor=bool(current_user.is_admin),
                           username=current_user.username)


@app.route('/api/ment/summary')
@mentorship_member_required
def ment_summary():
    folders = MentorshipFolder.query.order_by(MentorshipFolder.position, MentorshipFolder.id).all()
    fl = []
    for f in folders:
        vids = MentorshipVideo.query.filter_by(folder_id=f.id).count()
        done = (db.session.query(MentorshipProgress)
                .join(MentorshipVideo, MentorshipVideo.id == MentorshipProgress.video_id)
                .filter(MentorshipProgress.user_id == current_user.id,
                        MentorshipProgress.completed.is_(True),
                        MentorshipVideo.folder_id == f.id).count())
        fl.append({'id': f.id, 'name': f.name, 'emoji': f.emoji or '📁',
                   'description': f.description or '', 'videos': vids, 'done': done})
    latest = (MentorshipVideo.query.order_by(MentorshipVideo.created_at.desc()).limit(6).all())
    # continue watching: most recent incomplete-progress video, else first unwatched
    cont = (db.session.query(MentorshipVideo)
            .join(MentorshipProgress, MentorshipProgress.video_id == MentorshipVideo.id)
            .filter(MentorshipProgress.user_id == current_user.id,
                    MentorshipProgress.completed.is_(False))
            .order_by(MentorshipProgress.updated_at.desc()).first())
    # Campus header numbers: the four things that tell a member the membership is
    # alive — how far along they are, what is new, and what is coming.
    total_v = MentorshipVideo.query.count()
    done_v = (db.session.query(MentorshipProgress)
              .filter(MentorshipProgress.user_id == current_user.id,
                      MentorshipProgress.completed.is_(True)).count())
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    fresh = MentorshipVideo.query.filter(MentorshipVideo.created_at >= week_ago).count()
    mins = db.session.query(db.func.sum(MentorshipVideo.duration_min)).scalar() or 0
    answered = (MentorshipQuestion.query
                .filter(MentorshipQuestion.user_id == current_user.id,
                        MentorshipQuestion.answer.isnot(None))
                .order_by(MentorshipQuestion.answered_at.desc()).first())
    return jsonify({
        'live': _ment_live_dict(_ment_live_state()),
        'folders': fl,
        'latest': [_ment_video_dict(v) for v in latest],
        'continue': _ment_video_dict(cont) if cont else None,
        'stats': {'videos': total_v, 'done': done_v, 'new_week': fresh,
                  'minutes': int(mins), 'modules': len(fl)},
        'last_answer': ({'body': answered.body, 'answer': answered.answer,
                         'at': _as_utc(answered.answered_at).isoformat() if answered.answered_at else None}
                        if answered else None),
        'is_mentor': bool(current_user.is_admin),
        'open_questions': (MentorshipQuestion.query.filter(MentorshipQuestion.answer.is_(None)).count()
                           if current_user.is_admin else None),
    })


@app.route('/api/ment/folder/<int:fid>')
@mentorship_member_required
def ment_folder(fid):
    f = db.session.get(MentorshipFolder, fid)
    if not f:
        return jsonify({'error': 'not_found'}), 404
    vids = (MentorshipVideo.query.filter_by(folder_id=fid)
            .order_by(MentorshipVideo.position, MentorshipVideo.id).all())
    return jsonify({'folder': {'id': f.id, 'name': f.name, 'emoji': f.emoji or '📁',
                               'description': f.description or ''},
                    'attachments': _ment_attachments(folder_id=f.id),
                    'videos': [_ment_video_dict(v) for v in vids]})


@app.route('/api/ment/video/<int:vid>')
@mentorship_member_required
def ment_video(vid):
    v = db.session.get(MentorshipVideo, vid)
    if not v:
        return jsonify({'error': 'not_found'}), 404
    comments = (MentorshipVideoComment.query.filter_by(video_id=vid)
                .order_by(MentorshipVideoComment.created_at.asc()).limit(200).all())
    return jsonify({'video': _ment_video_dict(v, with_desc=True),
                    'comments': [{'id': c.id, 'author': c.user.username if c.user else '—',
                                  'is_mentor': bool(c.user and c.user.is_admin),
                                  'at_sec': c.at_sec, 'at': _fmt_ts(c.at_sec) if c.at_sec is not None else '',
                                  'body': c.body, 'created_at': _as_utc(c.created_at).isoformat()}
                                 for c in comments]})


@app.route('/api/ment/video/<int:vid>/comment', methods=['POST'])
@mentorship_member_required
def ment_video_comment(vid):
    if not db.session.get(MentorshipVideo, vid):
        return jsonify({'error': 'not_found'}), 404
    data = request.json if request.is_json else {}
    body = (data.get('body') or '').strip()[:1000]
    if len(body) < 2:
        return jsonify({'error': 'too_short'}), 400
    at = data.get('at')
    at = int(at) if isinstance(at, (int, float)) and 0 <= at < 24 * 3600 else None
    db.session.add(MentorshipVideoComment(video_id=vid, user_id=current_user.id,
                                          body=body, at_sec=at))
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/ment/video/<int:vid>/note', methods=['GET', 'POST'])
@mentorship_member_required
def ment_video_note(vid):
    """The member's private notebook for one class."""
    if not db.session.get(MentorshipVideo, vid):
        return jsonify({'error': 'not_found'}), 404
    row = MentorshipNote.query.filter_by(user_id=current_user.id, video_id=vid).first()
    if request.method == 'POST':
        body = (request.json.get('body') or '') if request.is_json else ''
        body = body[:20000]
        if not row:
            row = MentorshipNote(user_id=current_user.id, video_id=vid)
            db.session.add(row)
        row.body = body
        row.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({'ok': True, 'saved_at': _as_utc(row.updated_at).isoformat()})
    return jsonify({'body': (row.body if row else '') or '',
                    'saved_at': _as_utc(row.updated_at).isoformat() if row and row.updated_at else None})


@app.route('/api/ment/attachment/<int:aid>/board')
@mentorship_member_required
def ment_attachment_board(aid):
    a = db.session.get(MentorshipAttachment, aid)
    if not a or a.kind != 'board':
        return jsonify({'error': 'not_found'}), 404
    try:
        return jsonify({'ok': True, 'title': a.title, 'board': json.loads(a.payload or '{}')})
    except (ValueError, TypeError):
        return jsonify({'error': 'corrupt'}), 500


@app.route('/api/ment/attachment/<int:aid>/download')
@mentorship_member_required
def ment_attachment_download(aid):
    """Support files never live under /static: they are served here so a copied
    path is useless to someone who is not a member."""
    a = db.session.get(MentorshipAttachment, aid)
    if not a or a.kind not in ('file', 'image') or not a.filename:
        return jsonify({'error': 'not_found'}), 404
    path = os.path.join(MENT_ATTACH_DIR, a.filename)
    if not os.path.exists(path):
        return jsonify({'error': 'gone'}), 404
    return send_file(path, mimetype=a.mime or 'application/octet-stream',
                     as_attachment=(a.kind == 'file'), download_name=a.title)


@app.route('/api/ment/video/<int:vid>/progress', methods=['POST'])
@mentorship_member_required
def ment_video_progress(vid):
    if not db.session.get(MentorshipVideo, vid):
        return jsonify({'error': 'not_found'}), 404
    done = bool(request.json.get('done')) if request.is_json else False
    row = MentorshipProgress.query.filter_by(user_id=current_user.id, video_id=vid).first()
    if not row:
        row = MentorshipProgress(user_id=current_user.id, video_id=vid)
        db.session.add(row)
    row.completed = done
    row.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'ok': True, 'done': done})


@app.route('/api/ment/questions', methods=['GET', 'POST'])
@mentorship_member_required
def ment_questions():
    if request.method == 'POST':
        body = (request.json.get('body') or '').strip()[:1000] if request.is_json else ''
        if len(body) < 5:
            return jsonify({'error': 'too_short'}), 400
        pending = MentorshipQuestion.query.filter_by(user_id=current_user.id).filter(
            MentorshipQuestion.answer.is_(None)).count()
        if pending >= 5 and not current_user.is_admin:
            return jsonify({'error': 'too_many_open'}), 429
        db.session.add(MentorshipQuestion(user_id=current_user.id, body=body))
        db.session.commit()
        return jsonify({'ok': True})
    q = MentorshipQuestion.query
    if not current_user.is_admin:
        q = q.filter_by(user_id=current_user.id)
    rows = q.order_by(MentorshipQuestion.created_at.desc()).limit(100).all()
    return jsonify({'questions': [
        {'id': r.id, 'body': r.body, 'answer': r.answer,
         'author': r.user.username if r.user else '—',
         'created_at': _as_utc(r.created_at).isoformat(),
         'answered_at': _as_utc(r.answered_at).isoformat() if r.answered_at else None}
        for r in rows]})


@app.route('/api/ment/channels')
@mentorship_member_required
def ment_channels():
    rows = MentorshipChannel.query.order_by(MentorshipChannel.position, MentorshipChannel.id).all()
    return jsonify({'channels': [
        {'id': c.id, 'name': c.name, 'emoji': c.emoji or '💬',
         'description': c.description or '', 'locked': bool(c.locked)} for c in rows]})


@app.route('/api/ment/channel/<int:cid>/messages')
@mentorship_member_required
def ment_channel_messages(cid):
    ch = db.session.get(MentorshipChannel, cid)
    if not ch:
        return jsonify({'error': 'not_found'}), 404
    try:
        after = int(request.args.get('after', 0))
    except (TypeError, ValueError):
        after = 0
    q = MentorshipMessage.query.filter_by(channel_id=cid, is_deleted=False)
    if after:
        rows = q.filter(MentorshipMessage.id > after).order_by(MentorshipMessage.id.asc()).limit(80).all()
    else:
        rows = q.order_by(MentorshipMessage.id.desc()).limit(60).all()[::-1]
    pinned = (MentorshipMessage.query.filter_by(channel_id=cid, is_deleted=False, pinned=True)
              .order_by(MentorshipMessage.id.desc()).limit(3).all())
    return jsonify({'messages': [_ment_msg_dict(m) for m in rows],
                    'pinned': [_ment_msg_dict(m) for m in pinned],
                    'locked': bool(ch.locked)})


@app.route('/api/ment/channel/<int:cid>/message', methods=['POST'])
@mentorship_member_required
def ment_channel_post(cid):
    ch = db.session.get(MentorshipChannel, cid)
    if not ch:
        return jsonify({'error': 'not_found'}), 404
    if ch.locked and not current_user.is_admin:
        return jsonify({'error': 'locked'}), 403
    data = request.json if request.is_json else {}
    body = (data.get('body') or '').strip()[:2000]
    if len(body) < 1:
        return jsonify({'error': 'too_short'}), 400
    # cheap flood guard: max 20 messages per minute per user
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    recent = MentorshipMessage.query.filter(MentorshipMessage.user_id == current_user.id,
                                            MentorshipMessage.created_at >= cutoff).count()
    if recent >= 20:
        return jsonify({'error': 'rate_limited'}), 429
    reply_to = data.get('reply_to')
    if reply_to:
        rm = db.session.get(MentorshipMessage, int(reply_to))
        if not rm or rm.channel_id != cid:
            reply_to = None
    m = MentorshipMessage(channel_id=cid, user_id=current_user.id, body=body,
                          reply_to_id=int(reply_to) if reply_to else None)
    db.session.add(m)
    db.session.commit()
    return jsonify({'ok': True, 'message': _ment_msg_dict(m)})


@app.route('/api/ment/message/<int:mid>/react', methods=['POST'])
@mentorship_member_required
def ment_message_react(mid):
    m = db.session.get(MentorshipMessage, mid)
    if not m or m.is_deleted:
        return jsonify({'error': 'not_found'}), 404
    emoji = (request.json.get('emoji') or '') if request.is_json else ''
    if emoji not in MENT_REACTIONS:
        return jsonify({'error': 'bad_emoji'}), 400
    row = MentorshipMsgReaction.query.filter_by(message_id=mid, user_id=current_user.id).first()
    if row and row.emoji == emoji:
        db.session.delete(row)          # toggle off
    elif row:
        row.emoji = emoji
    else:
        db.session.add(MentorshipMsgReaction(message_id=mid, user_id=current_user.id, emoji=emoji))
    db.session.commit()
    return jsonify({'ok': True})


# ── Mentor (admin) tools for the area ──────────────────────────────────────
def _mentor_only():
    if not (current_user.is_authenticated and current_user.is_admin):
        return jsonify({'error': 'forbidden'}), 403
    return None


@app.route('/api/ment/admin/folder', methods=['POST'])
@login_required
def ment_admin_folder():
    guard = _mentor_only()
    if guard: return guard
    d = request.json if request.is_json else {}
    name = (d.get('name') or '').strip()[:80]
    if len(name) < 2:
        return jsonify({'error': 'too_short'}), 400
    f = MentorshipFolder(name=name, description=(d.get('description') or '').strip()[:300] or None,
                         emoji=(d.get('emoji') or '').strip()[:8] or None,
                         position=int(d.get('position') or 0))
    db.session.add(f); db.session.commit()
    return jsonify({'ok': True, 'id': f.id})


@app.route('/api/ment/admin/folder/<int:fid>/delete', methods=['POST'])
@login_required
def ment_admin_folder_delete(fid):
    guard = _mentor_only()
    if guard: return guard
    f = db.session.get(MentorshipFolder, fid)
    if f:
        MentorshipVideo.query.filter_by(folder_id=fid).update({'folder_id': None})
        db.session.delete(f); db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/ment/admin/video', methods=['POST'])
@login_required
def ment_admin_video():
    guard = _mentor_only()
    if guard: return guard
    d = request.json if request.is_json else {}
    title = (d.get('title') or '').strip()[:160]
    url_ = (d.get('video_url') or '').strip()[:500]
    if len(title) < 2 or not (url_.startswith('http://') or url_.startswith('https://')):
        return jsonify({'error': 'invalid'}), 400
    kind = d.get('kind') if d.get('kind') in ('class', 'live', 'backtest') else 'class'
    fid = d.get('folder_id')
    source, provider_id, auto_thumb = _video_meta_from_url(url_)
    thumb = (d.get('thumb_url') or '').strip()[:500] or auto_thumb
    v = MentorshipVideo(folder_id=int(fid) if fid else None, title=title,
                        description=(d.get('description') or '').strip()[:4000] or None,
                        video_url=url_, source=source, provider_id=provider_id,
                        thumb_url=thumb,
                        duration_min=int(d.get('duration_min')) if d.get('duration_min') else None,
                        kind=kind, position=int(d.get('position') or 0))
    db.session.add(v); db.session.commit()
    return jsonify({'ok': True, 'id': v.id})


@app.route('/api/ment/admin/video/<int:vid>/delete', methods=['POST'])
@login_required
def ment_admin_video_delete(vid):
    guard = _mentor_only()
    if guard: return guard
    v = db.session.get(MentorshipVideo, vid)
    if v:
        MentorshipVideoComment.query.filter_by(video_id=vid).delete()
        MentorshipProgress.query.filter_by(video_id=vid).delete()
        MentorshipNote.query.filter_by(video_id=vid).delete()
        for a in MentorshipAttachment.query.filter_by(video_id=vid).all():
            if a.filename:
                try:
                    os.remove(os.path.join(MENT_ATTACH_DIR, a.filename))
                except OSError:
                    pass
            db.session.delete(a)
        db.session.delete(v); db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/ment/admin/live', methods=['POST'])
@login_required
def ment_admin_live():
    guard = _mentor_only()
    if guard: return guard
    d = request.json if request.is_json else {}
    row = _ment_live_state()
    row.is_live = bool(d.get('is_live'))
    row.title = (d.get('title') or '').strip()[:160] or None
    row.url = (d.get('url') or '').strip()[:500] or None
    row.note = (d.get('note') or '').strip()[:300] or None
    row.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'ok': True, 'live': _ment_live_dict(row)})


@app.route('/api/ment/admin/video/<int:vid>/chapters', methods=['POST'])
@login_required
def ment_admin_chapters(vid):
    guard = _mentor_only()
    if guard: return guard
    v = db.session.get(MentorshipVideo, vid)
    if not v:
        return jsonify({'error': 'not_found'}), 404
    chapters = _parse_chapters((request.json or {}).get('raw') if request.is_json else '')
    v.chapters = json.dumps(chapters) if chapters else None
    db.session.commit()
    return jsonify({'ok': True, 'chapters': _ment_chapters(v)})


@app.route('/api/ment/admin/attachment', methods=['POST'])
@login_required
def ment_admin_attachment():
    """Attach support material to a class or a module. Three shapes share this
    endpoint: an uploaded file (multipart), an external link, or a Chalkboard
    project captured from the mentor's own board (JSON)."""
    guard = _mentor_only()
    if guard: return guard
    is_json = request.is_json
    d = request.json if is_json else request.form
    title = (d.get('title') or '').strip()[:160]
    vid = d.get('video_id') or None
    fid = d.get('folder_id') or None
    try:
        vid = int(vid) if vid else None
        fid = int(fid) if fid else None
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid'}), 400
    if not vid and not fid:
        return jsonify({'error': 'no_target'}), 400
    if vid and not db.session.get(MentorshipVideo, vid):
        return jsonify({'error': 'not_found'}), 404
    if fid and not db.session.get(MentorshipFolder, fid):
        return jsonify({'error': 'not_found'}), 404

    kind = d.get('kind')
    if kind == 'link':
        url_ = (d.get('url') or '').strip()[:500]
        if not (url_.startswith('http://') or url_.startswith('https://')) or len(title) < 2:
            return jsonify({'error': 'invalid'}), 400
        a = MentorshipAttachment(video_id=vid, folder_id=fid, kind='link',
                                 title=title, url=url_)
    elif kind == 'board':
        board = d.get('board')
        raw = json.dumps(board) if board is not None else ''
        if not raw or len(raw) > MENT_BOARD_MAX or not isinstance(board, dict) or not board.get('slides'):
            return jsonify({'error': 'bad_board'}), 400
        a = MentorshipAttachment(video_id=vid, folder_id=fid, kind='board',
                                 title=title or 'Pizarrón', payload=raw, size=len(raw))
    else:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': 'no_file'}), 400
        mime = (f.content_type or '').lower().split(';')[0]
        if mime not in MENT_ATTACH_MIME:
            return jsonify({'error': 'format'}), 400
        data = f.read()
        if not data:
            return jsonify({'error': 'empty'}), 400
        if len(data) > MENT_ATTACH_MAX:
            return jsonify({'error': 'too_large'}), 400
        akind, ext = MENT_ATTACH_MIME[mime]
        os.makedirs(MENT_ATTACH_DIR, exist_ok=True)
        stored = '%s.%s' % (secrets.token_urlsafe(16), ext)
        with open(os.path.join(MENT_ATTACH_DIR, stored), 'wb') as fh:
            fh.write(data)
        a = MentorshipAttachment(video_id=vid, folder_id=fid, kind=akind,
                                 title=title or f.filename[:160] or 'Material',
                                 filename=stored, mime=mime, size=len(data))
    db.session.add(a)
    db.session.commit()
    return jsonify({'ok': True, 'attachment': _attach_dict(a)})


@app.route('/api/ment/admin/attachment/<int:aid>/delete', methods=['POST'])
@login_required
def ment_admin_attachment_delete(aid):
    guard = _mentor_only()
    if guard: return guard
    a = db.session.get(MentorshipAttachment, aid)
    if a:
        if a.filename:
            try:
                os.remove(os.path.join(MENT_ATTACH_DIR, a.filename))
            except OSError:
                pass        # the row is the record; a missing file must not 500
        db.session.delete(a)
        db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/ment/admin/settings', methods=['POST'])
@login_required
def ment_admin_settings():
    """Area-wide switches. Stored on the singleton live-state row."""
    guard = _mentor_only()
    if guard: return guard
    d = request.json if request.is_json else {}
    row = _ment_live_state()
    if 'watermark' in d:
        row.watermark_on = bool(d.get('watermark'))
    db.session.commit()
    return jsonify({'ok': True, 'live': _ment_live_dict(row)})


@app.route('/api/ment/admin/question/<int:qid>/answer', methods=['POST'])
@login_required
def ment_admin_answer(qid):
    guard = _mentor_only()
    if guard: return guard
    q = db.session.get(MentorshipQuestion, qid)
    if not q:
        return jsonify({'error': 'not_found'}), 404
    ans = (request.json.get('answer') or '').strip()[:4000] if request.is_json else ''
    if len(ans) < 2:
        return jsonify({'error': 'too_short'}), 400
    q.answer = ans
    q.answered_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/ment/admin/channel', methods=['POST'])
@login_required
def ment_admin_channel():
    guard = _mentor_only()
    if guard: return guard
    d = request.json if request.is_json else {}
    name = (d.get('name') or '').strip()[:60]
    if len(name) < 2:
        return jsonify({'error': 'too_short'}), 400
    c = MentorshipChannel(name=name, emoji=(d.get('emoji') or '').strip()[:8] or None,
                          description=(d.get('description') or '').strip()[:200] or None,
                          locked=bool(d.get('locked')), position=int(d.get('position') or 0))
    db.session.add(c); db.session.commit()
    return jsonify({'ok': True, 'id': c.id})


@app.route('/api/ment/admin/message/<int:mid>/pin', methods=['POST'])
@login_required
def ment_admin_pin(mid):
    guard = _mentor_only()
    if guard: return guard
    m = db.session.get(MentorshipMessage, mid)
    if not m:
        return jsonify({'error': 'not_found'}), 404
    m.pinned = not m.pinned
    db.session.commit()
    return jsonify({'ok': True, 'pinned': m.pinned})


@app.route('/api/ment/admin/message/<int:mid>/delete', methods=['POST'])
@login_required
def ment_admin_msg_delete(mid):
    guard = _mentor_only()
    if guard: return guard
    m = db.session.get(MentorshipMessage, mid)
    if m:
        m.is_deleted = True
        db.session.commit()
    return jsonify({'ok': True})


@app.route('/mentorship/checkout')
@login_required
def mentorship_checkout_review():
    """Cart / review page between picking a package on /improve/plans and
    creating the order — mirrors the site-plan checkout ("Review your order"):
    the chosen program, what's included, and the total. Price and label come
    from MENTORSHIP_SKUS server-side; the sku only selects which one."""
    _mentorship_gate()
    sku = (request.args.get('sku') or '').strip()
    spec = MENTORSHIP_SKUS.get(sku)
    if not spec:
        return redirect(url_for('improve_plans'))
    return render_template('mentorship_checkout.html', sku=sku, spec=spec)


@app.route('/mentorship/checkout/create', methods=['POST'])
@login_required
def mentorship_checkout_create():
    """Start a mentorship purchase for a chosen SKU. The price is taken from
    MENTORSHIP_SKUS server-side (never from the client). Mirrors the plan
    checkout: with Stripe on it hands off to Stripe Checkout (mode=payment);
    with Stripe off (or price 0) it falls through to a manual/pending page.
    This flow NEVER touches `user.plan`."""
    _mentorship_gate()
    sku = (request.form.get('sku') or '').strip()
    spec = MENTORSHIP_SKUS.get(sku)
    if not spec:
        return redirect(url_for('improve_plans'))

    # Purchase-time T&C acceptance (the review page carries a required checkbox;
    # this is the server-side backstop). Send them back to review if missing.
    if request.form.get('terms_ok') != '1':
        return redirect(url_for('mentorship_checkout_review', sku=sku))

    # One pending mentorship order at a time — don't let them pile up.
    existing = MentorshipOrder.query.filter_by(
        user_id=current_user.id, status='pending').first()
    if existing and existing.sku != sku:
        existing.status = 'cancelled'  # replace the stale selection
    if existing and existing.sku == sku:
        order = existing
    else:
        order = MentorshipOrder(
            user_id=current_user.id, sku=sku, kind=spec['kind'],
            label=spec['label'], price=float(spec['price']),
            status='pending', payment_method='manual')
        db.session.add(order)
    db.session.commit()
    record_audit_event('mentorship_order_created', user_id=current_user.id,
                        detail=f'{sku} ${order.price:.2f} (T&C accepted at checkout)')

    if STRIPE_ENABLED and order.price > 0:
        try:
            checkout_session = _stripe.checkout.Session.create(
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Tradeable Mentorship — {spec["label"]}',
                            'description': 'Mentorship purchase',
                        },
                        'unit_amount': int(round(order.price * 100)),  # cents
                    },
                    'quantity': 1,
                }],
                success_url=url_for('mentorship_checkout_success', _external=True)
                            + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('improve_plans', _external=True),
                client_reference_id=str(order.id),
                customer_email=current_user.email,
                # `kind` lets the shared webhook route this to the mentorship
                # path instead of the plan path — the two never cross.
                metadata={'kind': 'mentorship', 'mentorship_order_id': str(order.id)},
            )
            order.payment_method = 'stripe'
            db.session.commit()
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            app.logger.error('Stripe mentorship session create failed: %s', e)
            # fall through to the manual/pending page

    return render_template('mentorship_checkout_done.html', order=order)


@app.route('/mentorship/checkout/success')
@login_required
def mentorship_checkout_success():
    """Where Stripe returns the buyer after a successful mentorship payment.
    Verifies the session and fulfils via the idempotent activator (which never
    touches `user.plan`). The webhook is the canonical path; this covers local
    testing without a public webhook."""
    _mentorship_gate()
    session_id = request.args.get('session_id', '')
    if not (STRIPE_ENABLED and session_id):
        return redirect(url_for('improve_plans'))
    try:
        sess = _stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        app.logger.error('Stripe mentorship session retrieve failed: %s', e)
        return redirect(url_for('improve_plans'))
    order = db.session.get(MentorshipOrder, int(sess.get('client_reference_id') or 0))
    if (order and order.user_id == current_user.id
            and sess.get('payment_status') == 'paid'):
        if order.status == 'pending':
            order.status = 'paid'
            order.paid_at = datetime.now(timezone.utc)
            db.session.commit()
            activated = _activate_mentorship_order(order)
            record_audit_event('mentorship_order_paid', user_id=order.user_id,
                                detail=f'stripe mentorship #{order.id} {order.sku} ${order.price:.2f}',
                                success=activated)
        return render_template('mentorship_checkout_success.html', order=order)
    return redirect(url_for('improve_plans'))


# ── Application anti-spam throttle ────────────────────────────────────────
# The apply form is PUBLIC (no login required), so a joker could hammer it and
# flood both the DB and the company inbox. Rule: one submission per person per
# 24 h — for everyone, admin included. "Person" is matched three ways because
# an anonymous spammer can rotate any single one of them:
#   · account   — the logged-in user id
#   · email     — the address typed into the form
#   · device/IP — capped a bit looser (a household or office can share one NAT,
#                 so 1/24h per IP would block a legitimate second applicant)
MENTORSHIP_APPLY_WINDOW = timedelta(hours=24)
MENTORSHIP_APPLY_IP_MAX = 3


def _client_ip():
    """Best-effort client IP. Honours X-Forwarded-For (first hop) so the value
    stays correct once nginx sits in front of gunicorn."""
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()[:45]
    return (request.remote_addr or '')[:45]


def _apply_throttle_retry_after(email, ip):
    """Seconds the visitor must wait before applying again, or 0 if they may
    submit now. Counts only accepted submissions, so a blocked attempt never
    pushes the window further out."""
    now = datetime.now(timezone.utc)
    cutoff = now - MENTORSHIP_APPLY_WINDOW
    stamp = db.func.coalesce(MentorshipApplication.last_submit_at,
                             MentorshipApplication.created_at)

    def _wait(row):
        last = _aware(row.last_submit_at or row.created_at)
        if not last:
            return 0
        return max(1, int((last + MENTORSHIP_APPLY_WINDOW - now).total_seconds()))

    # 1) same account
    if current_user.is_authenticated:
        row = (MentorshipApplication.query
               .filter(MentorshipApplication.user_id == current_user.id, stamp >= cutoff)
               .order_by(stamp.desc()).first())
        if row:
            return _wait(row)
    # 2) same email
    if email:
        row = (MentorshipApplication.query
               .filter(db.func.lower(MentorshipApplication.email) == email, stamp >= cutoff)
               .order_by(stamp.desc()).first())
        if row:
            return _wait(row)
    # 3) same device/IP — looser cap so shared connections aren't punished
    if ip:
        rows = (MentorshipApplication.query
                .filter(MentorshipApplication.submit_ip == ip, stamp >= cutoff)
                .order_by(stamp.asc()).all())
        if len(rows) >= MENTORSHIP_APPLY_IP_MAX:
            return _wait(rows[0])   # freed when the OLDEST of them ages out
    return 0


@app.route('/api/improve/apply', methods=['POST'])
def improve_apply_submit():
    _mentorship_gate()
    data = request.get_json(silent=True) or {}

    def _s(key, maxlen):
        v = data.get(key)
        return v.strip()[:maxlen] if isinstance(v, str) else ''

    def _csv(key, allowed, maxn):
        """Multi-select: accept a list (or CSV string) of keys, all in `allowed`."""
        v = data.get(key)
        if isinstance(v, str):
            v = [x.strip() for x in v.split(',')]
        if not isinstance(v, list):
            return None
        seen = []
        for x in v[:maxn]:
            if not isinstance(x, str) or x not in allowed:
                return None
            if x not in seen:
                seen.append(x)
        return ','.join(seen) if seen else None

    name = _s('name', 80)
    username = _s('username', 40)
    email = _s('email', 255).lower()
    experience = _s('experience', 20)
    situation = _s('situation', 20)
    program = _s('program', 12)
    hours_week = _s('hours', 20)
    goals = _csv('goals', _APPLY_GOALS, 6)
    strength = _s('strength', 20)
    weakness = _s('weakness', 20)
    assets = _csv('assets', _APPLY_ASSETS, 2)
    country = _s('country', 80)
    tzname = _s('tz', 60) or None            # auto-captured, best-effort
    call_lang = _s('call_lang', 10)
    call_slot = _s('call_slot', 12)
    source = _s('source', 20)
    age_range = _s('age', 10)
    adult = bool(data.get('adult'))
    waiver = bool(data.get('waiver'))
    lang = _s('lang', 5) or None

    # Every field is required (the form is a get-to-know-the-trader FAQ).
    if not (name and username and email and '@' in email and adult and waiver
            and experience in _APPLY_EXPERIENCE and situation in _APPLY_SITUATION
            and program in _APPLY_PROGRAM and hours_week in _APPLY_HOURS
            and goals and strength in _APPLY_SKILL and weakness in _APPLY_SKILL
            and assets and country and call_lang in _APPLY_CLANG
            and call_slot in _APPLY_SLOT and source in _APPLY_SOURCE
            and age_range in _APPLY_AGE):
        return jsonify({'ok': False, 'error': 'invalid'}), 400

    # Anti-spam: one submission per person per 24 h (see the throttle helper).
    # Checked AFTER validation so a malformed payload can't burn someone's slot.
    ip = _client_ip()
    retry_after = _apply_throttle_retry_after(email, ip)
    if retry_after:
        return jsonify({'ok': False, 'error': 'throttled',
                        'retry_after': retry_after}), 429

    # One pending application per email — resubmits just refresh the existing
    # one instead of piling up duplicates for review.
    existing = MentorshipApplication.query.filter_by(email=email, status='pending').first()
    now = datetime.now(timezone.utc)
    if existing:
        existing.name, existing.username = name, username
        existing.experience, existing.situation = experience, situation
        existing.hours_week, existing.program = hours_week, program
        existing.goals, existing.strength, existing.weakness = goals, strength, weakness
        existing.assets, existing.country, existing.tzname = assets, country, tzname
        existing.call_lang, existing.call_slot = call_lang, call_slot
        existing.source, existing.age_range = source, age_range
        existing.waiver_accepted_at, existing.lang = now, lang
        existing.last_submit_at, existing.submit_ip = now, ip or None
        existing.submit_count = (existing.submit_count or 1) + 1
        if current_user.is_authenticated:
            existing.user_id = current_user.id
        application = existing
    else:
        application = MentorshipApplication(
            user_id=current_user.id if current_user.is_authenticated else None,
            name=name, username=username, email=email,
            experience=experience, situation=situation,
            program=program, struggle='', why='', hours_week=hours_week,
            goals=goals, strength=strength, weakness=weakness, assets=assets,
            country=country, tzname=tzname, call_lang=call_lang, call_slot=call_slot,
            source=source, age_range=age_range,
            waiver_accepted_at=now, lang=lang,
            last_submit_at=now, submit_ip=ip or None, submit_count=1)
        db.session.add(application)
    db.session.commit()
    # Company inbox copy (best-effort; the DB row is the source of truth).
    try:
        send_mentorship_application_email(application)
    except Exception as exc:
        app.logger.warning('mentorship application email raised: %s', exc)
    # Unlocks /improve/plans (the offer) for this visitor — filter first, then prices.
    session['improve_applied'] = True
    return jsonify({'ok': True, 'next': url_for('improve_plans')})


@app.route('/camos')
def camos():
    if current_user.is_authenticated:
        owned = sorted(s for s in CAMO_SLUGS if current_user.owns_camo(s))
        active = current_user.active_camo or ''
        authed = True
    else:
        owned, active, authed = [], '', False
    return render_template('camos.html',
                           camo_owned=owned, camo_active=active,
                           camo_ready=sorted(CAMO_READY), camo_authed=authed)


@app.route('/api/camo/activate', methods=['POST'])
@login_required
def camo_activate():
    """Activate an owned, ready camo as the user's website skin."""
    slug = ((request.get_json(silent=True) or {}).get('slug') or '').strip()
    if slug not in CAMO_READY:
        return jsonify({'error': 'not_available'}), 400
    if not current_user.owns_camo(slug):
        return jsonify({'error': 'not_owned'}), 403
    current_user.active_camo = slug
    db.session.commit()
    return jsonify({'ok': True, 'active': slug})


@app.route('/api/camo/deactivate', methods=['POST'])
@login_required
def camo_deactivate():
    """Revert to the default (light/dark) theme."""
    current_user.active_camo = ''
    db.session.commit()
    return jsonify({'ok': True, 'active': ''})


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/guide')
def guide():
    return render_template('guide.html')


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


@app.route('/api/bug/report', methods=['POST'])
@login_required
def api_bug_report():
    """Accept a user bug report. Technical context (page, browser, plan, recent
    console errors) is captured automatically so the admin can verify a real bug
    quickly. No reward is promised here — it stays discretionary on review."""
    data = request.get_json(silent=True) or {}
    desc = (data.get('description') or '').strip()[:4000]
    kind = (data.get('kind') or 'other').strip()[:20]
    if kind not in ('visual', 'broken', 'data', 'other'):
        kind = 'other'
    if len(desc) < 8:
        return jsonify({'ok': False, 'error': 'too_short'}), 200
    # Anti-spam: cap reports per user per hour.
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = BugReport.query.filter(
        BugReport.user_id == current_user.id,
        BugReport.created_at >= since).count()
    if recent >= 5:
        return jsonify({'ok': False, 'error': 'rate_limited'}), 200
    report = BugReport(
        user_id=current_user.id,
        username=current_user.username,
        kind=kind, description=desc,
        page_url=(data.get('url') or '')[:500] or None,
        user_agent=(request.headers.get('User-Agent') or '')[:400] or None,
        plan=current_user.plan,
        console_log=(data.get('console') or '')[:6000] or None,
        status='new',
    )
    db.session.add(report)
    db.session.commit()
    record_audit_event('bug_report', user_id=current_user.id,
                       detail=f'{kind}: {desc[:80]}', success=True)
    try:
        _send_bug_email(report)
    except Exception as e:
        app.logger.error('bug email failed: %s', e)
    return jsonify({'ok': True, 'id': report.id})


@app.route('/admin/bug/update', methods=['POST'])
@login_required
def admin_bug_update():
    if not current_user.is_admin:
        abort(403)
    report = db.session.get(BugReport, int(request.form.get('id', 0)))
    if not report:
        abort(404)
    status = request.form.get('status', '')
    if status in ('new', 'reviewing', 'resolved', 'not_repro'):
        report.status = status
    note = request.form.get('note')
    if note is not None:
        report.admin_note = note.strip()[:600] or None
    rewarded = request.form.get('rewarded')
    if rewarded is not None:
        report.rewarded = rewarded == '1'
    db.session.commit()
    return redirect(url_for('admin') + '#bugs')


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
        # Only the explicit 'review' demo shows the testimonial prompt — otherwise
        # a plan/rank/spin demo could leak the admin's own pending testimonial
        # (which the client now shows immediately in demo mode).
        if not demo.get('review'):
            review_prompt = False
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

    # Aurora Glass rail — expose the analysis quota (read-only; additive, no
    # behaviour change). Reuses the same PLAN_LIMITS window + UsageLog count
    # that check_rate_limit() enforces, so the rail matches the real limit.
    _q_cfg = PLAN_LIMITS.get(plan_view, PLAN_LIMITS['free'])
    _q_since = datetime.now(timezone.utc) - _q_cfg['window']
    analyses_used = (UsageLog.query
                     .filter(UsageLog.user_id == current_user.id,
                             UsageLog.created_at >= _q_since).count())
    analyses_max = _q_cfg['max']
    resp = make_response(render_template(
        'index.html',
        plan=plan_view,
        analyses_used=analyses_used,
        analyses_max=analyses_max,
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
        active_camo=(current_user.active_camo or ''),
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

    # ── Individual AI calls (most recent) — per-call cost breakdown, not just the
    #    daily total, so each analysis can be inspected on its own. ──
    recent_calls = (AICostLog.query
                    .order_by(AICostLog.created_at.desc())
                    .limit(100).all())
    ai_calls_recent = [{
        'time': c.created_at,
        'user': (uname.get(c.user_id) if c.user_id is not None else 'anon') or '—',
        'plan': c.plan or '—',
        'kind': c.kind,
        'cat': KIND_CAT.get(c.kind, 'analyzer'),
        'model': c.model or '—',
        'pt': int(c.prompt_tokens or 0),
        'ct': int(c.completion_tokens or 0),
        'cost': float(c.cost_usd or 0.0),
    } for c in recent_calls]

    return {
        'ai_rows': rows[:120], 'ai_flagged': flagged,
        'ai_calls_recent': ai_calls_recent,
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

    # ── Bug reports: newest first, with a badge for untriaged ones ──
    bug_rows = BugReport.query.order_by(BugReport.created_at.desc()).limit(120).all()
    bug_reports = [{
        'id': b.id, 'username': b.username or (uname.get(b.user_id, '—')),
        'user_id': b.user_id, 'kind': b.kind, 'description': b.description,
        'page_url': b.page_url, 'user_agent': b.user_agent, 'plan': b.plan,
        'console_log': b.console_log, 'status': b.status, 'admin_note': b.admin_note,
        'rewarded': b.rewarded, 'created_at': b.created_at,
    } for b in bug_rows]
    bug_new_count = sum(1 for b in bug_rows if b.status == 'new')

    ai_ctx = _build_ai_analytics_context()

    # Opening the panel re-checks every recent unpaid order with the processor.
    # This is what makes a lost notification impossible to miss: the owner does
    # not have to wait for the buyer to come back and reload their page.
    swept, recovered = payments_sweep()
    attention = orders_needing_attention()

    return render_template(
        'admin.html', users=users, counts=counts,
        audit_events=audit_events, audit_failed_count=audit_failed_count,
        warn_counts=warn_counts, recent_warnings=recent_warnings, flagged=flagged,
        ban_queue=ban_queue, demo_active=_admin_demo() is not None,
        bug_reports=bug_reports, bug_new_count=bug_new_count,
        pay_attention=attention, pay_swept=swept, pay_recovered=recovered,
        crypto_on=bool(available_payment_rails()), sla_hours=CRYPTO_SLA_HOURS,
        **ai_ctx, **revenue,
    )


@app.route('/admin/trace')
@login_required
def admin_trace():
    """Evidence sheet for one purchase (or the search results to pick one)."""
    if not current_user.is_admin:
        return redirect(url_for('app_view'))
    q = (request.args.get('q') or '').strip()
    oid = request.args.get('order', type=int)
    trace, results = None, []
    if oid:
        o = db.session.get(Order, oid)
        if o:
            trace = order_trace(o)
    elif q:
        results = find_orders(q)
        if len(results) == 1:
            trace, results = order_trace(results[0]), []
    return render_template('admin_trace.html', q=q, trace=trace, results=results,
                           plan_labels=PLAN_LABELS)


@app.route('/admin/device-preview')
@login_required
def admin_device_preview():
    """Admin-only responsive preview: renders the live site inside phone and
    tablet frames so we can catch mobile/iPad layout issues from a desktop."""
    if not current_user.is_admin:
        return redirect(url_for('app_view'))
    d = _admin_demo() or {}
    return render_template('device_preview.html', demo_plan=d.get('plan') or 'normal')


def _preview_order(plan='premium', cycle='monthly'):
    """A fake, un-persisted Order for the admin checkout/payment previews.
    Never touches the DB — pure render data so we can eyeball the screens."""
    from types import SimpleNamespace
    q = _quote(plan, cycle)
    return SimpleNamespace(
        id=99999, plan=plan, billing_cycle=cycle,
        base_price=q['base_price'], discount_pct=0,
        final_price=q['final_price'], promo_code=None, status='pending',
    )


def _preview_plan_cycle():
    """Read + sanitize plan/cycle query args for the admin preview routes."""
    plan = request.args.get('plan', 'premium')
    cycle = request.args.get('cycle', 'monthly')
    if plan not in PLAN_PRICING or cycle not in ('monthly', 'annual'):
        return 'premium', 'monthly'
    return plan, cycle


@app.route('/admin/preview/checkout')
@login_required
def admin_preview_checkout():
    """Admin-only: the checkout cart exactly as a buyer sees it, but read-only
    (no order created, no charge). The pay button walks to the success preview."""
    if not current_user.is_admin:
        return redirect(url_for('app_view'))
    plan, cycle = _preview_plan_cycle()
    return render_template('checkout.html', plan=plan, cycle=cycle,
                           plan_label=PLAN_LABELS[plan], quote=_quote(plan, cycle),
                           preview=True,
                           preview_next=url_for('admin_preview_success', plan=plan, cycle=cycle))


@app.route('/admin/preview/success')
@login_required
def admin_preview_success():
    """Admin-only: the post-payment success screen with sample data."""
    if not current_user.is_admin:
        return redirect(url_for('app_view'))
    plan, cycle = _preview_plan_cycle()
    return render_template('checkout_success.html', order=_preview_order(plan, cycle),
                           plan_label=PLAN_LABELS[plan], preview=True)


@app.route('/admin/preview/order')
@login_required
def admin_preview_order():
    """Admin-only: the manual 'order received' screen (USDT/bank fallback view,
    shown only when Stripe is off)."""
    if not current_user.is_admin:
        return redirect(url_for('app_view'))
    plan, cycle = _preview_plan_cycle()
    return render_template('checkout_done.html', order=_preview_order(plan, cycle),
                           plan_label=PLAN_LABELS[plan], duplicate=False, preview=True)


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

    # Expenses. The whole ledger is read at once — this table stays small, and
    # it lets the panel offer any month without another round trip.
    all_expenses = Expense.query.order_by(Expense.incurred_on.desc(),
                                          Expense.id.desc()).all()

    def _key(d):
        return '%04d-%02d' % (d.year, d.month) if d else ''

    this_key = _key(month_start.date())
    # Every month that has something recorded, newest first, plus the current
    # one so it is always selectable even before the first expense is logged.
    months = {}
    for e in all_expenses:
        k = _key(e.incurred_on)
        if k:
            slot = months.setdefault(k, {'key': k, 'total': 0.0, 'count': 0})
            slot['total'] += e.amount or 0.0
            slot['count'] += 1
    months.setdefault(this_key, {'key': this_key, 'total': 0.0, 'count': 0})
    for k, m in months.items():
        y, mo = int(k[:4]), int(k[5:])
        m['label'] = datetime(y, mo, 1).strftime('%B %Y')
        m['total'] = round(m['total'], 2)
        m['is_current'] = (k == this_key)
    expense_months = sorted(months.values(), key=lambda m: m['key'], reverse=True)

    # The month being browsed. Defaults to the current one; an unknown value
    # falls back to it rather than showing an empty table for no clear reason.
    view_key = (request.args.get('exp_month') or '').strip()
    if view_key not in months:
        view_key = this_key

    # The KPI cards and net profit always describe the CURRENT month — browsing
    # the history must not silently change what "profit this month" means.
    expenses_total = round(sum(e.amount for e in all_expenses
                               if _key(e.incurred_on) == this_key), 2)
    view_expenses = [e for e in all_expenses if _key(e.incurred_on) == view_key]
    expense_rows = [{
        'id': e.id, 'label': e.label, 'category': e.category,
        'amount': e.amount, 'incurred_on': e.incurred_on,
        'recurring': e.recurring, 'note': e.note,
    } for e in view_expenses]
    expense_view_total = round(sum(e.amount for e in view_expenses), 2)

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
        'expense_months': expense_months,
        'expense_view_key': view_key,
        'expense_view_total': expense_view_total,
        'expense_view_is_current': view_key == this_key,
        'expense_view_label': months[view_key]['label'],
        'expenses_lifetime': round(sum(e.amount for e in all_expenses), 2),
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
# ═══ Crypto payments ══════════════════════════════════════════════════════
def _crypto_api(method, path, payload=None):
    """Small JSON client for the payment processor.

    Deliberately tiny and isolated: every provider-specific detail (base URL,
    auth header, field names) lives here, so switching processors later is a
    change in this file section, not across the app."""
    url = CRYPTO_API_BASE.rstrip('/') + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('x-api-key', CRYPTO_API_KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


# Processor statuses that mean "the money is in".
CRYPTO_PAID_STATES = ('finished', 'confirmed')
CRYPTO_FAILED_STATES = ('failed', 'refunded', 'expired')


def _crypto_create_invoice(order, kind='plan'):
    """Create a hosted invoice and return its URL, or None on failure.

    A failure here must never dead-end the buyer: the caller falls back to the
    manual instructions, and the order still exists so it can be settled later."""
    label = ('Tradeable — %s' % PLAN_LABELS.get(order.plan, order.plan)) if kind == 'plan' \
            else ('Tradeable — %s' % getattr(order, 'label', 'Order'))
    price = order.final_price if kind == 'plan' else order.price
    try:
        inv = _crypto_api('POST', '/invoice', {
            'price_amount': round(float(price), 2),
            'price_currency': 'usd',
            'pay_currency': CRYPTO_PAY_CURRENCY,
            'order_id': '%s-%d' % (kind, order.id),
            'order_description': label,
            'ipn_callback_url': url_for('crypto_webhook', _external=True),
            'success_url': url_for('checkout_status', order_id=order.id, _external=True),
            'cancel_url': url_for('checkout_status', order_id=order.id, _external=True),
        })
    except Exception as exc:
        app.logger.error('crypto invoice create failed (order %s): %s', order.id, exc)
        return None
    order.provider_ref = str(inv.get('id') or '')
    order.payment_method = 'crypto'
    order.pay_status = 'waiting'
    db.session.commit()
    return inv.get('invoice_url')


def send_payment_alert_email(order, kind):
    """Tell the owner what just happened with a payment.

    `kind` is 'sale' (money in, plan granted), 'problem' (the processor reports
    a partial/failed/expired payment) or 'stuck' (paid but the plan was not
    granted). Best-effort: the order row is always the source of truth, so a
    mail failure can never affect the customer.
    """
    if not app.config.get('MAIL_PASSWORD'):
        app.logger.warning('MAIL_APP_PASSWORD not set — payment alert (%s) not sent.', kind)
        return False
    to_addr = os.environ.get('ADMIN_EMAIL', 'mauroramirezmij@gmail.com')
    u = db.session.get(User, order.user_id)
    head = {'sale': '💰 VENTA confirmada',
            'problem': '⚠️ PAGO con problema',
            'stuck': '🚨 PAGO recibido pero el plan NO se activó'}.get(kind, 'Pago')
    action = {
        'sale': 'No hay nada que hacer: el plan ya está activo.',
        'problem': ('Revisá el pedido en /admin. Si el monto que llegó alcanza, '
                    'podés activarlo a mano con "Marcar pagado".'),
        'stuck': ('ACCIÓN REQUERIDA: entrá a /admin y activá el pedido a mano. '
                  'El cliente ya pagó.'),
    }.get(kind, '')
    body = (
        f'{head} — Tradeable Academy\n'
        f'{"=" * 46}\n\n'
        f'Pedido:    #{order.id}\n'
        f'Plan:      {PLAN_LABELS.get(order.plan, order.plan)} / {order.billing_cycle}\n'
        f'Monto:     ${order.final_price:.2f} USD\n'
        f'Recibido:  {order.paid_amount if order.paid_amount is not None else "—"} '
        f'{(order.pay_currency or "").upper()}\n'
        f'Estado:    {order.status} / {order.pay_status or "—"}\n'
        f'Usuario:   {(u.username if u else "?")} / {(u.email if u else "?")}\n'
        f'Tx:        {order.tx_hash or "—"}\n\n'
        f'{action}\n'
    )
    msg = Message(f'{head} — pedido #{order.id}', recipients=[to_addr])
    msg.body = body
    prev_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        app.logger.warning('Failed to send payment alert: %s', exc)
        return False
    finally:
        socket.setdefaulttimeout(prev_timeout)


# Statuses that mean the buyer's money did NOT arrive cleanly.
CRYPTO_PROBLEM_STATES = ('partially_paid', 'failed', 'expired', 'refunded')


def _crypto_apply_status(order, info):
    """Fold a processor payload into the order and activate when it is paid.

    Called from BOTH the webhook and the reconciliation path, which is why it
    must be safe to run repeatedly — `_activate_plan_from_order` is the
    idempotency guard."""
    status = (info.get('payment_status') or info.get('invoice_status') or '').lower()
    if status:
        order.pay_status = status
    if info.get('actually_paid') is not None:
        try:
            order.paid_amount = float(info['actually_paid'])
        except (TypeError, ValueError):
            pass
    if info.get('pay_currency'):
        order.pay_currency = str(info['pay_currency'])[:20]
    if info.get('payin_hash') or info.get('outcome_hash'):
        order.tx_hash = str(info.get('payin_hash') or info.get('outcome_hash'))[:120]
    activated = False
    if status in CRYPTO_PAID_STATES and order.status != 'paid':
        order.status = 'paid'
        order.paid_at = datetime.now(timezone.utc)
    db.session.commit()
    if order.status == 'paid':
        activated = _activate_plan_from_order(order)
        # Only alert the first time the plan is granted: a repeated notification
        # must not spam the inbox (same idempotency guard as the activation).
        if activated:
            send_payment_alert_email(order, 'sale')
        elif order.applied_at is None:
            # Money in but the plan did not land — this is the one that needs a
            # human, so it must never depend on the buyer coming back.
            send_payment_alert_email(order, 'stuck')
    elif status in CRYPTO_PROBLEM_STATES and not order.alerted_at:
        order.alerted_at = datetime.now(timezone.utc)
        db.session.commit()
        send_payment_alert_email(order, 'problem')
    return activated


def payments_sweep(max_orders=25):
    """Re-check every recent unpaid order against its processor.

    The customer's own page already reconciles their order — but a buyer who
    pays and never comes back would go unnoticed. This runs when the owner opens
    the admin panel, so the panel itself is the trigger: no scheduler, no cron,
    and the answer is always fresh when you are looking at it.

    Returns (checked, recovered).
    """
    if not available_payment_rails():
        return 0, 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    pending = (Order.query
               .filter(Order.status == 'pending',
                       Order.provider_ref.isnot(None),
                       Order.created_at >= cutoff)
               .order_by(Order.created_at.desc())
               .limit(max_orders).all())
    recovered = 0
    for o in pending:
        try:
            if _reconcile_order(o):
                recovered += 1
        except Exception as exc:            # one bad order must not stop the sweep
            app.logger.warning('sweep failed on order %s: %s', o.id, exc)
    return len(pending), recovered


def order_trace(order):
    """Everything that proves what happened with one purchase.

    Answering "I paid in January and never got anything" should not require
    stitching four tables together by hand. This assembles the whole story:
    when they paid, the exact moment the plan was granted, how long it ran, how
    many times they logged in and how much of the product they actually used.
    """
    u = db.session.get(User, order.user_id)
    start = _aware(order.paid_at) or _aware(order.created_at)
    # The window we measure activity over: from payment to expiry (or to now if
    # the plan is still running / never expired).
    end = _aware(u.plan_expires_at) if u else None
    if not end or end > datetime.now(timezone.utc):
        end = datetime.now(timezone.utc)

    logins = usage = 0
    last_seen = None
    if u and start:
        logins = XPLog.query.filter(XPLog.user_id == u.id, XPLog.source == 'login',
                                    XPLog.created_at >= start,
                                    XPLog.created_at <= end).count()
        usage = UsageLog.query.filter(UsageLog.user_id == u.id,
                                      UsageLog.created_at >= start,
                                      UsageLog.created_at <= end).count()
        row = (XPLog.query.filter(XPLog.user_id == u.id)
               .order_by(XPLog.created_at.desc()).first())
        last_seen = _aware(row.created_at) if row else None

    events = []
    if u:
        events = (AuditEvent.query
                  .filter(AuditEvent.user_id == u.id)
                  .order_by(AuditEvent.created_at.desc()).limit(40).all())

    # The timeline, in the order a human reads it.
    steps = [('Pedido creado', _aware(order.created_at), True)]
    steps.append(('Pago confirmado', _aware(order.paid_at), order.status == 'paid'))
    steps.append(('Plan ENTREGADO', _aware(order.applied_at), order.applied_at is not None))
    if u and u.plan_expires_at:
        exp = _aware(u.plan_expires_at)
        steps.append(('Vence el plan', exp, True if exp else False))

    delivered = order.applied_at is not None
    return {
        'order': order, 'user': u, 'steps': steps, 'events': events,
        'logins': logins, 'usage': usage, 'last_seen': last_seen,
        'delivered': delivered,
        'other_orders': (Order.query.filter(Order.user_id == order.user_id,
                                            Order.id != order.id)
                         .order_by(Order.created_at.desc()).limit(10).all()) if u else [],
        'summary': _trace_summary(order, u, logins, usage, delivered),
    }


def _trace_summary(order, u, logins, usage, delivered):
    """Plain-text version, ready to paste into a reply to the customer."""
    def when(dt):
        dt = _aware(dt)
        return dt.strftime('%d/%m/%Y %H:%M UTC') if dt else '—'
    lines = [
        'PEDIDO #%d — %s (%s)' % (order.id, PLAN_LABELS.get(order.plan, order.plan),
                                  order.billing_cycle),
        'Cuenta: %s <%s>' % (u.username if u else '?', u.email if u else '?'),
        'Importe: $%.2f USD' % order.final_price,
        '',
        'Pedido creado:    %s' % when(order.created_at),
        'Pago confirmado:  %s' % when(order.paid_at),
        'PLAN ENTREGADO:   %s' % when(order.applied_at),
    ]
    if u and u.plan_expires_at:
        lines.append('Vigencia hasta:   %s' % when(u.plan_expires_at))
    if order.tx_hash:
        lines.append('Transaccion:      %s' % order.tx_hash)
    if order.provider_ref:
        lines.append('Factura:          %s' % order.provider_ref)
    lines += ['',
              'Inicios de sesion tras el pago: %d' % logins,
              'Analisis con IA utilizados:     %d' % usage,
              '',
              ('CONCLUSION: el plan fue entregado y la cuenta lo utilizo.'
               if delivered and (logins or usage) else
               ('CONCLUSION: el plan fue entregado.' if delivered else
                'CONCLUSION: el plan NO fue entregado — corresponde activar o reembolsar.'))]
    return '\n'.join(lines)


def find_orders(query):
    """Look up orders by number, username or email — however the complaint
    arrives, you can search with what you have."""
    q = (query or '').strip()
    if not q:
        return []
    if q.startswith('#'):
        q = q[1:]
    if q.isdigit():
        o = db.session.get(Order, int(q))
        if o:
            return [o]
    like = '%%%s%%' % q.lower()
    users = User.query.filter(db.or_(db.func.lower(User.username).like(like),
                                     db.func.lower(User.email).like(like))).limit(10).all()
    if users:
        return (Order.query.filter(Order.user_id.in_([u.id for u in users]))
                .order_by(Order.created_at.desc()).limit(25).all())
    return (Order.query.filter(db.or_(Order.tx_hash == q, Order.provider_ref == q))
            .order_by(Order.created_at.desc()).limit(25).all())


def orders_needing_attention():
    """Orders a human should look at, newest first.

    Three kinds: money arrived but the plan is not active, the processor
    reported a problem, and payments that have been sitting unconfirmed for
    more than the promised window.
    """
    stale = datetime.now(timezone.utc) - timedelta(hours=CRYPTO_SLA_HOURS)
    problem_states = tuple(CRYPTO_PROBLEM_STATES) + tuple(PAYPAL_PROBLEM_STATES)
    rows = (Order.query
            .filter(db.or_(
                db.and_(Order.status == 'paid', Order.applied_at.is_(None)),
                Order.pay_status.in_(problem_states),
                db.and_(Order.status == 'pending',
                        Order.provider_ref.isnot(None),
                        Order.created_at < stale)))
            .order_by(Order.created_at.desc()).limit(50).all())
    out = []
    for o in rows:
        if o.status == 'paid' and o.applied_at is None:
            why = 'paid_not_applied'
        elif (o.pay_status or '') in problem_states:
            why = o.pay_status
        else:
            why = 'awaiting_payment'
        u = db.session.get(User, o.user_id)
        out.append({'order': o, 'why': why,
                    'username': u.username if u else '—',
                    'email': u.email if u else '—'})
    return out


def _crypto_reconcile(order):
    """Ask the processor about an order we believe is still unpaid.

    This is the net that catches a lost notification: it runs whenever the buyer
    opens their order page, so in practice the payment settles itself without
    anyone noticing there was a problem."""
    if not (CRYPTO_ENABLED and order.provider_ref) or order.status == 'paid':
        return False
    try:
        # An invoice can have several payments; ask for the ones attached to it.
        data = _crypto_api('GET', '/payment/?invoiceId=%s&limit=10' % order.provider_ref)
    except Exception as exc:
        app.logger.warning('crypto reconcile failed (order %s): %s', order.id, exc)
        return False
    items = data.get('data') if isinstance(data, dict) else None
    for item in (items or []):
        if (item.get('payment_status') or '').lower() in CRYPTO_PAID_STATES:
            return _crypto_apply_status(order, item)
        _crypto_apply_status(order, item)      # keep the visible status fresh
    return False


# ═══ PayPal payments ══════════════════════════════════════════════════════
# Access tokens last hours; asking for a new one on every call would be a
# needless round trip on the critical path of a purchase.
_PP_TOKEN = {'value': '', 'expires': 0.0}


def _paypal_token():
    """OAuth token for the REST API, cached until shortly before it expires."""
    now = time.time()
    if _PP_TOKEN['value'] and _PP_TOKEN['expires'] > now:
        return _PP_TOKEN['value']
    creds = base64.b64encode(
        ('%s:%s' % (PAYPAL_CLIENT_ID, PAYPAL_SECRET)).encode()).decode()
    req = urllib.request.Request(
        PAYPAL_API_BASE + '/v1/oauth2/token',
        data=b'grant_type=client_credentials', method='POST')
    req.add_header('Authorization', 'Basic ' + creds)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    _PP_TOKEN['value'] = data.get('access_token', '')
    # Renew a minute early rather than discovering expiry mid-checkout.
    _PP_TOKEN['expires'] = now + max(60.0, float(data.get('expires_in', 300)) - 60.0)
    return _PP_TOKEN['value']


def _paypal_api(method, path, payload=None, request_id=None):
    """JSON client for PayPal. Every provider-specific detail lives here.

    Raises on transport failure; returns (status_code, parsed_body) otherwise,
    because PayPal answers some perfectly normal situations (an order that was
    already captured) with an error status we want to inspect, not swallow.
    """
    req = urllib.request.Request(
        PAYPAL_API_BASE + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method)
    req.add_header('Authorization', 'Bearer ' + _paypal_token())
    req.add_header('Content-Type', 'application/json')
    if request_id:
        # Idempotency: replaying the same request id cannot charge twice.
        req.add_header('PayPal-Request-Id', request_id)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode() or '{}'
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode() or '{}')
        except ValueError:
            return exc.code, {}


# PayPal capture statuses that mean the money is ours.
PAYPAL_PAID_STATES = ('completed',)
# ...and the ones a human needs to look at. A dispute or a reversal lands here
# too, so the owner finds out from the panel and not from a shrinking balance.
PAYPAL_PROBLEM_STATES = ('declined', 'failed', 'denied', 'voided',
                         'pending_review', 'reversed', 'refunded', 'disputed')


def _paypal_create_order(order, kind='plan'):
    """Create a PayPal order and return the URL where the buyer approves it."""
    price = order.final_price if kind == 'plan' else order.price
    label = ('Tradeable — %s' % PLAN_LABELS.get(order.plan, order.plan)) if kind == 'plan' \
            else ('Tradeable — %s' % getattr(order, 'label', 'Order'))
    ref = '%s-%d' % (kind, order.id)
    try:
        code, data = _paypal_api('POST', '/v2/checkout/orders', {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': ref,
                'custom_id': ref,
                'description': label[:127],
                'amount': {'currency_code': 'USD', 'value': '%.2f' % float(price)},
            }],
            'payment_source': {'paypal': {'experience_context': {
                'brand_name': PAYPAL_BRAND_NAME,
                'user_action': 'PAY_NOW',
                'shipping_preference': 'NO_SHIPPING',
                'return_url': url_for('paypal_return', order_id=order.id, _external=True),
                'cancel_url': url_for('checkout_status', order_id=order.id, _external=True),
            }}},
        }, request_id='create-%s' % ref)
    except Exception as exc:
        app.logger.error('paypal order create failed (order %s): %s', order.id, exc)
        return None
    if code >= 300 or not data.get('id'):
        app.logger.error('paypal order create rejected (order %s): %s %s',
                         order.id, code, data)
        return None
    order.provider_ref = str(data['id'])
    order.payment_method = 'paypal'
    order.pay_status = 'created'
    order.pay_currency = 'usd'
    db.session.commit()
    for link in data.get('links') or []:
        if link.get('rel') in ('payer-action', 'approve'):
            return link.get('href')
    return None


def _paypal_read_status(data):
    """Boil a PayPal order payload down to (status, amount, capture_id)."""
    units = data.get('purchase_units') or [{}]
    caps = ((units[0].get('payments') or {}).get('captures')) or []
    if caps:
        cap = caps[0]
        amount = (cap.get('amount') or {}).get('value')
        return (cap.get('status') or '').lower(), amount, cap.get('id')
    # No capture yet: the order-level status is all we know.
    amount = (units[0].get('amount') or {}).get('value')
    return (data.get('status') or '').lower(), amount, None


def _paypal_apply_status(order, status, amount=None, capture_id=None):
    """Fold a PayPal result into the order and activate when it is paid.

    Reached from the return URL, from the webhook and from reconciliation — so,
    like its crypto twin, it must be safe to run any number of times.
    `_activate_plan_from_order` is the guard that makes that true.
    """
    if status:
        order.pay_status = status
    if amount is not None:
        try:
            order.paid_amount = float(amount)
        except (TypeError, ValueError):
            pass
    if capture_id:
        order.tx_hash = str(capture_id)[:120]
    order.pay_currency = order.pay_currency or 'usd'
    if status in PAYPAL_PAID_STATES and order.status != 'paid':
        order.status = 'paid'
        order.paid_at = datetime.now(timezone.utc)
    db.session.commit()
    activated = False
    problem = status in PAYPAL_PROBLEM_STATES
    if order.status == 'paid' and not problem:
        activated = _activate_plan_from_order(order)
        if activated:
            send_payment_alert_email(order, 'sale')
        elif order.applied_at is None:
            send_payment_alert_email(order, 'stuck')
    # Checked independently of the branch above: a dispute or a reversal lands
    # on an order that is already paid and delivered, and that is exactly the
    # one the owner must hear about — it never revokes the plan on its own.
    if problem and not order.alerted_at:
        order.alerted_at = datetime.now(timezone.utc)
        db.session.commit()
        send_payment_alert_email(order, 'problem')
    return activated


def _paypal_capture(order):
    """Take the money for an order the buyer has approved.

    PayPal answers a second capture attempt with an error naming the situation
    ("already captured"), which is not a failure for us: it means the payment
    exists, so we read it instead of giving up."""
    if not (PAYPAL_ENABLED and order.provider_ref):
        return False
    try:
        code, data = _paypal_api(
            'POST', '/v2/checkout/orders/%s/capture' % order.provider_ref, {},
            request_id='capture-plan-%d' % order.id)
    except Exception as exc:
        app.logger.warning('paypal capture failed (order %s): %s', order.id, exc)
        return False
    if code >= 300:
        issues = [str(d.get('issue', '')).upper() for d in (data.get('details') or [])]
        if 'ORDER_ALREADY_CAPTURED' in issues:
            return _paypal_reconcile(order)
        app.logger.warning('paypal capture rejected (order %s): %s %s',
                           order.id, code, issues or data)
        # An order the buyer never approved simply stays pending.
        return False
    status, amount, cap_id = _paypal_read_status(data)
    return _paypal_apply_status(order, status, amount, cap_id)


def _paypal_reconcile(order):
    """Ask PayPal what happened to an order we believe is still unpaid.

    The net that catches an approval whose notification never arrived: it runs
    when the buyer opens their order page and when the owner opens the panel."""
    if not (PAYPAL_ENABLED and order.provider_ref) or order.status == 'paid':
        return False
    try:
        code, data = _paypal_api('GET', '/v2/checkout/orders/%s' % order.provider_ref)
    except Exception as exc:
        app.logger.warning('paypal reconcile failed (order %s): %s', order.id, exc)
        return False
    if code >= 300:
        return False
    status, amount, cap_id = _paypal_read_status(data)
    # Approved but never captured: the buyer clicked pay and we dropped the
    # ball. Capturing here is precisely how that purchase is rescued.
    if (data.get('status') or '').upper() == 'APPROVED' and not cap_id:
        return _paypal_capture(order)
    return _paypal_apply_status(order, status, amount, cap_id)


# ═══ Payment rails — the shared front door ════════════════════════════════
def available_payment_rails():
    """Which ways of paying are switched on right now, in the order shown."""
    rails = []
    if PAYPAL_ENABLED:
        rails.append('paypal')
    if CRYPTO_ENABLED:
        rails.append('crypto')
    if STRIPE_ENABLED:
        rails.append('stripe')
    return rails


def _reconcile_order(order):
    """Re-check one order with whichever processor it belongs to."""
    if order.payment_method == 'paypal':
        return _paypal_reconcile(order)
    return _crypto_reconcile(order)


def grant_plan_camo(user, plan, switch_on=False):
    """Give the user the camo that comes with their plan.

    Recorded in `owned_camos` rather than derived from the plan, because the
    Terms promise it survives the subscription. `switch_on` turns it on for
    them — worth doing the first time they buy, since a skin nobody discovers
    is a feature that was never delivered — but only when they are still on the
    default theme, so it can never overwrite a camo they chose themselves. A
    camo whose theme has not shipped yet is granted but not switched on.
    """
    slug = PLAN_CAMOS.get(plan)
    if not slug:
        return None
    user.add_camo(slug)
    if switch_on and slug in CAMO_READY and not (user.active_camo or ''):
        user.active_camo = slug
    return slug


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
    renewal = user.plan == order.plan and cur_exp and cur_exp > now
    if renewal:
        base = cur_exp  # renewal → stack onto remaining time
    # The camo is part of the purchase. Switch it on only when this is a new
    # plan for them, so renewing never yanks someone off the skin they picked.
    grant_plan_camo(user, order.plan, switch_on=not renewal)
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

    Discounts NEVER stack: the buyer gets whichever single one is better, the
    standing launch offer or their code. Stacking them is how a plan ends up
    sold below cost, and it is also what a buyer would call a bait price.

    A code that loses to the launch offer is still recorded on the order —
    the partner earns their commission either way, since the attribution is
    what they were promised, not the size of the discount.
    """
    base = _plan_base_price(plan, cycle) or 0.0
    launch = launch_discount_for(cycle)
    promo_pct = promo.discount_pct if promo else 0
    discount = max(launch, promo_pct)
    final = round(base * (1 - discount / 100.0), 2)
    return {'base_price': base, 'discount_pct': discount, 'final_price': final,
            'launch_pct': launch, 'promo_pct': promo_pct}


@app.context_processor
def _inject_launch_offer():
    """Let every plan card price itself off the same numbers the server charges."""
    pct = launch_discount_for('monthly')
    return {
        'LAUNCH_PCT': pct,
        'LAUNCH_PRICE': {p: round(v['monthly'] * (1 - pct / 100.0), 2)
                         for p, v in PLAN_PRICING.items()},
        'PLAN_PRICING': PLAN_PRICING,
    }


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
    # What twelve monthly payments would have cost, minus the annual price:
    # the pricing page promises this saving, so the cart has to show it too.
    saving = 0.0
    if cycle == 'annual':
        prices = PLAN_PRICING.get(plan, {})
        saving = max(0.0, prices.get('monthly', 0) * 12 - prices.get('annual', 0))
    return render_template('checkout.html', plan=plan, cycle=cycle,
                           plan_label=PLAN_LABELS[plan], quote=q,
                           annual_saving=saving)


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
        # With rails on, an abandoned attempt must not lock the buyer out of
        # paying: send them back to their open order so they can finish it —
        # or switch method, which is exactly what happens when one rail fails.
        if available_payment_rails():
            return redirect(url_for('checkout_pay', order_id=existing.id))
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

    # Hand the buyer to a payment rail. With one rail on, they go straight
    # there — the same single-click flow as before. With several, they choose,
    # which is the whole point of adding PayPal next to USDT rather than
    # replacing it. With none (or a $0 promo order), the manual instructions.
    rails = available_payment_rails()
    if order.final_price > 0 and rails:
        if len(rails) > 1:
            return redirect(url_for('checkout_pay', order_id=order.id))
        dest = _start_payment(order, rails[0])
        if dest:
            return redirect(dest, code=303)
        # falls through to the manual instructions rather than dead-ending

    return render_template('checkout_done.html', order=order,
                           plan_label=PLAN_LABELS.get(plan, plan), duplicate=False)


def _start_payment(order, method):
    """Send an order down one rail; returns where to send the buyer, or None.

    None is never a dead end: every caller falls back to the manual payment
    instructions, and the order survives either way so it can still be settled.
    """
    if method == 'stripe' and STRIPE_ENABLED:
        return _stripe_checkout_url(order)
    if method == 'paypal' and PAYPAL_ENABLED:
        return _paypal_create_order(order, 'plan')
    if method == 'crypto' and CRYPTO_ENABLED:
        return _crypto_create_invoice(order, 'plan')
    return None


@app.route('/checkout/pay/<int:order_id>', methods=['GET', 'POST'])
@login_required
def checkout_pay(order_id):
    """Pick how to pay. Only ever seen when more than one rail is enabled."""
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        abort(404)
    if order.status == 'paid':
        return redirect(url_for('checkout_status', order_id=order.id))
    rails = available_payment_rails()
    if request.method == 'POST':
        method = request.form.get('method', '')
        if method in rails:
            dest = _start_payment(order, method)
            if dest:
                return redirect(dest, code=303)
        # Could not reach the processor: show the manual instructions rather
        # than leaving the buyer staring at a button that does nothing.
        return render_template('checkout_done.html', order=order,
                               plan_label=PLAN_LABELS.get(order.plan, order.plan),
                               duplicate=False)
    return render_template('checkout_method.html', order=order, rails=rails,
                           plan_label=PLAN_LABELS.get(order.plan, order.plan),
                           sla_hours=CRYPTO_SLA_HOURS)


@app.route('/checkout/paypal/return/<int:order_id>')
@login_required
def paypal_return(order_id):
    """Where PayPal sends the buyer after they approve the payment.

    The capture happens here, but the plan is granted by the shared activator —
    so a buyer who closes this tab too early loses nothing: the webhook and the
    reconciliation on their order page both finish the job."""
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        abort(404)
    if order.status != 'paid':
        try:
            _paypal_capture(order)
        except Exception as exc:                # never dead-end on the way back
            app.logger.error('paypal return failed (order %s): %s', order.id, exc)
    return redirect(url_for('checkout_status', order_id=order.id))


@app.route('/webhook/paypal', methods=['POST'])
def paypal_webhook():
    """Payment notification from PayPal.

    Verified by asking PayPal itself whether the signature on the message is
    theirs — an unverified notification is refused, otherwise anyone could POST
    "order 7 is paid"."""
    if not (PAYPAL_ENABLED and PAYPAL_WEBHOOK_ID):
        app.logger.warning('paypal webhook received but PAYPAL_WEBHOOK_ID is not set — ignoring')
        return jsonify({'error': 'not_configured'}), 400
    try:
        event = json.loads(request.get_data().decode() or '{}')
    except ValueError:
        return jsonify({'error': 'bad_json'}), 400
    try:
        code, verdict = _paypal_api('POST', '/v1/notifications/verify-webhook-signature', {
            'transmission_id': request.headers.get('paypal-transmission-id', ''),
            'transmission_time': request.headers.get('paypal-transmission-time', ''),
            'cert_url': request.headers.get('paypal-cert-url', ''),
            'auth_algo': request.headers.get('paypal-auth-algo', ''),
            'transmission_sig': request.headers.get('paypal-transmission-sig', ''),
            'webhook_id': PAYPAL_WEBHOOK_ID,
            'webhook_event': event,
        })
    except Exception as exc:
        app.logger.warning('paypal webhook verification error: %s', exc)
        return jsonify({'error': 'verify_failed'}), 400
    if code >= 300 or (verdict.get('verification_status') or '') != 'SUCCESS':
        app.logger.warning('paypal webhook: bad signature')
        return jsonify({'error': 'bad_signature'}), 400

    res = event.get('resource') or {}
    ref = str(res.get('custom_id') or '')
    if not ref:
        units = res.get('purchase_units') or []
        ref = str((units[0].get('custom_id') if units else '') or '')
    kind, _, oid = ref.partition('-')
    try:
        oid = int(oid)
    except (TypeError, ValueError):
        return jsonify({'ok': True, 'ignored': 'no_order_ref'})
    if kind != 'plan':
        return jsonify({'ok': True, 'ignored': kind})
    order = db.session.get(Order, oid)
    if not order:
        return jsonify({'error': 'not_found'}), 404

    etype = (event.get('event_type') or '').upper()
    if etype == 'CHECKOUT.ORDER.APPROVED':
        # Approved but not captured — taking the money is on us.
        _paypal_capture(order)
        return jsonify({'ok': True})
    amount = (res.get('amount') or {}).get('value')
    if etype in ('PAYMENT.CAPTURE.REVERSED', 'PAYMENT.CAPTURE.REFUNDED'):
        status = 'reversed' if 'REVERSED' in etype else 'refunded'
    elif etype.startswith('CUSTOMER.DISPUTE'):
        status = 'disputed'
        amount = None
    elif etype in ('PAYMENT.CAPTURE.COMPLETED', 'PAYMENT.CAPTURE.DENIED',
                   'PAYMENT.CAPTURE.PENDING'):
        status = (res.get('status') or '').lower()
    else:
        return jsonify({'ok': True, 'ignored': etype})
    _paypal_apply_status(order, status, amount, res.get('id'))
    return jsonify({'ok': True})


def _stripe_checkout_url(order):
    """Create a Stripe Checkout session and return its URL, or None."""
    if STRIPE_ENABLED:
        try:
            checkout_session = _stripe.checkout.Session.create(
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Tradeable — {PLAN_LABELS.get(order.plan, order.plan)}',
                            'description': ('Annual' if order.billing_cycle == 'annual'
                                            else 'Monthly') + ' plan',
                        },
                        'unit_amount': int(round(order.final_price * 100)),  # cents
                    },
                    'quantity': 1,
                }],
                success_url=url_for('checkout_success', _external=True)
                            + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('pricing', _external=True),
                client_reference_id=str(order.id),
                customer_email=current_user.email,
                metadata={'order_id': str(order.id)},
            )
            order.payment_method = 'stripe'
            db.session.commit()
            return checkout_session.url
        except Exception as e:
            app.logger.error('Stripe session create failed: %s', e)
            return None


@app.route('/webhook/crypto', methods=['POST'])
def crypto_webhook():
    """Payment notification from the processor.

    Signed with a shared secret: the body is HMAC-SHA512'd over its JSON with
    keys sorted, exactly as the sender does it. An unsigned or badly signed
    notification is rejected — otherwise anyone could POST "order 7 is paid"."""
    raw = request.get_data()
    if CRYPTO_IPN_SECRET:
        sig = request.headers.get('x-nowpayments-sig', '')
        try:
            payload = json.loads(raw.decode() or '{}')
        except ValueError:
            return jsonify({'error': 'bad_json'}), 400
        expected = hmac.new(CRYPTO_IPN_SECRET.encode(),
                            json.dumps(payload, sort_keys=True, separators=(',', ':')).encode(),
                            hashlib.sha512).hexdigest()
        if not hmac.compare_digest(expected, sig):
            app.logger.warning('crypto webhook: bad signature')
            return jsonify({'error': 'bad_signature'}), 400
    else:
        app.logger.warning('crypto webhook received but CRYPTO_IPN_SECRET is not set — ignoring')
        return jsonify({'error': 'not_configured'}), 400

    ref = str(payload.get('order_id') or '')
    kind, _, oid = ref.partition('-')
    try:
        oid = int(oid)
    except (TypeError, ValueError):
        return jsonify({'error': 'bad_order'}), 400

    if kind == 'mentorship':
        order = db.session.get(MentorshipOrder, oid)
        if order and (payload.get('payment_status') or '').lower() in CRYPTO_PAID_STATES:
            if order.status != 'paid':
                order.status = 'paid'
                order.paid_at = datetime.now(timezone.utc)
                db.session.commit()
            _activate_mentorship_order(order)
        return jsonify({'ok': True})

    order = db.session.get(Order, oid)
    if not order:
        return jsonify({'error': 'not_found'}), 404
    _crypto_apply_status(order, payload)
    return jsonify({'ok': True})


@app.route('/checkout/status/<int:order_id>')
@login_required
def checkout_status(order_id):
    """The buyer's permanent home for an order.

    Opening it reconciles against the processor, so a notification that never
    arrived is picked up here without the buyer having to ask for anything."""
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        abort(404)
    if order.status != 'paid':
        _reconcile_order(order)
    return render_template('checkout_status.html', order=order,
                           plan_label=PLAN_LABELS.get(order.plan, order.plan),
                           sla_hours=CRYPTO_SLA_HOURS)


@app.route('/api/checkout/status/<int:order_id>')
@login_required
def checkout_status_api(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({'error': 'not_found'}), 404
    if order.status != 'paid':
        _reconcile_order(order)
    return jsonify({'id': order.id, 'status': order.status,
                    'pay_status': order.pay_status or '',
                    'applied': order.applied_at is not None,
                    'amount': order.final_price, 'plan': order.plan})


@app.route('/api/checkout/txid/<int:order_id>', methods=['POST'])
@login_required
def checkout_txid(order_id):
    """The buyer can hand us the transaction id. It settles nothing by itself —
    it just lets a human find the payment in seconds instead of hunting."""
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({'error': 'not_found'}), 404
    txid = ((request.json or {}).get('tx') or '').strip()[:120] if request.is_json else ''
    if len(txid) < 6:
        return jsonify({'error': 'too_short'}), 400
    order.tx_hash = txid
    db.session.commit()
    record_audit_event('order_txid', user_id=current_user.id,
                       detail='order %d tx %s' % (order.id, txid[:24]))
    return jsonify({'ok': True})


@app.route('/checkout/success')
@login_required
def checkout_success():
    """Where Stripe sends the buyer after a successful card payment.

    Stripe's webhook is the canonical activator, but for local testing (where a
    public webhook isn't reachable without the Stripe CLI) this page ALSO
    verifies the session with Stripe and activates the plan. Both paths call the
    idempotent `_activate_plan_from_order`, so a plan is never granted twice."""
    session_id = request.args.get('session_id', '')
    if not (STRIPE_ENABLED and session_id):
        return redirect(url_for('pricing'))
    try:
        sess = _stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        app.logger.error('Stripe session retrieve failed: %s', e)
        return redirect(url_for('pricing'))
    order = db.session.get(Order, int(sess.get('client_reference_id') or 0))
    # Only the buyer may activate their own order, and only if Stripe says paid.
    if (order and order.user_id == current_user.id
            and sess.get('payment_status') == 'paid'):
        if order.status == 'pending':
            order.status = 'paid'
            order.paid_at = datetime.now(timezone.utc)
            db.session.commit()
            activated = _activate_plan_from_order(order)
            record_audit_event('order_paid', user_id=order.user_id,
                                detail=f'stripe order #{order.id} {order.plan}/{order.billing_cycle}',
                                success=activated)
        return render_template('checkout_success.html', order=order,
                               plan_label=PLAN_LABELS.get(order.plan, order.plan))
    return redirect(url_for('pricing'))


@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Canonical payment confirmation from Stripe (server-to-server).

    Configure it in the Stripe dashboard → Webhooks with your public HTTPS URL
    (needs the domain + nginx + SSL) and the event `checkout.session.completed`.
    Verifies the signature when STRIPE_WEBHOOK_SECRET is set."""
    if not STRIPE_ENABLED:
        abort(404)
    payload = request.data
    sig = request.headers.get('Stripe-Signature', '')
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = _stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload or b'{}')   # unsigned: local dev only
    except Exception as e:
        app.logger.error('Stripe webhook verify failed: %s', e)
        abort(400)
    if event.get('type') == 'checkout.session.completed':
        sess = event['data']['object']
        meta = sess.get('metadata') or {}
        paid = sess.get('payment_status') == 'paid'
        ref = int(sess.get('client_reference_id') or 0)
        if meta.get('kind') == 'mentorship':
            # Mentorship path — a separate table; never touches user.plan.
            m_order = db.session.get(MentorshipOrder, ref)
            if m_order and m_order.status == 'pending' and paid:
                m_order.status = 'paid'
                m_order.paid_at = datetime.now(timezone.utc)
                db.session.commit()
                activated = _activate_mentorship_order(m_order)   # idempotent
                record_audit_event('mentorship_order_paid', user_id=m_order.user_id,
                                    detail=f'stripe webhook mentorship #{m_order.id} {m_order.sku}',
                                    success=activated)
        else:
            # Plan path (unchanged).
            order = db.session.get(Order, ref)
            if order and order.status == 'pending' and paid:
                order.status = 'paid'
                order.paid_at = datetime.now(timezone.utc)
                db.session.commit()
                activated = _activate_plan_from_order(order)   # idempotent
                record_audit_event('order_paid', user_id=order.user_id,
                                    detail=f'stripe webhook order #{order.id}',
                                    success=activated)
    return '', 200


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


def _recompute_user_rank(user):
    """Rebuild a user's XP + rank from the append-only XPLog ledger — the recovery
    path when the cached user.xp/user.rank get corrupted (e.g. a bug zeroes them).
    The ledger is the source of truth, so summing it restores the exact lifetime
    XP, and rank is a pure function of that. Seals rank_celebrated to the restored
    rank so the recovery doesn't replay rank-up reveals. Returns (old, new)."""
    old = (user.xp or 0, user.rank or 1)
    total = int(db.session.query(db.func.coalesce(db.func.sum(XPLog.amount), 0))
                .filter(XPLog.user_id == user.id).scalar() or 0)
    user.xp = total
    user.rank = rank_for_xp(total)
    user.rank_celebrated = user.rank
    db.session.commit()
    return old, (user.xp, user.rank)


@app.route('/admin/user/recompute-rank', methods=['POST'])
@login_required
def admin_recompute_rank():
    """Restore a user's rank/XP from the XPLog ledger (one-click recovery)."""
    if not current_user.is_admin:
        abort(403)
    user = db.session.get(User, int(request.form.get('user_id', 0)))
    if not user:
        abort(404)
    old, new = _recompute_user_rank(user)
    record_audit_event('rank_recompute', user_id=user.id,
                       detail=f'xp {old[0]}->{new[0]}, rank {old[1]}->{new[1]}',
                       success=True)
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


@app.route('/api/synapse/l10n/<lang>')
def synapse_l10n(lang):
    """Language pack for the WEB Synapse map: topic titles, method names and the
    full translated topic content. This is the exact same audited corpus the PDF
    uses (synapse_translations.py + synapse_content_{lang}.json) — the web
    flipbook used to read only the English synapse_library.js, which is why the
    dossiers stayed in English for es/fr/pt users. Any missing key falls back to
    English client-side."""
    if lang not in ('es', 'fr', 'pt'):
        return jsonify({'titles': {}, 'methods': {}, 'content': {}})
    try:
        import synapse_translations as T          # run as script (python3 scalpel/app.py)
    except ModuleNotFoundError:
        from scalpel import synapse_translations as T   # imported as package
    resp = jsonify({
        'titles': T.TITLES.get(lang, {}),
        'methods': T.METHODS.get(lang, {}),
        'content': _load_synapse_content(lang),
    })
    # Static corpus — let browsers cache it for an hour.
    resp.cache_control.public = True
    resp.cache_control.max_age = 3600
    return resp


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
  <div class="cv-brand">Tradeable</div>
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
    plan = current_plan()
    cfg = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
    since = datetime.now(timezone.utc) - cfg['window']
    if current_user.is_authenticated:
        used = UsageLog.query.filter(UsageLog.user_id == current_user.id,
                                     UsageLog.created_at >= since).count()
    else:
        anon = get_anon_id()
        used = (UsageLog.query.filter(UsageLog.anon_id == anon,
                                      UsageLog.created_at >= since).count()
                if anon else 0)
    info = check_rate_limit()
    # Always report the live count so the client can keep its quota display in
    # sync after each analysis (used to only return counts when blocked).
    resp = {
        'allowed': info is None,
        'plan': plan,
        'used': used,
        'max': cfg['max'],
        'remaining': max(0, cfg['max'] - used),
    }
    if info:
        resp.update(info)
    return jsonify(resp)


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
        try:
            image_bytes, content_type = normalize_chart_image(image_bytes, content_type)
        except ImageTooLarge:
            return jsonify({'error': 'This image is too large to process. Please upload a standard chart screenshot.'}), 400
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
                            "image_url": {"url": f"data:{content_type};base64,{image_data}", "detail": "low"}
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
        # Cap the free-text construction (server-side safety net — the uploader
        # also enforces this live). HARD CHAR CEILING FIRST: a word count alone
        # can be gamed with one giant space-less blob ("11111…") that reads as a
        # single "word" but explodes the token bill, so clamp raw length before
        # anything else. Then cap at 200 words. Keeps prompt cost bounded no
        # matter what is pasted.
        if len(notes) > NOTES_MAX_CHARS:
            notes = notes[:NOTES_MAX_CHARS]
        _nw = notes.split()
        if len(_nw) > 200:
            notes = ' '.join(_nw[:200])
        language = request.form.get('language', 'English').strip() or 'English'

        screenshot = request.files.get('screenshot')
        if not screenshot or screenshot.filename == '':
            return jsonify({'error': 'A chart screenshot is required to analyze the setup.'}), 400

        allowed_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
        content_type = screenshot.content_type or 'image/jpeg'
        if content_type not in allowed_types:
            return jsonify({'error': 'Please upload a JPG, PNG, or WebP image.'}), 400

        image_bytes = screenshot.read()
        try:
            image_bytes, content_type = normalize_chart_image(image_bytes, content_type)
        except ImageTooLarge:
            return jsonify({'error': 'This image is too large to process. Please upload a standard chart screenshot.'}), 400
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

        user_message = f"""Trade submitted for retrospective, educational analysis (approach: {approach}):

Instrument: {instrument}
DIRECTION (ground truth — the trader took a {direction} position): {direction}
Session: {session}
Result: {result}
HTF Bias held: {htf_bias}
Traded aligned with HTF bias: {aligned}
Approach / model used: {approach}
Confluences identified by trader: {confluences_str}
{trade_construction_block}
This was a {direction} trade — anchor your entire analysis to that fact. Locate where the trader entered and exited on the chart using the {direction} direction as your reference. Analyze it through the trader's stated approach ({approach}) via the METHODOLOGY ROUTER — if the approach is OTE / Std Dev, lead with the dedicated OTE / Standard Deviation lens (its distinct fib-driven trigger), not a generic ICT read. Identify possible setup considerations — or confirm if the setup was technically sound and this may have been within normal statistical variance.

LANGUAGE: Write your entire response in {language}. Keep ICT-specific terms and acronyms (FVG, IFVG, OTE, CHoCH, MSS, BOS, OB, SMT, BSL, SSL, EQH, EQL, Kill Zone, Silver Bullet, etc.) in their standard English form, but write all explanatory prose in {language}."""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": build_system_prompt(approach)},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{image_data}",
                                "detail": ANALYZE_IMG_DETAIL
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
    subject = f'[Tradeable] Forum auto-mute — {uname}'
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
        'community': ({'id': p.community.id, 'name': p.community.name,
                       'emoji': p.community.emoji or '👥'}
                      if getattr(p, 'community_id', None) and p.community else None),
        'following_author': (p.user_id != current_user.id and
                             ForumFollow.query.filter_by(follower_id=current_user.id,
                                                         followed_id=p.user_id).first() is not None),
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


# ═══ Forum BOOST — communities, follows, DMs (Standard+) ═══════════════════
MAX_COMMUNITIES_PER_USER = 3
DM_PAGE = 40


def _community_dict(c):
    return {'id': c.id, 'name': c.name, 'emoji': c.emoji or '👥',
            'description': c.description or '',
            'members': ForumCommunityMember.query.filter_by(community_id=c.id).count(),
            'posts': ForumPost.query.filter_by(community_id=c.id, is_deleted=False).count(),
            'creator': c.creator.username if c.creator else '—',
            'is_mine': c.creator_id == current_user.id,
            'joined': ForumCommunityMember.query.filter_by(
                community_id=c.id, user_id=current_user.id).first() is not None}


@app.route('/forum/communities', methods=['GET', 'POST'])
@standard_required
def forum_communities():
    if request.method == 'POST':
        muted = forum_mute_remaining(current_user)
        if muted:
            return jsonify({'error': 'muted', 'retry_after': muted}), 403
        d = request.json if request.is_json else {}
        name = (d.get('name') or '').strip()[:60]
        desc = (d.get('description') or '').strip()[:240]
        emoji = (d.get('emoji') or '').strip()[:8]
        if len(name) < 3:
            return jsonify({'error': 'too_short'}), 400
        if ForumCommunity.query.filter_by(creator_id=current_user.id).count() >= MAX_COMMUNITIES_PER_USER:
            return jsonify({'error': 'limit', 'max': MAX_COMMUNITIES_PER_USER}), 429
        if ForumCommunity.query.filter(db.func.lower(ForumCommunity.name) == name.lower()).first():
            return jsonify({'error': 'name_taken'}), 409
        trip = local_text_pretrip(f"{name}\n{desc}")
        if trip:
            record_warning(current_user.id, trip, 'Community text blocked by pre-filter', name)
            return jsonify({'error': 'blocked', 'category': trip}), 422
        c = ForumCommunity(name=name, description=desc or None, emoji=emoji or None,
                           creator_id=current_user.id)
        db.session.add(c)
        db.session.flush()
        db.session.add(ForumCommunityMember(community_id=c.id, user_id=current_user.id))
        db.session.commit()
        return jsonify({'ok': True, 'community': _community_dict(c)})
    rows = ForumCommunity.query.order_by(ForumCommunity.created_at.desc()).limit(100).all()
    return jsonify({'communities': [_community_dict(c) for c in rows]})


@app.route('/forum/community/<int:cid>/membership', methods=['POST'])
@standard_required
def forum_community_membership(cid):
    c = db.session.get(ForumCommunity, cid)
    if not c:
        return jsonify({'error': 'not_found'}), 404
    join = bool(request.json.get('join')) if request.is_json else False
    row = ForumCommunityMember.query.filter_by(community_id=cid, user_id=current_user.id).first()
    if join and not row:
        db.session.add(ForumCommunityMember(community_id=cid, user_id=current_user.id))
    elif not join and row:
        if c.creator_id == current_user.id:
            return jsonify({'error': 'creator_cannot_leave'}), 400
        db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True, 'community': _community_dict(c)})


@app.route('/forum/follow', methods=['POST'])
@standard_required
def forum_follow():
    d = request.json if request.is_json else {}
    uname = (d.get('username') or '').strip()
    target = User.query.filter(db.func.lower(User.username) == uname.lower()).first()
    if not target or target.id == current_user.id:
        return jsonify({'error': 'not_found'}), 404
    row = ForumFollow.query.filter_by(follower_id=current_user.id, followed_id=target.id).first()
    on = bool(d.get('on'))
    if on and not row:
        db.session.add(ForumFollow(follower_id=current_user.id, followed_id=target.id))
    elif not on and row:
        db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True, 'following': on,
                    'followers': ForumFollow.query.filter_by(followed_id=target.id).count()})


def _dm_dict(m):
    return {'id': m.id, 'body': m.body, 'is_mine': m.sender_id == current_user.id,
            'created_at': _as_utc(m.created_at).isoformat()}


@app.route('/forum/dm/threads')
@standard_required
def forum_dm_threads():
    """One row per counterpart, newest conversation first, with unread counts."""
    msgs = (ForumDM.query.filter(db.or_(ForumDM.sender_id == current_user.id,
                                        ForumDM.recipient_id == current_user.id))
            .order_by(ForumDM.created_at.desc()).limit(400).all())
    seen = {}
    for m in msgs:
        other = m.recipient if m.sender_id == current_user.id else m.sender
        if not other or other.id in seen:
            continue
        unread = ForumDM.query.filter_by(sender_id=other.id, recipient_id=current_user.id,
                                         read_at=None).count()
        seen[other.id] = {'username': other.username, 'rank': other.rank or 1,
                          'last': (m.body or '')[:70], 'unread': unread,
                          'at': _as_utc(m.created_at).isoformat()}
    return jsonify({'threads': list(seen.values()),
                    'unread_total': ForumDM.query.filter_by(recipient_id=current_user.id,
                                                            read_at=None).count()})


@app.route('/forum/dm/with/<username>', methods=['GET', 'POST'])
@standard_required
def forum_dm_with(username):
    other = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if not other or other.id == current_user.id:
        return jsonify({'error': 'not_found'}), 404
    if request.method == 'POST':
        muted = forum_mute_remaining(current_user)
        if muted:
            return jsonify({'error': 'muted', 'retry_after': muted}), 403
        body = (request.json.get('body') or '').strip()[:2000] if request.is_json else ''
        if len(body) < 1:
            return jsonify({'error': 'too_short'}), 400
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
        if ForumDM.query.filter(ForumDM.sender_id == current_user.id,
                                ForumDM.created_at >= cutoff).count() >= 30:
            return jsonify({'error': 'rate_limited'}), 429
        trip = local_text_pretrip(body)
        if trip:
            record_warning(current_user.id, trip, 'DM blocked by pre-filter', body[:80])
            return jsonify({'error': 'blocked', 'category': trip}), 422
        m = ForumDM(sender_id=current_user.id, recipient_id=other.id, body=body)
        db.session.add(m)
        db.session.commit()
        return jsonify({'ok': True, 'message': _dm_dict(m)})
    try:
        after = int(request.args.get('after', 0))
    except (TypeError, ValueError):
        after = 0
    pair = db.or_(db.and_(ForumDM.sender_id == current_user.id, ForumDM.recipient_id == other.id),
                  db.and_(ForumDM.sender_id == other.id, ForumDM.recipient_id == current_user.id))
    q = ForumDM.query.filter(pair)
    if after:
        rows = q.filter(ForumDM.id > after).order_by(ForumDM.id.asc()).limit(DM_PAGE).all()
    else:
        rows = q.order_by(ForumDM.id.desc()).limit(DM_PAGE).all()[::-1]
    # opening the thread marks their messages read
    ForumDM.query.filter_by(sender_id=other.id, recipient_id=current_user.id,
                            read_at=None).update({'read_at': datetime.now(timezone.utc)})
    db.session.commit()
    return jsonify({'messages': [_dm_dict(m) for m in rows],
                    'with': {'username': other.username, 'rank': other.rank or 1}})


@app.route('/forum/feed')
@standard_required
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
    # Communities boost: ?community=<id> narrows to one community's posts;
    # ?feed=following narrows to authors the viewer follows.
    comm = request.args.get('community')
    if comm:
        try:
            q = q.filter(ForumPost.community_id == int(comm))
        except (TypeError, ValueError):
            pass
    if request.args.get('feed') == 'following':
        fids = [f.followed_id for f in ForumFollow.query.filter_by(follower_id=current_user.id).all()]
        q = q.filter(ForumPost.user_id.in_(fids or [-1]))
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
@standard_required
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
@standard_required
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

    community_id = None
    craw = (request.form.get('community_id') or '').strip()
    if craw:
        try:
            cid = int(craw)
        except (TypeError, ValueError):
            cid = None
        if cid:
            if not ForumCommunityMember.query.filter_by(community_id=cid,
                                                        user_id=current_user.id).first():
                return jsonify({'error': 'not_a_member'}), 403
            community_id = cid

    post = ForumPost(user_id=current_user.id, title=title, body=body, image_path=image_path,
                     community_id=community_id)
    db.session.add(post)
    db.session.commit()
    add_xp(current_user, 'forum_post', ref=f'post:{post.id}')
    return jsonify({
        'ok': True,
        'post': serialize_post(post),
        'posts_left_today': max(0, DAILY_POST_LIMIT - todays_post_count(current_user.id)),
    })


@app.route('/forum/post/<int:pid>/comment', methods=['POST'])
@standard_required
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
@standard_required
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
@standard_required
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
@standard_required
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
@standard_required
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
_DAILY_ANS = []       # correct option indices for the Daily pool (DAILY_BANK), in bank order
_DAILY_CONTENT = []   # daily question texts (q/opts/exp, NO answers) served via the API


def _load_quiz_key():
    """Load (and best-effort regenerate) the server-side answer key. Regenerating
    at startup keeps it in sync whenever node is available; otherwise the
    committed JSON is used."""
    global _QUIZ_KEY, _DAILY_ANS, _DAILY_CONTENT
    base = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(base)
    keypath = os.path.join(base, 'quiz_answer_key.json')
    contentpath = os.path.join(base, 'daily_bank_content.json')
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
        _DAILY_ANS = data.get('daily', [])
        app.logger.info('Loaded quiz answer key: %d questions, %d daily.',
                        len(_QUIZ_KEY), len(_DAILY_ANS))
    except Exception as e:
        app.logger.error('Could not load quiz answer key: %s', e)
        _QUIZ_KEY, _DAILY_ANS = [], []
    # Daily question CONTENT (texts only — answers stay in the key above). The
    # browser never receives the bank: /api/daily/start serves q+opts from here.
    try:
        with open(contentpath, 'r', encoding='utf-8') as f:
            _DAILY_CONTENT = json.load(f).get('questions', [])
        app.logger.info('Loaded daily bank content: %d questions.', len(_DAILY_CONTENT))
    except Exception as e:
        app.logger.error('Could not load daily bank content: %s', e)
        _DAILY_CONTENT = []


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


def _user_daily_order(user_id, cycle, n):
    """Per-USER, per-cycle permutation of the Daily pool. Seeded with an HMAC of
    the server SECRET_KEY, so two subscribers get different question calendars
    and no client can derive anyone's order (the salt never leaves the server).
    Every cycle is shuffled (including the first) and each cycle re-shuffles, so
    within a cycle no question repeats and across cycles the order changes."""
    key = str(app.config['SECRET_KEY']).encode()
    digest = hmac.new(key, f'daily:{user_id}:{cycle}'.encode(), hashlib.sha256).digest()
    rng = _mulberry32(_u32(int.from_bytes(digest[:4], 'big')))
    order = list(range(n))
    for i in range(len(order) - 1, 0, -1):
        j = int(rng() * (i + 1))
        order[i], order[j] = order[j], order[i]
    return order


def _daily_pool_idx():
    """Which DAILY_BANK question today is for the CURRENT user. Deterministic
    per (user, day): same question on refresh, different across users."""
    n = len(_DAILY_ANS)
    if n == 0:
        return None
    seed = _daily_seed()
    cycle = seed // n
    pos = ((seed % n) + n) % n
    return _user_daily_order(current_user.id, cycle, n)[pos]


def _daily_correct_index():
    """The correct option index (original order) of today's question for the
    current user — computed entirely server-side; never sent before answering."""
    idx = _daily_pool_idx()
    return _DAILY_ANS[idx] if idx is not None else None


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
    # The client gets ONLY the texts of this user's question for today. The
    # correct-answer flag never leaves the server (see /api/daily/answer).
    idx = _daily_pool_idx()
    qc = _DAILY_CONTENT[idx] if idx is not None and idx < len(_DAILY_CONTENT) else None
    if not qc:
        return jsonify({'error': 'unavailable'}), 503
    return jsonify({'question': {'q': qc.get('q'), 'opts': qc.get('opts')},
                    'seconds_left': remaining})


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
    # Safe to reveal now: the day is consumed for this user, and the reveal is
    # what lets the client highlight the right option and show the explanation.
    idx = _daily_pool_idx()
    qc = _DAILY_CONTENT[idx] if idx is not None and idx < len(_DAILY_CONTENT) else None
    payload.update({'correct_index': answer_idx, 'exp': (qc or {}).get('exp')})
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
           'eduNote': 'Educational achievement — recognizes progress in the Tradeable learning program. Not a professional, financial, or trading qualification.',
           'download': 'Download PDF', 'back': 'Back'},
    'es': {'kicker': 'Certificate of Achievement', 'title': 'Certificado de Rango',
           'presented': 'Se otorga el presente certificado a',
           'attained': 'por haber alcanzado, con práctica y dedicación, el rango de',
           'rank': 'Rango', 'of': 'de', 'issued': 'Fecha de emisión', 'issuedBy': 'Emitido por',
           'eduNote': 'Logro educativo — reconoce el avance en el programa de aprendizaje de Tradeable. No constituye una calificación profesional, financiera ni de trading.',
           'download': 'Descargar PDF', 'back': 'Volver'},
    'fr': {'kicker': 'Certificate of Achievement', 'title': 'Certificat de Rang',
           'presented': 'Le présent certificat est décerné à',
           'attained': 'pour avoir atteint, par la pratique et la persévérance, le rang de',
           'rank': 'Rang', 'of': 'sur', 'issued': "Date d'émission", 'issuedBy': 'Émis par',
           'eduNote': "Accomplissement éducatif — reconnaît la progression dans le programme d'apprentissage Tradeable. Pas une qualification professionnelle, financière ou de trading.",
           'download': 'Télécharger le PDF', 'back': 'Retour'},
    'pt': {'kicker': 'Certificate of Achievement', 'title': 'Certificado de Rank',
           'presented': 'O presente certificado é concedido a',
           'attained': 'por ter alcançado, com prática e dedicação, o rank de',
           'rank': 'Rank', 'of': 'de', 'issued': 'Data de emissão', 'issuedBy': 'Emitido por',
           'eduNote': 'Conquista educativa — reconhece o progresso no programa de aprendizado da Tradeable. Não é uma qualificação profissional, financeira ou de trading.',
           'download': 'Baixar PDF', 'back': 'Voltar'},
}
VERIFY_I18N = {
    'en': {'okStatus': 'Certificate verified', 'okTitle': 'Authentic document',
           'attained': 'attained the rank of', 'rank': 'Rank', 'issued': 'Issued', 'code': 'Code',
           'note': 'Issued by Tradeable. This certificate is genuine and on record.',
           'noStatus': 'Not verified', 'noTitle': 'Certificate not found',
           'noDesc': 'does not match any certificate issued by Tradeable. It may be mistyped or forged.'},
    'es': {'okStatus': 'Certificado verificado', 'okTitle': 'Documento auténtico',
           'attained': 'alcanzó el rango de', 'rank': 'Rango', 'issued': 'Emitido', 'code': 'Código',
           'note': 'Emitido por Tradeable. Este certificado es genuino y consta en nuestros registros.',
           'noStatus': 'No verificado', 'noTitle': 'Certificado no encontrado',
           'noDesc': 'no corresponde a ningún certificado emitido por Tradeable. Podría estar mal escrito o ser falso.'},
    'fr': {'okStatus': 'Certificat vérifié', 'okTitle': 'Document authentique',
           'attained': 'a atteint le rang de', 'rank': 'Rang', 'issued': 'Émis', 'code': 'Code',
           'note': 'Émis par Tradeable. Ce certificat est authentique et enregistré.',
           'noStatus': 'Non vérifié', 'noTitle': 'Certificat introuvable',
           'noDesc': "ne correspond à aucun certificat émis par Tradeable. Il peut être mal saisi ou falsifié."},
    'pt': {'okStatus': 'Certificado verificado', 'okTitle': 'Documento autêntico',
           'attained': 'alcançou o rank de', 'rank': 'Rank', 'issued': 'Emitido', 'code': 'Código',
           'note': 'Emitido por Tradeable. Este certificado é genuíno e consta nos registros.',
           'noStatus': 'Não verificado', 'noTitle': 'Certificado não encontrado',
           'noDesc': 'não corresponde a nenhum certificado emitido por Tradeable. Pode estar incorreto ou ser falso.'},
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


def _migrate_user_camo_columns():
    """Add camo-skin columns (active_camo, owned_camos) to an existing user table.
    Each ALTER runs in its own transaction with a guard so that a concurrent
    gunicorn worker adding the same column first (a "duplicate column" error)
    can never crash startup — the column just ends up present either way."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns('user')}
    stmts = []
    if 'active_camo' not in cols:
        stmts.append('ALTER TABLE "user" ADD COLUMN active_camo VARCHAR(40)')
    if 'owned_camos' not in cols:
        stmts.append('ALTER TABLE "user" ADD COLUMN owned_camos TEXT')
    for s in stmts:
        try:
            with db.engine.begin() as conn:
                conn.execute(text(s))
        except Exception as e:
            app.logger.info('camo migration note (ignored): %s', e)
    if stmts:
        app.logger.info('Migrated user table: camo columns ensured.')


def _migrate_mentorship_application_columns():
    """Add columns introduced after the mentorship_application table first
    shipped (program, then the 2026-07 FAQ-profile fields). Same guard pattern
    as the camo migration: a concurrent worker adding the column first can
    never crash startup."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    if not insp.has_table('mentorship_application'):
        return  # create_all already made it with every column
    cols = {c['name'] for c in insp.get_columns('mentorship_application')}
    wanted = [
        ('program', 'VARCHAR(12)'),
        ('username', 'VARCHAR(40)'),
        ('goals', 'VARCHAR(200)'),
        ('strength', 'VARCHAR(20)'),
        ('weakness', 'VARCHAR(20)'),
        ('assets', 'VARCHAR(120)'),
        ('country', 'VARCHAR(80)'),
        ('tzname', 'VARCHAR(60)'),
        ('call_lang', 'VARCHAR(10)'),
        ('call_slot', 'VARCHAR(12)'),
        ('source', 'VARCHAR(20)'),
        ('age_range', 'VARCHAR(10)'),
        ('last_submit_at', 'TIMESTAMP'),
        ('submit_ip', 'VARCHAR(45)'),
        ('submit_count', 'INTEGER'),
    ]
    added = []
    for cname, ctype in wanted:
        if cname in cols:
            continue
        try:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE mentorship_application ADD COLUMN %s %s' % (cname, ctype)))
            added.append(cname)
        except Exception as e:
            app.logger.info('mentorship migration note (ignored): %s', e)
    if added:
        app.logger.info('Migrated mentorship_application: added %s.', ', '.join(added))


def _migrate_mentorship_area_columns():
    """Columns added to the members-area tables after they first shipped
    (video source/cover, area watermark switch). Same guarded pattern as the
    other migrations: a concurrent worker winning the race can't crash boot."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    wanted = {
        'mentorship_video': [('source', 'VARCHAR(12)'), ('thumb_url', 'VARCHAR(500)'),
                             ('provider_id', 'VARCHAR(120)'), ('chapters', 'TEXT')],
        'mentorship_video_comment': [('at_sec', 'INTEGER')],
        'order': [('provider_ref', 'VARCHAR(80)'), ('pay_status', 'VARCHAR(24)'),
                  ('paid_amount', 'FLOAT'), ('pay_currency', 'VARCHAR(20)'),
                  ('tx_hash', 'VARCHAR(120)'), ('alerted_at', 'TIMESTAMP')],
        'mentorship_live_state': [('watermark_on', 'BOOLEAN')],
    }
    for table, cols in wanted.items():
        if not insp.has_table(table):
            continue        # create_all already made it with every column
        have = {c['name'] for c in insp.get_columns(table)}
        for cname, ctype in cols:
            if cname in have:
                continue
            try:
                with db.engine.begin() as conn:
                    # `order` is a reserved word in PostgreSQL — quote the name.
                    tbl = '"%s"' % table if table in ('order', 'user') else table
                    conn.execute(text('ALTER TABLE %s ADD COLUMN %s %s' % (tbl, cname, ctype)))
                app.logger.info('Migrated %s: %s added.', table, cname)
            except Exception as exc:
                app.logger.warning('Could not add %s.%s: %s', table, cname, exc)


def _migrate_forum_post_community_column():
    """Add community_id to an existing forum_post table (prod PG / local sqlite)."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    try:
        cols = {c['name'] for c in insp.get_columns('forum_post')}
    except Exception:
        return
    if 'community_id' not in cols:
        try:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE forum_post ADD COLUMN community_id INTEGER'))
            app.logger.info('Migrated forum_post: community_id added.')
        except Exception as e:
            app.logger.info('forum community migration note (ignored): %s', e)


def _resync_postgres_sequences():
    """Point every id counter back at the rows that already exist.

    PostgreSQL hands out primary keys from a sequence, and that sequence only
    advances when *it* generates the id. Rows imported with their ids already
    set — a restored dump, a move from SQLite — land in the table without ever
    touching it, so the counter stays behind. The table then looks fine until
    the next insert, which asks for id 1, finds id 1 taken, and fails with a
    duplicate-key error. That is what broke adding an expense: the rows were
    never lost, the counter was simply still at the beginning.

    Runs at boot, only on PostgreSQL, and only ever moves a counter forward —
    never backward, which could hand out an id that is already in use.
    """
    if not db.engine.dialect.name.startswith('postgres'):
        return 0
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    fixed = []
    for table in insp.get_table_names():
        try:
            pk = (insp.get_pk_constraint(table) or {}).get('constrained_columns') or []
            if len(pk) != 1:
                continue            # composite or no primary key: nothing to advance
            col = pk[0]
            quoted = '"%s"' % table
            with db.engine.begin() as conn:
                seq = conn.execute(
                    text("SELECT pg_get_serial_sequence(:t, :c)"),
                    {'t': quoted, 'c': col}).scalar()
                if not seq:
                    continue        # id is not sequence-backed
                max_id = conn.execute(
                    text('SELECT COALESCE(MAX(%s), 0) FROM %s' % (col, quoted))).scalar() or 0
                if not max_id:
                    continue                # empty table: the counter is already right
                # A counter also records whether it has ever been read. Until it
                # has, it hands out `last_value` itself rather than the next one
                # — so a table holding a single row at id 1, with the counter
                # parked at 1 and never read, still collides on the next insert.
                row = conn.execute(
                    text('SELECT last_value, is_called FROM %s' % seq)).first()
                last, is_called = (row[0] or 0), bool(row[1])
                next_id = last + 1 if is_called else last
                if next_id <= max_id:
                    conn.execute(text('SELECT setval(:s, :v, true)'),
                                 {'s': seq, 'v': int(max_id)})
                    fixed.append('%s→%d' % (table, max_id))
        except Exception as exc:
            app.logger.warning('Could not resync the id counter for %s: %s', table, exc)
    if fixed:
        app.logger.info('Resynced id counters: %s', ', '.join(fixed))
    return len(fixed)


def _backfill_plan_camos():
    """Write the plan camo into every account that already pays for one.

    Ownership used to be read off the current plan, so these accounts would
    have lost their camo the day their subscription lapsed. Recording it makes
    the guarantee real for people who bought before the grant existed. Runs
    once per boot, touches only accounts that are missing it, and never removes
    anything.
    """
    changed = 0
    try:
        for user in User.query.filter(User.plan.in_(tuple(PLAN_CAMOS))).all():
            slug = PLAN_CAMOS.get(user.plan)
            if slug and slug not in user.camos_owned():
                user.add_camo(slug)
                changed += 1
        if changed:
            db.session.commit()
            app.logger.info('Backfilled the plan camo on %d account(s).', changed)
    except Exception as exc:
        db.session.rollback()
        app.logger.warning('Plan-camo backfill skipped: %s', exc)


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
        _migrate_user_camo_columns()
        _migrate_mentorship_application_columns()
        _migrate_forum_post_community_column()
        _migrate_mentorship_area_columns()
        _resync_postgres_sequences()
        _backfill_plan_camos()
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
    msg = (f"🚨 *Tradeable — ERROR 500*\n"
           f"URL: {request.url}\n"
           f"Error: {str(e)[:200]}\n"
           f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    send_whatsapp_alert(msg)
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
