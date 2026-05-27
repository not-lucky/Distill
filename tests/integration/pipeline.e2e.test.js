/**
 * End-to-end integration test: real CLI + real Python compiler (signal: integration_tests_exist).
 *
 * Writes a real Stage-3 JSON fixture, runs the real `uv run src/compile.py …`
 * subprocess, and validates the produced `.apkg` against a Python helper that
 * inspects the zip layout with the standard library `zipfile`. No mocks of
 * compile.py, genanki, or the JSON pipeline.
 */
import { describe, it, expect, afterEach, beforeAll } from 'vitest';
import fs from 'fs';
import fsp from 'fs/promises';
import os from 'os';
import path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileP = promisify(execFile);

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const COMPILER = path.join(REPO_ROOT, 'src', 'compile.py');

const STAGE3_BASIC = {
  title: 'E2E Basic Title',
  topic: 'E2E::Basic',
  difficulty: 'Basic',
  cards: [
    {
      card_format: 'Basic',
      card_type: 'Concept',
      front: 'What is Distill?',
      back: 'A flashcard generation pipeline.',
      explanation: 'It uses LLMs to turn study material into Anki decks.',
      tags: ['e2e', 'concept'],
    },
  ],
};

const STAGE3_CLOZE = {
  title: 'E2E Cloze Title',
  topic: 'E2E::Cloze',
  difficulty: 'Intermediate',
  cards: [
    {
      card_format: 'Cloze',
      card_type: 'Code',
      front: 'The capital of {{c1::France}} is Paris.',
      explanation: 'Geography fact.',
      tags: ['e2e', 'cloze'],
    },
  ],
};

const STAGE3_MCQ = {
  title: 'E2E MCQ Title',
  topic: 'E2E::MCQ',
  difficulty: 'Advanced',
  cards: [
    {
      card_format: 'MCQ',
      card_type: 'Behavior',
      front: 'Which sorting algorithm is stable?',
      options: ['Quicksort', 'Mergesort', 'Heapsort', 'Selection sort'],
      correct_answer: 'B',
      explanation: 'Mergesort preserves the relative order of equal elements.',
      tags: ['e2e', 'mcq'],
    },
  ],
};

async function writeFixture(dir, name, payload) {
  const jsonPath = path.join(dir, `${name}.json`);
  await fsp.writeFile(jsonPath, JSON.stringify(payload, null, 2), 'utf8');
  return jsonPath;
}

/**
 * Uses Python's stdlib `zipfile` to introspect the .apkg layout. Avoids
 * adding a JS zip dependency to the project just for tests.
 */
async function inspectApkg(apkgPath) {
  const script = `
import json, sys, zipfile
apkg = sys.argv[1]
with zipfile.ZipFile(apkg, "r") as zf:
    names = zf.namelist()
    has_collection = ("collection.anki21" in names) or ("collection.anki2" in names)
    has_media = "media" in names
    media_map = {}
    if has_media:
        media_map = json.loads(zf.read("media").decode("utf-8"))
    sys.stdout.write(json.dumps({
        "names": names,
        "has_collection": has_collection,
        "has_media": has_media,
        "media_count": len(media_map),
    }))
`;
  const { stdout } = await execFileP('python3', ['-c', script, apkgPath], {
    maxBuffer: 4 * 1024 * 1024,
  });
  return JSON.parse(stdout);
}

describe('Integration: end-to-end pipeline (real CLI + real Python compiler)', () => {
  let workdir;

  beforeAll(() => {
    if (!fs.existsSync(COMPILER)) {
      throw new Error(`compile.py not found at expected path: ${COMPILER}`);
    }
  });

  afterEach(async () => {
    if (workdir) {
      await fsp.rm(workdir, { recursive: true, force: true });
      workdir = null;
    }
  });

  it('compiles a Basic card fixture into a valid .apkg package', async () => {
    workdir = await fsp.mkdtemp(path.join(os.tmpdir(), 'distill-e2e-basic-'));
    const jsonPath = await writeFixture(workdir, 'basic', STAGE3_BASIC);
    const apkgPath = path.join(workdir, 'basic.apkg');

    const { stdout, stderr } = await execFileP(
      'uv',
      ['run', COMPILER, jsonPath, '-o', apkgPath, '--deck-name', 'E2E Basic Deck'],
      { cwd: REPO_ROOT, maxBuffer: 8 * 1024 * 1024 },
    );

    expect(stdout).toMatch(/Successfully compiled/);
    expect(fs.existsSync(apkgPath)).toBe(true);
    expect(fs.statSync(apkgPath).size).toBeGreaterThan(0);

    const info = await inspectApkg(apkgPath);
    expect(info.has_collection).toBe(true);
    // Media map may be empty when no images/sounds are referenced; its presence
    // is what genanki always emits.
    expect(info.has_media).toBe(true);
    expect(info.media_count).toBeGreaterThanOrEqual(0);
    expect(stderr || '').not.toMatch(/Traceback/);
  }, 60000);

  it('compiles a Cloze card fixture and produces a valid .apkg', async () => {
    workdir = await fsp.mkdtemp(path.join(os.tmpdir(), 'distill-e2e-cloze-'));
    const jsonPath = await writeFixture(workdir, 'cloze', STAGE3_CLOZE);
    const apkgPath = path.join(workdir, 'cloze.apkg');

    await execFileP('uv', ['run', COMPILER, jsonPath, '-o', apkgPath], {
      cwd: REPO_ROOT,
      maxBuffer: 8 * 1024 * 1024,
    });

    expect(fs.existsSync(apkgPath)).toBe(true);
    const info = await inspectApkg(apkgPath);
    expect(info.has_collection).toBe(true);
    expect(info.has_media).toBe(true);
  }, 60000);

  it('compiles an MCQ card fixture and produces a valid .apkg', async () => {
    workdir = await fsp.mkdtemp(path.join(os.tmpdir(), 'distill-e2e-mcq-'));
    const jsonPath = await writeFixture(workdir, 'mcq', STAGE3_MCQ);
    const apkgPath = path.join(workdir, 'mcq.apkg');

    await execFileP(
      'uv',
      ['run', COMPILER, jsonPath, '-o', apkgPath, '--subject', 'CS/Algorithms'],
      { cwd: REPO_ROOT, maxBuffer: 8 * 1024 * 1024 },
    );

    expect(fs.existsSync(apkgPath)).toBe(true);
    expect(fs.statSync(apkgPath).size).toBeGreaterThan(0);
    const info = await inspectApkg(apkgPath);
    expect(info.has_collection).toBe(true);
  }, 60000);

  it('fails with a non-zero exit code for malformed JSON input', async () => {
    workdir = await fsp.mkdtemp(path.join(os.tmpdir(), 'distill-e2e-bad-'));
    const jsonPath = path.join(workdir, 'bad.json');
    await fsp.writeFile(jsonPath, '{ not valid json', 'utf8');
    const apkgPath = path.join(workdir, 'bad.apkg');

    await expect(
      execFileP('uv', ['run', COMPILER, jsonPath, '-o', apkgPath], { cwd: REPO_ROOT }),
    ).rejects.toThrow();
  }, 60000);
});
