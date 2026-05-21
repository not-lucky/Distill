#!/usr/bin/env node
/**
 * Tech-debt scanner for LLM2Deck.
 *
 * Walks src/, tests/, and scripts/ looking for TODO/FIXME/XXX/HACK comments
 * and enforces the `TODO(<TICKET-ID>)` annotation format required by the
 * project's quality bar. Produces a Markdown report at reports/todos.md and
 * exits non-zero if any unannotated markers are found.
 */

import { readFileSync, readdirSync, statSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, relative, extname } from 'node:path';

const ROOT = process.cwd();
const SCAN_DIRS = ['src', 'tests'];
const SELF_FILE = 'scripts/scan-todos.js';
const REPORT_PATH = join(ROOT, 'reports', 'todos.md');

const PATTERN = /\b(TODO|FIXME|XXX|HACK)\b(\([^)]+\))?/g;

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      if (entry === 'node_modules' || entry === '.venv' || entry === '__pycache__') continue;
      out.push(...walk(full));
    } else if (['.js', '.mjs', '.cjs', '.py'].includes(extname(entry))) {
      out.push(full);
    }
  }
  return out;
}

function scanFile(path) {
  const lines = readFileSync(path, 'utf8').split('\n');
  const findings = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    let match;
    PATTERN.lastIndex = 0;
    while ((match = PATTERN.exec(line)) !== null) {
      const [, marker, ticket] = match;
      findings.push({
        line: i + 1,
        marker,
        ticket: ticket || null,
        text: line.trim(),
        annotated: Boolean(ticket),
      });
    }
  }
  return findings;
}

function main() {
  const files = SCAN_DIRS.flatMap((d) => {
    const abs = join(ROOT, d);
    try {
      return walk(abs);
    } catch {
      return [];
    }
  });

  const all = [];
  for (const file of files) {
    if (relative(ROOT, file) === SELF_FILE) continue;
    const findings = scanFile(file);
    for (const f of findings) {
      all.push({ file: relative(ROOT, file), ...f });
    }
  }

  mkdirSync(join(ROOT, 'reports'), { recursive: true });
  const stamp = new Date().toISOString();
  const annotated = all.filter((f) => f.annotated);
  const unannotated = all.filter((f) => !f.annotated);

  const lines = [];
  lines.push(`# Tech-debt markers`);
  lines.push('');
  lines.push(`Generated: ${stamp}`);
  lines.push('');
  lines.push(`Total markers: **${all.length}**`);
  lines.push(`Annotated (TODO(TICKET-123) format): **${annotated.length}**`);
  lines.push(`Unannotated (must add a ticket id): **${unannotated.length}**`);
  lines.push('');

  if (annotated.length > 0) {
    lines.push('## Annotated');
    lines.push('');
    lines.push('| File | Line | Marker | Ticket | Text |');
    lines.push('|------|------|--------|--------|------|');
    for (const f of annotated) {
      lines.push(
        `| ${f.file} | ${f.line} | ${f.marker} | ${f.ticket} | ${f.text.replace(/\|/g, '\\|')} |`,
      );
    }
    lines.push('');
  }

  if (unannotated.length > 0) {
    lines.push('## Unannotated (action required)');
    lines.push('');
    lines.push('| File | Line | Marker | Text |');
    lines.push('|------|------|--------|------|');
    for (const f of unannotated) {
      lines.push(`| ${f.file} | ${f.line} | ${f.marker} | ${f.text.replace(/\|/g, '\\|')} |`);
    }
    lines.push('');
  }

  writeFileSync(REPORT_PATH, lines.join('\n'));
  console.log(
    `[scan-todos] Wrote report to ${relative(ROOT, REPORT_PATH)} (${all.length} markers).`,
  );

  if (unannotated.length > 0) {
    console.error(
      `[scan-todos] FAIL: ${unannotated.length} unannotated markers must be linked to a ticket.`,
    );
    process.exit(1);
  }
}

main();
