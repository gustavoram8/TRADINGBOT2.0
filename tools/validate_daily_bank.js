#!/usr/bin/env node
/*
 * DAILY_BANK validator — enforces the content rules of the dedicated Daily
 * Challenge pool (ultra-hard, text-only):
 *
 *   1. Every entry has q / opts / exp in ALL of en, es, fr, pt (non-empty).
 *   2. Exactly 4 options, exactly ONE with ok:true.
 *   3. Option-length parity per language: the longest option may not exceed
 *      the shortest by more than LEN_RATIO_FAIL (guessing by length must not
 *      work). Ratios above LEN_RATIO_WARN are reported as warnings.
 *   4. The correct option must not systematically be the longest/shortest —
 *      reported as a distribution for human review.
 *   5. Correct-option position (A-D) distribution is reported; heavy skew to
 *      one slot fails (display is shuffled client-side, but source hygiene
 *      still matters).
 *
 * Run after every batch:  node tools/validate_daily_bank.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const LANGS = ['en', 'es', 'fr', 'pt'];
const LEN_RATIO_FAIL = 1.45;
const LEN_RATIO_WARN = 1.32;

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'scalpel', 'templates', 'index.html'), 'utf8');

// Bracket-matcher aware of strings AND comments.
function sliceArray(name) {
  const decl = html.indexOf('const ' + name);
  if (decl < 0) return null;
  const start = html.indexOf('[', decl);
  let depth = 0, end = -1, inStr = null, esc = false, inLC = false, inBC = false;
  for (let i = start; i < html.length; i++) {
    const ch = html[i], nx = html[i + 1];
    if (inLC) { if (ch === '\n') inLC = false; continue; }
    if (inBC) { if (ch === '*' && nx === '/') { inBC = false; i++; } continue; }
    if (inStr) {
      if (esc) esc = false;
      else if (ch === '\\') esc = true;
      else if (ch === inStr) inStr = null;
      continue;
    }
    if (ch === '/' && nx === '/') { inLC = true; i++; continue; }
    if (ch === '/' && nx === '*') { inBC = true; i++; continue; }
    if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
    if (ch === '[') depth++;
    else if (ch === ']') { depth--; if (depth === 0) { end = i; break; } }
  }
  if (end < 0) return null;
  return html.slice(start, end + 1);
}

const src = sliceArray('DAILY_BANK');
if (!src) { console.error('DAILY_BANK not found in index.html'); process.exit(1); }
const sandbox = {};
vm.createContext(sandbox);
const BANK = vm.runInContext('(' + src + ')', sandbox, { timeout: 8000 });
if (!Array.isArray(BANK)) { console.error('DAILY_BANK did not eval to an array'); process.exit(1); }

let fails = 0, warns = 0;
const posHist = [0, 0, 0, 0];
const rankHist = { longest: 0, shortest: 0, middle: 0 };

BANK.forEach((q, qi) => {
  const tag = `#${qi + 1} (${q.m || '?'} / ${q.topic || '?'})`;
  const fail = (msg) => { console.error(`FAIL ${tag}: ${msg}`); fails++; };
  const warn = (msg) => { console.warn(`warn ${tag}: ${msg}`); warns++; };

  LANGS.forEach(l => {
    if (!q.q || !q.q[l] || !q.q[l].trim()) fail(`question missing lang '${l}'`);
    if (!q.exp || !q.exp[l] || !q.exp[l].trim()) fail(`explanation missing lang '${l}'`);
  });
  if (!Array.isArray(q.opts) || q.opts.length !== 4) { fail(`needs exactly 4 options, has ${q.opts ? q.opts.length : 0}`); return; }
  const okIdx = q.opts.map((o, i) => o.ok === true ? i : -1).filter(i => i >= 0);
  if (okIdx.length !== 1) { fail(`must have exactly ONE ok:true, has ${okIdx.length}`); return; }
  posHist[okIdx[0]]++;

  LANGS.forEach(l => {
    const lens = q.opts.map((o, i) => {
      if (!o.t || !o.t[l] || !o.t[l].trim()) { fail(`option ${i + 1} missing lang '${l}'`); return 1; }
      return o.t[l].length;
    });
    const mx = Math.max(...lens), mn = Math.min(...lens), ratio = mx / mn;
    if (ratio > LEN_RATIO_FAIL) fail(`[${l}] option length ratio ${ratio.toFixed(2)} > ${LEN_RATIO_FAIL} (lens: ${lens.join('/')})`);
    else if (ratio > LEN_RATIO_WARN) warn(`[${l}] option length ratio ${ratio.toFixed(2)} (lens: ${lens.join('/')})`);
    if (l === 'en') {
      const sorted = [...lens].sort((a, b) => b - a);
      const cl = lens[okIdx[0]];
      if (cl === sorted[0]) rankHist.longest++;
      else if (cl === sorted[3]) rankHist.shortest++;
      else rankHist.middle++;
    }
  });
});

console.log(`\nDAILY_BANK: ${BANK.length} questions`);
console.log(`correct-position histogram [A,B,C,D]: [${posHist.join(', ')}]`);
console.log(`correct-length rank (en): longest=${rankHist.longest} middle=${rankHist.middle} shortest=${rankHist.shortest}`);
const maxPos = Math.max(...posHist), total = BANK.length || 1;
if (BANK.length >= 20 && maxPos / total > 0.5) { console.error('FAIL: >50% of correct answers share one position'); fails++; }
if (BANK.length >= 20 && (rankHist.longest / total > 0.6)) { console.error('FAIL: correct answer is the longest option >60% of the time'); fails++; }
console.log(fails ? `\n${fails} FAILURES, ${warns} warnings` : `\nALL CHECKS PASSED (${warns} warnings)`);
process.exit(fails ? 1 : 0);
