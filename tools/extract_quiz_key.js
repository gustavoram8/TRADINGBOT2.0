#!/usr/bin/env node
/*
 * Quiz answer-key extractor.
 *
 * Reads the canonical QUESTION_BANK (practice quiz) and DAILY_BANK (dedicated
 * Daily Challenge pool) out of scalpel/templates/index.html and emits
 * scalpel/quiz_answer_key.json — the per-question correct option index the
 * SERVER uses to validate Daily Challenge / Quiz answers. This exists so a
 * client can never just assert "I was correct": it must submit which option it
 * picked, and the server judges it against this key.
 *
 * It evaluates the real arrays in a sandbox (not regex), so it stays exact
 * even as questions are edited. NOTHING about the questions/answers is
 * changed — this only derives a key from them.
 *
 * Run after editing QUESTION_BANK or DAILY_BANK:
 *   node tools/extract_quiz_key.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const htmlPath = path.join(root, 'scalpel', 'templates', 'index.html');
const outPath = path.join(root, 'scalpel', 'quiz_answer_key.json');

const html = fs.readFileSync(htmlPath, 'utf8');

// Slice out `const <name> = [ ... ];` by matching brackets from the first '['
// after the declaration — aware of strings and comments.
function sliceArray(name, required) {
  const decl = html.indexOf('const ' + name);
  if (decl < 0) {
    if (required) { console.error(name + ' not found'); process.exit(1); }
    return null;
  }
  const start = html.indexOf('[', decl);
  let depth = 0, end = -1, inStr = null, esc = false, inLC = false, inBC = false;
  for (let i = start; i < html.length; i++) {
    const ch = html[i], nx = html[i + 1];
    if (inLC) { if (ch === '\n') inLC = false; continue; }
    if (inBC) { if (ch === '*' && nx === '/') { inBC = false; i++; } continue; }
    if (inStr) {
      if (esc) { esc = false; }
      else if (ch === '\\') { esc = true; }
      else if (ch === inStr) { inStr = null; }
      continue;
    }
    if (ch === '/' && nx === '/') { inLC = true; i++; continue; }
    if (ch === '/' && nx === '*') { inBC = true; i++; continue; }
    if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
    if (ch === '[') depth++;
    else if (ch === ']') { depth--; if (depth === 0) { end = i; break; } }
  }
  if (end < 0) { console.error('Could not match ' + name + ' brackets'); process.exit(1); }
  return html.slice(start, end + 1);
}

function evalArray(src, name) {
  const sandbox = {};
  vm.createContext(sandbox);
  const arr = vm.runInContext('(' + src + ')', sandbox, { timeout: 8000 });
  if (!Array.isArray(arr)) { console.error(name + ' did not eval to an array'); process.exit(1); }
  return arr;
}

function correctIndex(q) {
  const opts = Array.isArray(q.opts) ? q.opts : [];
  for (let i = 0; i < opts.length; i++) { if (opts[i] && opts[i].ok === true) return i; }
  return -1;
}

// Practice quiz bank — key preserves level so the server can build pools.
const BANK = evalArray(sliceArray('QUESTION_BANK', true), 'QUESTION_BANK');
const key = BANK.map((q) => ({ lv: q.lv || '', ans: correctIndex(q) }));
const missing = key.filter((k) => k.ans < 0).length;

// Dedicated Daily Challenge bank (may not exist yet in older checkouts).
const dailySrc = sliceArray('DAILY_BANK', false);
const daily = dailySrc
  ? evalArray(dailySrc, 'DAILY_BANK').map(correctIndex)
  : [];
const dailyMissing = daily.filter((a) => a < 0).length;

fs.writeFileSync(outPath, JSON.stringify(
  { count: key.length, key, daily_count: daily.length, daily }, null, 0));
console.log(`Wrote ${outPath}: ${key.length} questions (${missing} with no marked answer); ` +
            `daily bank: ${daily.length} (${dailyMissing} with no marked answer).`);
