#!/usr/bin/env node
/**
 * Oversize source-file detector for Distill.
 *
 * Walks src/ looking for *.js and *.py files that exceed a 500-line
 * threshold and fails the build if any are found. Produces a Markdown
 * report at reports/oversize-files.md (alongside reports/todos.md and
 * reports/agents-md-validation.md) so CI can surface the full offender
 * list as an artifact even on a clean run.
 *
 * Replaces an earlier inline bash one-liner in .github/workflows/ci.yml
 * that was matching the aggregate `wc -l` total line and always failing.
 *
 * Run with:  node scripts/check-oversize.js
 */

import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { extname, join, relative } from 'node:path';

const ROOT = process.cwd();
const SCAN_DIR = join(ROOT, 'src');
const REPORT_PATH = join(ROOT, 'reports', 'oversize-files.md');
const THRESHOLD = 500;
const EXTS = new Set(['.js', '.py']);

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      if (entry === 'node_modules' || entry === '.venv' || entry === '__pycache__') continue;
      out.push(...walk(full));
    } else if (EXTS.has(extname(entry))) {
      out.push(full);
    }
  }
  return out;
}

function countLines(path) {
  // Match `wc -l` semantics: number of newline characters.
  const content = readFileSync(path, 'utf8');
  if (content.length === 0) return 0;
  return content.split('\n').length - 1;
}

function main() {
  if (!existsSync(SCAN_DIR)) {
    console.error(`[check-oversize] FAIL: source directory not found at ${SCAN_DIR}.`);
    process.exit(1);
  }

  const files = walk(SCAN_DIR);
  const offenders = [];
  for (const file of files) {
    const lines = countLines(file);
    if (lines > THRESHOLD) {
      offenders.push({ file: relative(ROOT, file), lines });
    }
  }
  offenders.sort((a, b) => b.lines - a.lines);

  mkdirSync(join(ROOT, 'reports'), { recursive: true });
  const stamp = new Date().toISOString();
  const lines = [];
  lines.push('# Oversize source files');
  lines.push('');
  lines.push(`Generated: ${stamp}`);
  lines.push(`Threshold: ${THRESHOLD} lines`);
  lines.push(`Files scanned: ${files.length}`);
  lines.push(`Files over threshold: ${offenders.length}`);
  lines.push('');

  if (offenders.length > 0) {
    lines.push('## Oversize files');
    lines.push('');
    lines.push('| File | Lines | Overshoot |');
    lines.push('|------|-------|-----------|');
    for (const o of offenders) {
      lines.push(`| ${o.file} | ${o.lines} | +${o.lines - THRESHOLD} |`);
    }
    lines.push('');
  }

  writeFileSync(REPORT_PATH, lines.join('\n'));

  if (offenders.length === 0) {
    console.log(
      `[check-oversize] Wrote report to ${relative(ROOT, REPORT_PATH)} (${files.length} files, 0 over threshold).`,
    );
    return;
  }

  for (const o of offenders) {
    process.stderr.write(
      `::error file=${o.file},line=1::${o.file} is ${o.lines} lines (max ${THRESHOLD})\n`,
    );
  }
  const summary = offenders.map((o) => `${o.file} (${o.lines})`).join(', ');
  console.error(
    `[check-oversize] FAIL: ${offenders.length} file(s) exceed ${THRESHOLD} lines: ${summary}`,
  );
  process.exit(1);
}

main();
