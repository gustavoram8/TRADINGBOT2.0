/* ════════════════════════════════════════════════════════════════════════
   SYNAPSE LIBRARY — real content + textbook SVG diagrams for the 41 topics.

   Consumed by the flipbook dossier in index.html:
     • window.SynapseContent[slug]  → { lead, body?, mechanics[], mistake,
                                        setup?, terms[], figcap? }
     • window.SynapseDiagrams[slug] → () => '<svg…>'  (uses df-* CSS classes
                                       so it auto-adapts to light/dark)

   Content language: English (trading terminology is native English even in
   non-English trading communities). Structured for a clean translation pass.
   Diagrams are drawn in a shared 0 0 400 220 viewBox.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ── SVG toolkit ─────────────────────────────────────────────────────────
  const VB = 'viewBox="0 0 400 220"';
  const svg = (inner) => '<svg ' + VB + ' xmlns="http://www.w3.org/2000/svg">' + inner + '</svg>';

  // candle: y-coords (smaller y = higher price). bull = close above open.
  function candle(x, hiY, loY, openY, closeY, w) {
    w = w || 11;
    const bull = closeY < openY;
    const top = Math.min(openY, closeY), bot = Math.max(openY, closeY);
    const cls = bull ? 'df-up' : 'df-down';
    return '<line class="df-wick" x1="' + x + '" y1="' + hiY + '" x2="' + x + '" y2="' + loY + '"/>' +
           '<rect class="' + cls + '" x="' + (x - w / 2) + '" y="' + top + '" width="' + w +
           '" height="' + Math.max(1.5, bot - top) + '" rx="1"/>';
  }
  // quick neutral candle by direction with auto wicks
  function bar(x, top, bot, dir, w, wickTop, wickBot) {
    w = w || 11;
    const hiY = wickTop != null ? wickTop : top - 6;
    const loY = wickBot != null ? wickBot : bot + 6;
    return dir === 'up' ? candle(x, hiY, loY, bot, top, w) : candle(x, hiY, loY, top, bot, w);
  }
  const line = (x1, y1, x2, y2, cls) => '<line class="' + (cls || 'df-axis') + '" x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '"/>';
  const rect = (x, y, w, h, cls) => '<rect class="' + cls + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="2"/>';
  const txt = (x, y, s, cls, anchor) => '<text class="' + (cls || 'df-tag') + '" x="' + x + '" y="' + y + '"' + (anchor ? ' text-anchor="' + anchor + '"' : '') + '>' + s + '</text>';
  const dot = (x, y, r, cls) => '<circle class="' + (cls || 'df-accent-f') + '" cx="' + x + '" cy="' + y + '" r="' + (r || 3) + '"/>';
  const path = (d, cls) => '<path class="' + cls + '" d="' + d + '"/>';
  // accent arrow (line + head)
  function arrow(x1, y1, x2, y2, cls) {
    cls = cls || 'df-line-accent';
    const fill = cls.indexOf('up') > -1 ? 'df-up' : cls.indexOf('down') > -1 ? 'df-down' : 'df-accent-f';
    const a = Math.atan2(y2 - y1, x2 - x1), h = 8, w = 4.5;
    const bx = x2 - h * Math.cos(a), by = y2 - h * Math.sin(a);
    const lx = bx - w * Math.sin(a), ly = by + w * Math.cos(a);
    const rx = bx + w * Math.sin(a), ry = by - w * Math.cos(a);
    return line(x1, y1, bx, by, cls) +
      '<polygon class="' + fill + '" points="' + x2 + ',' + y2 + ' ' + lx + ',' + ly + ' ' + rx + ',' + ry + '"/>';
  }
  // frame: faint axes
  const frame = () => line(34, 196, 384, 196, 'df-axis') + line(34, 16, 34, 196, 'df-axis');

  const C = {};  // content
  const D = {};  // diagrams

  // ══════════════════════════════════════════════════════════════════════
  // METHODOLOGY 1 — PRICE ACTION
  // ══════════════════════════════════════════════════════════════════════

  C['price.support-resistance'] = {
    lead: 'Support and resistance are price zones where the market has repeatedly reversed — the chart\'s memory of where buyers and sellers fought before.',
    body: 'They are not exact lines but bands, formed where unfilled orders cluster around prior swing highs and lows. Support is where falling price tends to stop and bounce; resistance is where rising price tends to stall and turn.',
    mechanics: [
      { term: 'Static levels', text: 'Form at prior swing highs/lows where resting orders remain — price revisits and reacts to them.' },
      { term: 'Psychological levels', text: 'Round numbers (1.2000, 50.00) attract clustered stops and pending orders, amplifying their pull.' },
      { term: 'Role reversal', text: 'Once support breaks and price closes below it, that level flips to resistance on the retest — and vice versa.' },
      { term: 'Strength by touches', text: 'More tested levels are more significant — but each test consumes resting orders, eventually weakening the zone.' },
      { term: 'Draw with bodies', text: 'Anchor levels to clustered candle closes, not isolated wicks; slide the line to maximise contact on both sides.' },
    ],
    mistake: ['The number-one error is treating support/resistance as an exact line and entering right on it.',
      'They are zones several pips wide. Wait for a rejection from the zone rather than a precise touch. And remember: a level is strongest on its first retest after forming — every additional test depletes the orders sitting there.'],
    terms: ['Swing highs/lows', 'Role reversal', 'Psychological levels', 'Zone width', 'Confluence', 'Order clusters'],
    figcap: 'Price respects a level twice as resistance, breaks it, then retests it as support (role reversal).',
  };
  D['price.support-resistance'] = () => svg(
    frame() +
    line(40, 70, 384, 70, 'df-dash-accent') +
    txt(372, 64, 'level', 'df-tag-accent', 'end') +
    // two rejections from above (resistance)
    bar(70, 78, 120, 'down', 11, 72, 128) +
    bar(92, 72, 110, 'down', 11, 70, 120) +
    arrow(105, 74, 112, 104, 'df-line-accent') +
    bar(150, 74, 118, 'down', 11, 71, 126) +
    arrow(163, 76, 170, 104, 'df-line-accent') +
    // breakout through level
    bar(200, 60, 96, 'up', 11, 54, 100) +
    bar(222, 44, 82, 'up', 11, 40, 88) +
    // retest from below = support flip
    bar(270, 60, 88, 'down', 11, 56, 96) +
    bar(292, 66, 96, 'up', 11, 50, 100) +
    arrow(305, 92, 312, 64, 'df-line-accent') +
    bar(330, 40, 72, 'up', 11, 34, 78) +
    txt(60, 150, 'resistance', 'df-tag', 'start') +
    txt(300, 150, 'now support', 'df-tag', 'start')
  );

  C['price.trend-structure'] = {
    lead: 'Market structure reads trend through a sequence of swings: an uptrend prints higher highs and higher lows; a downtrend prints lower highs and lower lows.',
    body: 'Trend is never uniform — it alternates between impulsive legs (strong, directional) and corrective legs (overlapping pullbacks). Reading which leg is which is the trader\'s core job.',
    mechanics: [
      { term: 'Swing points', text: 'A swing high is a peak flanked by lower candles; a swing low is a trough flanked by higher candles. These define structure.' },
      { term: 'Impulse vs correction', text: 'Impulse legs are long and close near their extreme; corrections are shorter and overlapping. Impulse sets direction, correction offers entries.' },
      { term: 'Multi-timeframe', text: 'Higher timeframes set the bias; lower timeframes time the entry. A pullback on the 1H inside a bullish daily is a buy, not a short.' },
      { term: 'Trend change', text: 'A trend reverses only when the opposing side breaks the most recent swing extreme with a close — not a single wick.' },
      { term: 'Ranges', text: 'When price alternates between defined highs and lows without breaking either, the market is ranging and trend tools fail.' },
    ],
    mistake: 'Beginners flip bias too fast — one candle in the "wrong" direction does not break structure. The swing point must actually be taken out by a body close. Read structure one or two timeframes above your entry timeframe to avoid drowning in noise.',
    terms: ['Higher highs / lows', 'Swing point', 'Impulse leg', 'Corrective leg', 'Multi-timeframe', 'Range'],
    figcap: 'An uptrend as a staircase of higher highs (HH) and higher lows (HL) connected by impulse and correction.',
  };
  D['price.trend-structure'] = () => {
    const pts = [[40,180],[90,110],[130,140],[180,80],[225,112],[280,50],[330,86],[372,30]];
    let pth = 'M' + pts[0][0] + ' ' + pts[0][1];
    for (let i = 1; i < pts.length; i++) pth += ' L' + pts[i][0] + ' ' + pts[i][1];
    const labels = ['', 'HH', 'HL', 'HH', 'HL', 'HH', 'HL', 'HH'];
    let marks = '';
    pts.forEach((p, i) => { if (labels[i]) marks += dot(p[0], p[1], 3) + txt(p[0], p[1] + (i % 2 ? 16 : -8), labels[i], 'df-tag-accent', 'middle'); });
    return svg(frame() + path(pth, 'df-line-accent') + marks + arrow(330, 86, 372, 30, 'df-line-accent'));
  };

  C['price.candles'] = {
    lead: 'A candlestick compresses four numbers — open, high, low, close — into one shape that records the battle between buyers and sellers over a period.',
    body: 'The body (open-to-close) shows who won; the wicks show how far the losing side pushed before being rejected. Reading candles is reading order flow in visual form.',
    mechanics: [
      { term: 'Body', text: 'A large body closing near its extreme signals conviction; a small body (doji) signals indecision and balance.' },
      { term: 'Upper wick', text: 'Price was pushed up then sold back before the close — the longer the wick, the stronger the rejection of higher prices.' },
      { term: 'Lower wick (tail)', text: 'Price was pushed down then bought back up — long tails at key lows are among the most reliable reversal hints.' },
      { term: 'Sequences', text: 'Single candles rarely confirm; 2–3 candles build context. Growing bodies = accelerating momentum; growing wicks = momentum fading.' },
    ],
    mistake: 'Reading a candle in isolation is nearly useless — context is everything. A hammer at key support is a signal; the same hammer mid-range is noise. And don\'t dismiss wicks: they are the most information-rich part of the candle.',
    terms: ['Body', 'Wick / shadow', 'Doji', 'Hammer', 'Conviction', 'Rejection'],
    figcap: 'Anatomy of a candle: body (open→close) plus upper and lower wicks marking the rejected extremes.',
  };
  D['price.candles'] = () => svg(
    // big bullish candle anatomy on the left
    candle(150, 30, 196, 150, 70, 40) +
    line(150, 30, 250, 30, 'df-grid') + txt(258, 34, 'high', 'df-label', 'start') +
    line(170, 70, 250, 70, 'df-grid') + txt(258, 74, 'close', 'df-label', 'start') +
    line(170, 150, 250, 150, 'df-grid') + txt(258, 154, 'open', 'df-label', 'start') +
    line(150, 196, 250, 196, 'df-grid') + txt(258, 200, 'low', 'df-label', 'start') +
    txt(150, 16, 'upper wick', 'df-tag', 'middle') +
    arrow(110, 50, 130, 50, 'df-line-accent') + txt(60, 54, 'body', 'df-tag', 'start') +
    txt(150, 212, 'lower wick', 'df-tag', 'middle')
  );

  C['price.chart-patterns'] = {
    lead: 'Chart patterns are recurring geometric formations born from repeated crowd psychology — they split into continuation patterns (trend resumes) and reversal patterns (trend ends).',
    body: 'Each carries a measurable price objective derived from its own dimensions, giving both a directional bias and a target.',
    mechanics: [
      { term: 'Flags & pennants', text: 'A sharp "flagpole" then a tight pause — continuation. Target = flagpole length projected from the breakout.' },
      { term: 'Triangles', text: 'Ascending (flat top) is bullish, descending (flat bottom) bearish, symmetric is neutral until the break. Target = widest height.' },
      { term: 'Head & shoulders', text: 'Three peaks with the middle highest; a close below the neckline confirms reversal. Target = head height from the neckline.' },
      { term: 'Double tops/bottoms', text: 'Two equal extremes; breaking the intermediate level (neckline) confirms. Target = pattern height.' },
      { term: 'Volume', text: 'Classical patterns want volume contracting in the build and expanding on the breakout. Flat-volume breakouts are suspect.' },
    ],
    mistake: 'Patterns fail to complete 30–40% of the time, so the measured move is a guideline, not a promise. In algo-driven markets many "head and shoulders" are engineered stop-runs above the right shoulder before the real move — manage risk rather than assume completion.',
    terms: ['Flagpole', 'Neckline', 'Measured move', 'Breakout', 'Continuation', 'Reversal'],
    figcap: 'A head-and-shoulders top: left shoulder, higher head, right shoulder, and the neckline whose break confirms.',
  };
  D['price.chart-patterns'] = () => {
    const pts = [[40,150],[80,150],[110,110],[140,150],[200,60],[260,150],[300,112],[330,150],[372,150]];
    let pth = 'M' + pts[0][0] + ' ' + pts[0][1];
    for (let i = 1; i < pts.length; i++) pth += ' L' + pts[i][0] + ' ' + pts[i][1];
    return svg(frame() + path(pth, 'df-line-accent') +
      line(110, 150, 300, 150, 'df-dash') +
      txt(110, 100, 'L sh', 'df-tag', 'middle') + txt(200, 50, 'head', 'df-tag-accent', 'middle') + txt(300, 102, 'R sh', 'df-tag', 'middle') +
      txt(310, 144, 'neckline', 'df-tag', 'start') +
      arrow(330, 152, 350, 188, 'df-line-down'));
  };

  C['price.supply-demand'] = {
    lead: 'Supply and demand zones mark where institutional orders — too large to fill at once — left unfilled residue, causing price to react when it returns to that origin.',
    body: 'Unlike support/resistance, which marks where price reacted, a supply/demand zone marks the cause — the base from which an impulsive move originated and where remaining orders still sit.',
    mechanics: [
      { term: 'Origin base', text: 'A valid zone is the small consolidation right before an aggressive impulse away — that base is where institutions positioned.' },
      { term: 'Zone anatomy', text: 'Demand = last low of the base to the first impulse candle; supply = last high of the base to the first impulse down.' },
      { term: 'Fresh vs tested', text: 'A fresh, untouched zone is highest probability; after 3+ tests the orders are largely filled and the zone is "spent".' },
      { term: 'Quality', text: 'The sharper and faster the move away (ideally leaving imbalances), the stronger the institutional intent behind the zone.' },
    ],
    mistake: 'Drawing zones from wicks instead of bodies, and re-entering zones that have already been tapped several times. Each test consumes orders — quality degrades. The size and speed of the move away is what tells you how serious the remaining orders are.',
    terms: ['Origin base', 'Impulsive move', 'Fresh zone', 'Spent zone', 'Imbalance', 'Proximal / distal'],
    figcap: 'A tight base followed by an explosive rally — the base becomes a demand zone price returns to.',
  };
  D['price.supply-demand'] = () => svg(
    frame() +
    rect(40, 130, 120, 34, 'df-zone-up') + txt(46, 124, 'demand zone', 'df-tag', 'start') +
    bar(60, 138, 158, 'down', 10, 134, 162) +
    bar(82, 134, 160, 'up', 10, 130, 164) +
    bar(104, 138, 158, 'down', 10, 134, 162) +
    bar(126, 134, 160, 'up', 10, 130, 164) +
    // explosive impulse away
    bar(170, 96, 140, 'up', 11, 92, 144) +
    bar(196, 60, 100, 'up', 11, 54, 104) +
    bar(222, 36, 66, 'up', 11, 30, 70) +
    arrow(150, 150, 232, 48, 'df-line-up') +
    // return to zone
    bar(300, 40, 90, 'down', 11, 36, 96) +
    bar(326, 80, 150, 'down', 11, 74, 156) +
    arrow(338, 150, 345, 120, 'df-line-up')
  );

  C['price.pin-bar'] = {
    type: 't',
    lead: 'A pin bar is a single-candle reversal: a small body with a long wick that shows price was driven hard one way, then forcefully rejected back, closing near where it opened.',
    body: 'The tail points toward the expected reversal; the nose marks the rejected extreme. Location is everything — a pin bar only matters at a meaningful level.',
    mechanics: [
      { term: 'Anatomy', text: 'Body under ~25% of the range, tail at least two-thirds of it, little or no opposite wick.' },
      { term: 'Wick-to-body ratio', text: 'Aim for 2:1 minimum; elite signals show 3:1 or more — the longer the tail, the stronger the rejection.' },
      { term: 'Location', text: 'Only counts at key S/R, supply/demand, a Fibonacci level, or aligned with the higher-timeframe trend.' },
      { term: 'Refined entry', text: 'Entering at the 50% retrace of the pin bar (instead of the close) improves risk/reward and filters some fakes.' },
    ],
    mistake: 'A pin bar on its own means nothing — the identical candle at a random mid-range price has near-zero edge. And bearish pins against a strong uptrend usually fail; the pin must agree with the higher-timeframe bias.',
    setup: {
      cond: 'Pin bar forms at key S/R, a supply/demand zone, or a Fibonacci level aligned with the higher-timeframe trend.',
      entry: 'On the pin bar\'s close, or a limit at its 50% retrace; aggressive traders use a break of the opposite body extreme.',
      stop: 'Just beyond the tip of the wick, with a small ATR buffer for volatility.',
      target: 'The next key level in the reversal direction; minimum 1:2, or 2× the pin bar\'s range.',
    },
    terms: ['Rejection candle', 'Wick-to-body ratio', 'Tail / nose', '50% entry', 'Confluence', 'HTF bias'],
    figcap: 'A bullish pin bar rejecting support: a long lower tail, tiny body, entry on the close, stop below the wick.',
  };
  D['price.pin-bar'] = () => svg(
    frame() +
    line(40, 150, 384, 150, 'df-dash-accent') + txt(372, 144, 'support', 'df-tag-accent', 'end') +
    bar(90, 70, 110, 'down', 12, 64, 116) +
    bar(125, 90, 120, 'down', 12, 84, 128) +
    // the pin bar: small body near top, long lower tail piercing support
    candle(180, 96, 184, 118, 104, 16) +
    txt(180, 86, 'pin bar', 'df-tag-accent', 'middle') +
    arrow(180, 178, 180, 130, 'df-line-accent') +
    // continuation up
    bar(235, 86, 116, 'up', 12, 80, 120) +
    bar(270, 56, 96, 'up', 12, 50, 100) +
    bar(305, 34, 70, 'up', 12, 28, 74) +
    txt(150, 200, 'stop below wick', 'df-tag', 'start')
  );

  C['price.engulfing'] = {
    type: 't',
    lead: 'An engulfing pattern is a two-candle reversal where the second candle\'s body completely swallows the first — a decisive takeover by the opposing side.',
    body: 'Bullish engulfing appears at lows (a big up candle eats the prior down candle); bearish engulfing at highs (a big down candle eats the prior up candle).',
    mechanics: [
      { term: 'Body engulfment', text: 'The second body must fully contain the first body (wicks matter less). 80%+ partial engulfs are weaker but tradable.' },
      { term: 'Size', text: 'The strongest signals have a second candle 2×+ the first — a dramatic shift in order flow.' },
      { term: 'Context', text: 'Only has edge at significant levels — major S/R, supply/demand, trend extremes — not mid-range.' },
      { term: 'Volume', text: 'Higher volume on the engulfing candle confirms institutional participation absorbing the prior move.' },
    ],
    mistake: 'Trading engulfing candles in the middle of a range produces a stream of losers. The pattern is only an edge at structural levels. A full "outside bar" (wicks also engulfed) at a key level is the highest-quality version.',
    setup: {
      cond: 'Prior trend in place; pattern forms at key S/R, a supply/demand zone, or Fibonacci confluence; second candle closes decisively.',
      entry: 'On the engulfing candle\'s close, or a small pullback to its midpoint.',
      stop: 'Beyond the low of the whole pattern (bullish) or its high (bearish), plus a buffer.',
      target: 'Next key level; 1:2 minimum, or 2× the pattern height.',
    },
    terms: ['Outside bar', 'Body engulfment', 'Order-flow shift', 'Context', 'Volume confirmation'],
    figcap: 'A bullish engulfing at a low: the green body fully engulfs the prior red body, signalling a takeover.',
  };
  D['price.engulfing'] = () => svg(
    frame() +
    line(40, 150, 384, 150, 'df-dash') +
    bar(80, 70, 108, 'down', 12, 64, 114) +
    bar(115, 86, 120, 'down', 12, 80, 126) +
    // small down candle then big engulfing up candle
    candle(170, 110, 150, 138, 120, 14) + txt(170, 102, 'down', 'df-tag', 'middle') +
    candle(200, 96, 152, 124, 104, 20) + txt(214, 96, 'engulfs', 'df-tag-accent', 'start') +
    arrow(200, 170, 200, 132, 'df-line-accent') +
    bar(250, 88, 116, 'up', 12, 82, 120) +
    bar(285, 58, 96, 'up', 12, 52, 100) +
    bar(320, 38, 70, 'up', 12, 32, 74)
  );

  C['price.breakout-retest'] = {
    type: 't',
    lead: 'Break-and-retest waits for price to close decisively beyond a level, then return to test that broken level from the other side before entering — trading role reversal with confirmation.',
    body: 'It sacrifices the very first move for a far better entry price and a cleaner invalidation than chasing the breakout.',
    mechanics: [
      { term: 'Valid breakout', text: 'A clear close beyond the level (not just a wick), ideally on above-average volume with a strong-bodied candle.' },
      { term: 'The retest', text: 'Profit-taking pulls price back toward the broken level, which — as role reversal predicts — should now hold.' },
      { term: 'Confirmation', text: 'Look for a rejection (pin/engulfing) at the retest, or a volume contraction into it followed by expansion away.' },
      { term: 'Fakeout filter', text: 'A real breakout retests and continues; a fakeout closes back inside the level. Stops just inside the level exploit this.' },
    ],
    mistake: 'Not every breakout retests — some run away immediately, so waiting only for the retest means missing trades; many traders split size (half on break, half on retest). Also, choppy ranges spawn constant fake breakouts — this works only with real momentum or at genuinely significant levels.',
    setup: {
      cond: 'A clear structural level broken with a closing candle and volume, then a return toward that level from the new side.',
      entry: 'On a rejection candle at the retest, or a limit order in the broken-level zone.',
      stop: 'Below the retest low (longs) / above the retest high (shorts), or just inside the broken level.',
      target: 'The measured move from the breakout, or the next key structural level; 1:2 minimum.',
    },
    terms: ['Role reversal', 'Throwback', 'Breakout candle', 'Fakeout', 'Volume confirmation'],
    figcap: 'Resistance breaks on a strong close, price retests it as support, then continues — the retest is the entry.',
  };
  D['price.breakout-retest'] = () => svg(
    frame() +
    line(40, 96, 384, 96, 'df-dash-accent') + txt(372, 90, 'level', 'df-tag-accent', 'end') +
    bar(70, 104, 150, 'down', 11, 100, 156) +
    bar(96, 110, 150, 'up', 11, 104, 156) +
    bar(122, 104, 148, 'down', 11, 100, 154) +
    // breakout close above
    bar(170, 60, 104, 'up', 12, 54, 108) + txt(170, 48, 'break', 'df-tag-accent', 'middle') +
    bar(200, 50, 86, 'up', 11, 44, 90) +
    // retest of level from above
    bar(244, 60, 92, 'down', 11, 56, 98) +
    bar(270, 70, 94, 'up', 11, 60, 100) + txt(284, 88, 'retest', 'df-tag', 'start') +
    arrow(282, 92, 290, 70, 'df-line-accent') +
    bar(316, 50, 78, 'up', 11, 44, 82) +
    bar(346, 32, 64, 'up', 11, 26, 68)
  );

  C['price.harmonic'] = {
    type: 't',
    lead: 'Harmonic patterns are five-point (X-A-B-C-D) structures whose legs obey precise Fibonacci ratios, projecting a Potential Reversal Zone at point D where the reversal is traded.',
    body: 'Codified by Scott Carney from Gartley\'s original work, the family includes the Gartley, Bat, Butterfly, and Crab — each defined by its own ratio set.',
    mechanics: [
      { term: 'Gartley', text: 'B = 61.8% of XA, D = 78.6% of XA — the most conservative pattern with the tightest PRZ.' },
      { term: 'Bat', text: 'B = 38.2–50% of XA, D = 88.6% of XA — a deeper retracement that suits strong trends.' },
      { term: 'Butterfly', text: 'B = 78.6% of XA, D = 127–162% extension of XA (past X) — catches exhaustion moves.' },
      { term: 'PRZ', text: 'At D, several Fibonacci levels cluster; the more confluence in that zone, the higher the reversal odds.' },
    ],
    mistake: 'Two killers: loosening the ratios (a B at 65% is not a Gartley), and entering the moment price reaches the PRZ without a reversal candle — especially on Butterfly/Crab, which overshoot. The pattern gives the where, not the when; wait for confirmation at D.',
    setup: {
      cond: 'All five points formed with correct Fibonacci ratios; the PRZ reached with multiple Fib confluences.',
      entry: 'On a reversal confirmation candle at point D (pin/engulfing or momentum shift).',
      stop: 'Beyond the PRZ extreme (e.g. the 1.272/1.618 of XA for Butterfly/Crab).',
      target: 'First the C-point retracement, then the A-point; extended targets toward X on strong reversals.',
    },
    terms: ['PRZ', 'Fibonacci confluence', 'Gartley', 'Bat', 'Butterfly', 'D-point'],
    figcap: 'An X-A-B-C-D harmonic structure completing at the PRZ (point D), where the reversal entry is taken.',
  };
  D['price.harmonic'] = () => {
    const X = [40,60], A = [120,176], B = [190,110], Cp = [260,168], Dp = [330,128];
    const seg = (p, q) => line(p[0], p[1], q[0], q[1], 'df-line');
    const lbl = (p, s, dy) => dot(p[0], p[1], 3) + txt(p[0], p[1] + (dy || -8), s, 'df-tag-accent', 'middle');
    return svg(frame() + seg(X, A) + seg(A, B) + seg(B, Cp) + seg(Cp, Dp) +
      line(X[0], X[1], Dp[0], Dp[1], 'df-dash') +
      rect(310, 116, 40, 28, 'df-zone') + txt(330, 110, 'PRZ', 'df-tag-accent', 'middle') +
      lbl(X, 'X', -8) + lbl(A, 'A', 16) + lbl(B, 'B', -8) + lbl(Cp, 'C', 16) + lbl(Dp, 'D', -10));
  };

  // ── publish (merge so later methodology files/edits can extend) ──────────
  window.SynapseContent = Object.assign(window.SynapseContent || {}, C);
  window.SynapseDiagrams = Object.assign(window.SynapseDiagrams || {}, D);
})();
