import {
  vi, describe, it, expect, beforeEach, afterEach, beforeAll, afterAll,
} from 'vitest';
import { EventEmitter } from 'events';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import {
  initDatabase,
  closeDatabase,
  createRun,
  getRun,
  getPipelineStepsForRun,
  addPipelineStep,
  upsertQuestionEntry,
  getDb,
} from '../src/database.js';
import {
  sanitizeFilename,
  spawnCompiler,
  getCompletedQuestions,
  runPipeline,
} from '../src/orchestrator.js';

vi.mock('../src/database.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    initDatabase: vi.fn().mockImplementation((dbPath) => {
      const targetPath = dbPath === './llm2deck.db' ? './llm2deck_test_fallback.db' : dbPath;
      return actual.initDatabase(targetPath);
    }),
  };
});

vi.mock('child_process', () => ({
  spawn: vi.fn(),
}));

vi.mock('../src/stages.js', () => ({
  runStage1: vi.fn().mockImplementation(async ({ runId, questionId }) => {
    addPipelineStep({
      runId,
      questionId,
      stage: 'generation',
      provider: 'mock-provider',
      model: 'gen-model',
      inputData: 'stage1-input',
      outputData: 'stage1-output',
    });
    return [{ provider: 'mock-provider', model: 'gen-model', output: 'stage1-output' }];
  }),
  runStage2: vi.fn().mockImplementation(async ({ runId, questionId }) => {
    addPipelineStep({
      runId,
      questionId,
      stage: 'synthesis',
      provider: 'mock-provider',
      model: 'synth-model',
      inputData: 'stage2-input',
      outputData: 'stage2-output',
    });
    return 'stage2-output';
  }),
  runStage3: vi.fn().mockImplementation(async ({ runId, questionId }) => {
    addPipelineStep({
      runId,
      questionId,
      stage: 'enforcement',
      provider: 'mock-provider',
      model: 'enforce-model',
      inputData: 'stage3-input',
      outputData: 'stage3-output',
    });
    return {
      title: 'Mock Title',
      topic: 'Mock Topic',
      difficulty: 'Basic',
      cards: [
        {
          card_format: 'Basic',
          card_type: 'Concept',
          tags: ['MockTag'],
          front: 'Front',
          back: 'Back',
        },
      ],
    };
  }),
  cleanJsonOutput: vi.fn().mockImplementation((text) => text),
}));

describe('Orchestrator Module', () => {
  const tempOutputDir = './tests/temp_out';

  beforeAll(() => {
    initDatabase(':memory:');
  });

  afterAll(() => {
    closeDatabase();
    const fallbackDb = './llm2deck_test_fallback.db';
    if (fs.existsSync(fallbackDb)) fs.unlinkSync(fallbackDb);
    if (fs.existsSync(`${fallbackDb}-wal`)) fs.unlinkSync(`${fallbackDb}-wal`);
    if (fs.existsSync(`${fallbackDb}-shm`)) fs.unlinkSync(`${fallbackDb}-shm`);
  });

  beforeEach(() => {
    vi.restoreAllMocks();

    vi.mocked(spawn).mockImplementation(() => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      process.nextTick(() => {
        mockChild.emit('close', 0);
      });
      return mockChild;
    });

    if (!fs.existsSync(tempOutputDir)) {
      fs.mkdirSync(tempOutputDir, { recursive: true });
    }
  });

  afterEach(() => {
    if (fs.existsSync(tempOutputDir)) {
      fs.rmSync(tempOutputDir, { recursive: true, force: true });
    }
  });

  describe('sanitizeFilename', () => {
    it('should strip non-alphanumeric characters except hyphens and underscores', () => {
      expect(sanitizeFilename('CS::LeetCode::Two Sum')).toBe('CS__LeetCode__Two_Sum');
      expect(sanitizeFilename('file-name_123.json')).toBe('file-name_123_json');
      expect(sanitizeFilename('hello/world\\test?')).toBe('hello_world_test_');
    });

    it('should handle non-string inputs gracefully', () => {
      expect(sanitizeFilename(null)).toBe('');
      expect(sanitizeFilename(undefined)).toBe('');
      expect(sanitizeFilename(123)).toBe('');
      expect(sanitizeFilename({})).toBe('');
    });
  });

  describe('spawnCompiler', () => {
    it('should resolve on successful exit code (0)', async () => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      const promise = spawnCompiler('input.json', 'output.apkg', {
        deckName: 'My Deck',
        subject: 'Algorithms',
        source: 'source.txt',
      });

      process.nextTick(() => {
        mockChild.stdout.emit('data', 'compiler output line 1\n');
        mockChild.stderr.emit('data', 'compiler warning line 1\n');
        mockChild.emit('close', 0);
      });

      const res = await promise;
      expect(res.code).toBe(0);
      expect(res.stdout).toContain('compiler output');
      expect(res.stderr).toContain('compiler warning');
      expect(spawn).toHaveBeenCalledWith('uv', [
        'run',
        'src/compile.py',
        'input.json',
        '-o',
        'output.apkg',
        '--deck-name',
        'My Deck',
        '--subject',
        'Algorithms',
        '--source',
        'source.txt',
      ]);
    });

    it('should reject on non-zero exit codes', async () => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      const promise = spawnCompiler('input.json', 'output.apkg');

      process.nextTick(() => {
        mockChild.stderr.emit('data', 'fatal compiler error\n');
        mockChild.emit('close', 1);
      });

      await expect(promise).rejects.toThrow('Compiler process exited with code 1');
    });

    it('should reject if spawn triggers error event', async () => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      const promise = spawnCompiler('input.json', 'output.apkg');

      process.nextTick(() => {
        mockChild.emit('error', new Error('Spawn failed'));
      });

      await expect(promise).rejects.toThrow('Spawn failed');
    });

    it('should resolve even if outputPath is not provided', async () => {
      // Intent: Verify that spawnCompiler works and constructs correct args
      // even if outputPath is missing.
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      const promise = spawnCompiler('input.json');

      process.nextTick(() => {
        mockChild.emit('close', 0);
      });

      const res = await promise;
      expect(res.code).toBe(0);
      expect(spawn).toHaveBeenCalledWith('uv', [
        'run',
        'src/compile.py',
        'input.json',
      ]);
    });

    it('should reject and terminate process if execution exceeds timeout limit', async () => {
      // Intent: Verify that if compilation execution exceeds the timeout limit,
      // spawnCompiler rejects and terminates the child process.
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      mockChild.kill = vi.fn().mockImplementation(() => {
        process.nextTick(() => {
          mockChild.emit('close', null, 'SIGTERM');
          mockChild.emit('error', new Error('Killed'));
        });
      });
      vi.mocked(spawn).mockReturnValue(mockChild);

      const promise = spawnCompiler('input.json', 'output.apkg', { timeout: 10 });

      await expect(promise).rejects.toThrow('Compiler execution timed out after 10ms.');
      expect(mockChild.kill).toHaveBeenCalledWith('SIGTERM');
    });

    it('should resolve without setting a timer if timeout is 0', async () => {
      // Intent: Verify that if timeout is set to 0, no timeout timer is created,
      // and spawnCompiler handles the null timer correctly on process close.
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      const promise = spawnCompiler('input.json', 'output.apkg', { timeout: 0 });

      process.nextTick(() => {
        mockChild.emit('close', 0);
      });

      const res = await promise;
      expect(res.code).toBe(0);
    });

    it('should handle process error without timer when timeout is 0', async () => {
      // Intent: Verify that process error handler behaves correctly when no timer is active.
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      const promise = spawnCompiler('input.json', 'output.apkg', { timeout: 0 });

      process.nextTick(() => {
        mockChild.emit('error', new Error('Process crash'));
      });

      await expect(promise).rejects.toThrow('Process crash');
    });
  });

  describe('getCompletedQuestions', () => {
    it('should query completed questions (those with enforcement stage) correctly', () => {
      const runId = 'run-comp-test';
      createRun({
        runId,
        subject: 'Algorithms',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-comp',
      });

      // q1 is completed
      upsertQuestionEntry({
        runId,
        questionId: 'q1',
        currentStage: 'enforcement',
      });

      // q2 is partially completed (no enforcement step)
      upsertQuestionEntry({
        runId,
        questionId: 'q2',
        currentStage: 'generation',
      });

      const completed = getCompletedQuestions(runId);
      expect(completed.has('q1')).toBe(true);
      expect(completed.has('q2')).toBe(false);
      expect(completed.size).toBe(1);
    });
  });

  describe('runPipeline', () => {
    let mockConfig;
    let mockKeys;

    beforeEach(() => {
      mockConfig = {
        global: {
          cache_db_path: ':memory:',
          concurrency_limit: 2,
          request_delay: 0.05,
          default_timeout: 30,
        },
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
          },
        },
        pipeline: {
          generation: {
            models: ['openai/gpt-4'],
          },
          synthesis: {
            model: 'openai/gpt-4',
          },
        },
      };

      mockKeys = {
        openai: 'test-key',
      };
    });

    it('should throw if config or questions are missing/invalid', async () => {
      await expect(runPipeline({ config: null, questions: [] })).rejects.toThrow(
        'Configuration object is required',
      );
      await expect(runPipeline({ config: {}, questions: null })).rejects.toThrow(
        'Questions parameter must be an array',
      );
    });

    it('should execute full pipeline and call spawnCompiler successfully', async () => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      process.nextTick(() => {
        mockChild.emit('close', 0);
      });

      const questions = [
        { questionId: 'q-test-flow-1', content: 'content 1' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
      });

      expect(res.runId).toBeDefined();
      expect(res.hasFailures).toBe(false);
      expect(res.results).toHaveLength(1);
      expect(res.results[0].questionId).toBe('q-test-flow-1');
      expect(res.results[0].jsonPath).toBeDefined();
      expect(fs.existsSync(res.results[0].jsonPath)).toBe(true);

      const runRecord = getRun(res.runId);
      expect(runRecord).toBeDefined();
      expect(runRecord.status).toBe('completed');

      const steps = getPipelineStepsForRun(res.runId);
      expect(steps.some((s) => s.stage === 'generation')).toBe(true);
      expect(steps.some((s) => s.stage === 'synthesis')).toBe(true);
      expect(steps.some((s) => s.stage === 'enforcement')).toBe(true);
    });

    it('should skip already completed questions on resumption', async () => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      process.nextTick(() => {
        mockChild.emit('close', 0);
      });

      const resumeRunId = 'run-resume-test';
      createRun({
        runId: resumeRunId,
        subject: 'Algorithms',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-resume',
      });

      // Manually set created_at to NULL to cover line 214 fallback
      getDb().prepare('UPDATE runs SET created_at = NULL WHERE run_id = ?').run(resumeRunId);

      // Mark q1 as completed
      upsertQuestionEntry({
        runId: resumeRunId,
        questionId: 'q-resume-1',
        currentStage: 'enforcement',
        latestResponse: JSON.stringify({
          title: 'Mock Title 1',
          topic: 'Mock Topic 1',
          difficulty: 'Basic',
          cards: [],
        }),
      });

      // Mark q1b as completed
      upsertQuestionEntry({
        runId: resumeRunId,
        questionId: 'q-resume-1b',
        currentStage: 'enforcement',
        latestResponse: JSON.stringify({
          title: 'Mock Title 1b',
          topic: 'Mock Topic 1b',
          difficulty: 'Basic',
          cards: [],
        }),
      });

      // Mark q1c with null latestResponse to cover line 31
      upsertQuestionEntry({
        runId: resumeRunId,
        questionId: 'q-resume-1c',
        currentStage: 'enforcement',
        latestResponse: null,
      });

      const questions = [
        { questionId: 'q-resume-1', content: 'content 1' },
        {
          questionId: 'q-resume-1b',
          content: 'content 1b',
          metadata: {
            categoryName: 'ResumeCat',
            categoryIndex: 5,
            problemIndex: 6,
          },
        },
        { questionId: 'q-resume-1c', content: 'content 1c' },
        { questionId: 'q-resume-2', content: 'content 2' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
        resumeRunId,
      });

      expect(res.runId).toBe(resumeRunId);
      expect(res.hasFailures).toBe(false);
      expect(res.results).toHaveLength(4);
      expect(res.results[0].skipped).toBe(true);
      expect(res.results[1].skipped).toBe(true);
      expect(res.results[2].skipped).toBeUndefined();
      expect(res.results[3].jsonPath).toBeDefined();

      const runRecord = getRun(resumeRunId);
      expect(runRecord.status).toBe('completed');
    });

    it('should throw error when resuming non-existent run ID', async () => {
      await expect(
        runPipeline({
          config: mockConfig,
          keys: mockKeys,
          questions: [],
          subject: 'Algorithms',
          resumeRunId: 'non-existent-run-id',
        }),
      ).rejects.toThrow('Run with ID "non-existent-run-id" not found');
    });

    it('should handle dry-run mode correctly', async () => {
      const questions = [
        { questionId: 'q-dry-1', content: 'content 1' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        dryRun: true,
      });

      expect(res.hasFailures).toBe(false);
      expect(res.results).toHaveLength(1);
      expect(res.results[0].dryRun).toBe(true);
      expect(getRun(res.runId)).toBeUndefined();
    });

    it('should tolerate failures in individual questions and mark run failed', async () => {
      const stages = await import('../src/stages.js');
      const originalStage1 = stages.runStage1;

      // Mock runStage1 to throw on q-fail
      vi.mocked(originalStage1).mockImplementationOnce(async ({ questionId }) => {
        if (questionId === 'q-fail') {
          throw new Error('Stage 1 Simulation Failure');
        }
        return [{ provider: 'mock', model: 'model', output: 'ok' }];
      });

      const questions = [
        { questionId: 'q-fail', content: 'content fail' },
        { questionId: 'q-ok', content: 'content ok' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
      });

      expect(res.hasFailures).toBe(true);
      expect(res.results).toHaveLength(1); // Only the successful one is written/recorded as success
      expect(res.results[0].questionId).toBe('q-ok');

      const runRecord = getRun(res.runId);
      expect(runRecord.status).toBe('failed');
    });

    it('should handle custom outputPath which is a directory', async () => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      process.nextTick(() => {
        mockChild.emit('close', 0);
      });

      const customDir = path.join(tempOutputDir, 'custom_dir');
      // Create questions
      const questions = [{ questionId: 'q-dir-test', content: 'content' }];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
        outputPath: customDir,
      });

      expect(res.hasFailures).toBe(false);
      const expectedFilename = `${res.results[0].apkgPath.split('/').pop()}`;
      expect(expectedFilename).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z_[0-9a-fA-F-]+\.apkg$/);
      expect(res.results[0].apkgPath).toBe(path.join(customDir, expectedFilename));
      expect(fs.existsSync(customDir)).toBe(true);
    });

    it('should append question ID to files if multiple questions and outputPath is file path', async () => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      vi.mocked(spawn).mockReturnValue(mockChild);

      process.nextTick(() => {
        mockChild.emit('close', 0);
      });

      const customFile = path.join(tempOutputDir, 'output.apkg');
      const questions = [
        { questionId: 'q-multi-1', content: 'content 1' },
        { questionId: 'q-multi-2', content: 'content 2' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
        outputPath: customFile,
      });

      expect(res.hasFailures).toBe(false);
      const res1 = res.results.find((r) => r.questionId === 'q-multi-1');
      const res2 = res.results.find((r) => r.questionId === 'q-multi-2');
      expect(res1.apkgPath).toBe(customFile);
      expect(res2.apkgPath).toBe(customFile);
    });

    it('should initialize and close the database if it is not already initialized', async () => {
      // Intent: Verify that if the database is not initialized prior to calling the pipeline,
      // the orchestrator will initialize it dynamically and clean up by closing it afterward.
      closeDatabase();

      // Verify that the database is closed (getDb should throw an error)
      expect(() => getDb()).toThrow();

      const questions = [
        { questionId: 'q-init-db', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
      });

      expect(res.runId).toBeDefined();

      // Verify that the database was correctly closed at the end of the pipeline run
      expect(() => getDb()).toThrow();

      // Restore the in-memory database connection for subsequent tests
      initDatabase(':memory:');
    });

    it('should skip questions without a valid identifier and mark the run as failed', async () => {
      // Intent: Verify the robustness of the question loop when some inputs are missing
      // key fields (questionId, topic, and deckPath) and skip them safely.
      const questions = [
        { content: 'some content' }, // Invalid item: missing all identifier fields
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
      });

      expect(res.hasFailures).toBe(true);
      expect(res.results).toHaveLength(0);
    });

    it('should create the output directory if it does not already exist', async () => {
      // Intent: Verify that the orchestrator creates the intermediate JSON output directory
      // recursively if it is missing at run time.
      const nestedOutputDir = path.join(tempOutputDir, 'nested_dir_not_exists');
      const questions = [
        { questionId: 'q-mkdir-test', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: nestedOutputDir,
      });

      expect(res.hasFailures).toBe(false);
      expect(fs.existsSync(nestedOutputDir)).toBe(true);
    });

    it('should handle custom outputPath that already exists as a directory', async () => {
      // Intent: Verify that if outputPath refers to a directory that already exists,
      // the orchestrator appends the sanitized question ID to resolve the final output path.
      const existingDir = path.join(tempOutputDir, 'existing_dir');
      fs.mkdirSync(existingDir, { recursive: true });

      const questions = [
        { questionId: 'q-existing-dir-test', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
        outputPath: existingDir,
      });

      expect(res.hasFailures).toBe(false);
      const expectedFilename = `${res.results[0].apkgPath.split('/').pop()}`;
      expect(expectedFilename).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z_[0-9a-fA-F-]+\.apkg$/);
      expect(res.results[0].apkgPath).toBe(path.join(existingDir, expectedFilename));
    });

    it('should compile to custom single file path when there is only one compiled question', async () => {
      // Intent: Verify that if the user specifies a specific file path and there is only
      // a single output file, the orchestrator compiles directly to that specific output path.
      const customFilePath = path.join(tempOutputDir, 'custom_file.apkg');
      const questions = [
        { questionId: 'q-single-file-test', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
        outputPath: customFilePath,
      });

      expect(res.hasFailures).toBe(false);
      expect(res.results[0].apkgPath).toBe(customFilePath);
    });

    it('should handle compilation failure and mark run as failed', async () => {
      // Intent: Verify compilation error handling and ensure the orchestrator marks the run
      // as failed when the Python subprocess exits with a non-zero exit code.
      vi.mocked(spawn).mockImplementationOnce(() => {
        const mockChild = new EventEmitter();
        mockChild.stdout = new EventEmitter();
        mockChild.stderr = new EventEmitter();
        process.nextTick(() => {
          mockChild.stderr.emit('data', 'Mock compilation failed error\n');
          mockChild.emit('close', 1);
        });
        return mockChild;
      });

      const questions = [
        { questionId: 'q-compile-fail-test', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
      });

      expect(res.hasFailures).toBe(true);
      expect(res.results[0].apkgPath).toBeUndefined();
    });

    it('should fall back to default values for pipeline, providers, and content', async () => {
      // Intent: Cover fallback branch logic when config structure or question content is missing.
      // We close the DB so it is initialized with default DB path.
      closeDatabase();

      const minimalConfig = { global: {} };

      const questions = [
        { questionId: 'q-fallback-test' }, // missing content, metadata, indices
      ];

      const res = await runPipeline({
        config: minimalConfig,
        keys: {},
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
      });

      expect(res.hasFailures).toBe(false);
      expect(res.results[0].questionId).toBe('q-fallback-test');

      // The database should have been closed at the end because dbInitialized was true
      expect(() => getDb()).toThrow();

      // Clean up the default test database file created
      const fallbackDb = './llm2deck_test_fallback.db';
      if (fs.existsSync(fallbackDb)) {
        fs.unlinkSync(fallbackDb);
      }
      if (fs.existsSync(`${fallbackDb}-wal`)) fs.unlinkSync(`${fallbackDb}-wal`);
      if (fs.existsSync(`${fallbackDb}-shm`)) fs.unlinkSync(`${fallbackDb}-shm`);

      // Re-initialize for subsequent tests
      initDatabase(':memory:');
    });

    it('should close database if initialized inside runPipeline when resume run is not found', async () => {
      // Intent: Verify database cleanup logic when resumption fails on a non-existent run ID.
      closeDatabase();
      expect(() => getDb()).toThrow();

      await expect(
        runPipeline({
          config: mockConfig,
          keys: mockKeys,
          questions: [],
          subject: 'Algorithms',
          resumeRunId: 'non-existent-run-id',
        }),
      ).rejects.toThrow('Run with ID "non-existent-run-id" not found');

      expect(() => getDb()).toThrow(); // should be closed
      initDatabase(':memory:'); // restore for other tests
    });

    it('should map category and problem indices from both metadata and root levels', async () => {
      // Intent: Verify metadata extraction logic prioritizes metadata object properties
      // over root question properties.
      const questions = [
        {
          questionId: 'q-idx-1',
          content: 'content 1',
          categoryIndex: 10,
          problemIndex: 20,
        },
        {
          questionId: 'q-idx-2',
          content: 'content 2',
          metadata: {
            categoryName: 'MetaCat',
            categoryIndex: 100,
            problemIndex: 200,
          },
        },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
      });

      expect(res.hasFailures).toBe(false);

      // Read written JSON array to verify postProcess injected correct index values
      const mergedArray = JSON.parse(fs.readFileSync(res.results[0].jsonPath, 'utf8'));
      const file1 = mergedArray[0];
      const file2 = mergedArray[1];

      // For q-idx-1: Category/problem index from root question structure
      expect(file1.category_index).toBe(10);
      expect(file1.problem_index).toBe(20);

      // For q-idx-2: Category/problem index from nested metadata block (overriding/taking priority)
      expect(file2.category_name).toBe('MetaCat');
      expect(file2.category_index).toBe(100);
      expect(file2.problem_index).toBe(200);
    });

    it('should update run status to running during resumption', async () => {
      // Intent: Verify database status gets updated back to 'running' during resumption.
      const resumeRunId = 'run-resume-status-test';
      createRun({
        runId: resumeRunId,
        subject: 'Algorithms',
        cardType: 'standard',
        status: 'failed',
        configHash: 'hash-resume-status',
      });

      // Mark q1 as completed
      addPipelineStep({
        runId: resumeRunId,
        questionId: 'q-resume-status-1',
        stage: 'enforcement',
        provider: 'openai',
        model: 'gpt-4',
        inputData: '',
        outputData: '',
      });

      const questions = [
        { questionId: 'q-resume-status-1', content: 'content 1' },
        { questionId: 'q-resume-status-2', content: 'content 2' },
      ];

      // Temporarily mock runStage2 to check database status during execution
      const stages = await import('../src/stages.js');
      const originalStage2 = stages.runStage2;
      vi.mocked(originalStage2).mockImplementationOnce(async ({ runId }) => {
        const run = getRun(runId);
        expect(run.status).toBe('running');
        return 'stage2-out';
      });

      await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
        resumeRunId,
      });

      const finalRun = getRun(resumeRunId);
      expect(finalRun.status).toBe('completed');
    });

    it('should close database if setup fails before question loop starts', async () => {
      // Intent: Verify database connection closure is guaranteed if setup crashes early.
      closeDatabase();
      expect(() => getDb()).toThrow();

      const questions = [{ questionId: 'q-setup-fail', content: 'content' }];

      // Passing providers: null triggers TypeError inside createProviderClients
      const configWithGetter = {
        global: { cache_db_path: './temp_early_err.db' },
        get providers() {
          throw new Error('Simulation Setup Error');
        },
      };

      await expect(
        runPipeline({
          config: configWithGetter,
          keys: {},
          questions,
          subject: 'Algorithms',
        }),
      ).rejects.toThrow('Simulation Setup Error');

      // The database should have been closed in the finally block
      expect(() => getDb()).toThrow();

      // Clean up the temporary database file created
      if (fs.existsSync('./temp_early_err.db')) {
        fs.unlinkSync('./temp_early_err.db');
      }

      // Re-initialize for subsequent tests
      initDatabase(':memory:');
    });

    it('should not update run status if resuming in dry-run mode', async () => {
      // Intent: Verify that if resuming a run in dry-run mode, the run status in the database
      // is not updated to 'running'.
      const resumeRunId = 'run-resume-dry-test';
      createRun({
        runId: resumeRunId,
        subject: 'Algorithms',
        cardType: 'standard',
        status: 'failed',
        configHash: 'hash-resume-dry',
      });

      const questions = [
        { questionId: 'q-resume-dry-1', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        resumeRunId,
        dryRun: true,
      });

      expect(res.hasFailures).toBe(false);
      // Run status in DB should still be 'failed' (not updated to running)
      const run = getRun(resumeRunId);
      expect(run.status).toBe('failed');
    });

    it('should skip completed questions in dry-run resumption mode', async () => {
      const resumeRunId = 'run-resume-dry-completed-test';
      createRun({
        runId: resumeRunId,
        subject: 'Algorithms',
        cardType: 'standard',
        status: 'failed',
        configHash: 'hash-resume-dry-comp',
      });

      upsertQuestionEntry({
        runId: resumeRunId,
        questionId: 'q-resume-dry-comp-1',
        currentStage: 'enforcement',
      });

      const questions = [
        { questionId: 'q-resume-dry-comp-1', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        resumeRunId,
        dryRun: true,
      });

      expect(res.hasFailures).toBe(false);
      expect(res.results).toHaveLength(1);
      expect(res.results[0].dryRun).toBe(true);
    });

    it('should handle database parse errors gracefully when retrieving completed questions', async () => {
      const resumeRunId = 'run-db-parse-err-test';
      createRun({
        runId: resumeRunId,
        subject: 'Algorithms',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-db-parse',
      });

      // Insert invalid JSON string in latestResponse to trigger JSON parse failure
      upsertQuestionEntry({
        runId: resumeRunId,
        questionId: 'q-parse-err-1',
        currentStage: 'enforcement',
        latestResponse: '{invalid_json',
      });

      const questions = [
        { questionId: 'q-parse-err-1', content: 'content' },
      ];

      const res = await runPipeline({
        config: mockConfig,
        keys: mockKeys,
        questions,
        subject: 'Algorithms',
        cardType: 'standard',
        outputDir: tempOutputDir,
        resumeRunId,
      });

      expect(res.hasFailures).toBe(false);
      // Since it couldn't retrieve from DB, it should have re-processed the question and succeeded
      expect(res.results).toHaveLength(1);
      expect(res.results[0].skipped).toBeUndefined();
    });
  });
});
