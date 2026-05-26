import os
import json
import base64
import socket
import secrets
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'scalpel.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

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

# ── AI client ──
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "placeholder")
MODEL = os.environ.get("SCALPEL_MODEL", "gpt-4o")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)


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

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    anon_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ──────────────────────────────────────────────────────────────────────────
# PLAN LIMITS & ACCESS HELPERS
# ──────────────────────────────────────────────────────────────────────────
PLAN_WINDOWS = {
    'free': timedelta(days=7),
    'standard': timedelta(days=1),
    'premium': None,  # unlimited
}

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


def _as_utc(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def check_rate_limit():
    """Return None if an analysis is allowed, else a dict describing the block."""
    plan = current_plan()
    window = PLAN_WINDOWS.get(plan)
    if window is None:
        return None  # premium = unlimited

    if current_user.is_authenticated:
        last = (UsageLog.query
                .filter_by(user_id=current_user.id)
                .order_by(UsageLog.created_at.desc())
                .first())
    else:
        anon = get_anon_id()
        last = (UsageLog.query
                .filter_by(anon_id=anon)
                .order_by(UsageLog.created_at.desc())
                .first()) if anon else None

    if last is None:
        return None  # never used → allow

    next_allowed = _as_utc(last.created_at) + window
    now = datetime.now(timezone.utc)
    if now >= next_allowed:
        return None

    remaining = int((next_allowed - now).total_seconds())
    return {
        'plan': plan,
        'remaining_seconds': remaining,
        'next_available': next_allowed.isoformat(),
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
# PUBLIC / ENTRY ROUTES
# ──────────────────────────────────────────────────────────────────────────
@app.route('/')
def splash():
    session['splash_shown'] = True
    return render_template('splash.html')


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/app')
def app_view():
    if not session.get('splash_shown'):
        return redirect(url_for('splash'))
    if not has_access():
        return redirect(url_for('login'))
    return render_template(
        'index.html',
        plan=current_plan(),
        is_admin=current_user.is_admin if current_user.is_authenticated else False,
        username=current_user.username if current_user.is_authenticated else None,
        is_guest=not current_user.is_authenticated,
    )


# ──────────────────────────────────────────────────────────────────────────
# AUTH ROUTES
# ──────────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if not session.get('splash_shown') and request.method == 'GET':
        return redirect(url_for('splash'))
    if current_user.is_authenticated:
        return redirect(url_for('app_view'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        user = (User.query.filter_by(email=identifier.lower()).first()
                or User.query.filter_by(username=identifier).first())
        if user and user.check_password(password):
            login_user(user, remember=True, duration=timedelta(days=30))
            target = url_for('admin') if user.is_admin else url_for('app_view')
            return redirect(target)
        return render_template('login.html', error='invalid')

    return render_template('login.html', reset=request.args.get('reset'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if not session.get('splash_shown') and request.method == 'GET':
        return redirect(url_for('splash'))
    if current_user.is_authenticated:
        return redirect(url_for('app_view'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if len(username) < 3 or len(email) < 5 or len(password) < 6:
            return render_template('register.html', error='invalid', username=username, email=email)
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='username_taken', username=username, email=email)
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='email_taken', username=username, email=email)

        user = User(username=username, email=email, plan='free')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True, duration=timedelta(days=30))
        return redirect(url_for('app_view'))

    return render_template('register.html')


@app.route('/start-free')
def start_free():
    resp = make_response(redirect(url_for('app_view')))
    if not get_anon_id():
        resp.set_cookie(
            ANON_COOKIE, secrets.token_urlsafe(24),
            max_age=60 * 60 * 24 * 365, samesite='Lax'
        )
    return resp


@app.route('/logout')
def logout():
    logout_user()
    resp = make_response(redirect(url_for('login')))
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
            send_reset_email(email, reset_url)
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
        if len(password) < 6:
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
    return render_template('admin.html', users=users, counts=counts)


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

    # ── Rate limit gate (free 1/week, standard 1/day, premium unlimited) ──
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

        user_message = f"""Trade submitted for ICT analysis:

Instrument: {instrument}
DIRECTION (ground truth — the trader took a {direction} position): {direction}
Session: {session}
Result: {result}
HTF Bias held: {htf_bias}
Traded aligned with HTF bias: {aligned}
Approach / model used: {approach}
Confluences identified by trader: {confluences_str}
{f'Trader notes: {notes}' if notes else ''}

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
        return jsonify({'analysis': analysis})

    except Exception as e:
        error_msg = str(e)
        if 'token' in error_msg.lower() or 'auth' in error_msg.lower() or '401' in error_msg:
            return jsonify({'error': 'Authentication failed. Check your GITHUB_TOKEN in the .env file.'}), 401
        if '429' in error_msg:
            return jsonify({'error': 'Rate limit reached. Please wait a moment and try again.'}), 429
        return jsonify({'error': f'Analysis failed: {error_msg}'}), 500


# ──────────────────────────────────────────────────────────────────────────
# BOOTSTRAP: create tables + seed admin
# ──────────────────────────────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        admin_email = os.environ.get('ADMIN_EMAIL', 'mauroramirezmij@gmail.com').lower()
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Codica2310$')
        if not User.query.filter_by(email=admin_email).first():
            admin = User(
                username=admin_username,
                email=admin_email,
                plan='premium',
                is_admin=True,
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            app.logger.info('Seeded admin account: %s', admin_email)


init_db()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
