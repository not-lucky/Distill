import {
  vi, describe, it, expect, beforeEach, beforeAll, afterAll,
} from 'vitest';
import { EventEmitter } from 'events';
import { spawn } from 'child_process';
import fs from 'fs';
import {
  initDatabase,
  closeDatabase,
  clearCache,
  createRun,
  upsertQuestionEntry,
} from '../src/database.js';
import { createThrottledFetcher, createProviderClients } from '../src/providers.js';
import { runStage1 } from '../src/stages.js';
import { runPipeline } from '../src/orchestrator.js';

// Mock child_process spawn to simulate python compiler calls
vi.mock('child_process', () => ({
  spawn: vi.fn(),
}));

// Mock stages modules to control execution flow in orchestrator tests.
// Default mocked stages return canned responses, avoiding heavy LLM/schema checks.
vi.mock('../src/stages.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    runStage1: vi.fn().mockImplementation(async () => [
      { provider: 'mock', model: 'model-a', output: 'stage 1 output' },
    ]),
    runStage2: vi.fn().mockImplementation(async () => 'stage 2 output'),
    runStage3: vi.fn().mockImplementation(async () => ({
      title: 'Title',
      topic: 'Topic',
      difficulty: 'Basic',
      cards: [],
    })),
  };
});

describe('Pipeline Dual Concurrency & Edge Cases', () => {
  let config;
  let keys;
  let clients;
  let throttledFetch;

  beforeAll(() => {
    // Set up in-memory sqlite database for foreign key and step logging assertions
    initDatabase(':memory:');
  });

  afterAll(() => {
    closeDatabase();
  });

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
    clearCache();

    // Standard baseline configuration
    config = {
      global: {
        model_concurrency: 0,
        topic_concurrency: 1,
        request_delay: 0,
        default_timeout: 30.0,
        cache_db_path: ':memory:',
      },
      providers: {
        openai: {
          base_url: 'https://api.openai.com/v1',
          temperature: 0.3,
        },
        cerebras: {
          base_url: 'https://api.cerebras.ai/v1',
          temperature: 0.2,
        },
      },
      pipeline: {
        generation: {
          models: ['openai/gpt-4', 'cerebras/llama-3.1'],
        },
        synthesis: {
          model: 'openai/gpt-4',
        },
      },
    };

    keys = {
      openai: 'key-openai',
      cerebras: 'key-cerebras',
    };

    clients = createProviderClients(config, keys);
    throttledFetch = createThrottledFetcher(config);

    // Reset default mock implementations for stages.js functions to prevent leakage across tests
    vi.mocked(runStage1).mockImplementation(async () => [
      { provider: 'mock', model: 'model-a', output: 'stage 1 output' },
    ]);

    // Mock spawn to always succeed immediately
    vi.mocked(spawn).mockImplementation(() => {
      const mockChild = new EventEmitter();
      mockChild.stdout = new EventEmitter();
      mockChild.stderr = new EventEmitter();
      process.nextTick(() => {
        mockChild.emit('close', 0);
      });
      return mockChild;
    });
  });

  describe('Defensive Concurrency Fallbacks', () => {
    it('should fall back to sequential topic processing on negative/invalid inputs', async () => {
      const runId = 'run-defensive-topic';
      createRun({
        runId,
        subject: 'General',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      // Test with invalid negative concurrency
      config.global.topic_concurrency = -5;
      const questions = [
        { questionId: 'q-def-1', content: 'content 1' },
        { questionId: 'q-def-2', content: 'content 2' },
      ];

      // If defensive fallback doesn't work, p-limit will throw because concurrency < 1
      const resNeg = await runPipeline({
        config,
        keys,
        questions,
        subject: 'General',
        cardType: 'standard',
        resumeRunId: runId,
      });
      expect(resNeg.hasFailures).toBe(false);

      // Test with non-numeric concurrency
      config.global.topic_concurrency = 'invalid-string';
      const resStr = await runPipeline({
        config,
        keys,
        questions,
        subject: 'General',
        cardType: 'standard',
        resumeRunId: runId,
      });
      expect(resStr.hasFailures).toBe(false);

      // Test with NaN concurrency
      config.global.topic_concurrency = NaN;
      const resNaN = await runPipeline({
        config,
        keys,
        questions,
        subject: 'General',
        cardType: 'standard',
        resumeRunId: runId,
      });
      expect(resNaN.hasFailures).toBe(false);
    });

    it('should fall back to unlimited model processing on negative/invalid inputs', async () => {
      const runId = 'run-defensive-model';
      createRun({
        runId,
        subject: 'General',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      const openaiClient = clients.get('openai');
      const mockOpenai = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'OpenAI output' } }],
      });

      // Use only one model to avoid unmocked cerebras call
      config.pipeline.generation.models = ['openai/gpt-4'];

      const { runStage1: originalRunStage1 } = await vi.importActual('../src/stages.js');

      // Test negative concurrency
      config.global.model_concurrency = -3;
      await expect(
        originalRunStage1({
          runId,
          questionId: 'q-def-model-1',
          content: 'content',
          deckPath: 'Deck',
          cardType: 'standard',
          config,
          keys,
          clients,
          throttledFetch,
        }),
      ).resolves.toBeDefined();

      // Test non-numeric concurrency
      config.global.model_concurrency = 'invalid-string';
      await expect(
        originalRunStage1({
          runId,
          questionId: 'q-def-model-2',
          content: 'content',
          deckPath: 'Deck',
          cardType: 'standard',
          config,
          keys,
          clients,
          throttledFetch,
        }),
      ).resolves.toBeDefined();

      // Test NaN concurrency
      config.global.model_concurrency = NaN;
      await expect(
        originalRunStage1({
          runId,
          questionId: 'q-def-model-3',
          content: 'content',
          deckPath: 'Deck',
          cardType: 'standard',
          config,
          keys,
          clients,
          throttledFetch,
        }),
      ).resolves.toBeDefined();

      expect(mockOpenai).toHaveBeenCalled();
    });
  });

  describe('createThrottledFetcher Edge Cases', () => {
    it('should execute requests concurrently when request_delay is 0 (no global limit)', async () => {
      config.global.request_delay = 0;
      const fetcher = createThrottledFetcher(config);

      let activeCount = 0;
      let maxActiveCount = 0;

      const task = async () => {
        activeCount++;
        maxActiveCount = Math.max(maxActiveCount, activeCount);
        // Simulate a brief asynchronous operation
        await new Promise((resolve) => {
          setTimeout(resolve, 30);
        });
        activeCount--;
      };

      // Firing 5 tasks simultaneously
      const tasks = Array.from({ length: 5 }, () => fetcher(task));
      await Promise.all(tasks);

      // Verify that all 5 tasks ran in parallel (since delay is 0 and there's no concurrency_limit)
      expect(maxActiveCount).toBe(5);
    });

    it('should correctly stagger request start times allowing concurrent execution', async () => {
      // Set delay to 50ms
      config.global.request_delay = 0.05;
      const fetcher = createThrottledFetcher(config);

      const startTimes = [];
      const task = async () => {
        startTimes.push(Date.now());
        // Simulating request taking 100ms (longer than delay)
        await new Promise((resolve) => {
          setTimeout(resolve, 100);
        });
      };

      const tasks = Array.from({ length: 3 }, () => fetcher(task));
      await Promise.all(tasks);

      // Even though tasks take 100ms, they should start sequentially every ~50ms
      const diff1 = startTimes[1] - startTimes[0];
      const diff2 = startTimes[2] - startTimes[1];

      // Start times must be spaced out by at least 40ms (allowing scheduler margin)
      expect(diff1).toBeGreaterThanOrEqual(40);
      expect(diff2).toBeGreaterThanOrEqual(40);
    });
  });

  describe('model_concurrency Edge Cases', () => {
    it('should run all models in parallel when model_concurrency is 0', async () => {
      const runId = 'run-model-unlimited';
      createRun({
        runId,
        subject: 'General',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      config.global.model_concurrency = 0;
      config.pipeline.generation.models = [
        'openai/gpt-4',
        'cerebras/llama-3.1',
      ];

      const openaiClient = clients.get('openai');
      const cerebrasClient = clients.get('cerebras');

      let activeCalls = 0;
      let maxActiveCalls = 0;

      const mockCall = async () => {
        activeCalls++;
        maxActiveCalls = Math.max(maxActiveCalls, activeCalls);
        await new Promise((resolve) => {
          setTimeout(resolve, 50);
        });
        activeCalls--;
        return { choices: [{ message: { content: 'mock output' } }] };
      };

      vi.spyOn(openaiClient.chat.completions, 'create').mockImplementation(mockCall);
      vi.spyOn(cerebrasClient.chat.completions, 'create').mockImplementation(mockCall);

      const { runStage1: originalRunStage1 } = await vi.importActual('../src/stages.js');

      await originalRunStage1({
        runId,
        questionId: 'q-unlimited',
        content: 'content',
        deckPath: 'Deck',
        cardType: 'standard',
        config,
        keys,
        clients,
        throttledFetch,
      });

      // Both models should have executed concurrently
      expect(maxActiveCalls).toBe(2);
    });

    it('should respect model_concurrency when it is less than the total configured models', async () => {
      const runId = 'run-model-limited';
      createRun({
        runId,
        subject: 'General',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      // 3 models configured but concurrency limit is 2
      config.global.model_concurrency = 2;
      config.pipeline.generation.models = [
        'openai/gpt-4',
        'cerebras/llama-3.1',
        'openai/gpt-3.5-turbo',
      ];

      const openaiClient = clients.get('openai');
      const cerebrasClient = clients.get('cerebras');

      let activeCalls = 0;
      let maxActiveCalls = 0;

      const mockCall = async () => {
        activeCalls++;
        maxActiveCalls = Math.max(maxActiveCalls, activeCalls);
        await new Promise((resolve) => {
          setTimeout(resolve, 50);
        });
        activeCalls--;
        return { choices: [{ message: { content: 'mock output' } }] };
      };

      vi.spyOn(openaiClient.chat.completions, 'create').mockImplementation(mockCall);
      vi.spyOn(cerebrasClient.chat.completions, 'create').mockImplementation(mockCall);

      const { runStage1: originalRunStage1 } = await vi.importActual('../src/stages.js');

      await originalRunStage1({
        runId,
        questionId: 'q-limited',
        content: 'content',
        deckPath: 'Deck',
        cardType: 'standard',
        config,
        keys,
        clients,
        throttledFetch,
      });

      // Max active calls must never exceed 2
      expect(maxActiveCalls).toBeLessThanOrEqual(2);
      expect(maxActiveCalls).toBeGreaterThan(0);
    });

    it('should release model slot and continue subsequent tasks if a model API call throws', async () => {
      const runId = 'run-model-error';
      createRun({
        runId,
        subject: 'General',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      config.global.model_concurrency = 1; // Sequential execution
      config.pipeline.generation.models = [
        'openai/gpt-4',
        'cerebras/llama-3.1',
      ];

      const openaiClient = clients.get('openai');
      const cerebrasClient = clients.get('cerebras');

      // The first model throws an error with HTTP status 400 to prevent retry delays
      const apiError = new Error('API failure');
      apiError.status = 400;

      vi.spyOn(openaiClient.chat.completions, 'create').mockRejectedValue(apiError);
      // The second model succeeds
      const cerebrasSpy = vi.spyOn(cerebrasClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Success output' } }],
      });

      const { runStage1: originalRunStage1 } = await vi.importActual('../src/stages.js');

      // Stage 1 throws the propagated error from the first failing model
      await expect(
        originalRunStage1({
          runId,
          questionId: 'q-fail-model',
          content: 'content',
          deckPath: 'Deck',
          cardType: 'standard',
          config,
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('API failure');

      // Verify that the second model was still invoked (failure did not block the loop)
      expect(cerebrasSpy).toHaveBeenCalled();
    });
  });

  describe('topic_concurrency Edge Cases', () => {
    it('should preserve input order in results even if parallel execution finishes out of order', async () => {
      // Mock runStage1 to resolve dynamically with artificial delay:
      // Topic 1 takes 100ms, Topic 2 takes 10ms, Topic 3 takes 50ms.
      // Therefore, they finish in the order: Topic 2 -> Topic 3 -> Topic 1.
      const stages = await import('../src/stages.js');
      const originalStage1 = stages.runStage1;
      const originalStage3 = stages.runStage3;

      vi.mocked(originalStage1).mockImplementation(async ({ questionId }) => {
        let delay = 10;
        if (questionId === 'topic-1') delay = 100;
        if (questionId === 'topic-3') delay = 50;

        await new Promise((resolve) => {
          setTimeout(resolve, delay);
        });
        return [{ provider: 'mock', model: 'model', output: 'ok' }];
      });

      vi.mocked(originalStage3).mockImplementation(async ({ questionId }) => ({
        title: `Title ${questionId}`,
        topic: `Topic ${questionId}`,
        difficulty: 'Basic',
        cards: [],
      }));

      config.global.topic_concurrency = 3; // Fully parallel

      const questions = [
        { questionId: 'topic-1', content: 'c1' },
        { questionId: 'topic-2', content: 'c2' },
        { questionId: 'topic-3', content: 'c3' },
      ];

      const res = await runPipeline({
        config,
        keys,
        questions,
        subject: 'General',
        cardType: 'standard',
        outputDir: './tests/temp_out_concurrency',
      });

      expect(res.hasFailures).toBe(false);

      // Verify results order matches input order: topic-1, topic-2, topic-3
      expect(res.results).toHaveLength(3);
      expect(res.results[0].questionId).toBe('topic-1');
      expect(res.results[1].questionId).toBe('topic-2');
      expect(res.results[2].questionId).toBe('topic-3');

      // Clean up generated json
      if (res.results[0].jsonPath && fs.existsSync(res.results[0].jsonPath)) {
        fs.unlinkSync(res.results[0].jsonPath);
      }
    });

    it('should correctly release the topic slot and continue processing subsequent tasks if a topic pipeline execution throws an error', async () => {
      const stages = await import('../src/stages.js');
      const originalStage1 = stages.runStage1;

      // Topic 1 throws an error
      vi.mocked(originalStage1).mockImplementationOnce(async () => {
        throw new Error('Pipeline topic crash');
      });
      // Topic 2 succeeds
      vi.mocked(originalStage1).mockImplementationOnce(async () => [
        { provider: 'mock', model: 'model', output: 'succeed' },
      ]);

      // Limit concurrency to 1 to test queue release behavior sequentially
      config.global.topic_concurrency = 1;

      const questions = [
        { questionId: 'topic-fail', content: 'c1' },
        { questionId: 'topic-success', content: 'c2' },
      ];

      const res = await runPipeline({
        config,
        keys,
        questions,
        subject: 'General',
        cardType: 'standard',
        outputDir: './tests/temp_out_concurrency_error',
      });

      // Pipeline continues, topic-success is executed successfully
      expect(res.hasFailures).toBe(true);
      expect(res.results).toHaveLength(1);
      expect(res.results[0].questionId).toBe('topic-success');

      // Cleanup
      if (res.results[0].jsonPath && fs.existsSync(res.results[0].jsonPath)) {
        fs.unlinkSync(res.results[0].jsonPath);
      }
    });

    it('should bypass pipeline stage processing for skipped/completed topics, releasing the slot instantly without blocking other concurrent tasks', async () => {
      const resumeRunId = 'run-skip-concurrency';
      createRun({
        runId: resumeRunId,
        subject: 'General',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      // Mark topic-skip as already completed in DB
      upsertQuestionEntry({
        runId: resumeRunId,
        questionId: 'topic-skip',
        currentStage: 'enforcement',
        latestResponse: JSON.stringify({
          title: 'Mock Title',
          topic: 'Mock Topic',
          difficulty: 'Basic',
          cards: [],
        }),
      });

      const stages = await import('../src/stages.js');
      const originalStage1 = stages.runStage1;

      const stage1Spy = vi.mocked(originalStage1).mockImplementation(async () => [
        { provider: 'mock', model: 'model', output: 'ok' },
      ]);

      config.global.topic_concurrency = 1;

      const questions = [
        { questionId: 'topic-skip', content: 'c1' },
        { questionId: 'topic-run', content: 'c2' },
      ];

      // Explicitly clear mock counts to isolate this test's calls
      vi.mocked(originalStage1).mockClear();

      const res = await runPipeline({
        config,
        keys,
        questions,
        subject: 'General',
        cardType: 'standard',
        outputDir: './tests/temp_out_concurrency_skip',
        resumeRunId,
      });

      expect(res.hasFailures).toBe(false);
      expect(res.results).toHaveLength(2);
      expect(res.results[0].skipped).toBe(true);
      expect(res.results[1].skipped).toBeUndefined();

      // Stage 1 should only be called for the second topic
      expect(stage1Spy).toHaveBeenCalledTimes(1);

      // Cleanup
      if (res.results[1].jsonPath && fs.existsSync(res.results[1].jsonPath)) {
        fs.unlinkSync(res.results[1].jsonPath);
      }
    });
  });
});
