#!/usr/bin/env node
/*
 * Quiz answer-key extractor.
 *
 * Reads the canonical QUESTION_BANK out of scalpel/templates/index.html and
 * emits scalpel/quiz_answer_key.json — the per-question correct option index
 * the SERVER uses to validate Daily Challenge / Quiz answers. This exists so a
 * client can never just assert "I was correct": it must submit which option it
 * picked, and the server judges it against this key.
 *
 * It evaluates the real array in a sandbox (not regex), so it stays exact even
 * as questions are edited. NOTHING about the questions/answers is changed —
 * this only derives a key from them.
 *
 * Run after editing QUESTION_BANK:
 *   node tools/extract_quiz_key.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const htmlPath = path.join(root, 'scalpel', 'templates', 'index.html');
const outPath = path.join(root, 'scalpel', 'quiz_answer_key.json');

const html = fs.readFileSync(htmlPath, 'utf8');

// Slice out `const QUESTION_BANK = [ ... ];` by matching brackets from the
// first '[' after the declaration.
const decl = html.indexOf('const QUESTION_BANK');
if (decl < 0) { console.error('QUESTION_BANK not found'); process.exit(1); }
const start = html.indexOf('[', decl);
let depth = 0, end = -1;
let inStr = null, esc = false;
for (let i = start; i < html.length; i++) {
  const ch = html[i];
  if (inStr) {
    if (esc) { esc = false; }
    else if (ch === '\\') { esc = true; }
    else if (ch === inStr) { inStr = null; }
    continue;
  }
  if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
  if (ch === '[') depth++;
  else if (ch === ']') { depth--; if (depth === 0) { end = i; break; } }
}
if (end < 0) { console.error('Could not match QUESTION_BANK brackets'); process.exit(1); }

const arrSrc = html.slice(start, end + 1);
const sandbox = {};
vm.createContext(sandbox);
const BANK = vm.runInContext('(' + arrSrc + ')', sandbox, { timeout: 5000 });

if (!Array.isArray(BANK)) { console.error('QUESTION_BANK did not eval to an array'); process.exit(1); }

// For each question, record its level and the index of the correct option in
// the ORIGINAL opts order (clients send the original index, never a shuffled one).
const key = BANK.map((q) => {
  const opts = Array.isArray(q.opts) ? q.opts : [];
  let ans = -1;
  for (let i = 0; i < opts.length; i++) { if (opts[i] && opts[i].ok === true) { ans = i; break; } }
  return { lv: q.lv || '', ans };
});

const missing = key.filter((k) => k.ans < 0).length;
fs.writeFileSync(outPath, JSON.stringify({ count: key.length, key }, null, 0));
console.log(`Wrote ${outPath}: ${key.length} questions (${missing} with no marked answer).`);
