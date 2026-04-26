import {
  vi, describe, it, expect, beforeEach, beforeAll, afterAll,
} from 'vitest';
import {
  initDatabase, closeDatabase, getPipelineStepsForRun, createRun, clearCache,
} from '../src/database.js';
import {
  createProviderClients, createThrottledFetcher, computeCacheKey, computePromptHash, writeCache,
} from '../src/providers.js';
import {
  DEFAULT_SYNTHESIS,
  FORMAT_STANDARD,
} from '../src/prompts.js';
import {
  runStage2,
} from '../src/stages.js';

vi.mock('openai', () => {
  const MockOpenAI = vi.fn().mockImplementation(function mockOpenAIConstructor(options) {
    this.baseURL = options.baseURL;
    this.apiKey = options.apiKey;
    this.timeout = options.timeout;
    this.chat = {
      completions: {
        create: vi.fn(),
      },
    };
  });
  return {
    default: MockOpenAI,
    OpenAI: MockOpenAI,
  };
});

describe('Stage 2 Pipeline - Frontier Synthesis', () => {
  let config;
  let keys;
  let clients;
  let throttledFetch;

  beforeAll(() => {
    initDatabase(':memory:');
  });

  afterAll(() => {
    closeDatabase();
  });

  beforeEach(() => {
    vi.restoreAllMocks();
    clearCache();

    config = {
      global: {
        concurrency_limit: 2,
        request_delay: 0.05,
        default_timeout: 30.0,
      },
      providers: {
        openai: {
          base_url: 'https://api.openai.com/v1',
          temperature: 0.3,
        },
      },
      pipeline: {
        synthesis: {
          model: 'openai/gpt-4o',
        },
      },
    };

    keys = {
      openai: 'key-openai',
    };

    clients = createProviderClients(config, keys);
    throttledFetch = createThrottledFetcher(config);
  });

  it('should throw an error if synthesis model is not configured', async () => {
    const invalidConfig = {
      pipeline: {
        synthesis: {},
      },
    };

    await expect(
      runStage2({
        runId: 'run-synthesis-1',
        questionId: 'q-test-1',
        stage1Results: [{ provider: 'openai', model: 'gpt-3.5-turbo', output: 'some output' }],
        config: invalidConfig,
        keys,
        clients,
        throttledFetch,
      }),
    ).rejects.toThrow('No synthesis model configured in config.pipeline.synthesis.model');
  });

  it('should throw an error if Stage 1 results are missing or empty', async () => {
    await expect(
      runStage2({
        runId: 'run-synthesis-2',
        questionId: 'q-test-2',
        stage1Results: [],
        config,
        keys,
        clients,
        throttledFetch,
      }),
    ).rejects.toThrow('No Stage 1 results provided');

    await expect(
      runStage2({
        runId: 'run-synthesis-2',
        questionId: 'q-test-2',
        stage1Results: null,
        config,
        keys,
        clients,
        throttledFetch,
      }),
    ).rejects.toThrow('No Stage 1 results provided');
  });

  it('should join Stage 1 outputs correctly and query the synthesis model', async () => {
    const openaiClient = clients.get('openai');
    const mockCreate = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
      choices: [{ message: { content: 'Synthesized flashcard list output' } }],
    });

    const runId = 'run-synthesis-success-1';
    createRun({
      runId,
      subject: 'LeetCode',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash123',
    });

    const stage1Results = [
      { provider: 'openai', model: 'gpt-3.5-turbo', output: 'Card 1 from OpenAI' },
      { provider: 'cerebras', model: 'llama3.1-70b', output: 'Card 2 from Cerebras' },
    ];

    const result = await runStage2({
      runId,
      questionId: 'q-synthesis-1',
      stage1Results,
      cardType: 'standard',
      subject: 'LeetCode',
      prompts: {},
      config,
      keys,
      clients,
      throttledFetch,
    });

    expect(result).toBe('Synthesized flashcard list output');
    expect(mockCreate).toHaveBeenCalledTimes(1);

    // Verify messages sent
    const calledWithParams = mockCreate.mock.calls[0][0];
    expect(calledWithParams.model).toBe('gpt-4o');
    expect(calledWithParams.messages).toHaveLength(2);
    expect(calledWithParams.messages[0].role).toBe('system');
    expect(calledWithParams.messages[0].content).toContain(DEFAULT_SYNTHESIS);
    expect(calledWithParams.messages[1].role).toBe('user');
    expect(calledWithParams.messages[1].content).toContain('--- Provider: openai, Model: gpt-3.5-turbo ---');
    expect(calledWithParams.messages[1].content).toContain('Card 1 from OpenAI');
    expect(calledWithParams.messages[1].content).toContain('--- Provider: cerebras, Model: llama3.1-70b ---');
    expect(calledWithParams.messages[1].content).toContain('Card 2 from Cerebras');

    // Verify DB pipeline step logging
    const steps = getPipelineStepsForRun(runId);
    expect(steps).toHaveLength(1);
    expect(steps[0].stage).toBe('synthesis');
    expect(steps[0].provider).toBe('openai');
    expect(steps[0].model).toBe('gpt-4o');
    expect(steps[0].output_data).toBe('Synthesized flashcard list output');
  });

  it('should support YAML custom prompts overrides and subject combiners', async () => {
    const openaiClient = clients.get('openai');
    const mockCreate = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
      choices: [{ message: { content: 'Custom synthesis output' } }],
    });

    const runId = 'run-synthesis-yaml-1';
    createRun({
      runId,
      subject: 'CustomLC',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash123',
    });

    const promptsConfig = {
      defaults: {
        synthesis: 'YAML Default Synthesis Guidelines',
      },
      subjects: {
        CustomLC: {
          synthesis: 'YAML Custom Subject Combiner Guidelines',
        },
      },
    };

    const stage1Results = [
      { provider: 'openai', model: 'gpt-3.5-turbo', output: 'Raw cards content' },
    ];

    const result = await runStage2({
      runId,
      questionId: 'q-synthesis-yaml',
      stage1Results,
      cardType: 'standard',
      subject: 'CustomLC',
      prompts: promptsConfig,
      config,
      keys,
      clients,
      throttledFetch,
    });

    expect(result).toBe('Custom synthesis output');
    const calledWithParams = mockCreate.mock.calls[0][0];
    expect(calledWithParams.messages[0].content).toContain('YAML Default Synthesis Guidelines');
    expect(calledWithParams.messages[0].content).toContain('YAML Custom Subject Combiner Guidelines');
  });

  it('should propagate API errors correctly', async () => {
    const openaiClient = clients.get('openai');
    const apiError = new Error('API Rate Limit Exceeded');
    apiError.status = 400; // 400 is not retryable, so it fails immediately without retrying
    vi.spyOn(openaiClient.chat.completions, 'create').mockRejectedValue(apiError);

    const runId = 'run-synthesis-err-1';
    createRun({
      runId,
      subject: 'LeetCode',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash123',
    });

    const stage1Results = [
      { provider: 'openai', model: 'gpt-3.5-turbo', output: 'Card 1' },
    ];

    await expect(
      runStage2({
        runId,
        questionId: 'q-err-1',
        stage1Results,
        cardType: 'standard',
        config,
        keys,
        clients,
        throttledFetch,
      }),
    ).rejects.toThrow('API Rate Limit Exceeded');
  });

  it('should integrate with llm_cache and return cached results without API call', async () => {
    const openaiClient = clients.get('openai');
    const mockCreate = vi.spyOn(openaiClient.chat.completions, 'create').mockRejectedValue(
      new Error('Should not make API call on cache hit'),
    );

    const runId = 'run-synthesis-cache-1';
    createRun({
      runId,
      subject: 'LeetCode',
      cardType: 'standard',
      status: 'running',
      configHash: 'hash123',
    });

    const stage1Results = [
      { provider: 'openai', model: 'gpt-3.5-turbo', output: 'Card 1' },
    ];

    const combinedContent = '--- Provider: openai, Model: gpt-3.5-turbo ---\nCard 1';
    const messages = [
      { role: 'system', content: `${DEFAULT_SYNTHESIS}\n\n${FORMAT_STANDARD}` },
      { role: 'user', content: `Flashcard lists to consolidate:\n\n${combinedContent}` },
    ];

    const cacheKey = computeCacheKey({
      provider: 'openai',
      model: 'gpt-4o',
      messages,
      temperature: undefined, // runStage2 does not pass temperature, so callLLM sees undefined
    });
    const promptHash = computePromptHash(messages);

    // Pre-populate cache
    await writeCache({
      cacheKey,
      provider: 'openai',
      model: 'gpt-4o',
      promptHash,
      response: 'Cached consolidated flashcard list',
    });

    const result = await runStage2({
      runId,
      questionId: 'q-cache-1',
      stage1Results,
      cardType: 'standard',
      subject: 'LeetCode',
      prompts: {},
      config,
      keys,
      clients,
      throttledFetch,
    });

    expect(result).toBe('Cached consolidated flashcard list');
    expect(mockCreate).not.toHaveBeenCalled();

    // Verify DB pipeline step logging still occurred
    const steps = getPipelineStepsForRun(runId);
    expect(steps).toHaveLength(1);
    expect(steps[0].stage).toBe('synthesis');
    expect(steps[0].provider).toBe('openai');
    expect(steps[0].model).toBe('gpt-4o');
    expect(steps[0].output_data).toBe('Cached consolidated flashcard list');
  });

  describe('Edge-case Configurations & Invalid Inputs', () => {
    it('should throw an error if config itself is null or undefined', async () => {
      // Intent: Verify function resilience when the main config object is
      // completely missing or null.
      await expect(
        runStage2({
          runId: 'run-edge-1',
          questionId: 'q-edge-1',
          stage1Results: [{ provider: 'openai', model: 'gpt-3.5-turbo', output: 'content' }],
          config: null,
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow();
    });

    it('should throw an error if config.pipeline is missing', async () => {
      // Intent: Verify handling when config is present but the pipeline stage
      // mappings block is missing.
      await expect(
        runStage2({
          runId: 'run-edge-2',
          questionId: 'q-edge-2',
          stage1Results: [{ provider: 'openai', model: 'gpt-3.5-turbo', output: 'content' }],
          config: { global: {} },
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('No synthesis model configured');
    });

    it('should throw an error if model configuration is not a valid format', async () => {
      // Intent: Validate that malformed model identification strings (e.g., missing slash
      // separating provider/model) trigger a parsing error before attempting external calls.
      const invalidConfigs = [
        { pipeline: { synthesis: { model: 'openai' } } },
        { pipeline: { synthesis: { model: 'openai/' } } },
        { pipeline: { synthesis: { model: '/gpt-4o' } } },
      ];

      for (const badConfig of invalidConfigs) {
        await expect(
          runStage2({
            runId: 'run-edge-3',
            questionId: 'q-edge-3',
            stage1Results: [{ provider: 'openai', model: 'gpt-3.5-turbo', output: 'content' }],
            config: badConfig,
            keys,
            clients,
            throttledFetch,
          }),
        ).rejects.toThrow('Invalid model format');
      }
    });

    it('should throw an error if any Stage 1 result item is null, undefined, or missing output string', async () => {
      // Intent: Enforce input cleanliness by rejecting malformed parallel output structures.
      const badStage1Results = [
        [null],
        [undefined],
        [{ provider: 'openai', model: 'gpt-3.5-turbo' }], // missing output completely
        [{ provider: 'openai', model: 'gpt-3.5-turbo', output: null }], // output is null
        [{ provider: 'openai', model: 'gpt-3.5-turbo', output: 12345 }], // output is not a string
      ];

      for (const results of badStage1Results) {
        await expect(
          runStage2({
            runId: 'run-edge-4',
            questionId: 'q-edge-4',
            stage1Results: results,
            config,
            keys,
            clients,
            throttledFetch,
          }),
        ).rejects.toThrow('Stage 1 result item is missing a valid string output');
      }
    });

    it('should default missing provider/model fields in Stage 1 results to unknown placeholders', async () => {
      // Intent: Ensure output concatenation doesn't break if provider or model are empty
      // string/falsy, falling back to placeholders instead of crashing.
      const openaiClient = clients.get('openai');
      const mockCreate = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Consolidated' } }],
      });

      const runId = 'run-edge-5';
      createRun({
        runId,
        subject: 'LeetCode',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      const results = [
        { output: 'Card A' }, // missing both provider and model
        { provider: '', model: null, output: 'Card B' }, // empty/null provider and model
      ];

      await runStage2({
        runId,
        questionId: 'q-edge-5',
        stage1Results: results,
        config,
        keys,
        clients,
        throttledFetch,
      });

      const calledWithParams = mockCreate.mock.calls[0][0];
      const userMessage = calledWithParams.messages[1].content;
      expect(userMessage).toContain('--- Provider: unknown-provider, Model: unknown-model ---');
    });

    it('should correctly pass the resolved synthesis prompts and change behavior for MCQ format', async () => {
      // Intent: Verify MCQ mode updates the prompt formatting expectations or
      // subject-specific configurations correctly.
      const openaiClient = clients.get('openai');
      const mockCreate = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'MCQ Consolidated' } }],
      });

      const runId = 'run-edge-6';
      createRun({
        runId,
        subject: 'LeetCode',
        cardType: 'mcq',
        status: 'running',
        configHash: 'hash123',
      });

      const promptsConfig = {
        subjects: {
          LeetCode: {
            synthesis: 'MCQ Specific Combiner Rule',
          },
        },
      };

      await runStage2({
        runId,
        questionId: 'q-edge-6',
        stage1Results: [{ provider: 'openai', model: 'gpt-3.5-turbo', output: 'content' }],
        cardType: 'mcq',
        subject: 'LeetCode',
        prompts: promptsConfig,
        config,
        keys,
        clients,
        throttledFetch,
      });

      const calledWithParams = mockCreate.mock.calls[0][0];
      expect(calledWithParams.messages[0].content).toContain('MCQ Specific Combiner Rule');
    });
  });
});
