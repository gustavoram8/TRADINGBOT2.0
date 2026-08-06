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
    // the horizontal level
    line(40, 90, 384, 90, 'df-dash-accent') +
    txt(44, 84, 'resistance', 'df-tag-accent', 'start') +
    // rally up to level — rejected (rejection 1)
    bar(60, 130, 170, 'up', 11, 124, 176) +
    bar(84, 96, 138, 'up', 11, 90, 144) +
    bar(108, 94, 118, 'down', 11, 92, 126) +
    arrow(108, 82, 108, 116, 'df-down-s') +
    // second approach — rejected again
    bar(148, 110, 160, 'up', 11, 104, 166) +
    bar(172, 94, 122, 'up', 11, 88, 128) +
    bar(196, 93, 112, 'down', 11, 91, 118) +
    arrow(196, 82, 196, 110, 'df-down-s') +
    // breakout — strong close above
    bar(236, 64, 100, 'up', 13, 58, 106) +
    txt(236, 50, 'break', 'df-tag-accent', 'middle') +
    // retest from above — support
    bar(276, 72, 100, 'down', 11, 66, 106) +
    bar(300, 88, 108, 'up', 11, 82, 114) +
    arrow(300, 76, 300, 62, 'df-up-s') +
    txt(310, 108, 'retest', 'df-tag', 'start') +
    // continue up
    bar(336, 50, 80, 'up', 11, 44, 86) +
    bar(360, 32, 62, 'up', 11, 26, 68) +
    txt(310, 130, 'now support', 'df-tag-accent', 'start')
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
    // HH HL staircase: [x, y, label, labelDY]
    const pts = [
      [40, 188, '', 0],
      [90, 120, 'HH', -10],
      [130, 148, 'HL', 14],
      [180, 88, 'HH', -10],
      [224, 116, 'HL', 14],
      [272, 60, 'HH', -10],
      [316, 88, 'HL', 14],
      [370, 34, 'HH', -10],
    ];
    let pth = 'M' + pts[0][0] + ' ' + pts[0][1];
    for (let i = 1; i < pts.length; i++) pth += ' L' + pts[i][0] + ' ' + pts[i][1];
    let marks = '';
    pts.forEach(p => {
      if (p[2]) marks += dot(p[0], p[1], 3) + txt(p[0], p[1] + p[3], p[2], 'df-tag-accent', 'middle');
    });
    return svg(frame() + path(pth, 'df-line-accent') + marks +
      arrow(350, 46, 378, 22, 'df-line-accent'));
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
    // large bullish candle at x=120
    candle(120, 28, 192, 148, 68, 36) +
    // leader lines + labels
    line(120, 28, 220, 28, 'df-grid') + txt(225, 32, 'high', 'df-label', 'start') +
    line(138, 68, 220, 68, 'df-grid') + txt(225, 72, 'close', 'df-label', 'start') +
    line(138, 148, 220, 148, 'df-grid') + txt(225, 152, 'open', 'df-label', 'start') +
    line(120, 192, 220, 192, 'df-grid') + txt(225, 196, 'low', 'df-label', 'start') +
    // wick labels with arrows
    txt(120, 18, 'upper wick', 'df-tag', 'middle') +
    arrow(120, 22, 120, 36, 'df-line-accent') +
    txt(120, 210, 'lower wick', 'df-tag', 'middle') +
    arrow(120, 204, 120, 188, 'df-line-accent') +
    // body label
    txt(66, 112, 'body', 'df-tag', 'middle') +
    arrow(84, 112, 100, 112, 'df-line-accent')
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
    // H&S: left shoulder peak=100, head peak=50, right shoulder peak=100, troughs at 140
    const pts = [[40,170],[75,170],[100,100],[130,140],[190,50],[250,140],[280,100],[310,140],[350,140]];
    let pth = 'M' + pts[0][0] + ' ' + pts[0][1];
    for (let i = 1; i < pts.length; i++) pth += ' L' + pts[i][0] + ' ' + pts[i][1];
    return svg(frame() +
      path(pth, 'df-line-accent') +
      // neckline through the two troughs at y=140
      line(80, 140, 370, 140, 'df-dash') +
      txt(355, 134, 'neckline', 'df-tag', 'end') +
      // labels
      txt(100, 90, 'L sh', 'df-tag', 'middle') +
      txt(190, 40, 'head', 'df-tag-accent', 'middle') +
      txt(280, 90, 'R sh', 'df-tag', 'middle') +
      // neckline break down
      arrow(350, 142, 370, 190, 'df-down-s'));
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
    // demand zone rect over the base
    rect(40, 148, 110, 30, 'df-zone-up') +
    txt(95, 142, 'demand zone', 'df-tag', 'end') +
    // tight consolidation base
    bar(58, 154, 172, 'down', 10, 150, 176) +
    bar(80, 152, 170, 'up', 10, 148, 174) +
    bar(102, 155, 172, 'down', 10, 151, 176) +
    bar(124, 150, 170, 'up', 10, 147, 174) +
    // explosive rally
    bar(158, 110, 154, 'up', 12, 104, 158) +
    bar(184, 74, 116, 'up', 12, 68, 120) +
    bar(210, 42, 80, 'up', 12, 36, 84) +
    arrow(170, 168, 220, 54, 'df-up-s') +
    // return to zone and bounce
    bar(280, 48, 96, 'down', 12, 42, 102) +
    bar(308, 108, 158, 'down', 12, 102, 164) +
    bar(336, 136, 168, 'up', 12, 130, 174) +
    arrow(348, 158, 348, 120, 'df-up-s')
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
    // support line
    line(40, 138, 384, 138, 'df-dash-accent') +
    txt(376, 134, 'support', 'df-tag-accent', 'end') +
    // some down candles approaching support
    bar(70, 80, 118, 'down', 12, 74, 124) +
    bar(100, 94, 130, 'down', 12, 88, 136) +
    // pin bar: tiny body near top, long lower wick piercing support
    candle(140, 88, 188, 112, 98, 14) +
    txt(140, 78, 'pin bar', 'df-tag-accent', 'middle') +
    // stop label at wick bottom
    txt(156, 194, 'stop', 'df-tag', 'start') +
    arrow(152, 190, 144, 184, 'df-line-accent') +
    // UP arrow indicating reversal
    arrow(140, 174, 140, 116, 'df-up-s') +
    // continuation up
    bar(184, 76, 116, 'up', 12, 70, 122) +
    bar(216, 52, 90, 'up', 12, 46, 96) +
    bar(248, 30, 64, 'up', 12, 24, 70) +
    bar(280, 14, 44, 'up', 12, 10, 50)
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
    // support line
    line(40, 162, 384, 162, 'df-dash') +
    txt(44, 156, 'support', 'df-tag', 'start') +
    // downtrend approaching support
    bar(65, 90, 128, 'down', 11, 84, 134) +
    bar(90, 108, 148, 'down', 11, 102, 154) +
    bar(115, 122, 158, 'down', 11, 116, 164) +
    // small bearish candle
    candle(152, 138, 168, 158, 144, 13) +
    txt(152, 130, 'small', 'df-tag', 'middle') +
    // large bullish engulfing candle — body wider and taller
    candle(190, 126, 172, 166, 124, 22) +
    txt(215, 118, 'engulfs', 'df-tag-accent', 'start') +
    arrow(212, 126, 205, 136, 'df-line-accent') +
    // continuation up
    bar(232, 96, 136, 'up', 12, 90, 142) +
    bar(264, 66, 106, 'up', 12, 60, 112) +
    bar(296, 42, 80, 'up', 12, 36, 86) +
    bar(328, 22, 56, 'up', 12, 16, 62)
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
    // the resistance level
    line(40, 100, 384, 100, 'df-dash-accent') +
    txt(376, 96, 'level', 'df-tag-accent', 'end') +
    // consolidation below level
    bar(60, 108, 148, 'up', 11, 102, 154) +
    bar(84, 118, 158, 'down', 11, 112, 164) +
    bar(108, 110, 150, 'up', 11, 104, 156) +
    // strong breakout candle
    bar(148, 60, 108, 'up', 13, 54, 112) +
    txt(148, 48, 'break', 'df-tag-accent', 'middle') +
    bar(176, 46, 76, 'up', 11, 40, 82) +
    // retest: price pulls back to level from above
    bar(216, 56, 88, 'down', 11, 50, 94) +
    bar(244, 80, 108, 'down', 11, 74, 114) +
    dot(244, 100, 3.5) +
    txt(258, 114, 'retest', 'df-tag', 'start') +
    arrow(258, 110, 252, 102, 'df-line-accent') +
    // bounce and continue up
    bar(280, 68, 104, 'up', 11, 62, 110) +
    bar(308, 44, 80, 'up', 11, 38, 86) +
    bar(336, 24, 58, 'up', 11, 18, 64)
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
    const X = [44, 56], A = [120, 178], B = [196, 108], Cp = [268, 162], Dp = [336, 120];
    const seg = (p, q, cls) => line(p[0], p[1], q[0], q[1], cls || 'df-line');
    const lbl = (p, s, dy) => dot(p[0], p[1], 3.5) + txt(p[0], p[1] + dy, s, 'df-tag-accent', 'middle');
    return svg(frame() +
      seg(X, A) + seg(A, B) + seg(B, Cp) + seg(Cp, Dp) +
      // XD reference line dashed
      line(X[0], X[1], Dp[0], Dp[1], 'df-dash') +
      // PRZ zone at D
      rect(318, 108, 36, 28, 'df-zone') +
      txt(336, 102, 'PRZ', 'df-tag-accent', 'middle') +
      // point labels
      lbl(X, 'X', -10) +
      lbl(A, 'A', 14) +
      lbl(B, 'B', -10) +
      lbl(Cp, 'C', 14) +
      lbl(Dp, 'D', -10) +
      // reversal arrow up at D
      arrow(336, 136, 336, 108, 'df-up-s'));
  };

  // ══════════════════════════════════════════════════════════════════════
  // METHODOLOGY 2 — TECHNICAL ANALYSIS
  // ══════════════════════════════════════════════════════════════════════

  C['technical.moving-averages'] = {
    lead: 'A moving average smooths price into a single flowing line, filtering noise to reveal the underlying trend — and acting as dynamic support and resistance as price travels.',
    body: 'Different calculations weight the data differently: the SMA treats all periods equally, the EMA favours recent price, and VWAP weights by volume to mark the session\'s true institutional cost basis.',
    mechanics: [
      { term: 'SMA vs EMA', text: 'SMA reacts slower but cleaner; EMA hugs recent price and turns faster. Common periods: 20, 50, 200.' },
      { term: 'The 200-day', text: 'The 200 SMA is watched by virtually every large fund — breaks across it on volume are genuine structural events.' },
      { term: 'VWAP', text: 'Volume-weighted, session-reset — the real intraday institutional benchmark; price above = bullish bias, below = bearish.' },
      { term: 'Dynamic S/R', text: 'In trends, price repeatedly bounces off the 20 EMA (support up-trends, resistance down-trends).' },
    ],
    mistake: 'Every MA lags by definition — it reacts to price, it never predicts it. Treating a cross as a forecast leads to chronically late entries. And the "right" period is contextual: the 20 EMA is great support in a trend but meaningless in a range.',
    terms: ['SMA', 'EMA', 'VWAP', '200-day', 'Dynamic S/R', 'Lag'],
    figcap: 'Price trends upward while repeatedly using the moving average as dynamic support on each pullback.',
  };
  D['technical.moving-averages'] = () => {
    // price zigzags up, MA is smoother below it
    const price = 'M40 184 L70 158 L95 174 L125 136 L155 154 L190 106 L225 122 L260 78 L295 96 L330 56 L360 72';
    const ma    = 'M40 190 L100 172 L170 144 L240 112 L310 80 L360 62';
    // bounce dots where price touches MA
    const bx = [[95,174],[155,154],[225,122]];
    let dots = '';
    bx.forEach(b => { dots += dot(b[0], b[1], 3.5); });
    return svg(frame() +
      path(ma, 'df-line-accent') +
      path(price, 'df-line') +
      dots +
      txt(368, 58, 'MA', 'df-tag-accent', 'end') +
      txt(155, 168, 'bounce', 'df-tag', 'middle') +
      arrow(160, 164, 158, 156, 'df-line-accent'));
  };

  C['technical.rsi'] = {
    lead: 'The RSI is a 0–100 momentum oscillator measuring the speed and size of recent price changes — most powerful not as a crude overbought/oversold gauge but as a reader of momentum, divergence, and trend regime.',
    body: 'Wilder set 70 as overbought and 30 as oversold, but in real trends those thresholds mislead constantly. The deeper signal is the range RSI lives in.',
    mechanics: [
      { term: 'Formula', text: 'RSI = 100 − 100/(1+RS), where RS = average gain ÷ average loss over the lookback (default 14).' },
      { term: 'Trend regime', text: 'Uptrends tend to hold RSI between 40–80, downtrends 20–60 — the range itself tells you the regime (Cardwell).' },
      { term: 'Divergence', text: 'Price makes a new extreme but RSI does not — a warning that momentum is fading beneath the move.' },
      { term: 'Centerline (50)', text: 'Crossing above 50 = positive momentum shift; below 50 = negative — a clean trend filter.' },
    ],
    mistake: 'The 70/30 levels only work in ranges. In a strong trend, RSI can sit above 70 for weeks — shorting every "overbought" reading in an uptrend is the classic way to get run over. Read the regime before the level.',
    terms: ['Momentum oscillator', 'Overbought / oversold', 'Divergence', 'Centerline', 'Trend regime', 'Lookback'],
    figcap: 'The RSI oscillator with the 70/30 bands; it can ride along overbought through a strong trend.',
  };
  D['technical.rsi'] = () => {
    const top = 30, bot = 200, y = v => bot - (v / 100) * (bot - top);
    // curve: rises to overbought zone (~75), stays elevated, then dips toward 35
    const curve = 'M40 ' + y(38) + ' C80 ' + y(65) + ' 120 ' + y(78) + ' 170 ' + y(74) +
                  ' C220 ' + y(70) + ' 270 ' + y(42) + ' 372 ' + y(36);
    return svg(
      line(34, top, 34, bot, 'df-axis') + line(34, bot, 384, bot, 'df-axis') +
      // overbought zone tint
      rect(34, y(100), 350, y(70) - y(100), 'df-zone-down') +
      // oversold zone tint
      rect(34, y(30), 350, y(0) - y(30), 'df-zone-up') +
      line(34, y(70), 384, y(70), 'df-dash') + txt(376, y(70) - 4, '70', 'df-tag', 'end') +
      line(34, y(30), 384, y(30), 'df-dash') + txt(376, y(30) + 10, '30', 'df-tag', 'end') +
      line(34, y(50), 384, y(50), 'df-grid') + txt(376, y(50) - 4, '50', 'df-tag', 'end') +
      path(curve, 'df-line-accent') +
      txt(44, top + 10, 'RSI', 'df-tag-accent', 'start'));
  };

  C['technical.macd'] = {
    lead: 'MACD blends trend and momentum from two EMAs into three parts — the MACD line, its signal line, and a histogram — revealing direction, strength, and turning points at once.',
    body: 'Built entirely from lagging averages, it stays one of the most versatile indicators because the histogram exposes momentum shifts before the lines themselves cross.',
    mechanics: [
      { term: 'MACD line', text: '12-EMA minus 26-EMA. Positive = bullish momentum, negative = bearish; its slope matters as much as its level.' },
      { term: 'Signal line', text: '9-EMA of the MACD line. A cross above = bullish trigger, below = bearish.' },
      { term: 'Histogram', text: 'MACD minus signal. Growing bars = momentum building; shrinking bars warn of an upcoming cross.' },
      { term: 'Zero line', text: 'Crossing zero means the 12-EMA crossed the 26-EMA — slower but structurally more significant than a signal cross.' },
    ],
    mistake: 'In sideways markets MACD fires endless signal-line crosses that whipsaw you. The histogram is the underused tip: shrinking bars while price still rises often precede the cross by several candles — earlier, lower-risk warning. Always filter with trend context.',
    terms: ['MACD line', 'Signal line', 'Histogram', 'Zero line', 'Divergence', 'Crossover'],
    figcap: 'MACD and signal lines crossing above a histogram whose bars flip from negative to positive.',
  };
  D['technical.macd'] = () => {
    const mid = 110;
    // histogram: 4 red bars then 4 green bars
    const hv = [-28, -36, -30, -14, 10, 22, 32, 20];
    let hist = '';
    hv.forEach((v, i) => {
      const x = 52 + i * 40;
      hist += rect(x - 10, v >= 0 ? mid - v : mid, 20, Math.abs(v), v >= 0 ? 'df-up' : 'df-down');
    });
    // cross happens between bar 4 and 5 (x≈212)
    const macd = 'M40 172 C100 158 140 138 184 130 C220 124 280 104 372 88';
    const sig  = 'M40 160 C100 154 148 146 196 138 C240 130 300 116 372 100';
    return svg(
      line(34, mid, 384, mid, 'df-axis') +
      txt(38, mid - 4, '0', 'df-tag', 'start') +
      hist +
      path(sig, 'df-line') +
      path(macd, 'df-line-accent') +
      dot(212, 132, 3.5) +
      txt(220, 124, 'cross', 'df-tag-accent', 'start') +
      txt(44, 30, 'MACD', 'df-tag-accent', 'start') +
      txt(44, 44, '—— signal', 'df-tag', 'start'));
  };

  C['technical.bollinger'] = {
    lead: 'Bollinger Bands wrap a 20-period average in two bands set two standard deviations away — a volatility envelope that expands when markets move and contracts when they rest.',
    body: 'They are first a volatility tool, not a reversal tool: the most actionable pattern is the squeeze, where contraction precedes expansion.',
    mechanics: [
      { term: 'Construction', text: 'Upper/lower = 20 SMA ± 2σ; ~95% of recent price sits inside, so band touches are statistically unusual.' },
      { term: 'Squeeze', text: 'Bands narrowing to a multi-month low signal coiled energy and an imminent breakout — direction not yet decided.' },
      { term: 'Walking the bands', text: 'In strong trends price rides the upper (or lower) band for long stretches — that\'s continuation, not reversal.' },
      { term: '%B and Bandwidth', text: '%B locates price within the bands; Bandwidth quantifies the squeeze — its lowest readings precede the biggest moves.' },
    ],
    mistake: 'Fading every band touch expecting mean reversion is the cardinal error — in a trend, touching the band is confirmation, not a turn. Assess trend context first. The middle band (20 SMA) is often better dynamic support than the outer bands.',
    terms: ['Standard deviation', 'Squeeze', '%B', 'Bandwidth', 'Walking the bands', 'Mean reversion'],
    figcap: 'Bands contract into a squeeze, then expand violently as price breaks out and walks the upper band.',
  };
  D['technical.bollinger'] = () => {
    // bands pinch in the middle (x≈160-220), then widen on right
    const upper = 'M40 60 C90 72 130 96 165 104 C200 110 240 86 290 54 C320 36 350 28 372 22';
    const lower = 'M40 160 C90 148 130 124 165 116 C200 110 240 134 290 166 C320 184 350 192 372 198';
    const mid   = 'M40 110 C120 110 160 110 200 110 C240 110 300 110 372 110';
    // price walking upper band after breakout
    const price = 'M40 120 L75 108 L110 132 L145 114 L175 112 L205 108 L235 88 L260 68 L290 50 L320 36 L352 24';
    return svg(frame() +
      path(upper, 'df-dash-accent') + path(lower, 'df-dash-accent') + path(mid, 'df-line') +
      // squeeze zone rect
      rect(148, 100, 60, 20, 'df-zone') +
      txt(178, 94, 'squeeze', 'df-tag', 'middle') +
      path(price, 'df-line-accent') +
      arrow(230, 88, 256, 64, 'df-up-s'));
  };

  C['technical.volume'] = {
    lead: 'Volume is the most direct measure of participation and conviction. Volume Profile sharpens it by distributing trades across price levels instead of time, exposing where the real auction happened.',
    body: 'It reveals the institutional footprint candles alone cannot: institutions must transact in size, leaving detectable signatures at specific prices.',
    mechanics: [
      { term: 'Point of Control', text: 'The price with the most traded volume — a magnet price tends to return to; the "fairest" agreed price.' },
      { term: 'Value Area', text: 'The range holding 70% of volume (VAH–VAL); price outside it is "unfair" and tends to revert.' },
      { term: 'High/low volume nodes', text: 'Price stalls at HVNs (thick volume) and rips through LVNs (thin volume) with little friction.' },
      { term: 'Volume in trends', text: 'Healthy trends show higher volume on with-trend bars; a climax bar (huge volume, little progress) warns of exhaustion.' },
    ],
    mistake: 'Many traders ignore Volume Profile entirely and miss the institutional footprint. And the POC is not an automatic turning point — in strong trends it gets broken through; context decides whether it holds or breaks.',
    terms: ['POC', 'Value Area', 'VAH / VAL', 'HVN / LVN', 'Volume climax', 'Volume Profile'],
    figcap: 'Rising price on healthy volume, then a climax bar — outsized volume with little progress — warning of exhaustion.',
  };
  D['technical.volume'] = () => {
    // Two-panel: price top (y 24-142), volume bottom (y 148-196)
    // [x, bodyTop, bodyBot, dir, volH]
    const data = [
      [55, 96, 118, 'up', 18],
      [82, 84, 108, 'up', 24],
      [109, 90, 114, 'down', 16],
      [136, 68, 96, 'up', 28],
      [163, 52, 82, 'up', 32],
      [190, 38, 70, 'up', 26],
      [217, 44, 76, 'down', 20],
      [244, 30, 62, 'up', 24],
      // climax bar: large red with big volume
      [286, 28, 136, 'down', 44],
    ];
    const divY = 144, volBase = 194;
    const candles = data.map(d => bar(d[0], d[1], d[2], d[3], 12)).join('');
    const vols = data.map((d, i) => {
      const cls = i === data.length - 1 ? 'df-down' : (d[3] === 'up' ? 'df-up' : 'df-down');
      const h = Math.min(d[4], volBase - divY - 2);
      return rect(d[0] - 8, volBase - h, 16, h, cls);
    }).join('');
    return svg(
      line(34, divY, 384, divY, 'df-axis') +
      line(34, 20, 34, divY, 'df-axis') +
      line(34, volBase, 384, volBase, 'df-axis') +
      candles + vols +
      txt(286, 22, 'climax', 'df-tag-down', 'middle') +
      txt(44, 188, 'volume', 'df-tag', 'start'));
  };

  C['technical.ma-cross'] = {
    type: 't',
    lead: 'An MA crossover fires when a faster average crosses a slower one: the golden cross (fast above slow) hints uptrend, the death cross (fast below slow) hints downtrend.',
    body: 'It is among the simplest signals in technical analysis — and among the most overused, because it always confirms the move after it has begun.',
    mechanics: [
      { term: 'Golden / death cross', text: 'Classic = 50 SMA crossing the 200 SMA; faster swing versions use 20/50 EMA, intraday 8/21 EMA.' },
      { term: 'Lag', text: 'The cross prints after the trend starts — by the time the slow MA confirms, much of the first move is gone.' },
      { term: 'Whipsaws', text: 'In ranges the two MAs weave back and forth, producing cross after cross that cancel each other out.' },
      { term: 'Filters', text: 'Require ADX > 25, the long MA sloping with the cross, or wait for a pullback to the fast MA before entering.' },
    ],
    mistake: 'The cross is mostly a lagging confirmation of structure that price showed weeks earlier — structure traders are usually in before it. Treat it as confirmation, not prediction, and never trade it in a known-ranging market.',
    setup: {
      cond: 'ADX > 25 confirming a trend; long-term MA sloping with the cross; price the right side of the long MA.',
      entry: 'On the candle after the confirmed cross, or the first pullback to the faster MA.',
      stop: 'Below the slower MA (longs) / above it (shorts), or beyond the recent swing.',
      target: 'Next key level; trail the faster MA as the trend develops.',
    },
    terms: ['Golden cross', 'Death cross', 'Lag', 'Whipsaw', 'ADX filter', 'Pullback entry'],
    figcap: 'A golden cross: the fast moving average crosses up through the slow one, marking the trend trigger.',
  };
  D['technical.ma-cross'] = () => {
    // fast starts below slow, crosses above at ~x=200, then diverges
    const fast = 'M40 168 C90 160 140 148 180 130 C220 112 280 76 372 44';
    const slow = 'M40 140 C100 140 160 138 210 132 C260 126 320 118 372 108';
    // cross point approximately at x=196, y=132
    return svg(frame() +
      path(slow, 'df-line') +
      path(fast, 'df-line-accent') +
      dot(196, 132, 4.5) +
      txt(196, 150, 'golden cross', 'df-tag-accent', 'middle') +
      txt(372, 40, 'fast', 'df-tag-accent', 'end') +
      txt(372, 116, 'slow', 'df-tag', 'end'));
  };

  C['technical.rsi-divergence'] = {
    type: 't',
    lead: 'RSI divergence is when price and momentum disagree — price prints a new extreme but RSI does not — signalling the move is running on fumes.',
    body: 'Regular divergence warns of reversal; hidden divergence, the underused cousin, signals trend continuation on pullbacks.',
    mechanics: [
      { term: 'Regular bearish', text: 'Price higher high, RSI lower high — buying pressure fading near a top.' },
      { term: 'Regular bullish', text: 'Price lower low, RSI higher low — selling pressure fading near a bottom.' },
      { term: 'Hidden divergence', text: 'In an uptrend, price higher low while RSI lower low = continuation; the best in-trend entries with great R:R.' },
      { term: 'Confirmation', text: 'Never trade divergence alone — require a structure break or reversal candle at the divergence point.' },
    ],
    mistake: 'In strong trends, regular bearish divergence can appear repeatedly while price keeps climbing — shorting each one bleeds you out. Divergence on the daily carries far more weight than on the 15-minute, where noise dominates.',
    setup: {
      cond: 'Clear divergence at a significant level; trend context aligned (regular = reversal, hidden = continuation).',
      entry: 'On a confirmation candle or a short-term structure break after the divergence forms.',
      stop: 'Beyond the swing extreme that created the divergence.',
      target: 'Nearest key level in the new direction; first target at the divergence\'s origin.',
    },
    terms: ['Regular divergence', 'Hidden divergence', 'Momentum', 'Confirmation candle', 'Trend context'],
    figcap: 'Price makes a higher high while RSI makes a lower high — bearish regular divergence warning of a top.',
  };
  D['technical.rsi-divergence'] = () => {
    // price panel top, rsi panel bottom
    const pPrice = 'M40 120 L80 90 L120 110 L170 64 L210 96 L250 70';
    const rTop = 60, rBot = 150, ry = v => rBot - (v / 100) * (rBot - rTop) * 0.9;
    const rsiCurve = 'M40 ' + (rBot) + ' L80 ' + ry(82) + ' L120 ' + ry(55) + ' L170 ' + ry(72) + ' L210 ' + ry(50) + ' L250 ' + ry(60);
    return svg(
      // price section
      path(pPrice, 'df-line-accent') +
      dot(80, 90, 3) + dot(170, 64, 3) + line(80, 88, 170, 62, 'df-dash') + txt(125, 52, 'higher high', 'df-tag', 'middle') +
      line(40, 158, 384, 158, 'df-axis') +
      // rsi section
      path(rsiCurve, 'df-line') + txt(40, 176, 'RSI', 'df-tag', 'start') +
      dot(80, ry(82), 3) + dot(170, ry(72), 3) + line(80, ry(82), 170, ry(72), 'df-dash-accent') +
      txt(125, ry(90), 'lower high', 'df-tag-accent', 'middle') +
      arrow(250, 78, 280, 120, 'df-line-down')
    );
  };

  C['technical.macd-cross'] = {
    type: 't',
    lead: 'A MACD cross fires when the MACD line crosses its signal line (frequent, early) or the zero line (rarer, more significant) — momentum entries that need context to be worth taking.',
    mechanics: [
      { term: 'Signal cross', text: 'MACD above signal = bullish; most reliable when it happens below zero recovering from oversold momentum.' },
      { term: 'Zero cross', text: 'MACD through zero confirms the 12/26 EMA cross — slower, more confirmed; better as trend confirmation than trigger.' },
      { term: 'Histogram lead', text: 'Shrinking histogram bars precede the signal cross — the earliest (if noisiest) actionable hint.' },
      { term: 'Reliability', text: 'Zero cross > signal cross in trend context > histogram reversal (earliest but most prone to noise).' },
    ],
    mistake: 'Crosses near the zero line, with no momentum, are pure noise. In ranges they fire continuously with no follow-through. The best crosses happen at MACD extremes beginning to reverse — pair with RSI moving through 50 for confirmation.',
    setup: {
      cond: 'Clear higher-timeframe trend; signal cross after MACD was at an extreme; ideally RSI confirming and price at a key level.',
      entry: 'On the candle after the confirmed cross, or on histogram-slope reversal for an earlier fill.',
      stop: 'Below the recent swing low (longs) / above the swing high (shorts).',
      target: 'Next structural level; trail as the trend develops.',
    },
    terms: ['Signal cross', 'Zero cross', 'Histogram', 'MACD extreme', 'Trend filter', 'Whipsaw'],
    figcap: 'The MACD line crossing up through the signal line as the histogram flips from red to green.',
  };
  D['technical.macd-cross'] = () => {
    const mid = 140; let hist = '';
    const hv = [-22,-26,-20,-8,6,18,26];
    hv.forEach((v, i) => { const x = 60 + i * 44; hist += rect(x - 9, v >= 0 ? mid - v : mid, 18, Math.abs(v), v >= 0 ? 'df-up' : 'df-down'); });
    const macd = 'M40 176 C120 156 170 132 220 124 C280 114 340 96 372 86';
    const sig  = 'M40 162 C120 154 180 140 240 132 C300 124 350 108 372 100';
    return svg(line(34, mid, 384, mid, 'df-axis') + hist + path(sig, 'df-line') + path(macd, 'df-line-accent') +
      dot(214, 126, 3.5) + txt(222, 116, 'cross', 'df-tag-accent', 'start'));
  };

  C['technical.squeeze-break'] = {
    type: 't',
    lead: 'The Bollinger squeeze break trades the statistical truth that very low volatility precedes explosive moves: when the bands compress to a multi-month low, energy is coiling for a breakout.',
    mechanics: [
      { term: 'Squeeze ID', text: 'Bandwidth at a 6-month low — or, in the TTM Squeeze, Bollinger Bands contracting inside the Keltner Channels.' },
      { term: 'No built-in direction', text: 'The squeeze says a move is coming, not which way; the break + momentum (MACD histogram, %B) chooses the side.' },
      { term: 'Entry', text: 'First candle closing clearly beyond the squeeze range, ideally with %B breaching 1.0 (up) or 0.0 (down).' },
      { term: 'Volume', text: 'A breakout on weak volume often fails back inside the range — volume expansion is the key filter.' },
    ],
    mistake: 'Entering the moment Bandwidth hits a low — before any actual break — leaves you stuck as the squeeze drags on for more bars. And a squeeze right before scheduled news is often just positioning that reverts after the release.',
    setup: {
      cond: 'Bandwidth at a multi-month low (or BB inside Keltner); a clear directional break with momentum confirmation.',
      entry: 'On the close of the first candle breaking the squeeze range; %B > 1.0 (long) / < 0.0 (short).',
      stop: 'Below the squeeze range low (long) / above its high (short), or beyond the middle band.',
      target: '1–2× the squeeze-range height; trail with the 20 SMA.',
    },
    terms: ['Squeeze', 'Bandwidth', 'TTM Squeeze', 'Keltner Channels', '%B', 'Volatility expansion'],
    figcap: 'Bands pinch into a tight squeeze, then expand sharply as price breaks out with momentum.',
  };
  D['technical.squeeze-break'] = () => {
    const upper = 'M40 80 C120 96 170 108 210 108 C250 108 300 80 372 40';
    const lower = 'M40 140 C120 124 170 112 210 112 C250 112 300 140 372 180';
    const price = 'M40 112 L70 104 L100 116 L130 108 L165 112 L200 110 L235 96 L270 72 L305 60 L345 44';
    return svg(frame() + path(upper, 'df-dash-accent') + path(lower, 'df-dash-accent') +
      rect(190, 106, 40, 12, 'df-zone') + txt(210, 132, 'squeeze', 'df-tag', 'middle') +
      path(price, 'df-line-accent') + arrow(270, 110, 305, 64, 'df-line-accent'));
  };

  // ══════════════════════════════════════════════════════════════════════
  // METHODOLOGY 3 — SMC / ICT
  // ══════════════════════════════════════════════════════════════════════

  C['smc.wyckoff-roots'] = {
    lead: 'Wyckoff\'s 1930s framework is the bedrock beneath modern smart-money trading: a single large operator — the "Composite Man" — systematically accumulates and distributes through engineered price cycles you can learn to read.',
    body: 'Understanding Wyckoff gives you the why behind every ICT concept — order blocks are his demand zones, liquidity sweeps are his springs, BOS is his sign of strength.',
    mechanics: [
      { term: 'The Composite Man', text: 'Think like one rational large operator orchestrating the move, rather than reacting emotionally to price.' },
      { term: 'Three Laws', text: 'Supply/Demand; Cause & Effect (range size sets the move size); Effort vs Result (volume should match price progress).' },
      { term: 'Accumulation phases', text: 'A (selling stops) → B (cause-building) → C (the Spring) → D (Sign of Strength) → E (markup begins).' },
      { term: 'Spring & Upthrust', text: 'The Spring is a false break below range support on low volume — the optimal long; the UTAD is its mirror at tops.' },
    ],
    mistake: 'Volume is inseparable from Wyckoff — a Spring on high volume is suspect (real selling), a Spring on low volume is ideal (no supply). Modern algos also compress these phases: what took weeks in 1930 can complete in hours on a 5-minute chart.',
    terms: ['Composite Man', 'Accumulation', 'Distribution', 'Spring', 'Sign of Strength', 'Cause & Effect'],
    figcap: 'A Wyckoff accumulation range: a spring dips below support, then markup begins out of the range.',
  };
  D['smc.wyckoff-roots'] = () => {
    const sup = 150, res = 80;
    const rng = 'M40 120 L70 96 L100 140 L130 100 L160 144 L190 104 L210 150';
    const spring = 'M210 150 L228 178 L246 138';  // spring below support
    const markup = 'M246 138 L280 100 L310 70 L345 44 L372 34';
    return svg(frame() +
      line(40, sup, 372, sup, 'df-dash') + txt(44, sup - 5, 'support', 'df-tag', 'start') +
      line(40, res, 246, res, 'df-dash') + txt(44, res - 5, 'resistance', 'df-tag', 'start') +
      path(rng, 'df-line') + path(spring, 'df-line-accent') + path(markup, 'df-line-accent') +
      dot(228, 178, 3.5) + txt(228, 194, 'spring', 'df-tag-accent', 'middle') +
      arrow(310, 70, 345, 44, 'df-line-accent') + txt(330, 130, 'accumulation', 'df-tag', 'middle'));
  };

  C['smc.market-structure'] = {
    lead: 'In SMC, structure is the sequence of swings that defines trend. A Break of Structure (BOS) confirms continuation; a Change of Character (ChoCH) is the first break of the opposing extreme — the early warning of reversal.',
    mechanics: [
      { term: 'BOS', text: 'Price closes beyond the prior structural high (uptrend) or low (downtrend) — the trend casting a vote to continue.' },
      { term: 'ChoCH', text: 'The first time price breaks the opposing swing (e.g. a higher low in an uptrend) — control is shifting; a warning, not yet a reversal.' },
      { term: 'Internal vs external', text: 'External = the headline swings; internal = the smaller swings inside each leg, used to time entries on lower timeframes.' },
      { term: 'MSS', text: 'A Market Structure Shift is ICT\'s ChoCH after a liquidity sweep + displacement — confirmation the sweep mattered.' },
    ],
    mistake: 'The same candle "breaking a high" can be a BOS or a ChoCH depending on whether it broke internal or external structure — context decides. Mark only significant swings; labelling every micro-wiggle turns the chart to chaos. And HTF structure always overrides LTF.',
    terms: ['BOS', 'ChoCH', 'MSS', 'Internal structure', 'External structure', 'Displacement'],
    figcap: 'An uptrend of BOS continuations, then a ChoCH as price breaks the last higher low — reversal warning.',
  };
  D['smc.market-structure'] = () => {
    const pts = [[40,170],[85,110],[120,140],[165,80],[205,116],[250,56],[290,120],[330,150],[372,176]];
    let pth = 'M' + pts[0][0] + ' ' + pts[0][1];
    for (let i = 1; i < pts.length; i++) pth += ' L' + pts[i][0] + ' ' + pts[i][1];
    return svg(frame() + path(pth, 'df-line-accent') +
      line(85, 110, 230, 110, 'df-dash') + txt(150, 104, 'BOS', 'df-tag-accent', 'middle') +
      line(205, 116, 320, 116, 'df-dash') + txt(300, 110, 'ChoCH', 'df-tag-down', 'middle') +
      arrow(290, 120, 330, 150, 'df-line-down'));
  };

  C['smc.order-blocks'] = {
    lead: 'An order block is the last opposing candle before an impulsive institutional move — the final accumulation (or distribution) footprint where unfilled orders rest until price returns.',
    body: 'A bullish OB is the last down candle before a rally; a bearish OB is the last up candle before a sell-off. Price tends to react when it "mitigates" that zone.',
    mechanics: [
      { term: 'Identification', text: 'Find the last opposing candle right before a displacement move — its high-to-low range is the OB zone.' },
      { term: 'Validation', text: 'The move away must be impulsive (large, clean, leaving FVGs) and produce a BOS — that confirms the OB.' },
      { term: 'Mitigation', text: 'When price returns, it fills resting orders; the proximal edge is the entry zone, the distal edge the stop reference.' },
      { term: 'Breaker block', text: 'A failed OB (price closes through its distal edge) flips polarity and acts on the opposite side on the next return.' },
    ],
    mistake: 'Beginners mark every candle before a move as an OB — it must be the last opposing candle, color non-negotiable. And the OB alone is not enough: the best ones follow a liquidity sweep, produce a displacement with FVGs, and sit in the right premium/discount area.',
    terms: ['Last opposing candle', 'Displacement', 'Mitigation', 'Proximal / distal', 'Breaker block', 'BOS'],
    figcap: 'The last down candle before a rally is marked as a bullish order block; price returns to mitigate it.',
  };
  D['smc.order-blocks'] = () => svg(
    frame() +
    bar(70, 84, 120, 'down', 12, 78, 126) +
    bar(100, 100, 140, 'down', 12, 94, 146) +
    // the order block: last down candle before rally
    rect(120, 116, 130, 28, 'df-zone') + txt(126, 110, 'order block', 'df-tag-accent', 'start') +
    candle(132, 118, 146, 142, 122, 13) +
    // displacement up
    bar(168, 80, 124, 'up', 12, 74, 128) +
    bar(198, 50, 90, 'up', 12, 44, 94) +
    arrow(150, 150, 210, 60, 'df-line-up') +
    // return to mitigate
    bar(280, 50, 96, 'down', 12, 44, 102) +
    bar(310, 100, 134, 'down', 12, 94, 138) +
    arrow(322, 150, 330, 126, 'df-line-up') + txt(330, 168, 'mitigation', 'df-tag', 'middle')
  );

  C['smc.fair-value-gaps'] = {
    lead: 'A Fair Value Gap is a three-candle imbalance: price moves so fast that candle 3\'s wick never reaches candle 1\'s wick, leaving a one-sided zone the market is drawn back to "rebalance".',
    mechanics: [
      { term: 'Bullish FVG', text: 'In an up sequence, candle 3\'s low sits above candle 1\'s high — that gap acts as support on the return.' },
      { term: 'Consequent Encroachment', text: 'The 50% midpoint of the gap — often the most reactive level and the refined entry target.' },
      { term: 'Fill dynamics', text: 'Strong trends reach only the CE before resuming; weaker ones fill the whole gap before reacting.' },
      { term: 'Inverse FVG', text: 'A bullish FVG broken downward flips to resistance on the return (and vice versa).' },
    ],
    mistake: 'Not every gap is tradable — an FVG from a high-volume displacement after a sweep is gold; one from a dead overnight session is noise. And FVGs deep inside a powerful trend may never fill — treating all of them as guaranteed fill targets fades you into freight trains.',
    terms: ['Three-candle imbalance', 'Consequent Encroachment', '50% midpoint', 'Inverse FVG', 'Rebalancing', 'Displacement'],
    figcap: 'Three candles leave a bullish FVG (the shaded gap); price later returns to its 50% midpoint to rebalance.',
  };
  D['smc.fair-value-gaps'] = () => svg(
    frame() +
    candle(90, 150, 178, 172, 158, 16) +
    candle(140, 96, 150, 142, 104, 16) +
    candle(190, 58, 104, 96, 66, 16) +
    // FVG = gap between candle1 high (~150) and candle3 low (~104)
    rect(70, 108, 240, 40, 'df-zone') + txt(316, 130, 'FVG', 'df-tag-accent', 'start') +
    line(70, 128, 310, 128, 'df-dash-accent') + txt(316, 124, 'CE', 'df-tag-accent', 'start') +
    // return to fill CE
    bar(280, 58, 96, 'down', 13, 52, 102) +
    bar(310, 100, 126, 'up', 13, 94, 132) +
    arrow(322, 150, 330, 128, 'df-line-accent')
  );

  C['smc.liquidity'] = {
    lead: 'Liquidity is the pools of resting orders — stops and pending entries — clustered at obvious levels. Institutions drive price to those pools to fill their size, using predictable retail behaviour as fuel.',
    mechanics: [
      { term: 'Buy-side (BSL)', text: 'Rests above swing highs and equal highs (short stops + breakout buys). Price runs up to sell into it.' },
      { term: 'Sell-side (SSL)', text: 'Rests below swing lows and equal lows (long stops + breakdown sells). Price runs down to buy from it.' },
      { term: 'Equal highs/lows', text: 'Two identical extremes concentrate stops just beyond — the market almost always sweeps them before the real move.' },
      { term: 'Stop run', text: 'Price spikes past the level, triggers the stops, then reverses hard — often on a displacement candle.' },
    ],
    mistake: 'Placing stops at the obvious level (just past a key high/low) puts them exactly where stop hunts aim. Put stops beyond the next significant structure instead. And not every sweep reverses — some just accelerate the trend; the displacement after tells you which.',
    terms: ['Buy-side liquidity', 'Sell-side liquidity', 'Equal highs/lows', 'Stop hunt', 'Liquidity pool', 'Displacement'],
    figcap: 'Equal highs build a buy-side liquidity pool; price sweeps the stops above, then reverses down.',
  };
  D['smc.liquidity'] = () => svg(
    frame() +
    line(60, 70, 300, 70, 'df-dash') + txt(64, 64, 'equal highs · BSL', 'df-tag', 'start') +
    bar(80, 74, 130, 'up', 12, 68, 136) +
    bar(120, 110, 150, 'down', 12, 104, 156) +
    bar(160, 74, 120, 'up', 12, 70, 126) +
    bar(200, 108, 146, 'down', 12, 102, 152) +
    // sweep above equal highs then reverse
    candle(248, 50, 120, 64, 110, 13) + txt(248, 42, 'sweep', 'df-tag-accent', 'middle') +
    bar(288, 96, 140, 'down', 12, 90, 146) +
    bar(322, 130, 172, 'down', 12, 124, 178) +
    arrow(248, 58, 322, 150, 'df-line-down')
  );

  C['smc.pd-arrays'] = {
    lead: 'Premium/Discount splits a dealing range at its 50% equilibrium: above is premium (expensive), below is discount (cheap). Smart money buys discount and sells premium — so you should too.',
    mechanics: [
      { term: 'Equilibrium', text: 'The 50% of the swing low-to-high is "fair value"; everything keys off this midpoint.' },
      { term: 'Premium arrays', text: 'OB/FVG/OTE sitting above 50% — where you look for shorts as institutions distribute into chasers.' },
      { term: 'Discount arrays', text: 'OB/FVG/OTE sitting below 50% — where you look for longs as institutions accumulate from panic sellers.' },
      { term: 'Rule', text: 'In a bullish bias, only buy when price retraces into discount; never chase a long while price sits in premium.' },
    ],
    mistake: 'Using the wrong dealing range gives wrong equilibrium — anchor to the most recent significant swing. And a Fib level alone is no edge; it only matters when discount overlaps an actual array (OB/FVG) and the timeframes agree.',
    terms: ['Equilibrium', '50% midpoint', 'Premium', 'Discount', 'OTE', 'Dealing range'],
    figcap: 'A dealing range split at 50% equilibrium: discount below (buy zone) and premium above (sell zone).',
  };
  D['smc.pd-arrays'] = () => {
    const hi = 50, lo = 180, mid = (hi + lo) / 2;
    return svg(frame() +
      rect(40, mid, 332, lo - mid, 'df-zone-up') +
      rect(40, hi, 332, mid - hi, 'df-zone-down') +
      line(40, mid, 372, mid, 'df-dash-accent') + txt(376, mid - 4, 'EQ 50%', 'df-tag-accent', 'end') +
      line(40, hi, 372, hi, 'df-dash') + txt(44, hi + 12, 'swing high', 'df-tag', 'start') +
      line(40, lo, 372, lo, 'df-dash') + txt(44, lo - 6, 'swing low', 'df-tag', 'start') +
      txt(200, hi + 28, 'PREMIUM · sell', 'df-tag-down', 'middle') +
      txt(200, lo - 18, 'DISCOUNT · buy', 'df-tag', 'middle'));
  };

  C['smc.kill-zones'] = {
    lead: 'Kill Zones are the time windows when institutional activity peaks and the cleanest setups form. Trading only inside them — and avoiding the dead lunch hours — is a core ICT discipline.',
    mechanics: [
      { term: 'London Open', text: '02:00–05:00 EST — highest liquidity for EUR/GBP; the open often sweeps the Asian range before the true move.' },
      { term: 'New York Open', text: '07:00–10:00 EST — high-impact US data hits 08:30; the second-most active window of the day.' },
      { term: 'Silver Bullet', text: 'The 10:00–11:00 EST hour — a 15-min FVG aligned with daily bias is one of ICT\'s highest-conviction setups.' },
      { term: 'Avoid lunch', text: 'NY lunch / London close (12:00–14:00 EST) is low-volume chop where retail gets ground up.' },
    ],
    mistake: 'The same OB or FVG that prints clean entries in the London Open turns into indecisive chop during lunch. And track daylight-saving shifts — EST→EDT moves every window by an hour relative to GMT.',
    terms: ['London Open', 'New York Open', 'Silver Bullet', 'Asian range', 'Session overlap', 'IPDA'],
    figcap: 'A 24-hour bar highlighting the London, New York, and Silver Bullet kill zones against the dead lunch hours.',
  };
  D['smc.kill-zones'] = () => {
    const y = 96, h = 40, x0 = 40, x1 = 372, span = x1 - x0;
    const at = hr => x0 + (hr / 24) * span;
    const zone = (a, b, label, cls) => rect(at(a), y, at(b) - at(a), h, cls || 'df-zone') +
      txt((at(a) + at(b)) / 2, y + h + 16, label, 'df-tag-accent', 'middle');
    return svg(
      rect(x0, y, span, h, 'df-grid') + line(x0, y + h, x1, y + h, 'df-axis') +
      zone(2, 5, 'London') + zone(7, 10, 'New York') + zone(10, 11, 'SB') +
      txt(x0, y - 10, '00:00', 'df-tag', 'start') + txt(x1, y - 10, '24:00 EST', 'df-tag', 'end') +
      txt(at(13), y + h + 16, 'lunch', 'df-tag', 'middle'));
  };

  C['smc.ote'] = {
    type: 't',
    lead: 'The Optimal Trade Entry is ICT\'s Fibonacci pocket: in a confirmed trend, the retracement window the methodology rates highest sits between the 61.8% and 79% levels, with 70.5% the sweet spot.',
    body: 'It marries a deep-discount (or deep-premium) Fib zone with an actual institutional array for maximum confluence.',
    mechanics: [
      { term: 'Measurement', text: 'Anchor the Fib from the recent significant swing low to high (bullish); the OTE is the 0.62–0.79 band.' },
      { term: '70.5% sweet spot', text: 'ICT\'s most reactive level — a limit there with other confluences balances entry depth and stop efficiency.' },
      { term: 'Confluence required', text: 'OTE must align with a confirmed bias (HTF BOS), an array (OB/FVG) in the pocket, and Kill-Zone timing.' },
      { term: 'Discount alignment', text: 'In a bullish trade the OTE should sit in the discount half of the dealing range.' },
    ],
    mistake: 'Using OTE on a minor internal swing instead of the significant structural swing puts entries at irrelevant levels. And OTE without bias, array, and timing is just a Fib level with no edge — all the pieces must converge.',
    setup: {
      cond: 'HTF BOS confirms bias; price retraces into the 0.62–0.79 pocket; an OB/FVG sits inside it; Kill Zone active.',
      entry: 'Limit at the 70.5% sweet spot, or a rejection confirmation inside the pocket.',
      stop: 'Beyond the swing that anchored the Fib, plus a buffer past the array.',
      target: 'Prior swing high/low and the liquidity beyond it; 1:3 or better is typical.',
    },
    terms: ['Fibonacci pocket', '61.8% / 70.5% / 79%', 'OTE zone', 'Discount', 'Confluence', 'HTF bias'],
    figcap: 'A bullish impulse, then a retrace into the 62–79% OTE pocket where the entry is taken.',
  };
  D['smc.ote'] = () => {
    const lo = 180, hi = 50;
    const f = pct => hi + (lo - hi) * pct;
    const imp = 'M40 180 L90 150 L130 120 L175 78 L210 56';
    const ret = 'M210 56 L250 96 L285 130 L300 142';
    const cont = 'M300 142 L335 96 L372 48';
    return svg(frame() +
      rect(40, f(0.62), 332, f(0.79) - f(0.62), 'df-zone') +
      line(40, f(0.62), 372, f(0.62), 'df-dash') + txt(376, f(0.62) - 3, '.62', 'df-tag', 'end') +
      line(40, f(0.705), 372, f(0.705), 'df-dash-accent') + txt(376, f(0.705) - 3, '.705', 'df-tag-accent', 'end') +
      line(40, f(0.79), 372, f(0.79), 'df-dash') + txt(376, f(0.79) + 10, '.79', 'df-tag', 'end') +
      path(imp, 'df-line') + path(ret, 'df-line') + path(cont, 'df-line-accent') +
      txt(150, 200, 'OTE pocket', 'df-tag-accent', 'middle') +
      arrow(300, 142, 335, 96, 'df-line-accent'));
  };

  C['smc.ob-retest'] = {
    type: 't',
    lead: 'The order-block retest is the core ICT entry: after a sweep, displacement, and BOS leave an order block at the move\'s origin, price retraces into that OB to restart the move.',
    mechanics: [
      { term: 'Sequence', text: 'Liquidity sweep → displacement leaving OB+FVG → BOS confirms direction → retrace into the OB.' },
      { term: 'Entry zone', text: 'The proximal edge of the OB; the distal edge sets the stop reference.' },
      { term: 'Confirmation', text: 'Wait for a lower-timeframe rejection or MSS at the OB rather than a blind tap.' },
      { term: 'Confluence', text: 'Best when the OB overlaps an FVG, the OTE pocket, premium/discount alignment, and Kill-Zone timing.' },
    ],
    mistake: 'The biggest failure is entering before the retest actually happens — many pre-place limits and price never returns. And "wick through, don\'t close through": price may pierce the OB, but a body close beyond the distal edge invalidates it.',
    setup: {
      cond: 'HTF BOS after displacement; OB at the origin; price retracing toward it during a Kill Zone with LTF confirmation.',
      entry: 'At the OB\'s proximal edge on a rejection, or a limit there for experienced traders.',
      stop: 'Beyond the OB\'s distal edge plus a buffer, or past the sweep extreme.',
      target: 'The next draw on liquidity (BSL/SSL) and prior structure; 1:3+.',
    },
    terms: ['Proximal / distal', 'Mitigation', 'Displacement', 'MSS', 'Confluence', 'Draw on liquidity'],
    figcap: 'After displacement and a BOS, price returns to the order block\'s proximal edge — the retest entry.',
  };
  D['smc.ob-retest'] = () => svg(
    frame() +
    rect(60, 120, 70, 28, 'df-zone') + txt(64, 114, 'OB', 'df-tag-accent', 'start') +
    candle(95, 122, 150, 146, 126, 13) +
    bar(140, 84, 126, 'up', 12, 78, 130) +
    bar(172, 50, 92, 'up', 12, 44, 96) +
    line(140, 84, 320, 84, 'df-dash') + txt(250, 78, 'BOS', 'df-tag-accent', 'middle') +
    arrow(120, 150, 180, 56, 'df-line-up') +
    bar(250, 50, 96, 'down', 12, 44, 102) +
    bar(282, 96, 134, 'down', 12, 90, 138) +
    arrow(294, 150, 300, 130, 'df-line-up') + txt(300, 166, 'retest', 'df-tag', 'middle') +
    bar(330, 70, 120, 'up', 12, 64, 126)
  );

  C['smc.fvg-fill'] = {
    type: 't',
    lead: 'The FVG fill enters as price returns to a fair value gap, in the direction of the impulse that created it — the gap acts as a magnetic, institutionally-relevant zone with defined risk.',
    mechanics: [
      { term: 'Three entry levels', text: 'Full gap, the 50% Consequent Encroachment (primary reactive level), or the proximal edge for the tightest stop.' },
      { term: 'Partial vs full', text: 'Strong trends often tag only the CE before resuming; weaker ones fill the whole gap first.' },
      { term: 'Entry vs target', text: 'An FVG ahead of price is a target (draw on liquidity); an FVG price returns to is an entry — know which role it plays.' },
      { term: 'Inverse FVG', text: 'A broken bullish FVG becomes a short entry on the return from below, and vice versa.' },
    ],
    mistake: 'Waiting for a full fill often means missing the reaction — price frequently taps the CE and reverses without touching the bottom, giving worse R:R. And an FVG in isolation has no bias; context (OTE, premium/discount, BOS) makes it bullish or bearish.',
    setup: {
      cond: 'FVG from a clear displacement; HTF bias confirmed; price retracing toward the gap in a Kill Zone.',
      entry: 'Limit at the CE (50%), or the proximal edge for a tighter stop, with LTF confirmation.',
      stop: 'Beyond the far edge of the FVG plus a buffer.',
      target: 'Next liquidity draw / prior swing / next FVG; 1:3+.',
    },
    terms: ['Consequent Encroachment', '50% midpoint', 'Partial fill', 'Inverse FVG', 'Draw on liquidity'],
    figcap: 'Price returns to a fair value gap and reacts at its 50% midpoint (CE), resuming the original move.',
  };
  D['smc.fvg-fill'] = () => svg(
    frame() +
    bar(70, 150, 178, 'up', 13, 144, 184) +
    candle(105, 100, 152, 144, 108, 16) +
    bar(140, 56, 104, 'up', 13, 50, 110) +
    rect(56, 108, 250, 38, 'df-zone') +
    line(56, 127, 306, 127, 'df-dash-accent') + txt(312, 123, 'CE', 'df-tag-accent', 'start') +
    bar(240, 50, 92, 'down', 13, 44, 98) +
    bar(275, 96, 124, 'down', 13, 90, 130) +
    arrow(288, 150, 296, 128, 'df-line-accent') +
    bar(322, 70, 118, 'up', 13, 64, 124)
  );

  C['smc.liquidity-sweep'] = {
    type: 't',
    lead: 'The liquidity-sweep reversal is the foundational ICT setup: price runs beyond a pool of stops, fills institutional orders, then reverses — confirmed by a Market Structure Shift before you enter.',
    mechanics: [
      { term: 'Identify the pool', text: 'Equal highs/lows, prior session or swing extremes where retail stops predictably cluster.' },
      { term: 'The sweep', text: 'Price spikes past the pool and snaps back — a strong wick beyond, closing back inside.' },
      { term: 'Displacement + MSS', text: 'A forceful candle reverses and breaks internal structure (MSS), confirming the sweep was institutional.' },
      { term: 'Enter the retrace', text: 'After MSS, price pulls back into the displacement\'s FVG or OB — that\'s the entry at institutional value.' },
    ],
    mistake: 'Entering on the sweep close before MSS is aggressive — some sweeps run further first. Waiting for the MSS costs a little entry price but filters fakes. And the more obvious the pool (equal highs touched 3+ times), the more reliable the reversal.',
    setup: {
      cond: 'A clear liquidity pool swept (wick/close beyond), immediate displacement, and an MSS on the lower timeframe.',
      entry: 'Limit at the displacement\'s FVG CE or OB proximal edge, or market on the MSS candle close.',
      stop: 'Beyond the extreme of the sweep wick, plus a buffer.',
      target: 'The opposite liquidity pool; 1:3 minimum, often 1:5–1:10 with confluence.',
    },
    terms: ['Liquidity pool', 'Stop hunt', 'Displacement', 'MSS', 'Equal highs/lows', 'FVG entry'],
    figcap: 'Price sweeps the stops above equal highs, displaces down with an MSS, then retraces for the short entry.',
  };
  D['smc.liquidity-sweep'] = () => svg(
    frame() +
    line(60, 76, 250, 76, 'df-dash') + txt(64, 70, 'liquidity pool', 'df-tag', 'start') +
    bar(80, 80, 130, 'up', 12, 74, 136) +
    bar(118, 110, 150, 'down', 12, 104, 156) +
    bar(156, 80, 124, 'up', 12, 76, 130) +
    // sweep
    candle(200, 52, 122, 66, 112, 13) + txt(200, 44, 'sweep', 'df-tag-accent', 'middle') +
    // displacement down + MSS
    bar(236, 100, 150, 'down', 12, 94, 156) +
    bar(268, 130, 178, 'down', 12, 124, 184) +
    line(150, 150, 300, 150, 'df-dash') + txt(280, 144, 'MSS', 'df-tag-down', 'middle') +
    arrow(200, 60, 268, 150, 'df-line-down') +
    // retrace entry
    bar(310, 120, 160, 'up', 12, 114, 166) +
    arrow(322, 100, 316, 124, 'df-line-down')
  );

  // ══════════════════════════════════════════════════════════════════════
  // METHODOLOGY 4 — FUNDAMENTAL ANALYSIS
  // ══════════════════════════════════════════════════════════════════════

  C['fundamental.macro-drivers'] = {
    lead: 'Macro drivers are the large forces — growth, employment, inflation, and central-bank policy — that set the long-term directional bias of currencies, indices, and commodities.',
    body: 'They explain why an asset trends for weeks or months, providing the fundamental backdrop against which every technical setup either flows or fights.',
    mechanics: [
      { term: 'The cycle', text: 'Expansion → peak → contraction → trough; each phase has predictable effects on currency and equity valuations.' },
      { term: 'Growth & jobs', text: 'Strong GDP and employment attract capital and let central banks tighten — both currency-positive.' },
      { term: 'Inflation', text: 'Above-target inflation pushes policy hawkish (currency up); below-target permits easing (currency down).' },
      { term: 'Relative advantage', text: 'In FX the trade is always between two currencies — what matters is the differential, not either economy alone.' },
    ],
    mistake: 'Ignoring fundamentals leaves you blind to why a clean setup either runs hard (fundamentals align) or keeps failing (they oppose it). And markets price expectations far ahead — the reaction is to the deviation from consensus, not the absolute number.',
    terms: ['Economic cycle', 'GDP', 'Inflation', 'Central bank', 'Policy differential', 'Hawkish / dovish'],
    figcap: 'The economic cycle as a wave through expansion, peak, contraction, and trough.',
  };
  D['fundamental.macro-drivers'] = () => {
    const wave = 'M40 120 C90 60 130 60 170 110 C210 160 250 160 290 110 C320 72 350 80 372 100';
    return svg(line(34, 196, 384, 196, 'df-axis') + line(34, 16, 34, 196, 'df-axis') +
      line(40, 120, 372, 120, 'df-grid') +
      path(wave, 'df-line-accent') +
      dot(150, 66, 3) + txt(150, 56, 'peak', 'df-tag-accent', 'middle') +
      dot(230, 158, 3) + txt(230, 176, 'trough', 'df-tag', 'middle') +
      txt(95, 150, 'expansion', 'df-tag', 'middle') + txt(270, 70, 'recovery', 'df-tag', 'middle'));
  };

  C['fundamental.interest-rates'] = {
    lead: 'Interest rates — and the market\'s expectations for future rates — are the single most powerful driver of currency value. Capital flows toward the highest risk-adjusted return.',
    mechanics: [
      { term: 'Mechanism', text: 'Higher rates → higher yields → foreign inflows → currency demand → appreciation. Cuts do the reverse.' },
      { term: 'Rate differential', text: 'The gap between two currencies\' rates drives the carry trade — borrow low-rate, hold high-rate, collect the rollover.' },
      { term: 'Hawkish vs dovish', text: 'The shift in tone (toward hikes or cuts) often moves price more than the decision itself.' },
      { term: 'Forward guidance', text: 'A single word change in a statement ("transitory"→"persistent") can move markets more than a 25bp move.' },
    ],
    mistake: 'Trading a decision without knowing what was priced in is dangerous — a fully-expected hike can make a currency fall as positioning unwinds ("sell the fact"). What matters is the surprise versus consensus. Carry trades also unwind violently in risk-off.',
    terms: ['Rate differential', 'Carry trade', 'Hawkish / dovish', 'Forward guidance', 'Bond yields', 'DXY'],
    figcap: 'As the policy rate rises, the currency strengthens in step — the rate/currency relationship.',
  };
  D['fundamental.interest-rates'] = () => {
    const rate = 'M40 170 L110 168 L160 140 L210 138 L260 100 L310 70 L372 60';
    const ccy  = 'M40 176 L110 172 L160 150 L210 146 L260 112 L310 82 L372 70';
    return svg(frame() +
      path(rate, 'df-line-accent') + txt(360, 56, 'rate', 'df-tag-accent', 'end') +
      path(ccy, 'df-line') + txt(372, 80, 'currency', 'df-tag', 'end') +
      arrow(310, 70, 372, 60, 'df-line-accent'));
  };

  C['fundamental.news-data'] = {
    lead: 'Economic releases are scheduled publications of key metrics that spike volatility when the data deviates from consensus. Knowing what each measures — and when — is essential whether you trade them or avoid them.',
    mechanics: [
      { term: 'NFP', text: 'US Nonfarm Payrolls, first Friday 08:30 EST — the most market-moving FX release; the surprise vs consensus is what counts.' },
      { term: 'CPI / Core CPI', text: 'The key inflation read for the Fed; hot CPI is USD-bullish and equity-volatile, soft CPI the reverse.' },
      { term: 'FOMC', text: 'Eight times a year: the decision, statement, and dot plot — the press conference often moves more than the decision.' },
      { term: 'Impact tiers', text: 'Calendars colour-code events; only red (high-impact) reliably produces tradable volatility.' },
    ],
    mistake: '"Good news = up" is often wrong — markets are forward-looking and price expectations in advance; they react to the surprise. The 30-minute window before a red release is a no-trade zone of widening spreads and stop hunts. And prior-month revisions can cancel a headline beat.',
    terms: ['NFP', 'CPI', 'FOMC', 'Dot plot', 'Consensus', 'Economic calendar'],
    figcap: 'A scheduled release fires a volatility spike at the announcement time on the calendar.',
  };
  D['fundamental.news-data'] = () => {
    const pre = 'M40 120 L70 116 L100 122 L130 118 L160 120';
    const spike = 'M160 120 L172 60 L184 150 L196 90';
    const post = 'M196 90 L240 96 L290 80 L340 70 L372 64';
    return svg(frame() +
      line(160, 24, 160, 196, 'df-dash-accent') + txt(160, 18, 'release', 'df-tag-accent', 'middle') +
      path(pre, 'df-line') + path(spike, 'df-line-accent') + path(post, 'df-line'));
  };

  C['fundamental.intermarket'] = {
    lead: 'Intermarket analysis reads the relationships between asset classes — stocks, bonds, currencies, commodities — because global capital is interconnected and a move in one market often foretells another.',
    mechanics: [
      { term: 'USD vs Gold/Oil', text: 'A stronger dollar generally pressures gold and oil (both priced in USD); a weaker dollar lifts them.' },
      { term: 'Yields vs equities', text: 'Rising yields raise the discount on future earnings and compete with stocks — often inversely related short-term.' },
      { term: 'Risk-on / risk-off', text: 'Risk-on buys equities and commodity currencies (AUD/CAD/NZD); risk-off buys JPY, CHF, USD, and bonds.' },
      { term: 'DXY as master', text: 'As the reserve and commodity-pricing currency, DXY direction underpins gold, oil, EM, and the major pairs.' },
    ],
    mistake: 'Correlations are not static — the USD/gold inverse can break in a systemic crisis when everything sells for liquidity. The real value is spotting when a normal correlation breaks down — that regime shift is itself the signal.',
    terms: ['Risk-on / risk-off', 'Safe havens', 'Commodity currencies', 'DXY', 'Bond yields', 'Regime shift'],
    figcap: 'DXY and gold moving inversely — a classic intermarket correlation used as confluence.',
  };
  D['fundamental.intermarket'] = () => {
    const dxy  = 'M40 150 L90 120 L140 132 L190 90 L240 104 L290 64 L340 78 L372 50';
    const gold = 'M40 70 L90 100 L140 88 L190 130 L240 116 L290 156 L340 142 L372 170';
    return svg(frame() +
      path(dxy, 'df-line-accent') + txt(360, 46, 'DXY', 'df-tag-accent', 'end') +
      path(gold, 'df-line') + txt(372, 184, 'gold', 'df-tag', 'end'));
  };

  C['fundamental.news-fade'] = {
    type: 't',
    lead: 'The news-spike fade trades the knee-jerk overreaction to a release: price spikes on the headline, then reverts toward pre-release levels as the initial algo response gives way to rational pricing.',
    mechanics: [
      { term: 'Why it fades', text: 'Algos hit the headline instantly; humans then judge whether it truly changes the macro story — if not, the spike becomes liquidity to fade.' },
      { term: 'Timing', text: 'The spike is the first 1–5 minutes; the fade develops in the 5–30 minute window as momentum exhausts.' },
      { term: 'Fadeable signs', text: 'The spike overshoots a key level, volume drops after the burst, and price fails to extend after 5–10 minutes.' },
      { term: 'When NOT to fade', text: 'A genuine paradigm-shifting surprise turns the spike into a sustained trend — strong continuation means stand aside.' },
    ],
    mistake: 'Fading a true macro surprise (the first CPI that broke the "transitory" narrative) is catastrophic — the spike becomes the trend. Distinguishing a fadeable overreaction from a regime change needs macro context, not just the candle. Spreads also gut these trades.',
    setup: {
      cond: 'High-impact release; an outsized spike that overshoots a level; a reversal candle and no follow-through after 5+ min.',
      entry: 'On the reversal candle at the spike extreme, or a break of the first post-spike consolidation against the spike.',
      stop: 'Beyond the spike\'s extreme wick, with extra room for slippage.',
      target: 'Pre-release level or VWAP; conservative, given the speed.',
    },
    terms: ['Knee-jerk', 'Spike exhaustion', 'Mean reversion', 'Reversal candle', 'Slippage', 'Macro surprise'],
    figcap: 'Price spikes on the release, exhausts, and reverts back toward the pre-release level — the fade.',
  };
  D['fundamental.news-fade'] = () => {
    const pre = 'M40 120 L100 118 L150 120';
    const spike = 'M150 120 L170 40 L188 96';
    const fade = 'M188 96 L240 112 L300 118 L372 120';
    return svg(frame() +
      line(40, 120, 372, 120, 'df-dash') + txt(44, 114, 'pre-release', 'df-tag', 'start') +
      line(150, 24, 150, 196, 'df-dash-accent') + txt(150, 18, 'release', 'df-tag-accent', 'middle') +
      path(pre, 'df-line') + path(spike, 'df-line') + path(fade, 'df-line-accent') +
      arrow(200, 90, 300, 118, 'df-line-accent') + txt(290, 138, 'fade', 'df-tag-accent', 'middle'));
  };

  C['fundamental.data-continuation'] = {
    type: 't',
    lead: 'The data-release continuation rides a release that confirms the existing macro trend: after the spike and a brief pullback, price continues in the data-confirmed direction.',
    body: 'Unlike the fade, this follows the move — but only when the data agrees with the established fundamental narrative.',
    mechanics: [
      { term: 'Pre-conditions', text: 'A clear fundamental trend already in place (e.g. a hiking cycle) that the release reinforces.' },
      { term: 'The pullback', text: 'After the initial spike, a partial retrace is final profit-taking before continuation — that retrace is the entry.' },
      { term: 'Entry at a level', text: 'Wait for the pullback to a technical level (prior resistance-turned-support, VWAP) for precision.' },
      { term: 'Confluence', text: 'Strongest when the surprise direction agrees with the trend, the central-bank narrative, and risk sentiment.' },
    ],
    mistake: 'Entering on the initial spike gives terrible fills and huge slippage — wait for the retrace to a level. And counter-trend data does not automatically reverse the trend; it often just pauses it unless the surprise is large.',
    setup: {
      cond: 'Existing macro trend; release surprises in the trend\'s direction; initial spike then a retrace to a key level.',
      entry: 'A rejection at the technical level on the pullback, or a break of the post-spike consolidation with trend.',
      stop: 'Below the retrace low (longs) / above the high (shorts), under the level used.',
      target: 'The next major structural level; hold into the session, or overnight for paradigm-shift data.',
    },
    terms: ['Macro alignment', 'Spike-and-retrace', 'Post-release consolidation', 'Fundamental backdrop', 'Confluence'],
    figcap: 'A release spikes with the trend, pulls back to a level, then continues — the continuation entry.',
  };
  D['fundamental.data-continuation'] = () => {
    const pre = 'M40 150 L100 146 L150 148';
    const spike = 'M150 148 L168 96 L186 112';
    const cont = 'M186 112 L210 130 L230 124 L270 86 L310 60 L350 40';
    return svg(frame() +
      line(150, 24, 150, 196, 'df-dash-accent') + txt(150, 18, 'release', 'df-tag-accent', 'middle') +
      line(40, 124, 372, 124, 'df-dash') + txt(44, 118, 'level', 'df-tag', 'start') +
      path(pre, 'df-line') + path(spike, 'df-line') + path(cont, 'df-line-accent') +
      dot(230, 124, 3) + txt(238, 138, 'pullback', 'df-tag', 'start') +
      arrow(270, 86, 350, 40, 'df-line-accent'));
  };

  // ══════════════════════════════════════════════════════════════════════
  // METHODOLOGY 5 — QUANTITATIVE
  // ══════════════════════════════════════════════════════════════════════

  C['quant.probability'] = {
    lead: 'Quant trading rests on statistical thinking: trading is a probability game judged over large samples, not single outcomes. Expectancy tells you if you have an edge; variance explains the painful streaks along the way.',
    mechanics: [
      { term: 'Expectancy', text: 'E = (win% × avg win) − (loss% × avg loss). Positive = viable; negative = no discipline can save it.' },
      { term: 'Win-rate vs R:R', text: 'They trade off — a 25% win rate at 4:1 is profitable; the combination must be positive, not either metric alone.' },
      { term: 'Law of large numbers', text: 'Edge only shows over 100+ trades; judging a system on 10 trades is measuring variance, not edge.' },
      { term: 'Variance', text: 'Even a great system prints 10–20 loss streaks by chance — size positions to survive them.' },
    ],
    mistake: 'The number-one psychological error is treating a normal losing streak as a "broken" system and abandoning it mid-drawdown. The other is chasing high win rate for comfort — 70% win rates often hide tiny R:R and negative expectancy. The math doesn\'t care how it feels.',
    terms: ['Expectancy', 'Win rate', 'Risk:reward', 'Law of large numbers', 'Variance', 'Edge'],
    figcap: 'A positive-expectancy equity curve rises overall while still suffering normal variance drawdowns.',
  };
  D['quant.probability'] = () => {
    const eq = 'M40 180 L70 150 L95 168 L130 120 L160 138 L195 96 L225 118 L265 78 L300 96 L335 54 L372 40';
    return svg(frame() +
      path(eq, 'df-line-accent') +
      line(40, 188, 372, 44, 'df-dash') + txt(360, 56, 'edge', 'df-tag-accent', 'end') +
      txt(160, 156, 'variance', 'df-tag', 'middle') + arrow(160, 150, 195, 100, 'df-line'));
  };

  C['quant.backtesting'] = {
    lead: 'Backtesting applies a strategy to historical data to estimate its edge before risking capital — but it is riddled with traps that manufacture fake profitability that never survives live trading.',
    mechanics: [
      { term: 'Look-ahead bias', text: 'Using data unavailable at decision time (tomorrow\'s open, the bar\'s final high) — destroys all validity.' },
      { term: 'Overfitting', text: 'Tuning parameters on the same data you evaluate on memorises noise; more parameters = more overfit.' },
      { term: 'Walk-forward', text: 'Optimise on in-sample, then test untouched out-of-sample data; the gap reveals how much was overfit.' },
      { term: 'Costs & slippage', text: 'A strategy profitable before spreads/commissions/slippage and negative after was never real.' },
    ],
    mistake: 'Backtests are always optimistic versus live — the gap is "strategy decay", and it grows with complexity. You need 200–300+ trades across trending and ranging, high- and low-volatility regimes; 50 trades in one bull year tells you almost nothing.',
    terms: ['Look-ahead bias', 'Overfitting', 'Walk-forward', 'In/out-of-sample', 'Slippage', 'Strategy decay'],
    figcap: 'Walk-forward split: a strong in-sample curve and the out-of-sample test that exposes overfitting.',
  };
  D['quant.backtesting'] = () => {
    const inS  = 'M40 180 L80 150 L120 158 L160 110 L200 90';
    const outS = 'M200 90 L240 96 L280 110 L320 104 L372 120';
    return svg(frame() +
      line(200, 24, 200, 196, 'df-dash-accent') +
      txt(118, 40, 'in-sample', 'df-tag', 'middle') + txt(290, 40, 'out-of-sample', 'df-tag-accent', 'middle') +
      path(inS, 'df-line-accent') + path(outS, 'df-line') +
      txt(300, 140, 'decay', 'df-tag', 'middle'));
  };

  C['quant.risk-of-ruin'] = {
    lead: 'Risk of Ruin is the probability of losing enough capital to be knocked out of the game — a function of edge, risk per trade, and how much variance your account can absorb. Position sizing matters as much as the strategy.',
    mechanics: [
      { term: 'The math', text: 'RoR rises sharply with risk-per-trade — even a real edge ruins you if positions are too big for the variance.' },
      { term: 'Kelly Criterion', text: 'f* = (b·p − q)/b maximises growth, but full Kelly draws down ~50% — most use a quarter- to half-Kelly.' },
      { term: 'Drawdown asymmetry', text: 'A 25% loss needs +33% to recover; 50% needs +100%; 90% needs +900%. Losses compound against you.' },
      { term: 'Fixed fractional', text: 'Risk a fixed % of equity per trade — it compounds on the way up and auto-derisks on the way down.' },
    ],
    mistake: 'The deadliest belief is "I have an edge, so I should bet big to grow fast." Variance will produce a losing streak that, at large size, exceeds what the account can survive — and full Kelly is psychologically impossible to hold through its drawdowns.',
    terms: ['Kelly Criterion', 'Fixed fractional', 'Drawdown recovery', 'Variance', 'Position sizing', 'Half-Kelly'],
    figcap: 'Drawdown asymmetry: the gain required to recover grows non-linearly as the loss deepens.',
  };
  D['quant.risk-of-ruin'] = () => {
    const base = 188; let bars = '';
    const data = [['10%', 11, 60], ['25%', 33, 130], ['50%', 100, 220], ['75%', 300, 300]];
    data.forEach((d, i) => {
      const x = 70 + i * 78;
      const lossH = d[1] * 0.0 + (i + 1) * 18; // loss bar (illustrative steps)
      const gainH = Math.min(150, d[2] * 0.5);
      bars += rect(x - 22, base - (i + 1) * 22, 18, (i + 1) * 22, 'df-down') +
        rect(x + 2, base - gainH, 18, gainH, 'df-up') +
        txt(x - 8, base + 14, d[0], 'df-tag', 'middle');
    });
    return svg(line(34, base, 384, base, 'df-axis') + bars +
      txt(70, 40, 'loss', 'df-tag-down', 'middle') + txt(120, 40, 'gain to recover', 'df-tag', 'start'));
  };

  C['quant.algo-systems'] = {
    lead: 'Algorithmic systems execute pre-defined rules automatically, removing emotion and enabling rigorous testing. Different approaches exploit different inefficiencies — trend-following, mean-reversion, market-making, and arbitrage.',
    mechanics: [
      { term: 'Trend-following', text: 'Buy strength, sell weakness (MA crosses, ADX). Wins in trends, bleeds in ranges — the classic CTA approach.' },
      { term: 'Mean-reversion', text: 'Fade extremes back to the average (z-score, bands). Wins in ranges, suffers in trends.' },
      { term: 'Regime dependence', text: 'A system optimised in one regime fails in another — robust systems detect regime (ADX/volatility) and adapt.' },
      { term: 'Execution', text: 'Latency, slippage, and API limits decide high-frequency viability; retail latency disqualifies many fast strategies.' },
    ],
    mistake: 'Automation doesn\'t remove risk — it executes a flawed strategy with perfect consistency, so a bad system blows up faster. Keep a high trade-to-parameter ratio (30+ trades per parameter) and demand out-of-sample within 50–70% of in-sample.',
    terms: ['Trend-following', 'Mean-reversion', 'Arbitrage', 'Regime detection', 'Latency', 'Overfitting'],
    figcap: 'Two regimes: a trending stretch (trend-following territory) and a range (mean-reversion territory).',
  };
  D['quant.algo-systems'] = () => {
    const trend = 'M40 170 L80 150 L110 158 L150 120 L185 96 L215 70';
    const range = 'M215 70 L245 110 L275 76 L305 112 L335 78 L372 110';
    return svg(frame() +
      line(215, 24, 215, 196, 'df-dash') +
      path(trend, 'df-line-accent') + path(range, 'df-line') +
      txt(120, 40, 'trend', 'df-tag-accent', 'middle') + txt(300, 40, 'range', 'df-tag', 'middle'));
  };

  C['quant.mean-reversion'] = {
    type: 't',
    lead: 'A mean-reversion signal fires when price has stretched statistically far from its average — by z-score, band, or RSI extreme — betting on a snap back to the mean. But the regime must be range-bound first.',
    mechanics: [
      { term: 'Z-score', text: 'z = (price − mean) / σ; ±2 is a tradable extreme, ±3 statistically anomalous. Target = z back to 0.' },
      { term: 'Band reversion', text: 'A close beyond the 2σ Bollinger Band, then a reversal candle back inside; target the middle band.' },
      { term: 'Pairs trading', text: 'Trade the spread between two cointegrated assets when it deviates ±2σ — market-neutral by construction.' },
      { term: 'Regime gate', text: 'Require range-bound conditions (ADX < 20, flat MAs) before any reversion signal is valid.' },
    ],
    mistake: 'Applying mean-reversion in a trend is fatal — RSI below 20 in a strong downtrend is continuation, not a buy. Assess the regime before the signal. And correlation is not cointegration: pairs that "looked correlated" can diverge permanently.',
    setup: {
      cond: 'Range confirmed (ADX < 20, flat MAs); price 2+ σ from the mean; a reversal candle/structure at the extreme.',
      entry: 'On the confirmation candle at the extreme, not on the reach of it; or systematic limit at ±2σ.',
      stop: 'At ±3σ from the mean, or beyond the recent swing extreme.',
      target: 'Return to the mean (z=0 / middle band / RSI 50); typically 1:1.5–1:3.',
    },
    terms: ['Z-score', 'Standard deviation', 'Band reversion', 'Pairs trading', 'Cointegration', 'ADX gate'],
    figcap: 'Price stretches to the +2σ band in a range, then reverts to the mean — the reversion trade.',
  };
  D['quant.mean-reversion'] = () => {
    const mean = 110;
    const upper = 60, lower = 160;
    const price = 'M40 110 L70 84 L95 64 L120 96 L150 112 L180 138 L205 156 L235 120 L265 108 L300 70 L330 100 L372 112';
    return svg(frame() +
      line(40, upper, 372, upper, 'df-dash-accent') + txt(376, upper - 3, '+2σ', 'df-tag-accent', 'end') +
      line(40, lower, 372, lower, 'df-dash-accent') + txt(376, lower + 10, '−2σ', 'df-tag-accent', 'end') +
      line(40, mean, 372, mean, 'df-dash') + txt(376, mean - 4, 'mean', 'df-tag', 'end') +
      path(price, 'df-line-accent') +
      dot(95, 64, 3) + arrow(95, 70, 120, 104, 'df-line') +
      dot(205, 156, 3) + arrow(205, 150, 235, 116, 'df-line'));
  };

  C['quant.momentum'] = {
    type: 't',
    lead: 'A momentum signal enters when price moves with enough directional strength to ride — capturing persistence rather than fading it. ADX separates real momentum from noise.',
    mechanics: [
      { term: 'Rate of Change', text: 'ROC measures % change over a lookback; positive and rising = accelerating; zero-line crosses flag shifts.' },
      { term: 'ADX gate', text: 'ADX > 25 confirms a trend; > 45 warns of exhaustion (fade, don\'t chase). +DI/−DI give the direction.' },
      { term: 'Breakout entry', text: 'Enter a level break only when ADX is rising above 25 — filtering the fakeouts that fire on flat ADX.' },
      { term: 'Trend entries', text: 'Pullback to the 20/50 EMA, MACD cross, or RSI through 50 — all with ADX confirming the trend.' },
    ],
    mistake: 'ADX shows strength, not direction — without +DI/−DI you have half the picture. The worst outcome is a breakout that\'s really a liquidity sweep; check that the break isn\'t just grabbing stops. Momentum also needs wide stops beyond structure, not tight ATR clips that get whipped out.',
    setup: {
      cond: 'ADX > 25 and rising; direction confirmed by +DI/−DI; price at a level (breakout or pullback) with ROC/MACD agreeing.',
      entry: 'On the breakout/pullback rejection close, or a MACD signal cross with ADX > 25.',
      stop: 'Beyond the most recent structural swing that invalidates the trend.',
      target: 'A trending objective; trail the 20/50 EMA, banking partials at key levels.',
    },
    terms: ['Rate of Change', 'ADX', '+DI / −DI', 'Momentum breakout', 'Fakeout', 'Trailing stop'],
    figcap: 'An ADX-confirmed breakout running into a sustained trend, trailed by a rising moving average.',
  };
  D['quant.momentum'] = () => {
    const price = 'M40 170 L75 162 L110 166 L145 150 L165 118 L195 96 L230 104 L265 70 L300 80 L335 48 L372 36';
    const trail = 'M40 184 L120 174 L200 132 L280 96 L372 60';
    return svg(frame() +
      line(150, 150, 372, 150, 'df-dash') + txt(120, 144, 'level', 'df-tag', 'end') +
      path(trail, 'df-dash-accent') + path(price, 'df-line-accent') +
      arrow(150, 150, 168, 120, 'df-line-accent') + txt(176, 116, 'breakout', 'df-tag-accent', 'start') +
      txt(330, 74, 'trail', 'df-tag-accent', 'end'));
  };

  // ── publish (merge so later methodology files/edits can extend) ──────────
  window.SynapseContent = Object.assign(window.SynapseContent || {}, C);
  window.SynapseDiagrams = Object.assign(window.SynapseDiagrams || {}, D);
})();
