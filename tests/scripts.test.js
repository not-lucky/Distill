import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

const REPO = process.cwd();
const SCRIPTS = join(REPO, 'scripts');
const SCHEMAS = join(REPO, 'schemas');
const REPORTS = join(REPO, 'reports');

function runNodeScript(script, args = []) {
  return execFileSync('node', [join(SCRIPTS, script), ...args], {
    cwd: REPO,
    encoding: 'utf8',
  });
}

describe('scripts/export-schemas.js', () => {
  beforeAll(() => {
    mkdirSync(REPORTS, { recursive: true });
  });

  afterAll(() => {
    // Re-run the export so the repo is left in a consistent state for
    // subsequent test files.
    runNodeScript('export-schemas.js');
  });

  it('writes the published deck and card JSON Schema files', () => {
    runNodeScript('export-schemas.js');
    expect(existsSync(join(SCHEMAS, 'stage3-deck.schema.json'))).toBe(true);
    expect(existsSync(join(SCHEMAS, 'stage3-card.schema.json'))).toBe(true);
  });

  it('emits draft-07 schemas with a $id', () => {
    runNodeScript('export-schemas.js');
    const deck = JSON.parse(readFileSync(join(SCHEMAS, 'stage3-deck.schema.json'), 'utf8'));
    const card = JSON.parse(readFileSync(join(SCHEMAS, 'stage3-card.schema.json'), 'utf8'));
    expect(deck.$schema).toBe('http://json-schema.org/draft-07/schema#');
    expect(deck.$id).toMatch(/stage3-deck\.schema\.json$/);
    expect(card.$schema).toBe('http://json-schema.org/draft-07/schema#');
    expect(card.$id).toMatch(/stage3-card\.schema\.json$/);
  });

  it('the deck schema accepts a single topic and an array of topics', () => {
    runNodeScript('export-schemas.js');
    const deck = JSON.parse(readFileSync(join(SCHEMAS, 'stage3-deck.schema.json'), 'utf8'));
    expect(Array.isArray(deck.oneOf)).toBe(true);
    const titles = deck.oneOf.map((s) => s.title);
    expect(titles).toContain('Single topic');
    expect(titles).toContain('Array of topics');
  });
});

describe('scripts/validate-agents-md.js', () => {
  beforeAll(() => {
    mkdirSync(REPORTS, { recursive: true });
  });

  it('passes on the current AGENTS.md', () => {
    const out = runNodeScript('validate-agents-md.js');
    expect(out).toMatch(/0 missing/);
    expect(out).toMatch(/0 suspicious/);
  });

  it('writes a Markdown report', () => {
    runNodeScript('validate-agents-md.js');
    const reportPath = join(REPORTS, 'agents-md-validation.md');
    expect(existsSync(reportPath)).toBe(true);
    const report = readFileSync(reportPath, 'utf8');
    expect(report).toMatch(/^# AGENTS\.md validation report/m);
  });

  it('flags a missing path when validating a stub that references a non-existent file', () => {
    const tmp = join(REPO, '.tmp-agents-md-validation');
    mkdirSync(tmp, { recursive: true });
    try {
      const fakeAgents = join(tmp, 'AGENTS.md');
      const fakeReport = join(tmp, 'agents-md-validation.md');
      const stub = [
        '# Stub',
        '',
        'A reference to a real file: `src/cli.js`.',
        'A reference to a missing file: `does/not/exist/please.md`.',
        '',
        '```bash',
        'npm test',
        '```',
        '',
      ].join('\n');
      writeFileSync(fakeAgents, stub);

      const original = readFileSync(join(SCRIPTS, 'validate-agents-md.js'), 'utf8');
      const patched = original
        .replace("const AGENTS_MD = join(ROOT, 'AGENTS.md');", `const AGENTS_MD = '${fakeAgents}';`)
        .replace(
          "const REPORT_PATH = join(ROOT, 'reports', 'agents-md-validation.md');",
          `const REPORT_PATH = '${fakeReport}';`,
        );
      const patchedPath = join(tmp, 'validate-agents-md.js');
      writeFileSync(patchedPath, patched);

      let exitCode = 0;
      let stderr = '';
      try {
        execFileSync('node', [patchedPath], { cwd: REPO, stdio: 'pipe' });
      } catch (err) {
        exitCode = err.status;
        stderr = err.stderr ? err.stderr.toString() : '';
      }
      expect(exitCode).not.toBe(0);
      expect(stderr).toMatch(/FAIL: 1 paths in AGENTS\.md do not exist on disk/);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });
});

describe('scripts/check-oversize.js', () => {
  beforeAll(() => {
    mkdirSync(REPORTS, { recursive: true });
  });

  it('passes on the current src/ and writes a Markdown report', () => {
    const out = runNodeScript('check-oversize.js');
    expect(out).toMatch(/0 over threshold/);
    const reportPath = join(REPORTS, 'oversize-files.md');
    expect(existsSync(reportPath)).toBe(true);
    const report = readFileSync(reportPath, 'utf8');
    expect(report).toMatch(/^# Oversize source files/m);
    expect(report).toMatch(/Threshold: 500 lines/);
  });

  it('fails when a synthetic source file exceeds the threshold', () => {
    const tmp = join(REPO, '.tmp-oversize');
    const fakeSrc = join(tmp, 'src');
    const fakeReport = join(tmp, 'oversize-files.md');
    mkdirSync(fakeSrc, { recursive: true });
    try {
      // 600 newline-terminated lines, all comments, so it's a "real"
      // oversize file from the script's point of view.
      const big = Array.from({ length: 600 }, () => '// line').join('\n') + '\n';
      writeFileSync(join(fakeSrc, 'big.js'), big);
      writeFileSync(join(fakeSrc, 'small.js'), '// tiny\n');

      const original = readFileSync(join(SCRIPTS, 'check-oversize.js'), 'utf8');
      const patched = original
        .replace("const SCAN_DIR = join(ROOT, 'src');", `const SCAN_DIR = '${fakeSrc}';`)
        .replace(
          "const REPORT_PATH = join(ROOT, 'reports', 'oversize-files.md');",
          `const REPORT_PATH = '${fakeReport}';`,
        );
      const patchedPath = join(tmp, 'check-oversize.js');
      writeFileSync(patchedPath, patched);

      let exitCode = 0;
      let stderr = '';
      try {
        execFileSync('node', [patchedPath], { cwd: REPO, stdio: 'pipe' });
      } catch (err) {
        exitCode = err.status;
        stderr = err.stderr ? err.stderr.toString() : '';
      }
      expect(exitCode).not.toBe(0);
      expect(stderr).toMatch(
        /FAIL: 1 file\(s\) exceed 500 lines: \.tmp-oversize\/src\/big\.js \(600\)/,
      );
      const report = readFileSync(fakeReport, 'utf8');
      expect(report).toMatch(/\| \.tmp-oversize\/src\/big\.js \| 600 \| \+100 \|/);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });
});
