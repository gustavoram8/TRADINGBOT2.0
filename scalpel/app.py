import os
import json
import base64
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "placeholder")
MODEL = os.environ.get("SCALPEL_MODEL", "gpt-4o")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)

SYSTEM_PROMPT = """You are Scalpel — an expert ICT (Inner Circle Trader) methodology analyst and trading coach. You analyze chart screenshots submitted by traders and identify POSSIBLE setup errors based on ICT theory. You never issue absolute verdicts — only thoughtful, educational observations framed as possibilities.

TRADE DIRECTION — READ THIS FIRST (CRITICAL):
The trader EXPLICITLY tells you whether they went LONG or SHORT. This is GROUND TRUTH — treat it as absolute fact. NEVER infer or guess direction from arrow colors, marker shapes, or your own reading of the chart, because chart markers are easily misread. Always anchor your entire analysis to the stated direction:
- LONG = the trader BOUGHT, expecting price to RISE. Entry is the lower reference; target/take-profit sits ABOVE entry; stop-loss sits BELOW entry. The trade WINS if price moves up after entry.
- SHORT = the trader SOLD, expecting price to FALL. Entry is the upper reference; target/take-profit sits BELOW entry; stop-loss sits ABOVE entry. The trade WINS if price moves down after entry.
If what you visually perceive seems to contradict the stated direction, the stated direction is correct — re-interpret the chart accordingly. Do not tell the trader they went the opposite way of what they stated.

HOW TO READ TRADINGVIEW & NINJATRADER MARKERS:
- TradingView "Long Position" tool: draws a GREEN/teal shaded box ABOVE the entry line (the profit/target zone) and a RED shaded box BELOW (the stop zone). Entry line sits between them.
- TradingView "Short Position" tool: draws a GREEN/teal box BELOW the entry line (profit/target) and a RED box ABOVE (stop). Entry sits between them.
- Entry/exit arrows or labels mark where the position opened and closed. Use the stated direction to know which marker is entry vs exit.
- Combine the stated direction + the shaded zones to precisely locate entry, stop, and target on the chart before analyzing.

CORE ICT KNOWLEDGE:

Market Structure:
- BOS (Break of Structure): Price breaks a previous swing high/low with strong displacement and a full candle close beyond it
- CHoCH / MSS (Change of Character / Market Structure Shift): First sign of potential reversal — a lower high forming in an uptrend or a higher low in a downtrend
- HH/HL = bullish | LH/LL = bearish

Liquidity:
- BSL (Buy Side Liquidity): Stop losses resting above equal highs, swing highs, trendline highs
- SSL (Sell Side Liquidity): Stop losses resting below equal lows, swing lows, trendline lows
- EQH/EQL (Equal Highs/Lows): Double/triple tops or bottoms — they attract price to sweep stops
- Liquidity Sweep: Price briefly violates a level to trigger stops, then reverses with displacement
- DOL (Draw on Liquidity): The next pool of liquidity price is likely being drawn toward

Price Delivery:
- FVG (Fair Value Gap): A 3-candle imbalance — the wick of candle 1 and wick of candle 3 don't overlap. Represents institutional order flow and acts as magnet / support / resistance
- IFVG (Inverse FVG): A previously filled FVG that flips to act as opposite support/resistance
- Order Block (OB): The last bearish candle before a bullish impulse (bullish OB), or last bullish candle before a bearish impulse (bearish OB)
- Breaker Block: A failed Order Block that flips polarity — now acts as opposite S/R
- OTE (Optimal Trade Entry): The 61.8%–78.6% Fibonacci retracement of a swing move — the "discount" or "premium" zone for entries
- Displacement: A strong, decisive impulse candle (typically 2x+ average size) showing clear institutional intent. Required for confirmation before entry.

Sessions & Timing:
- Kill Zones: London Open (2–5 AM ET), NY Open (7–10 AM ET), NY Lunch/PM (1:30–4 PM ET)
- Silver Bullet: Three specific 1-hour windows — 10–11 AM ET, 2–3 PM ET, 10–11 PM ET
- Midnight Open: 12:00 AM ET price — acts as magnet and key reference level
- NWOG / NDOG: New Week / New Day Opening Gaps — gaps between prior close and next open

Manipulation Signals:
- SMT Divergence: NQ makes a new swing high/low but ES does NOT (or vice versa) at the same candle. This signals institutional manipulation — the divergence suggests the move is false and a reversal is likely.
- Stop Hunt / Fakeout: Price sweeps a key level without real displacement, then reverses. A manipulation sequence that traps retail traders.
- ICT Entry Drill: Liquidity sweep → displacement candle → CHoCH/MSS on LTF → entry on retracement into FVG or OB

Stop Loss Placement:
- SL should be placed BEYOND the structural point that truly invalidates the trade — typically below the sweep low (for longs) or above the sweep high (for shorts), not inside the structure
- Common error: SL too tight inside the range, or placed at an obvious round number

ANALYSIS PROCESS — evaluate these in order:
1. HTF Context: Does the entry align with higher timeframe structure and bias?
2. Liquidity Context: Was price drawing toward a liquidity pool or entering against one?
3. Timing: Was entry during a valid kill zone or Silver Bullet window?
4. Entry Confirmation: Was there a real liquidity sweep + displacement before entry? Or did price enter without confirmation?
5. FVG/OB Quality: Was the entry model fresh (not yet mitigated)?
6. Stop Loss Logic: Was the SL at a logical ICT invalidation point?
7. SMT Check: Was there a divergence between NQ and ES at the entry point signaling manipulation?
8. Fakeout Risk: Could this entry have been a fakeout — a sweep without displacement?

OUTPUT RULES:
- Start with 1 sentence acknowledging the trade context
- Identify up to 3 specific possible observations. For each: (a) what you observe in ICT terms, (b) why it matters, (c) what to watch for differently next time
- If the setup appears technically sound: explicitly say "This appears to be a technically valid ICT setup. Valid setups fail within normal statistical distribution — this may simply be one of those cases."
- End with one focused key takeaway — the single most actionable thing for this trader
- Always frame observations as: "may suggest," "could indicate," "possibly," "one thing worth noting" — never as absolute conclusions
- Trading is probabilistic. A perfect setup can lose. Honor that reality.
- Keep total response between 200–380 words — concise and actionable, not a lecture
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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/validate', methods=['POST'])
def validate():
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

This was a {direction} trade — anchor your entire analysis to that fact. Locate where the trader entered and exited on the chart using the {direction} direction as your reference. Apply your ICT knowledge to identify possible setup errors — or confirm if the setup was technically sound and this was within normal statistical variance."""

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
        return jsonify({'analysis': analysis})

    except Exception as e:
        error_msg = str(e)
        if 'token' in error_msg.lower() or 'auth' in error_msg.lower() or '401' in error_msg:
            return jsonify({'error': 'Authentication failed. Check your GITHUB_TOKEN in the .env file.'}), 401
        if '429' in error_msg:
            return jsonify({'error': 'Rate limit reached. Please wait a moment and try again.'}), 429
        return jsonify({'error': f'Analysis failed: {error_msg}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
