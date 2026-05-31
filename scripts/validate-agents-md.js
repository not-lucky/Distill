#!/usr/bin/env node
/**
 * AGENTS.md accuracy validator for Distill.
 *
 * Walks the AGENTS.md file and checks that:
 *  1. Every relative path it references exists in the repository.
 *  2. Every command inside a fenced code block matches a known npm/uv
 *     script, a `node <project>.js` invocation, or a standard shell
 *     tool. Lines that look like commands but match nothing are flagged
 *     as suspicious.
 *
 * Designed to fail fast in CI: AGENTS.md is the agent contract, and a
 * stale reference (a path that was renamed, a script that was deleted)
 * silently sends agents down broken paths.
 *
 * Run with:  node scripts/validate-agents-md.js
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOT = process.cwd();
const AGENTS_MD = join(ROOT, 'AGENTS.md');
const REPORT_PATH = join(ROOT, 'reports', 'agents-md-validation.md');

// Commands we trust implicitly because they are part of npm/uv/standard
// Unix tooling and the AGENTS.md block quotes them verbatim from the
// project's own package.json.
const NPM_SCRIPTS = new Set([
  'test',
  'test:js',
  'test:py',
  'lint',
  'lint:fix',
  'format',
  'format:check',
  'typecheck',
  'deadcode',
  'deps:check',
  'duplication',
  'todo:scan',
  'oversize',
  'coverage',
]);

const UV_SCRIPTS = new Set([
  'pytest',
  'ruff check',
  'ruff format',
  'ty check src',
  'vulture src',
  'deptry .',
]);

const SHELL_TOOLS = new Set([
  'git',
  'npx',
  'uv',
  'npm',
  'echo',
  'cp',
  'mv',
  'rm',
  'cd',
  'ls',
  'mkdir',
  'cat',
  'sed',
  'awk',
  'grep',
  'find',
  'curl',
  'tar',
  'source',
]);

function findReferencedPaths(md) {
  // Match a backtick-wrapped path. Accepts:
  //  - absolute paths (`/foo/bar`)
  //  - relative paths starting with `./` or `../`
  //  - repo-relative paths that contain a `/` AND a known file extension
  //    (e.g. `src/cli.js`, `eslint.config.js`)
  //  - repo-relative paths that start with `scripts/`, `src/`, `tests/`,
  //    `examples/`, `docs/`, `reports/`, `coverage/`, `output/`, `logs/`,
  //    or any path the project's directory layout defines as code.
  // The point is to flag things that *look* like filesystem references
  // (paths in code blocks, file tables, etc.) without picking up
  // identifiers like `import-x/extensions` (an ESLint rule name).
  const TOP_DIRS = new Set([
    'src',
    'scripts',
    'tests',
    'examples',
    'docs',
    'reports',
    'coverage',
    'output',
    'logs',
    'schemas',
    'site',
    '.github',
  ]);
  const KNOWN_EXTS = [
    '.js',
    '.mjs',
    '.cjs',
    '.ts',
    '.tsx',
    '.py',
    '.json',
    '.yaml',
    '.yml',
    '.md',
    '.txt',
    '.sh',
    '.css',
    '.html',
    '.apkg',
  ];
  const pathRe = /`([^`\s]+)`/g;
  const out = new Set();
  let m;
  while ((m = pathRe.exec(md)) !== null) {
    const candidate = m[1];
    if (candidate.startsWith('http')) continue;
    if (candidate.includes(' ')) continue;
    // Single-token identifiers (no slashes) are not file paths.
    if (!candidate.includes('/')) continue;
    const first = candidate.split('/')[0];
    const hasKnownExt = KNOWN_EXTS.some((ext) => candidate.endsWith(ext));
    const startsAbsolute = candidate.startsWith('/');
    const startsRelative = candidate.startsWith('./') || candidate.startsWith('../');
    const isTopLevel = TOP_DIRS.has(first);
    if (!startsAbsolute && !startsRelative && !isTopLevel && !hasKnownExt) continue;
    out.add(candidate);
  }
  return [...out];
}

function findCodeBlocks(md) {
  const out = [];
  const re = /```(\w*)\n([\s\S]*?)```/g;
  let m;
  while ((m = re.exec(md)) !== null) {
    out.push({ lang: m[1], body: m[2] });
  }
  return out;
}

function isNpmScript(line) {
  const m1 = line.match(/^\s*npm\s+run\s+([A-Za-z0-9_:-]+)/);
  if (m1 && NPM_SCRIPTS.has(m1[1])) return true;
  return /^\s*npm\s+test\b/.test(line);
}

function isUvScript(line) {
  const m = line.match(/^\s*uv\s+run\s+(.+)$/);
  if (!m) return false;
  return UV_SCRIPTS.has(m[1].trim());
}

function isNodeScript(line) {
  return /^\s*node\s+(src\/[A-Za-z0-9_./-]+\.js|scripts\/[A-Za-z0-9_./-]+\.js)/.test(line);
}

function isShellTool(line) {
  const m = line.match(/^\s*([A-Za-z][A-Za-z0-9_-]*)\b/);
  if (!m) return false;
  return SHELL_TOOLS.has(m[1]);
}

function validateCommands(blocks) {
  const issues = [];
  for (const block of blocks) {
    if (!block.lang || !['bash', 'sh', 'shell', ''].includes(block.lang)) continue;
    for (const raw of block.body.split('\n')) {
      const line = raw.replace(/#.*$/, '').trim();
      if (!line) continue;
      if (isNpmScript(line) || isUvScript(line) || isNodeScript(line) || isShellTool(line)) {
        continue;
      }
      issues.push(line);
    }
  }
  return issues;
}

function validatePaths(refs) {
  const issues = [];
  for (const ref of refs) {
    if (ref.startsWith('/')) continue; // absolute path; out of scope
    const cleanPath = ref.split('#')[0];
    if (!cleanPath) continue;
    const abs = resolve(ROOT, cleanPath);
    if (!existsSync(abs)) {
      issues.push(ref);
    }
  }
  return issues;
}

function main() {
  if (!existsSync(AGENTS_MD)) {
    console.error('[validate-agents-md] FAIL: AGENTS.md not found at repo root.');
    process.exit(1);
  }
  const md = readFileSync(AGENTS_MD, 'utf8');
  const refs = findReferencedPaths(md);
  const blocks = findCodeBlocks(md);

  const missing = validatePaths(refs);
  const suspicious = validateCommands(blocks);

  const lines = [];
  lines.push('# AGENTS.md validation report');
  lines.push('');
  lines.push(`Generated: ${new Date().toISOString()}`);
  lines.push(`Referenced paths checked: ${refs.length}`);
  lines.push(`Code blocks checked: ${blocks.length}`);
  lines.push(`Missing paths: ${missing.length}`);
  lines.push(`Suspicious commands: ${suspicious.length}`);
  lines.push('');

  if (missing.length) {
    lines.push('## Missing paths');
    lines.push('');
    for (const m of missing) lines.push(`- \`${m}\``);
    lines.push('');
  }

  if (suspicious.length) {
    lines.push('## Suspicious commands');
    lines.push('');
    lines.push(
      'These lines are inside a code block but do not match a known npm/uv/node script or a standard tool. Review and either classify them in the script or move them out of the code block.',
    );
    lines.push('');
    for (const s of suspicious) lines.push(`- \`${s}\``);
    lines.push('');
  }

  mkdirSync(join(ROOT, 'reports'), { recursive: true });
  writeFileSync(REPORT_PATH, lines.join('\n'));

  console.log(
    `[validate-agents-md] ${refs.length} paths, ${blocks.length} blocks, ${missing.length} missing, ${suspicious.length} suspicious.`,
  );

  if (missing.length > 0) {
    console.error(
      `[validate-agents-md] FAIL: ${missing.length} paths in AGENTS.md do not exist on disk.`,
    );
    process.exit(1);
  }
}

main();
