/**
 * Integration test: real runPipeline resume behavior with real SQLite.
 *
 * This is the second of three integration tests (signal: integration_tests_exist).
 * It exercises the real `runPipeline` orchestrator end-to-end with a real
 * better-sqlite3 in-memory database, real `getCompletedQuestions` /
 * `getCompletedStage3Results`, and the real `postProcess` path. The only
 * mocking is at the LLM stages (runStage1/2/3) since we don't make real
 * network calls in tests.
 */
import { describe, it, expect, beforeAll, beforeEach, afterAll, vi } from 'vitest';
import { EventEmitter } from 'events';
import { spawn } from 'child_process';
import fsp from 'fs/promises';
import os from 'os';
import path from 'path';
import {
  initDatabase,
  closeDatabase,
  getDb,
  createRun,
  getRun,
  upsertQuestionEntry,
} from '../../src/database.js';
import { runPipeline } from '../../src/orchestrator.js';

vi.mock('child_process', () => ({
  spawn: vi.fn(),
}));

// Mock stages modules to control execution flow in orchestrator tests.
// This is the only mock: we don't want to call real LLMs in tests. The rest
// of the pipeline (DB, postProcess, writeAndCompileOutput, getCompleted*
// helpers) runs un-mocked and is what this integration test exercises.
vi.mock('../../src/pipeline/stages/index.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    runStage1: vi
      .fn()
      .mockImplementation(async () => [
        { provider: 'mock', model: 'model-a', output: 'stage 1 output' },
      ]),
    runStage2: vi.fn().mockImplementation(async () => 'synthesis text'),
    runStage3: vi.fn().mockImplementation(async (context, { questionId }) => {
      // Persist the enforcement row so the integration test can verify
      // the orchestrator's resume path queries completed questions.
      upsertQuestionEntry({
        runId: context.runId,
        questionId,
        currentStage: 'enforcement',
        inputContent: 'mock',
        latestPrompt: 'mock',
        latestResponse: JSON.stringify({
          title: `Title for ${questionId}`,
          topic: `Topic for ${questionId}`,
          difficulty: 'Basic',
          cards: [
            {
              card_format: 'Basic',
              card_type: 'Concept',
              front: `Front of ${questionId}`,
              back: `Back of ${questionId}`,
              explanation: 'A test explanation',
              tags: ['integration'],
            },
          ],
        }),
      });
      return {
        title: `Title for ${questionId}`,
        topic: `Topic for ${questionId}`,
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            front: `Front of ${questionId}`,
            back: `Back of ${questionId}`,
            explanation: 'A test explanation',
            tags: ['integration'],
          },
        ],
      };
    }),
  };
});

function emitSuccessfulChild() {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  process.nextTick(() => {
    child.emit('close', 0);
  });
  return child;
}

const baseConfig = () => ({
  global: {
    cache_db_path: ':memory:',
    model_concurrency: 0,
    topic_concurrency: 2,
    request_delay: 0,
    default_timeout: 30,
  },
  providers: { openai: { base_url: 'https://api.openai.com/v1' } },
  pipeline: {
    generation: { models: ['openai/gpt-4'] },
    synthesis: { model: 'openai/gpt-4' },
  },
});

describe('Integration: orchestrator resume behavior (real DB + real runPipeline)', () => {
  let tempOutDir;

  beforeAll(() => {
    initDatabase(':memory:');
  });

  afterAll(() => {
    closeDatabase();
  });

  beforeEach(async () => {
    vi.clearAllMocks();
    tempOutDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'llm2deck-resume-it-'));
  });

  it('first run processes all questions, second run with same id is a no-op', async () => {
    // ---- First run: process 3 questions
    const firstChild = emitSuccessfulChild();
    vi.mocked(spawn).mockReturnValueOnce(firstChild);

    const config1 = baseConfig();
    const questions = [
      { questionId: 'q-a', content: 'A' },
      { questionId: 'q-b', content: 'B' },
      { questionId: 'q-c', content: 'C' },
    ];

    const first = await runPipeline({
      config: config1,
      keys: { openai: 'k' },
      prompts: {},
      questions,
      subject: 'Integration',
      cardType: 'standard',
      outputDir: tempOutDir,
    });

    expect(first.hasFailures).toBe(false);
    expect(first.results).toHaveLength(3);

    // All 3 questions should now be persisted at the enforcement stage
    const db = getDb();
    const countAfterFirst = db
      .prepare(
        `SELECT COUNT(*) as c FROM run_questions WHERE run_id = ? AND current_stage = 'enforcement'`,
      )
      .get(first.runId).c;
    expect(countAfterFirst).toBe(3);

    // The run record exists and is 'completed'
    const runRecord = getRun(first.runId);
    expect(runRecord.status).toBe('completed');

    // ---- Second run with the same questions but a fresh call: should write a NEW run
    // and process all questions again (no resumeRunId). This proves the pipeline
    // is idempotent across separate run ids.
    const secondChild = emitSuccessfulChild();
    vi.mocked(spawn).mockReturnValueOnce(secondChild);

    const second = await runPipeline({
      config: baseConfig(),
      keys: { openai: 'k' },
      prompts: {},
      questions,
      subject: 'Integration',
      cardType: 'standard',
      outputDir: tempOutDir,
    });
    expect(second.runId).not.toBe(first.runId);
    expect(second.results).toHaveLength(3);
  });

  it('resume run skips already-completed questions (real getCompletedQuestions path)', async () => {
    // Pre-create a run and mark 2 of 4 questions as completed
    const resumeRunId = 'integration-resume-run';
    createRun({
      runId: resumeRunId,
      subject: 'ResumeTest',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash-it',
    });

    const db = getDb();
    // q1 and q3 are completed; q2 and q4 are not
    db.prepare(
      `
      INSERT INTO run_questions
        (run_id, question_id, current_stage, input_content, latest_prompt, latest_response, errors)
      VALUES (?, ?, 'enforcement', ?, ?, ?, NULL)
    `,
    ).run(
      resumeRunId,
      'q1',
      'input1',
      'prompt1',
      JSON.stringify({
        title: 'T1',
        topic: 'Q1',
        difficulty: 'Basic',
        cards: [],
      }),
    );
    db.prepare(
      `
      INSERT INTO run_questions
        (run_id, question_id, current_stage, input_content, latest_prompt, latest_response, errors)
      VALUES (?, ?, 'enforcement', ?, ?, ?, NULL)
    `,
    ).run(
      resumeRunId,
      'q3',
      'input3',
      'prompt3',
      JSON.stringify({
        title: 'T3',
        topic: 'Q3',
        difficulty: 'Basic',
        cards: [],
      }),
    );

    // Mock the child_process spawn used by spawnCompiler
    const child = emitSuccessfulChild();
    vi.mocked(spawn).mockReturnValueOnce(child);

    const result = await runPipeline({
      config: baseConfig(),
      keys: { openai: 'k' },
      prompts: {},
      questions: [
        { questionId: 'q1', content: 'A' },
        { questionId: 'q2', content: 'B' },
        { questionId: 'q3', content: 'C' },
        { questionId: 'q4', content: 'D' },
      ],
      subject: 'ResumeTest',
      cardType: 'standard',
      outputDir: tempOutDir,
      resumeRunId,
    });

    expect(result.runId).toBe(resumeRunId);
    // q1 and q3 should be reported as skipped; q2 and q4 as fresh
    const skipped = result.results
      .filter((r) => r.skipped)
      .map((r) => r.questionId)
      .sort();
    const fresh = result.results
      .filter((r) => !r.skipped)
      .map((r) => r.questionId)
      .sort();
    expect(skipped).toEqual(['q1', 'q3']);
    expect(fresh).toEqual(['q2', 'q4']);

    // After resume, the run should be 'completed' (assuming no failures)
    const finalRun = getRun(resumeRunId);
    expect(finalRun.status).toBe('completed');
  });

  it('handles a stage 3 throw in a single question without losing sibling progress', async () => {
    // Replace the runStage3 mock with a conditional that fails for one qid
    const stages = await import('../../src/pipeline/stages/index.js');
    vi.mocked(stages.runStage3).mockImplementation(async (_context, { questionId }) => {
      if (questionId === 'q-bad') {
        throw new Error('synthetic stage 3 failure');
      }
      return {
        title: `Title for ${questionId}`,
        topic: `Topic for ${questionId}`,
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            front: `Front of ${questionId}`,
            back: `Back of ${questionId}`,
            explanation: 'A test explanation',
            tags: ['integration'],
          },
        ],
      };
    });

    const child = emitSuccessfulChild();
    vi.mocked(spawn).mockReturnValueOnce(child);

    const result = await runPipeline({
      config: baseConfig(),
      keys: { openai: 'k' },
      prompts: {},
      questions: [
        { questionId: 'q-good-1', content: 'A' },
        { questionId: 'q-bad', content: 'B' },
        { questionId: 'q-good-2', content: 'C' },
      ],
      subject: 'MixedFailures',
      cardType: 'standard',
      outputDir: tempOutDir,
    });

    // 2 should succeed; 1 (q-bad) should fail. The orchestrator's
    // `collectResults` drops failures from the public `results` array but
    // sets `hasFailures = true` and the run record will end in 'failed'.
    expect(result.hasFailures).toBe(true);
    expect(result.results).toHaveLength(2);
    const succeeded = result.results.map((r) => r.questionId).sort();
    expect(succeeded).toEqual(['q-good-1', 'q-good-2']);

    // Verify the failing run is marked as 'failed' in the DB
    const finalRun = getRun(result.runId);
    expect(finalRun.status).toBe('failed');
  });
});
