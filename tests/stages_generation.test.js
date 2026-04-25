import {
  vi, describe, it, expect, beforeEach, afterEach, beforeAll, afterAll,
} from 'vitest';
import fs from 'fs';
import {
  initDatabase, closeDatabase, getPipelineStepsForRun, createRun, clearCache,
} from '../src/database.js';
import {
  createProviderClients, createThrottledFetcher,
} from '../src/providers.js';
import {
  resolvePrompts,
  DEFAULT_GENERATION,
  DEFAULT_SYNTHESIS,
  DEFAULT_ENFORCEMENT,
} from '../src/prompts.js';
import {
  runStage1,
} from '../src/stages.js';
import { loadConfig } from '../src/config.js';

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

describe('Stage 1 Pipeline - Parallel Card Generation & Dynamic Prompts', () => {
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
        cerebras: {
          base_url: 'https://api.cerebras.ai/v1',
          temperature: 0.2,
        },
      },
      pipeline: {
        generation: {
          models: [
            'openai/gpt-3.5-turbo',
            'cerebras/llama3.1-70b',
          ],
        },
      },
    };

    keys = {
      openai: 'key-openai',
      cerebras: 'key-cerebras',
    };

    clients = createProviderClients(config, keys);
    throttledFetch = createThrottledFetcher(config);
  });

  describe('resolvePrompts with Hardcoded Fallbacks', () => {
    it('should resolve standard stage prompts by default', () => {
      const prompts = resolvePrompts({}, '', 'standard');
      expect(prompts.generation).toContain(DEFAULT_GENERATION);
      expect(prompts.synthesis).toBe(DEFAULT_SYNTHESIS);
      expect(prompts.enforcement).toBe(DEFAULT_ENFORCEMENT);
    });

    it('should inject format templates correctly', () => {
      const standard = resolvePrompts({}, '', 'standard');
      expect(standard.generation).toContain('Front: [The active recall question or statement');

      const mcq = resolvePrompts({}, '', 'mcq');
      expect(mcq.generation).toContain('Correct: [The correct option letter: A, B, C, or D]');
    });

    it('should handle non-string subject values gracefully', () => {
      const pNull = resolvePrompts({}, null, 'standard');
      expect(pNull.generation).toContain(DEFAULT_GENERATION);

      const pUndefined = resolvePrompts({}, undefined, 'standard');
      expect(pUndefined.generation).toContain(DEFAULT_GENERATION);

      const pNumber = resolvePrompts({}, 12345, 'standard');
      expect(pNumber.generation).toContain(DEFAULT_GENERATION);

      const pObj = resolvePrompts({}, {}, 'standard');
      expect(pObj.generation).toContain(DEFAULT_GENERATION);
    });

    it('should handle subjects config being invalid (non-object or null)', () => {
      const pStringSubjects = resolvePrompts({ subjects: 'invalid-subjects' }, 'test', 'standard');
      expect(pStringSubjects.generation).toContain(DEFAULT_GENERATION);

      const pNullSubjects = resolvePrompts({ subjects: null }, 'test', 'standard');
      expect(pNullSubjects.generation).toContain(DEFAULT_GENERATION);
    });
  });

  describe('resolvePrompts with YAML configuration overrides', () => {
    it('should override defaults with yaml defaults', () => {
      const yamlConfig = {
        defaults: {
          generation: 'YAML Gen Override',
          synthesis: 'YAML Synth Override',
          schema_enforcement: 'YAML Enforce Override',
        },
      };

      const prompts = resolvePrompts(yamlConfig, '', 'standard');
      expect(prompts.generation).toContain('YAML Gen Override');
      expect(prompts.synthesis).toBe('YAML Synth Override');
      expect(prompts.enforcement).toBe('YAML Enforce Override');
    });

    it('should resolve subject-specific overrides case-insensitively', () => {
      const yamlConfig = {
        subjects: {
          LeetCode: {
            generation: 'Custom LC Generation Guidelines',
            synthesis: 'Custom LC Synthesis Combiner Guidelines',
          },
        },
      };

      const p1 = resolvePrompts(yamlConfig, 'LeetCode', 'standard');
      expect(p1.generation).toContain('Custom LC Generation Guidelines');
      expect(p1.synthesis).toContain('Custom LC Synthesis Combiner Guidelines');

      const p2 = resolvePrompts(yamlConfig, 'leetcode', 'standard');
      expect(p2.generation).toContain('Custom LC Generation Guidelines');
      expect(p2.synthesis).toContain('Custom LC Synthesis Combiner Guidelines');
    });

    it('should handle subjects with empty config fields', () => {
      const yamlConfig = {
        subjects: {
          leetcode: {},
        },
      };
      const prompts = resolvePrompts(yamlConfig, 'leetcode', 'standard');
      expect(prompts.generation).toContain(DEFAULT_GENERATION);
      expect(prompts.synthesis).toBe(DEFAULT_SYNTHESIS);
    });

    it('should fall back to hardcoded defaults when subject is not in subjects config map', () => {
      const yamlConfig = {
        subjects: {
          LeetCode: {},
        },
      };
      const prompts = resolvePrompts(yamlConfig, 'nonexistent', 'standard');
      expect(prompts.generation).toContain(DEFAULT_GENERATION);
    });
  });

  describe('Config Loader Integration', () => {
    const tempConfigPath = './tests/temp_config.yaml';
    const tempPromptsPath = './tests/temp_prompts.yaml';

    afterEach(() => {
      if (fs.existsSync(tempConfigPath)) fs.unlinkSync(tempConfigPath);
      if (fs.existsSync(tempPromptsPath)) fs.unlinkSync(tempPromptsPath);
    });

    it('should load prompts.yaml file from config parameter', () => {
      const configYaml = `
global:
  prompts_file_path: "${tempPromptsPath}"
`;
      const promptsYaml = `
defaults:
  generation: "Configured YAML Gen"
subjects:
  test_subject:
    generation: "Test Gen Custom"
`;
      fs.writeFileSync(tempConfigPath, configYaml);
      fs.writeFileSync(tempPromptsPath, promptsYaml);

      const { prompts } = loadConfig(tempConfigPath, '/dev/null');
      expect(prompts.defaults?.generation).toBe('Configured YAML Gen');
      expect(prompts.subjects?.test_subject?.generation).toBe('Test Gen Custom');
    });

    it('should handle empty/missing prompts file gracefully without warnings/errors', () => {
      const configYaml = `
global:
  prompts_file_path: "./tests/non_existent_prompts.yaml"
`;
      fs.writeFileSync(tempConfigPath, configYaml);
      const { prompts, warnings } = loadConfig(tempConfigPath, '/dev/null');
      expect(prompts).toEqual({});
      expect(warnings.filter((w) => w.includes('non_existent_prompts'))).toHaveLength(0);
    });

    it('should record warning if prompts file is empty or invalid', () => {
      const configYaml = `
global:
  prompts_file_path: "${tempPromptsPath}"
`;
      fs.writeFileSync(tempConfigPath, configYaml);
      fs.writeFileSync(tempPromptsPath, 'invalid: : : yaml');

      const { prompts, warnings } = loadConfig(tempConfigPath, '/dev/null');
      expect(prompts).toEqual({});
      expect(warnings.some((w) => w.includes('Error reading prompts file') || w.includes('empty or invalid'))).toBe(true);
    });

    it('should record warning if prompts file is empty string', () => {
      const configYaml = `
global:
  prompts_file_path: "${tempPromptsPath}"
`;
      fs.writeFileSync(tempConfigPath, configYaml);
      fs.writeFileSync(tempPromptsPath, '');

      const { prompts, warnings } = loadConfig(tempConfigPath, '/dev/null');
      expect(prompts).toEqual({});
      expect(warnings.some((w) => w.includes('empty or invalid'))).toBe(true);
    });

    it('should record warning if prompts file is not an object', () => {
      const configYaml = `
global:
  prompts_file_path: "${tempPromptsPath}"
`;
      fs.writeFileSync(tempConfigPath, configYaml);
      fs.writeFileSync(tempPromptsPath, '42');

      const { prompts, warnings } = loadConfig(tempConfigPath, '/dev/null');
      expect(prompts).toEqual({});
      expect(warnings.some((w) => w.includes('empty or invalid'))).toBe(true);
    });
  });

  describe('runStage1 with Dynamic Prompts', () => {
    it('should throw an error if no models are configured', async () => {
      const invalidConfig = {
        pipeline: {
          generation: {
            models: [],
          },
        },
      };

      await expect(
        runStage1({
          runId: 'run-test-1',
          questionId: 'q-test-1',
          content: 'Some test content',
          deckPath: 'General::Test',
          cardType: 'standard',
          config: invalidConfig,
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('No generation models configured');
    });

    it('should throw an error if pipeline is missing', async () => {
      await expect(
        runStage1({
          runId: 'run-test-2',
          questionId: 'q-test-2',
          content: 'Some test content',
          deckPath: 'General::Test',
          cardType: 'standard',
          config: {},
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('No generation models configured');
    });

    it('should throw an error if generation block is missing', async () => {
      await expect(
        runStage1({
          runId: 'run-test-3',
          questionId: 'q-test-3',
          content: 'Some test content',
          deckPath: 'General::Test',
          cardType: 'standard',
          config: { pipeline: {} },
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('No generation models configured');
    });

    it('should throw an error if models block is missing', async () => {
      await expect(
        runStage1({
          runId: 'run-test-4',
          questionId: 'q-test-4',
          content: 'Some test content',
          deckPath: 'General::Test',
          cardType: 'standard',
          config: { pipeline: { generation: {} } },
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('No generation models configured');
    });

    it('should execute parallel model queries using resolved generation prompt from YAML', async () => {
      const openaiClient = clients.get('openai');
      const cerebrasClient = clients.get('cerebras');

      const mockOpenaiCreate = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'OpenAI output' } }],
      });
      const mockCerebrasCreate = vi.spyOn(cerebrasClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Cerebras output' } }],
      });

      const runId = 'run-parallel-yaml-1';
      createRun({
        runId,
        subject: 'MyDynamicSubject',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      const promptsConfig = {
        subjects: {
          MyDynamicSubject: {
            generation: 'DYNAMIC SYSTEM PROMPT FROM YAML FILE',
          },
        },
      };

      const result = await runStage1({
        runId,
        questionId: 'q-1',
        content: 'Topic content',
        deckPath: 'Deck::Path',
        cardType: 'standard',
        subject: 'MyDynamicSubject',
        prompts: promptsConfig,
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toHaveLength(2);
      expect(mockOpenaiCreate).toHaveBeenCalledTimes(1);
      expect(mockCerebrasCreate).toHaveBeenCalledTimes(1);

      const steps = getPipelineStepsForRun(runId);
      expect(steps).toHaveLength(2);

      const openaiStep = steps.find((s) => s.provider === 'openai');
      expect(openaiStep).toBeDefined();
      expect(openaiStep.input_data).toContain('DYNAMIC SYSTEM PROMPT FROM YAML FILE');
    });

    it('should propagate API errors correctly when one model fails in parallel', async () => {
      const openaiClient = clients.get('openai');
      const cerebrasClient = clients.get('cerebras');

      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'OpenAI output' } }],
      });
      const apiError = new Error('Cerebras API Error');
      apiError.status = 400;
      vi.spyOn(cerebrasClient.chat.completions, 'create').mockRejectedValue(apiError);

      const runId = 'run-parallel-error-1';
      createRun({
        runId,
        subject: 'ErrorSubject',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      await expect(
        runStage1({
          runId,
          questionId: 'q-err',
          content: 'Some content',
          deckPath: 'Deck::Error',
          cardType: 'standard',
          subject: 'ErrorSubject',
          prompts: {},
          config,
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('Cerebras API Error');
    });

    it('should generate a topic-based user prompt when content is empty or not provided', async () => {
      const openaiClient = clients.get('openai');
      const cerebrasClient = clients.get('cerebras');

      const mockOpenaiCreate = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'OpenAI output' } }],
      });
      vi.spyOn(cerebrasClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Cerebras output' } }],
      });

      const runId = 'run-parallel-empty-content';
      createRun({
        runId,
        subject: 'General',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash123',
      });

      await runStage1({
        runId,
        questionId: 'some_topic_name',
        content: '',
        topicName: 'Custom Topic Name',
        deckPath: 'Deck::Path',
        cardType: 'standard',
        subject: 'General',
        prompts: {},
        config,
        keys,
        clients,
        throttledFetch,
      });

      // Verify prompt uses topicName
      expect(mockOpenaiCreate.mock.calls[0][0]).toEqual(expect.objectContaining({
        messages: expect.arrayContaining([
          expect.objectContaining({
            role: 'user',
            content: 'Please generate comprehensive flashcards for the following topic: Custom Topic Name',
          }),
        ]),
      }));

      // Test fallback to questionId if topicName is also missing
      await runStage1({
        runId,
        questionId: 'fallback_question_id',
        content: '',
        topicName: '',
        deckPath: 'Deck::Path',
        cardType: 'standard',
        subject: 'General',
        prompts: {},
        config,
        keys,
        clients,
        throttledFetch,
      });

      // Verify prompt uses normalized questionId
      expect(mockOpenaiCreate.mock.calls[1][0]).toEqual(expect.objectContaining({
        messages: expect.arrayContaining([
          expect.objectContaining({
            role: 'user',
            content: 'Please generate comprehensive flashcards for the following topic: fallback question id',
          }),
        ]),
      }));
    });
  });
});
