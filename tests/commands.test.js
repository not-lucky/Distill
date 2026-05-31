/**
 * Tests for src/commands/* — CLI command orchestrators.
 *
 * Covers:
 *   - src/commands/_log.js    (resolveLogLevel)
 *   - src/commands/compile.js (resolveOutputPath, compileAction)
 *   - src/commands/cache.js   (cacheAction)
 *   - src/commands/run.js     (all helpers + runAction)
 *
 * Mocking strategy
 * ----------------
 * The action wrappers import collaborators (loadConfig, runPipeline,
 * spawnCompiler, ingestDirectory, etc.) from sibling src/ modules. To
 * intercept those calls we use `vi.mock` at the top of this file: each
 * external module is replaced with a partial mock that keeps the real
 * exports and stubs only the functions the wrappers invoke.
 *
 * The injected `exit` function behaves like a real `process.exit`:
 * it throws a sentinel error so callers stop executing immediately.
 * This matches the real cli.js `exit` (which calls process.exit)
 * without actually killing the vitest worker.
 */
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import fsp from 'fs/promises';
import os from 'os';
import path from 'path';
import { resolveLogLevel } from '../src/commands/_log.js';
import { compileAction, resolveOutputPath } from '../src/commands/compile.js';
import { cacheAction } from '../src/commands/cache.js';
import {
  runAction,
  assertValidCardType,
  pushDocumentQuestion,
  buildTopicQuestions,
  findSubjectKey,
  presetToQuestions,
  resolveQuestions,
} from '../src/commands/run.js';
import { loadConfig } from '../src/config.js';
import { initDatabase, closeDatabase, clearCache, getCacheStats } from '../src/database.js';
import { spawnCompiler } from '../src/pipeline/compiler.js';
import { runPipeline } from '../src/pipeline/orchestrator.js';
import { ingestDirectory, ingestDocumentSources, loadPreset } from '../src/ingestion.js';
import { setupLogging } from '../src/logger.js';

// ---------------------------------------------------------------------------
// vi.mock declarations — must come before any import that uses the mocks.
// Each mock keeps the real exports and stubs only the functions exercised
// by the wrappers under test.
// ---------------------------------------------------------------------------

vi.mock('../src/config.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, loadConfig: vi.fn(actual.loadConfig) };
});

vi.mock('../src/database.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    initDatabase: vi.fn(actual.initDatabase),
    closeDatabase: vi.fn(actual.closeDatabase),
    clearCache: vi.fn(actual.clearCache),
    getCacheStats: vi.fn(actual.getCacheStats),
  };
});

vi.mock('../src/pipeline/compiler.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, spawnCompiler: vi.fn(actual.spawnCompiler) };
});

vi.mock('../src/pipeline/orchestrator.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, runPipeline: vi.fn(actual.runPipeline) };
});

vi.mock('../src/ingestion.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    ingestDirectory: vi.fn(actual.ingestDirectory),
    ingestDocumentSources: vi.fn(actual.ingestDocumentSources),
    loadPreset: vi.fn(actual.loadPreset),
  };
});

vi.mock('../src/logger.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    setupLogging: vi.fn(actual.setupLogging),
    getLogger: actual.getLogger, // not mocked; used for diagnostic output
  };
});

/**
 * Sentinel "exit" function used by every wrapper test.
 *
 *   - exit(0) returns a resolved promise; callers continue normally so
 *     we can verify post-success side effects (mock calls, console.log,
 *     database close, etc.).
 *   - exit(non-zero) throws a sentinel so callers halt immediately,
 *     mirroring the behaviour of `process.exit(1)` injected by cli.js.
 *
 * Tests that exercise an error path use `.rejects.toThrow(/__exit__:<n>/)`
 * to assert both the error code and the halt. Tests that exercise the
 * happy path wait for the returned promise and inspect side effects.
 */
function fatalExit(code) {
  if (code === 0) return Promise.resolve();
  throw new Error(`__exit__:${code}`);
}

const baseConfig = () => ({
  global: {
    cache_db_path: './distill.db',
    output_dir: './output',
    log_level: 'info',
  },
  keys: {},
  prompts: {},
});

const sourceQuestion = () => ({
  deckPath: 'A',
  content: 'content',
  filePath: '/x/a.md',
});

let consoleLogSpy;
let consoleErrorSpy;

beforeEach(() => {
  consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  // Clear call history on every vi.fn so per-test assertions on mock.calls
  // (e.g. `runPipeline.mock.calls[0][0]`) read the *current* test's
  // invocation, not a stale one from a previous test.
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// _log.js — resolveLogLevel
// ---------------------------------------------------------------------------

describe('resolveLogLevel', () => {
  it('returns "debug" when --verbose is set, regardless of default', () => {
    expect(resolveLogLevel({ verbose: true }, 'info')).toBe('debug');
    expect(resolveLogLevel({ verbose: true }, 'error')).toBe('debug');
  });

  it('returns "error" when --quiet is set, regardless of default', () => {
    expect(resolveLogLevel({ quiet: true }, 'info')).toBe('error');
    expect(resolveLogLevel({ quiet: true }, 'debug')).toBe('error');
  });

  it('--verbose wins when both --verbose and --quiet are set', () => {
    // The order in the source checks verbose first; both flags is a user error
    // but the function should not crash and should pick verbose.
    expect(resolveLogLevel({ verbose: true, quiet: true }, 'info')).toBe('debug');
  });

  it('returns the default when neither flag is set', () => {
    expect(resolveLogLevel({}, 'info')).toBe('info');
    expect(resolveLogLevel({}, 'warn')).toBe('warn');
  });

  it('falls back to "info" when no flags and no default are provided', () => {
    expect(resolveLogLevel({}, undefined)).toBe('info');
    expect(resolveLogLevel({})).toBe('info');
  });
});

// ---------------------------------------------------------------------------
// compile.js — resolveOutputPath
// ---------------------------------------------------------------------------

describe('resolveOutputPath', () => {
  it('returns the explicit --output path when provided', () => {
    const out = resolveOutputPath(
      { output: '/tmp/deck.apkg' },
      { global: { output_dir: './output' } },
    );
    expect(out).toBe('/tmp/deck.apkg');
  });

  it('resolves config.global.output_dir against the current working directory when --output is missing', () => {
    const out = resolveOutputPath({}, { global: { output_dir: './custom-out' } });
    expect(out).toBe(path.resolve(process.cwd(), './custom-out'));
  });

  it('falls back to ./output when neither --output nor config.global.output_dir are set', () => {
    const out = resolveOutputPath({}, {});
    expect(out).toBe(path.resolve(process.cwd(), './output'));
  });

  it('falls back to ./output when config is null or undefined', () => {
    expect(resolveOutputPath({}, null)).toBe(path.resolve(process.cwd(), './output'));
    expect(resolveOutputPath({}, undefined)).toBe(path.resolve(process.cwd(), './output'));
  });
});

// ---------------------------------------------------------------------------
// compile.js — compileAction
// ---------------------------------------------------------------------------

describe('compileAction', () => {
  let tempDir;
  let jsonPath;

  beforeEach(async () => {
    tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'distill-compile-'));
    jsonPath = path.join(tempDir, 'stage3.json');
    await fsp.writeFile(jsonPath, '{}', 'utf8');

    vi.mocked(loadConfig).mockReturnValue({
      config: baseConfig(),
      keys: {},
      prompts: {},
      warnings: [],
    });
    vi.mocked(setupLogging).mockResolvedValue();
    vi.mocked(spawnCompiler).mockResolvedValue({
      code: 0,
      stdout: 'ok stdout',
      stderr: 'ok stderr',
    });
  });

  afterEach(() => {
    if (tempDir && fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('prints an error and exits(1) when the JSON file does not exist', async () => {
    const missing = path.join(tempDir, 'missing.json');
    await expect(compileAction(missing, {}, fatalExit)).rejects.toThrow(/__exit__:1/);
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringMatching(/does not exist/));
    expect(spawnCompiler).not.toHaveBeenCalled();
  });

  it('compiles the JSON file with the explicit --output when provided', async () => {
    const outPath = path.join(tempDir, 'my.apkg');
    await compileAction(jsonPath, { output: outPath }, fatalExit);
    expect(spawnCompiler).toHaveBeenCalledWith(path.resolve(jsonPath), outPath);
    expect(consoleLogSpy).toHaveBeenCalledWith('ok stdout');
    expect(consoleErrorSpy).toHaveBeenCalledWith('ok stderr');
  });

  it('falls back to config.global.output_dir when --output is missing', async () => {
    vi.mocked(loadConfig).mockReturnValue({
      config: { global: { output_dir: './configured-out', log_level: 'info' } },
      keys: {},
      prompts: {},
      warnings: [],
    });

    await compileAction(jsonPath, {}, fatalExit);

    const [, outArg] = vi.mocked(spawnCompiler).mock.calls[0];
    expect(outArg).toBe(path.resolve(process.cwd(), './configured-out'));
  });

  it('initialises logging at the requested level before compilation', async () => {
    await compileAction(jsonPath, { verbose: true }, fatalExit);
    expect(setupLogging).toHaveBeenCalledWith({ level: 'debug', logDir: null });
  });

  it('prints an error and exits(1) when spawnCompiler rejects', async () => {
    vi.mocked(spawnCompiler).mockRejectedValue(new Error('compile broke'));

    await expect(compileAction(jsonPath, {}, fatalExit)).rejects.toThrow(/__exit__:1/);
    expect(consoleErrorSpy).toHaveBeenCalledWith('Compilation failed: compile broke');
  });
});

// ---------------------------------------------------------------------------
// cache.js — cacheAction
// ---------------------------------------------------------------------------

describe('cacheAction', () => {
  beforeEach(() => {
    vi.mocked(loadConfig).mockReturnValue({
      config: { global: { cache_db_path: './cache.db', log_level: 'info' } },
      keys: {},
      prompts: {},
      warnings: [],
    });
    vi.mocked(setupLogging).mockResolvedValue();
    vi.mocked(initDatabase).mockImplementation(() => {});
    vi.mocked(closeDatabase).mockImplementation(() => {});
    vi.mocked(clearCache).mockImplementation(() => {});
    vi.mocked(getCacheStats).mockReturnValue({ count: 42 });
  });

  it('prints an error and exits(1) for an unknown action', async () => {
    await expect(cacheAction('wipe', {}, fatalExit)).rejects.toThrow(/__exit__:1/);
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringMatching(/Invalid action "wipe"/));
    expect(initDatabase).not.toHaveBeenCalled();
  });

  it('"clear" action: opens DB, clears cache, closes DB, exits(0)', async () => {
    await cacheAction('clear', {}, fatalExit);

    expect(initDatabase).toHaveBeenCalledWith(path.resolve(process.cwd(), './cache.db'));
    expect(clearCache).toHaveBeenCalledTimes(1);
    expect(consoleLogSpy).toHaveBeenCalledWith('Cache cleared successfully.');
    expect(closeDatabase).toHaveBeenCalledTimes(1);
  });

  it('"stats" action: prints the cached query count from getCacheStats', async () => {
    await cacheAction('stats', {}, fatalExit);

    expect(getCacheStats).toHaveBeenCalledTimes(1);
    expect(consoleLogSpy).toHaveBeenCalledWith('Total cached queries: 42');
    expect(closeDatabase).toHaveBeenCalledTimes(1);
  });

  it('--verbose upgrades the log level to debug', async () => {
    await cacheAction('clear', { verbose: true }, fatalExit);
    expect(setupLogging).toHaveBeenCalledWith({ level: 'debug', logDir: null });
  });

  it('--quiet downgrades the log level to error', async () => {
    await cacheAction('stats', { quiet: true }, fatalExit);
    expect(setupLogging).toHaveBeenCalledWith({ level: 'error', logDir: null });
  });

  it('uses config.global.log_dir when set', async () => {
    vi.mocked(loadConfig).mockReturnValue({
      config: {
        global: { cache_db_path: './x.db', log_level: 'info', log_dir: '/var/log/distill' },
      },
      keys: {},
      prompts: {},
      warnings: [],
    });
    await cacheAction('clear', {}, fatalExit);
    expect(setupLogging).toHaveBeenCalledWith({ level: 'info', logDir: '/var/log/distill' });
  });

  it('prints an error and closes DB if init throws', async () => {
    vi.mocked(initDatabase).mockImplementation(() => {
      throw new Error('disk full');
    });

    await expect(cacheAction('clear', {}, fatalExit)).rejects.toThrow(/__exit__:1/);
    expect(consoleErrorSpy).toHaveBeenCalledWith('Cache command failed: disk full');
    // closeDatabase should still be called from the catch block to avoid leaks.
    expect(closeDatabase).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// run.js — pure helpers (assertValidCardType, pushDocumentQuestion,
// buildTopicQuestions, findSubjectKey)
// ---------------------------------------------------------------------------

describe('assertValidCardType', () => {
  it('returns silently for "standard"', async () => {
    const exit = vi.fn().mockResolvedValue();
    await assertValidCardType('standard', exit);
    expect(exit).not.toHaveBeenCalled();
  });

  it('returns silently for "mcq"', async () => {
    const exit = vi.fn().mockResolvedValue();
    await assertValidCardType('mcq', exit);
    expect(exit).not.toHaveBeenCalled();
  });

  it.each([
    ['Cloze'],
    ['basic'], // case-sensitive
    ['mcq '], // trailing whitespace
    [''],
    ['null'],
  ])('rejects invalid card-type %s and exits(1)', async (bad) => {
    const exit = vi.fn().mockResolvedValue();
    await assertValidCardType(bad, exit);
    expect(exit).toHaveBeenCalledWith(1);
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringMatching(/Invalid card-type/));
  });
});

describe('pushDocumentQuestion', () => {
  it('appends a namespaced question descriptor using the preset prefix', () => {
    const questions = [];
    pushDocumentQuestion(questions, 'ReactDocs', {
      deckPath: 'Basics::Jsx',
      content: 'JSX content',
    });
    expect(questions).toEqual([
      {
        questionId: 'ReactDocs::Basics::Jsx',
        topic: 'Basics::Jsx',
        content: 'JSX content',
        categoryName: 'Basics::Jsx',
      },
    ]);
  });

  it('preserves prior entries in the questions array', () => {
    const questions = [{ questionId: 'existing' }];
    pushDocumentQuestion(questions, 'P', { deckPath: 'A::B', content: 'c' });
    expect(questions).toHaveLength(2);
    expect(questions[0]).toEqual({ questionId: 'existing' });
  });
});

describe('buildTopicQuestions', () => {
  it('expands categories/topics into a flat list of namespaced question descriptors', () => {
    const { questions, fmtName } = buildTopicQuestions('LeetCode', [
      { name: 'arrays & hashing', topics: ['two sum', 'group anagrams'] },
      { name: 'two pointers', topics: ['valid palindrome'] },
    ]);
    expect(fmtName).toBe('Leetcode'); // formatNamespaceComponent lowercases non-first chars
    expect(questions).toHaveLength(3);
    expect(questions[0]).toEqual({
      questionId: 'Leetcode::Arrays_&_Hashing::Two_Sum',
      topic: 'two sum',
      categoryName: 'arrays & hashing',
      content: '',
    });
    expect(questions[2].questionId).toBe('Leetcode::Two_Pointers::Valid_Palindrome');
  });

  it('skips null categories and categories without a topics array', () => {
    const { questions } = buildTopicQuestions('P', [
      null,
      { name: 'Empty' /* no topics */ },
      { name: 'HasTopics', topics: ['t1'] },
      { name: 'WrongShape', topics: 'not-an-array' },
    ]);
    expect(questions).toHaveLength(1);
    expect(questions[0].questionId).toBe('P::Hastopics::T1');
  });

  it('returns an empty array when categories is empty', () => {
    expect(buildTopicQuestions('P', []).questions).toEqual([]);
  });

  it('crashes when categories is null/undefined (documents existing behavior)', () => {
    // The source does for (const cat of categories) without a guard; null
    // throws "categories is not iterable". We document the behavior here so
    // future refactors know it's intentional, not a regression.
    expect(() => buildTopicQuestions('P', null)).toThrow(/not iterable/);
    expect(() => buildTopicQuestions('P', undefined)).toThrow(/not iterable/);
  });
});

describe('findSubjectKey', () => {
  const subjects = {
    LeetCode: {},
    JavaScript: {},
    'react basics': {},
  };

  it('finds a subject case-insensitively, preserving the original casing', () => {
    expect(findSubjectKey(subjects, 'leetcode')).toBe('LeetCode');
    expect(findSubjectKey(subjects, 'LEETCODE')).toBe('LeetCode');
    expect(findSubjectKey(subjects, 'react Basics')).toBe('react basics');
  });

  it('returns null when the subject is not present', () => {
    expect(findSubjectKey(subjects, 'python')).toBeNull();
  });

  it('returns null when the subjects map is null, undefined, or empty', () => {
    expect(findSubjectKey(null, 'foo')).toBeNull();
    expect(findSubjectKey(undefined, 'foo')).toBeNull();
    expect(findSubjectKey({}, 'foo')).toBeNull();
  });

  it('crashes when subjectQuery is null (documents existing behavior)', () => {
    // The source does `subjectQuery.toLowerCase()` without a guard; null
    // crashes. Documented here so future refactors know this is intentional.
    expect(() => findSubjectKey(subjects, null)).toThrow();
    expect(() => findSubjectKey(subjects, 123)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// run.js — async helpers (presetToQuestions, resolveQuestions). All external
// I/O is mocked via vi.mock at the top of this file.
// ---------------------------------------------------------------------------

describe('presetToQuestions', () => {
  beforeEach(() => {
    vi.mocked(ingestDocumentSources).mockResolvedValue([]);
  });

  it('returns null when preset is null/undefined', async () => {
    expect(await presetToQuestions(null, 'P', null)).toBeNull();
    expect(await presetToQuestions(undefined, 'P', null)).toBeNull();
  });

  it('routes document-mode presets to ingestDocumentSources', async () => {
    const result = await presetToQuestions({ mode: 'document', folder: './x' }, 'P', '/p.yaml');
    expect(result.mode).toBe('document');
    expect(result.fmtName).toBe('P');
    expect(ingestDocumentSources).toHaveBeenCalledWith({
      folder: path.resolve('/p.yaml'.replace(/[^/]+$/, ''), './x'),
    });
  });

  it('routes topic-mode presets (categories array) to flat question list', async () => {
    const result = await presetToQuestions(
      { categories: [{ name: 'A', topics: ['t'] }] },
      'P',
      '/p.yaml',
    );
    expect(result.mode).toBe('topic');
    expect(result.questions).toHaveLength(1);
    expect(result.questions[0].questionId).toBe('P::A::T');
    expect(result.sources).toBeNull();
  });

  it('returns null when the preset has neither mode nor categories', async () => {
    expect(await presetToQuestions({ name: 'Empty' }, 'P', null)).toBeNull();
  });
});

describe('resolveQuestions', () => {
  let tempDir;

  beforeEach(async () => {
    tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'distill-rq-'));
    vi.mocked(ingestDirectory).mockResolvedValue([]);
    vi.mocked(ingestDocumentSources).mockResolvedValue([]);
    vi.mocked(loadPreset).mockImplementation(async () => ({
      name: 'P',
      categories: [{ name: 'Cat', topics: ['Topic1'] }],
    }));
  });

  afterEach(() => {
    if (tempDir && fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('routes a known subject key (case-insensitive) to the subject-preset loader', async () => {
    const prompts = {
      subjects: {
        LeetCode: { categories: [{ name: 'Arrays', topics: ['Two Sum'] }] },
      },
    };
    const result = await resolveQuestions({
      sourcePath: 'leetcode',
      options: {},
      prompts,
    });
    expect(result.activeSubject).toBe('LeetCode');
    expect(result.questions).toHaveLength(1);
    expect(ingestDirectory).not.toHaveBeenCalled();
  });

  it('subject preset in document mode loads via ingestDocumentSources, not loadPreset', async () => {
    const prompts = {
      subjects: { Docs: { mode: 'document', folder: './notes' } },
    };
    const result = await resolveQuestions({
      sourcePath: 'docs',
      options: {},
      prompts,
    });
    expect(result.activeSubject).toBe('Docs');
    expect(ingestDocumentSources).toHaveBeenCalledTimes(1);
    expect(ingestDirectory).not.toHaveBeenCalled();
    expect(loadPreset).not.toHaveBeenCalled();
  });

  it('document-mode subject preset with `files` resolves relative paths against cwd', async () => {
    // Contract: when the preset specifies a list of files, each one is
    // resolved against process.cwd() before being handed to
    // ingestDocumentSources (so the user can write `./foo.md` etc. in the
    // prompts file without needing to pre-resolve it themselves).
    const prompts = {
      subjects: {
        Docs: {
          mode: 'document',
          files: ['./a.md', './b.md'],
        },
      },
    };
    const result = await resolveQuestions({
      sourcePath: 'docs',
      options: {},
      prompts,
    });
    expect(result.activeSubject).toBe('Docs');
    const callArgs = vi.mocked(ingestDocumentSources).mock.calls[0][0];
    expect(callArgs.folder).toBeUndefined();
    expect(callArgs.files).toEqual([
      path.resolve(process.cwd(), './a.md'),
      path.resolve(process.cwd(), './b.md'),
    ]);
  });

  it('document-mode subject preset that is missing both files and folder returns an error', async () => {
    // Contract: a malformed document-mode preset must surface a clear
    // error rather than silently producing an empty deck.
    const prompts = {
      subjects: { Broken: { mode: 'document' } },
    };
    const result = await resolveQuestions({
      sourcePath: 'broken',
      options: {},
      prompts,
    });
    expect(result.error).toMatch(/missing both "files" and "folder"/);
  });

  it('routes to loadFromPath when no matching subject is found', async () => {
    vi.mocked(ingestDirectory).mockResolvedValue([{ deckPath: 'X', content: 'x', filePath: '/x' }]);
    const result = await resolveQuestions({
      sourcePath: tempDir,
      options: { subject: 'MyDir' },
      prompts: {},
    });
    expect(ingestDirectory).toHaveBeenCalledTimes(1);
    expect(result.activeSubject).toBe('MyDir');
  });

  it('handles prompts=null gracefully (routes to loadFromPath)', async () => {
    // With prompts=null, findSubjectKey returns null, so loadFromPath is used.
    // The tempDir exists, so it scans it.
    const result = await resolveQuestions({
      sourcePath: tempDir,
      options: {},
      prompts: null,
    });
    expect(result.questions).toBeDefined();
    expect(result.activeSubject).toBe(null);
  });

  it('returns an error string when path does not exist and is not a subject preset', async () => {
    const result = await resolveQuestions({
      sourcePath: '/this/does/not/exist',
      options: {},
      prompts: null,
    });
    expect(result.error).toMatch(/does not exist/);
  });

  it('returns an error string for a non-YAML file', async () => {
    const txtPath = path.join(tempDir, 'notes.txt');
    await fsp.writeFile(txtPath, 'plain text', 'utf8');
    const result = await resolveQuestions({
      sourcePath: txtPath,
      options: {},
      prompts: null,
    });
    expect(result.error).toMatch(/not a YAML\/YML preset file/);
  });

  it('subject preset that is neither document-mode nor categories returns an empty deck (not an error)', async () => {
    // Contract: a malformed subject preset (e.g. just `name: Foo` with
    // no body) must not crash; it produces zero questions and uses the
    // subject key as the activeSubject so the run can still complete.
    const prompts = {
      subjects: { Empty: { name: 'Empty' } },
    };
    const result = await resolveQuestions({
      sourcePath: 'empty',
      options: {},
      prompts,
    });
    expect(result.questions).toEqual([]);
    expect(result.activeSubject).toBe('Empty');
    expect(result.error).toBeUndefined();
  });

  it('routes a YAML preset file through loadPreset and returns its categories', async () => {
    // Contract: a .yaml/.yml file at sourcePath is parsed as a preset
    // (categories-based), and its questions become the result. This covers
    // the preset-loading branch that a directory-based source skips.
    const yamlPath = path.join(tempDir, 'preset.yaml');
    await fsp.writeFile(
      yamlPath,
      'name: FromPreset\ncategories:\n  - name: Cat\n    topics: [T1]\n',
      'utf8',
    );
    vi.mocked(loadPreset).mockImplementation(async () => ({
      name: 'FromPreset',
      categories: [{ name: 'Cat', topics: ['T1'] }],
    }));

    const result = await resolveQuestions({
      sourcePath: yamlPath,
      options: { subject: 'MySubject' },
      prompts: null,
    });
    expect(loadPreset).toHaveBeenCalledWith(path.resolve(yamlPath));
    expect(result.questions).toHaveLength(1);
    expect(result.questions[0].questionId).toBe('Frompreset::Cat::T1');
    // explicit --subject option wins over the preset's name.
    expect(result.activeSubject).toBe('MySubject');
  });

  it('routes a document-mode preset file through ingestDocumentSources', async () => {
    // Contract: a preset whose body sets `mode: document` (and folder/files)
    // is loaded from YAML and then its content is collected via
    // ingestDocumentSources. The preset's `name` becomes the activeSubject.
    const yamlPath = path.join(tempDir, 'docs.yaml');
    await fsp.writeFile(yamlPath, 'name: Docs\n', 'utf8');
    vi.mocked(loadPreset).mockImplementation(async () => ({
      name: 'Docs',
      mode: 'document',
      folder: './notes',
    }));
    vi.mocked(ingestDocumentSources).mockResolvedValue([
      { deckPath: 'A', content: 'content-A' },
      { deckPath: 'B', content: 'content-B' },
    ]);

    const result = await resolveQuestions({
      sourcePath: yamlPath,
      options: {},
      prompts: null,
    });
    // The preset file path goes through loadPreset (and then its content
    // through ingestDocumentSources), not through the directory-walking
    // loadFromPath branch.
    expect(loadPreset).toHaveBeenCalledWith(path.resolve(yamlPath));
    expect(ingestDirectory).not.toHaveBeenCalled();
    expect(result.questions).toHaveLength(2);
    expect(result.questions[0].questionId).toBe('Docs::A');
    expect(result.questions[1].questionId).toBe('Docs::B');
    expect(result.activeSubject).toBe('Docs');
  });

  it('errors on a document-mode preset that is missing both folder and files', async () => {
    // Contract: a malformed document-mode preset must fail loudly with a
    // helpful error rather than silently produce an empty deck.
    const yamlPath = path.join(tempDir, 'broken.yaml');
    await fsp.writeFile(yamlPath, 'name: Broken\n', 'utf8');
    vi.mocked(loadPreset).mockImplementation(async () => ({
      name: 'Broken',
      mode: 'document',
    }));

    const result = await resolveQuestions({
      sourcePath: yamlPath,
      options: {},
      prompts: null,
    });
    expect(result.error).toMatch(/missing both "files" and "folder"/);
  });
});

// ---------------------------------------------------------------------------
// run.js — runAction: end-to-end orchestration
// ---------------------------------------------------------------------------

describe('runAction', () => {
  let tempDir;

  beforeEach(async () => {
    tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'distill-runaction-'));

    vi.mocked(loadConfig).mockReturnValue({
      config: baseConfig(),
      keys: {},
      prompts: {},
      warnings: [],
    });
    vi.mocked(setupLogging).mockResolvedValue();
    vi.mocked(initDatabase).mockImplementation(() => {});
    vi.mocked(closeDatabase).mockImplementation(() => {});
    vi.mocked(runPipeline).mockResolvedValue({
      runId: 'run-1',
      results: [],
      hasFailures: false,
    });
    vi.mocked(ingestDirectory).mockResolvedValue([sourceQuestion()]);
    vi.mocked(ingestDocumentSources).mockResolvedValue([]);
    vi.mocked(loadPreset).mockImplementation(async () => ({
      name: 'P',
      categories: [],
    }));
  });

  afterEach(() => {
    if (tempDir && fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('exits(1) before any side effect when card-type is invalid', async () => {
    await expect(runAction(tempDir, { cardType: 'flash' }, fatalExit)).rejects.toThrow(
      /__exit__:1/,
    );
    expect(loadConfig).not.toHaveBeenCalled();
    expect(runPipeline).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringMatching(/Invalid card-type/));
  });

  it('happy path: loads config, runs pipeline, closes DB, exits(0)', async () => {
    await runAction(tempDir, { cardType: 'standard', config: 'cfg.yaml' }, fatalExit);

    expect(loadConfig).toHaveBeenCalledWith('cfg.yaml');
    expect(setupLogging).toHaveBeenCalledWith({ level: 'info', logDir: null });
    expect(initDatabase).toHaveBeenCalledWith(path.resolve(process.cwd(), './distill.db'));
    expect(runPipeline).toHaveBeenCalledTimes(1);
    const args = vi.mocked(runPipeline).mock.calls[0][0];
    expect(args.subject).toBe(''); // no explicit --subject
    expect(args.cardType).toBe('standard');
    expect(args.outputDir).toBe(path.resolve(process.cwd(), './output'));
    expect(args.resumeRunId).toBeNull();
    expect(args.dryRun).toBe(false);
    expect(closeDatabase).toHaveBeenCalledTimes(1);
    expect(consoleLogSpy).toHaveBeenCalledWith('Pipeline completed successfully.');
  });

  it('exits(1) when no questions are resolved from the source', async () => {
    vi.mocked(ingestDirectory).mockResolvedValue([]);

    await expect(runAction(tempDir, { cardType: 'standard' }, fatalExit)).rejects.toThrow(
      /__exit__:1/,
    );
    expect(runPipeline).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringMatching(/No questions/));
  });

  it('exits(1) when resolveQuestions returns an error string', async () => {
    await expect(
      runAction('/this/does/not/exist', { cardType: 'standard' }, fatalExit),
    ).rejects.toThrow(/__exit__:1/);
    expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringMatching(/does not exist/));
    expect(runPipeline).not.toHaveBeenCalled();
  });

  it('uses the subject from the loaded subject preset as activeSubject', async () => {
    vi.mocked(loadConfig).mockReturnValue({
      config: baseConfig(),
      keys: {},
      prompts: {
        subjects: {
          MySubject: {
            categories: [{ name: 'Cat', topics: ['Topic1'] }],
          },
        },
      },
      warnings: [],
    });

    await runAction('mysubject', { cardType: 'standard' }, fatalExit);

    expect(runPipeline).toHaveBeenCalledTimes(1);
    expect(vi.mocked(runPipeline).mock.calls[0][0].subject).toBe('MySubject');
  });

  it('passes dry-run flag through to runPipeline', async () => {
    await runAction(tempDir, { cardType: 'standard', dryRun: true }, fatalExit);
    expect(vi.mocked(runPipeline).mock.calls[0][0].dryRun).toBe(true);
  });

  it('passes resume id through to runPipeline', async () => {
    await runAction(tempDir, { cardType: 'standard', resume: 'run-resume' }, fatalExit);
    expect(vi.mocked(runPipeline).mock.calls[0][0].resumeRunId).toBe('run-resume');
  });

  it('reports pipeline failures with exit(1)', async () => {
    vi.mocked(runPipeline).mockResolvedValue({
      runId: 'r',
      results: [],
      hasFailures: true,
    });

    await expect(runAction(tempDir, { cardType: 'standard' }, fatalExit)).rejects.toThrow(
      /__exit__:1/,
    );
    expect(consoleErrorSpy).toHaveBeenCalledWith('Pipeline completed with failures.');
  });

  it('on thrown error: closes DB and exits(1) with a readable message', async () => {
    vi.mocked(runPipeline).mockRejectedValue(new Error('pipeline boom'));

    await expect(runAction(tempDir, { cardType: 'standard' }, fatalExit)).rejects.toThrow(
      /__exit__:1/,
    );
    expect(consoleErrorSpy).toHaveBeenCalledWith('Pipeline failed: pipeline boom');
    expect(closeDatabase).toHaveBeenCalled();
  });

  it('uses --verbose / --quiet to choose the log level', async () => {
    await runAction(tempDir, { cardType: 'standard', verbose: true }, fatalExit);
    expect(setupLogging).toHaveBeenLastCalledWith({ level: 'debug', logDir: null });

    await runAction(tempDir, { cardType: 'standard', quiet: true }, fatalExit);
    expect(setupLogging).toHaveBeenLastCalledWith({ level: 'error', logDir: null });
  });
});
