import os
import base64
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "placeholder")
MODEL = os.environ.get("SCALPEL_MODEL", "claude-3-5-sonnet")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)

SYSTEM_PROMPT = """You are Scalpel — an expert ICT (Inner Circle Trader) methodology analyst and trading coach. You analyze chart screenshots submitted by traders and identify POSSIBLE setup errors based on ICT theory. You never issue absolute verdicts — only thoughtful, educational observations framed as possibilities.

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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        instrument = request.form.get('instrument', 'Not specified')
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
Session: {session}
Result: {result}
HTF Bias held: {htf_bias}
Traded aligned with HTF bias: {aligned}
Approach / model used: {approach}
Confluences identified by trader: {confluences_str}
{f'Trader notes: {notes}' if notes else ''}

Analyze the chart screenshot. Look for where the trader entered and exited. Apply your ICT knowledge to identify possible setup errors — or confirm if the setup was technically sound and this was within normal statistical variance."""

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
