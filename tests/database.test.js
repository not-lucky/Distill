import {
  describe, it, expect, beforeAll, afterAll, beforeEach, afterEach,
} from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  initDatabase,
  closeDatabase,
  getDb,
  createRun,
  updateRunStatus,
  getRun,
  deleteRun,
  addPipelineStep,
  getPipelineSteps,
  getPipelineStepsForRun,
  getCache,
  setCache,
  clearCache,
  getCacheStats,
  transaction,
} from '../src/database.js';

const FIXTURES_DIR = path.resolve('./tests/fixtures_database');
const TEST_DB_PATH = path.join(FIXTURES_DIR, 'test_llm2deck.db');

describe('Database Module & SQLite Operations', () => {
  beforeAll(() => {
    if (!fs.existsSync(FIXTURES_DIR)) {
      fs.mkdirSync(FIXTURES_DIR, { recursive: true });
    }
  });

  afterAll(() => {
    // Ensure database is closed
    closeDatabase();
    if (fs.existsSync(FIXTURES_DIR)) {
      fs.rmSync(FIXTURES_DIR, { recursive: true, force: true });
    }
  });

  beforeEach(() => {
    // Clean up file if it exists, then initialize fresh database
    closeDatabase();
    if (fs.existsSync(TEST_DB_PATH)) {
      fs.unlinkSync(TEST_DB_PATH);
    }
    // Delete SQLite WAL/SHM artifacts if they remain
    const walFile = `${TEST_DB_PATH}-wal`;
    const shmFile = `${TEST_DB_PATH}-shm`;
    if (fs.existsSync(walFile)) fs.unlinkSync(walFile);
    if (fs.existsSync(shmFile)) fs.unlinkSync(shmFile);

    initDatabase(TEST_DB_PATH);
  });

  afterEach(() => {
    closeDatabase();
  });

  it('should throw error when calling getDb() before initialization', () => {
    closeDatabase();
    expect(() => getDb()).toThrow(/Database is not initialized/);
  });

  it('should correctly initialize tables and indices', () => {
    const db = getDb();

    // Check if runs, pipeline_steps, and llm_cache tables exist
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map((r) => r.name);
    expect(tables).toContain('runs');
    expect(tables).toContain('pipeline_steps');
    expect(tables).toContain('llm_cache');

    // Check if indices exist
    const indices = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((r) => r.name);
    expect(indices).toContain('idx_pipeline_steps_lookup');
    expect(indices).toContain('idx_runs_status');
  });

  it('should support run creation, retrieval, and status updates', () => {
    const runId = 'test-run-123';

    // Create a run
    const res = createRun({
      runId,
      subject: 'LeetCode',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash123',
    });

    expect(res.changes).toBe(1);

    // Retrieve and verify details
    const run = getRun(runId);
    expect(run).toBeDefined();
    expect(run.run_id).toBe(runId);
    expect(run.subject).toBe('LeetCode');
    expect(run.card_type).toBe('standard');
    expect(run.status).toBe('running');
    expect(run.config_hash).toBe('hash123');
    expect(run.created_at).toBeDefined();

    // Update status
    const updateRes = updateRunStatus(runId, 'completed');
    expect(updateRes.changes).toBe(1);

    const updatedRun = getRun(runId);
    expect(updatedRun.status).toBe('completed');

    // Verify non-existent run update throws error
    expect(() => updateRunStatus('non-existent', 'completed')).toThrow(/not found/);
  });

  it('should support run creation with a custom createdAt timestamp', () => {
    const runId = 'test-run-custom-created-at';
    const customTime = '2026-05-31T10:00:00.000Z';

    createRun({
      runId,
      subject: 'LeetCode',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash123',
      createdAt: customTime,
    });

    const run = getRun(runId);
    expect(run).toBeDefined();
    expect(run.created_at).toBe(customTime);
  });

  it('should support pipeline steps insertion and retrieval', () => {
    const runId = 'test-run-456';
    createRun({
      runId,
      subject: 'JavaScript',
      cardType: 'standard',
      status: 'running',
      configHash: 'config456',
    });

    const step1 = {
      runId,
      questionId: 'question-1',
      stage: 'generation',
      provider: 'openai',
      model: 'gpt-3.5-turbo',
      inputData: 'Explain closures',
      outputData: 'A closure is...',
    };

    const step2 = {
      runId,
      questionId: 'question-1',
      stage: 'synthesis',
      provider: 'openai',
      model: 'gpt-4o',
      inputData: 'Combine results',
      outputData: 'Synthesized closure card...',
    };

    addPipelineStep(step1);
    addPipelineStep(step2);

    // Retrieve steps for run & question
    const steps = getPipelineSteps(runId, 'question-1');
    expect(steps.length).toBe(2);
    expect(steps[0].stage).toBe('generation');
    expect(steps[1].stage).toBe('synthesis');

    // Retrieve steps for run only
    const allSteps = getPipelineStepsForRun(runId);
    expect(allSteps.length).toBe(2);
  });

  it('should enforce cascading deletes from runs to pipeline_steps', () => {
    const runId = 'run-to-delete';
    createRun({
      runId,
      subject: 'MERN',
      cardType: 'standard',
      status: 'running',
      configHash: 'config789',
    });

    addPipelineStep({
      runId,
      questionId: 'q-1',
      stage: 'generation',
      provider: 'openai',
      model: 'gpt-3.5-turbo',
      inputData: 'Express route',
      outputData: 'app.get(...)',
    });

    // Verify step exists
    const beforeSteps = getPipelineStepsForRun(runId);
    expect(beforeSteps.length).toBe(1);

    // Delete the run
    const delRes = deleteRun(runId);
    expect(delRes.changes).toBe(1);

    // Verify run is deleted
    expect(getRun(runId)).toBeUndefined();

    // Verify pipeline steps associated with the run are deleted due to ON DELETE CASCADE
    const afterSteps = getPipelineStepsForRun(runId);
    expect(afterSteps.length).toBe(0);
  });

  it('should manage LLM cache keys, overrides, stats, and clearing', () => {
    const cacheKey = 'sha256-hash-key';

    // Check initial cache stats
    expect(getCacheStats().count).toBe(0);

    // Set cache entry
    setCache({
      cacheKey,
      provider: 'openai',
      model: 'gpt-4o',
      promptHash: 'prompt-hash-1',
      response: 'Initial cached response',
    });

    expect(getCacheStats().count).toBe(1);

    // Get cache entry
    const entry = getCache(cacheKey);
    expect(entry).toBeDefined();
    expect(entry.response).toBe('Initial cached response');
    expect(entry.prompt_hash).toBe('prompt-hash-1');

    // Overwrite the same cache key (upsert behavior)
    setCache({
      cacheKey,
      provider: 'openai',
      model: 'gpt-4o',
      promptHash: 'prompt-hash-2',
      response: 'Overwritten cached response',
    });

    // Check count is still 1
    expect(getCacheStats().count).toBe(1);

    const overwrittenEntry = getCache(cacheKey);
    expect(overwrittenEntry.response).toBe('Overwritten cached response');
    expect(overwrittenEntry.prompt_hash).toBe('prompt-hash-2');

    // Clear cache
    clearCache();
    expect(getCacheStats().count).toBe(0);
    expect(getCache(cacheKey)).toBeUndefined();
  });

  it('should support thread-safe parallel insert operations without busy/locking errors', async () => {
    const runId = 'concurrency-run';
    createRun({
      runId,
      subject: 'Concurrency',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash-parallel',
    });

    // Perform many insertions in parallel simulating high-frequency writes
    const insertionCount = 100;
    const promises = [];

    for (let i = 0; i < insertionCount; i++) {
      promises.push((async () => {
        addPipelineStep({
          runId,
          questionId: `parallel-q-${i}`,
          stage: 'generation',
          provider: 'cerebras',
          model: 'llama3',
          inputData: `input-${i}`,
          outputData: `output-${i}`,
        });
      })());
    }

    // Await all parallel write operations
    await Promise.all(promises);

    // Check that all insertions succeeded
    const steps = getPipelineStepsForRun(runId);
    expect(steps.length).toBe(insertionCount);
  });

  it('should execute callbacks in a transaction scope correctly rolling back on error', () => {
    const runId = 'transaction-run';
    createRun({
      runId,
      subject: 'Transactions',
      cardType: 'standard',
      status: 'running',
      configHash: 'tx-hash',
    });

    // Successful transaction
    transaction(() => {
      addPipelineStep({
        runId,
        questionId: 'tx-q-1',
        stage: 'generation',
        provider: 'openai',
        model: 'gpt-3.5',
        inputData: 'data1',
        outputData: 'out1',
      });
      addPipelineStep({
        runId,
        questionId: 'tx-q-2',
        stage: 'generation',
        provider: 'openai',
        model: 'gpt-3.5',
        inputData: 'data2',
        outputData: 'out2',
      });
    });

    const stepsBefore = getPipelineStepsForRun(runId);
    expect(stepsBefore.length).toBe(2);

    // Failing transaction
    expect(() => {
      transaction(() => {
        addPipelineStep({
          runId,
          questionId: 'tx-q-3',
          stage: 'generation',
          provider: 'openai',
          model: 'gpt-3.5',
          inputData: 'data3',
          outputData: 'out3',
        });

        // Intentional error to trigger rollback
        throw new Error('Rollback transaction');
      });
    }).toThrow('Rollback transaction');

    // Verify that tx-q-3 was NOT inserted due to rollback
    const stepsAfter = getPipelineStepsForRun(runId);
    expect(stepsAfter.length).toBe(2); // Still 2, no tx-q-3
  });

  it('should handle nested directory database path creation', () => {
    // Close the standard test DB
    closeDatabase();

    const nestedDbPath = path.join(FIXTURES_DIR, 'nested1/nested2/test_nested.db');
    // Ensure clean state: delete nested database file if present
    if (fs.existsSync(nestedDbPath)) {
      fs.unlinkSync(nestedDbPath);
    }
    const nestedDir = path.join(FIXTURES_DIR, 'nested1/nested2');
    if (fs.existsSync(nestedDir)) {
      fs.rmSync(path.join(FIXTURES_DIR, 'nested1'), { recursive: true, force: true });
    }

    // initDatabase should recursively create parent directories nested1/nested2
    initDatabase(nestedDbPath);
    expect(fs.existsSync(nestedDbPath)).toBe(true);

    // Clean up
    closeDatabase();
    fs.rmSync(path.join(FIXTURES_DIR, 'nested1'), { recursive: true, force: true });
  });

  it('should safely close stale connections when initDatabase is called multiple times', () => {
    // Call initDatabase to open first connection
    const db1 = getDb();

    // Call initDatabase again on standard path to re-initialize
    const db2 = initDatabase(TEST_DB_PATH);

    // db1 should now be closed. Calling prepare on db1 should throw because it is closed.
    expect(() => db1.prepare('SELECT 1')).toThrow(/database connection is not open/);

    // db2 should be open and operational
    expect(db2.prepare('SELECT 1').get()).toEqual({ 1: 1 });
  });

  it('should enforce NOT NULL constraints on runs table', () => {
    // Subject is NOT NULL. Omitting it should throw NOT NULL constraint failed.
    expect(() => {
      createRun({
        runId: 'invalid-run-1',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash',
      });
    }).toThrow(/NOT NULL constraint failed/);
  });

  it('should enforce CHECK constraints on runs and pipeline_steps tables', () => {
    // Status CHECK constraint: must be ('running', 'completed', 'failed')
    expect(() => {
      createRun({
        runId: 'invalid-run-status',
        subject: 'LeetCode',
        cardType: 'standard',
        status: 'invalid_status_value',
        configHash: 'hash',
      });
    }).toThrow(/CHECK constraint failed/);

    // Card type CHECK constraint: must be ('standard', 'mcq')
    expect(() => {
      createRun({
        runId: 'invalid-run-card',
        subject: 'LeetCode',
        cardType: 'invalid_card_type',
        status: 'running',
        configHash: 'hash',
      });
    }).toThrow(/CHECK constraint failed/);

    // Run must exist first for step insertion due to foreign key
    const runId = 'step-check-run';
    createRun({
      runId,
      subject: 'LeetCode',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash',
    });

    // Stage CHECK constraint: must be ('generation', 'synthesis', 'translation', 'enforcement')
    expect(() => {
      addPipelineStep({
        runId,
        questionId: 'q1',
        stage: 'invalid_stage',
        provider: 'openai',
        model: 'gpt-3.5',
        inputData: 'in',
        outputData: 'out',
      });
    }).toThrow(/CHECK constraint failed/);
  });

  it('should enforce PRIMARY KEY unique constraints on runs', () => {
    const runId = 'dup-run-id';
    createRun({
      runId,
      subject: 'LeetCode',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash',
    });

    // Inserting another run with the same primary key run_id should throw
    // UNIQUE/PRIMARY KEY failure
    expect(() => {
      createRun({
        runId,
        subject: 'Other',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash',
      });
    }).toThrow(/UNIQUE constraint failed: runs.run_id/);
  });

  it('should handle non-existent lookup results gracefully', () => {
    // Non-existent run
    expect(getRun('does-not-exist')).toBeUndefined();

    // Non-existent pipeline steps
    expect(getPipelineSteps('does-not-exist', 'q1')).toEqual([]);
    expect(getPipelineStepsForRun('does-not-exist')).toEqual([]);

    // Non-existent cache key
    expect(getCache('does-not-exist')).toBeUndefined();
  });

  it('should support nested transactions using native SQLite savepoints', () => {
    const runId = 'nested-tx-run';
    createRun({
      runId,
      subject: 'Transactions',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash',
    });

    // Outer transaction succeeds, inner transaction fails and rolls back only the inner part
    transaction(() => {
      addPipelineStep({
        runId,
        questionId: 'outer-q',
        stage: 'generation',
        provider: 'openai',
        model: 'gpt-3.5',
        inputData: 'outer-in',
        outputData: 'outer-out',
      });

      // Nested transaction
      try {
        transaction(() => {
          addPipelineStep({
            runId,
            questionId: 'inner-q',
            stage: 'generation',
            provider: 'openai',
            model: 'gpt-3.5',
            inputData: 'inner-in',
            outputData: 'inner-out',
          });
          throw new Error('Rollback nested');
        });
      } catch (err) {
        expect(err.message).toBe('Rollback nested');
      }
    });

    const steps = getPipelineStepsForRun(runId);
    // Outer question was saved, but inner question was rolled back
    const questionIds = steps.map((s) => s.question_id);
    expect(questionIds).toContain('outer-q');
    expect(questionIds).not.toContain('inner-q');
  });

  it('should handle special unicode characters and large inputs', () => {
    const runId = 'special-char-run';
    createRun({
      runId,
      subject: 'Unicode Study 🚀',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash',
    });

    // Large code block and complex unicode text
    const largeUnicodeInput = `const x = "你好, 世界!";\n${'🚀'.repeat(10000)}`;
    const unicodeOutput = 'Output: 🌟 🎏 💖';

    addPipelineStep({
      runId,
      questionId: 'unicode-q',
      stage: 'generation',
      provider: 'openai compatible client',
      model: 'gpt-4o-unicode-🚀',
      inputData: largeUnicodeInput,
      outputData: unicodeOutput,
    });

    const steps = getPipelineSteps(runId, 'unicode-q');
    expect(steps.length).toBe(1);
    expect(steps[0].input_data).toBe(largeUnicodeInput);
    expect(steps[0].output_data).toBe(unicodeOutput);
    expect(steps[0].model).toBe('gpt-4o-unicode-🚀');
  });
});
