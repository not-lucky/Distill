import {
  vi, describe, it, expect, beforeEach, beforeAll, afterAll,
} from 'vitest';
import {
  initDatabase, closeDatabase, getPipelineStepsForRun, createRun, clearCache,
} from '../src/database.js';
import {
  createProviderClients, createThrottledFetcher,
} from '../src/providers.js';
import {
  cleanJsonOutput,
  parseStage2Questions,
  verifyContentLoss,
  runStage3,
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

describe('Stage 3 - JSON Translation & AJV Schema Enforcement', () => {
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
        schema_enforcement: {
          model: 'openai/gpt-3.5-turbo',
        },
      },
    };

    keys = {
      openai: 'key-openai',
    };

    clients = createProviderClients(config, keys);
    throttledFetch = createThrottledFetcher(config);
  });

  describe('cleanJsonOutput helper', () => {
    it('should strip markdown code block fences correctly', () => {
      const inputWithJson = '```json\n{"key": "value"}\n```';
      expect(cleanJsonOutput(inputWithJson)).toBe('{"key": "value"}');

      const inputPlainFence = '```\n{"key": "value"}\n```';
      expect(cleanJsonOutput(inputPlainFence)).toBe('{"key": "value"}');

      const inputNoFence = '{"key": "value"}';
      expect(cleanJsonOutput(inputNoFence)).toBe('{"key": "value"}');

      expect(cleanJsonOutput(null)).toBe('');
      expect(cleanJsonOutput(undefined)).toBe('');
    });
  });

  describe('parseStage2Questions helper', () => {
    it('should parse questions with various prefixes correctly', () => {
      const text = `
Card 1 Q: What is React?
---
Front: How does useEffect work?
---
**Question:** Explain Virtual DOM
---
**Q:** Why use Redux?
---
Card 2 Front: What is JSX?
      `;
      const questions = parseStage2Questions(text);
      expect(questions).toEqual([
        'What is React?',
        'How does useEffect work?',
        'Explain Virtual DOM',
        'Why use Redux?',
        'What is JSX?',
      ]);
    });
  });

  describe('verifyContentLoss helper', () => {
    it('should identify missing questions using normalized comparison', () => {
      const stage2 = ['What is React?', 'How does useEffect work?'];
      const stage3Valid = [
        { front: 'what is react?' },
        { front: 'How does useEffect work! (details)' },
      ];
      expect(verifyContentLoss(stage2, stage3Valid)).toEqual([]);

      const stage3Missing = [
        { front: 'what is react?' },
      ];
      expect(verifyContentLoss(stage2, stage3Missing)).toEqual(['How does useEffect work?']);
    });
  });

  describe('runStage3 main function', () => {
    it('should throw error if synthesisResult is missing or empty', async () => {
      await expect(
        runStage3({
          runId: 'run-3-1',
          questionId: 'q-3-1',
          synthesisResult: '',
          config,
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('Stage 2 synthesis result is missing or empty');
    });

    it('should throw error if model configuration is missing', async () => {
      const badConfig = { pipeline: {} };
      await expect(
        runStage3({
          runId: 'run-3-2',
          questionId: 'q-3-2',
          synthesisResult: 'Front: Test Q',
          config: badConfig,
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow('No schema enforcement model configured');
    });

    it('should validate and parse correct Basic cards successfully', async () => {
      const mockResultObj = {
        title: 'React Basics',
        topic: 'React',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['react', 'basics'],
            front: 'What is React?',
            back: 'A JavaScript library for building user interfaces.',
            explanation: 'React uses a virtual DOM to optimize rendering performance.',
          },
        ],
      };

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const runId = 'run-basic-success';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-basic',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-basic',
        synthesisResult: 'Front: What is React?\nBack: A library',
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toEqual(mockResultObj);

      // Verify db log step
      const steps = getPipelineStepsForRun(runId);
      expect(steps).toHaveLength(1);
      expect(steps[0].stage).toBe('enforcement');
    });

    it('should validate and parse correct Cloze cards successfully', async () => {
      const mockResultObj = {
        title: 'React Hooks',
        topic: 'React',
        difficulty: 'Intermediate',
        cards: [
          {
            card_format: 'Cloze',
            card_type: 'Syntax',
            tags: ['hooks'],
            front: 'Use the {{c1::useState}} hook to manage functional state.',
            explanation: 'useState returns a state value and a setter function.',
          },
        ],
      };

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const runId = 'run-cloze-success';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-cloze',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-cloze',
        synthesisResult: 'Front: Use the {{c1::useState}} hook to manage functional state.',
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toEqual(mockResultObj);
    });

    it('should validate and parse correct MCQ cards successfully', async () => {
      const mockResultObj = {
        title: 'JS Types',
        topic: 'JavaScript',
        difficulty: 'Advanced',
        cards: [
          {
            card_format: 'MCQ',
            card_type: 'Behavior',
            tags: ['types'],
            front: 'Which of the following is NOT a primitive type in JavaScript?',
            options: ['String', 'Number', 'Object', 'Boolean'],
            correct_answer: 'C',
            explanation: 'Objects are reference types, not primitive types.',
          },
        ],
      };

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const runId = 'run-mcq-success';
      createRun({
        runId,
        subject: 'JSPreset',
        cardType: 'mcq',
        status: 'running',
        configHash: 'hash-mcq',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-mcq',
        synthesisResult: 'Front: Which of the following is NOT a primitive type in JavaScript?',
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toEqual(mockResultObj);
    });

    it('should enforce MCQ correct_answer rules correctly', async () => {
      // MCQ with correct_answer "C" but only 2 options (invalid)
      const mockInvalidC = {
        title: 'Invalid MCQ',
        topic: 'JS',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'MCQ',
            card_type: 'Behavior',
            tags: ['types'],
            front: 'Question',
            options: ['Option A', 'Option B'],
            correct_answer: 'C',
            explanation: 'Explanation',
          },
        ],
      };

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockInvalidC) } }],
      });

      const runId = 'run-mcq-invalid-c';
      createRun({
        runId,
        subject: 'JSPreset',
        cardType: 'mcq',
        status: 'running',
        configHash: 'hash-mcq-inv',
      });

      await expect(
        runStage3({
          runId: 'run-mcq-invalid-c',
          questionId: 'q-mcq-c',
          synthesisResult: 'Front: Question',
          config,
          keys,
          clients,
          throttledFetch,
          maxEnforcementRetries: 1,
        }),
      ).rejects.toThrow('must NOT have fewer than 3 items');
    });

    it('should trigger recovery loop on malformed JSON and succeed on retry', async () => {
      const openaiClient = clients.get('openai');
      const mockCompletions = vi.spyOn(openaiClient.chat.completions, 'create');

      // First response is malformed JSON, second response is valid
      const mockResultObj = {
        title: 'React Recovery',
        topic: 'React',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['react'],
            front: 'What is React?',
            back: 'A library',
            explanation: 'Details',
          },
        ],
      };

      mockCompletions
        .mockResolvedValueOnce({
          choices: [{ message: { content: 'This is invalid JSON output {{{' } }],
        })
        .mockResolvedValueOnce({
          choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
        });

      const runId = 'run-recovery-json';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-rec-json',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-recovery-json',
        synthesisResult: 'Front: What is React?',
        config,
        keys,
        clients,
        throttledFetch,
        maxEnforcementRetries: 3,
      });

      expect(result).toEqual(mockResultObj);
      expect(mockCompletions).toHaveBeenCalledTimes(2);

      // Verify the retry prompt included the JSON Parsing error message
      const secondCallParams = mockCompletions.mock.calls[1][0];
      expect(secondCallParams.messages).toHaveLength(4);
      expect(secondCallParams.messages[2].role).toBe('assistant');
      expect(secondCallParams.messages[3].role).toBe('user');
      expect(secondCallParams.messages[3].content).toContain('JSON Parsing Error');
    });

    it('should trigger recovery loop on AJV validation error and succeed on retry', async () => {
      const openaiClient = clients.get('openai');
      const mockCompletions = vi.spyOn(openaiClient.chat.completions, 'create');

      // First response has validation error (missing required 'explanation' on card),
      // second is valid
      const mockInvalidObj = {
        title: 'React Validation',
        topic: 'React',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['react'],
            front: 'What is React?',
            back: 'A library',
            // explanation missing
          },
        ],
      };

      const mockResultObj = {
        title: 'React Validation',
        topic: 'React',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['react'],
            front: 'What is React?',
            back: 'A library',
            explanation: 'Details',
          },
        ],
      };

      mockCompletions
        .mockResolvedValueOnce({
          choices: [{ message: { content: JSON.stringify(mockInvalidObj) } }],
        })
        .mockResolvedValueOnce({
          choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
        });

      const runId = 'run-recovery-schema';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-rec-schema',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-recovery-schema',
        synthesisResult: 'Front: What is React?',
        config,
        keys,
        clients,
        throttledFetch,
        maxEnforcementRetries: 3,
      });

      expect(result).toEqual(mockResultObj);
      expect(mockCompletions).toHaveBeenCalledTimes(2);

      const secondCallParams = mockCompletions.mock.calls[1][0];
      expect(secondCallParams.messages[3].content).toContain('must have required property');
    });

    it('should trigger recovery loop on Content Loss Audit failure and succeed on retry', async () => {
      const openaiClient = clients.get('openai');
      const mockCompletions = vi.spyOn(openaiClient.chat.completions, 'create');

      // First response misses one of the questions from synthesisResult
      const mockInvalidObj = {
        title: 'React Audit',
        topic: 'React',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['react'],
            front: 'What is React?',
            back: 'A library',
            explanation: 'Details',
          },
        ],
      };

      const mockResultObj = {
        title: 'React Audit',
        topic: 'React',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['react'],
            front: 'What is React?',
            back: 'A library',
            explanation: 'Details',
          },
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['virtual-dom'],
            front: 'Explain Virtual DOM',
            back: 'A lightweight representation of the real DOM.',
            explanation: 'Used for reconciliation.',
          },
        ],
      };

      mockCompletions
        .mockResolvedValueOnce({
          choices: [{ message: { content: JSON.stringify(mockInvalidObj) } }],
        })
        .mockResolvedValueOnce({
          choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
        });

      const runId = 'run-recovery-audit';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-rec-audit',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-recovery-audit',
        synthesisResult: 'Front: What is React?\nFront: Explain Virtual DOM',
        config,
        keys,
        clients,
        throttledFetch,
        maxEnforcementRetries: 3,
      });

      expect(result).toEqual(mockResultObj);
      expect(mockCompletions).toHaveBeenCalledTimes(2);

      const secondCallParams = mockCompletions.mock.calls[1][0];
      expect(secondCallParams.messages[3].content).toContain('Content Loss Audit Error');
      expect(secondCallParams.messages[3].content).toContain('Explain Virtual DOM');
    });

    it('should throw error when all recovery loop attempts fail', async () => {
      const openaiClient = clients.get('openai');
      const mockCompletions = vi.spyOn(openaiClient.chat.completions, 'create');

      // All responses are invalid JSON
      mockCompletions.mockResolvedValue({
        choices: [{ message: { content: 'Invalid JSON completely' } }],
      });

      const runId = 'run-recovery-fail';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-rec-fail',
      });

      await expect(
        runStage3({
          runId: 'run-recovery-fail',
          questionId: 'q-recovery-fail',
          synthesisResult: 'Front: What is React?',
          config,
          keys,
          clients,
          throttledFetch,
          maxEnforcementRetries: 2,
        }),
      ).rejects.toThrow('Stage 3 Schema Enforcement failed after 2 attempts');
    });

    it('should fall back to translation model if schema_enforcement model is not configured', async () => {
      const fallbackConfig = {
        global: config.global,
        providers: config.providers,
        pipeline: {
          translation: {
            model: 'openai/gpt-3.5-turbo-fallback',
          },
        },
      };

      const mockResultObj = {
        title: 'Fallback Model',
        topic: 'React',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['react'],
            front: 'What is React?',
            back: 'A library',
            explanation: 'Details',
          },
        ],
      };

      const openaiClient = clients.get('openai');
      const mockCompletions = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const runId = 'run-fallback';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-fallback',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-fallback',
        synthesisResult: 'Front: What is React?',
        config: fallbackConfig,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toEqual(mockResultObj);
      expect(mockCompletions.mock.calls[0][0].model).toBe('gpt-3.5-turbo-fallback');
    });
  });

  describe('Additional Edge Cases', () => {
    it('verifyContentLoss edge cases: stage3Cards is not an array', () => {
      const stage2 = ['What is React?'];
      expect(verifyContentLoss(stage2, null)).toEqual(stage2);
      expect(verifyContentLoss(stage2, undefined)).toEqual(stage2);
      expect(verifyContentLoss(stage2, {})).toEqual(stage2);
    });

    it('verifyContentLoss edge cases: stage2 has empty/non-alphanumeric questions', () => {
      const stage2 = ['?', '   ', '!!!'];
      // Should skip them without checking or flagging as missing
      expect(verifyContentLoss(stage2, [])).toEqual([]);
    });

    it('verifyContentLoss edge cases: card is null or front is not a string', () => {
      const stage2 = ['What is React?'];
      const cards = [null, { front: 123 }, { front: 'What is React?' }];
      expect(verifyContentLoss(stage2, cards)).toEqual([]);
    });

    it('cleanJsonOutput edge cases: non-string or no match', () => {
      expect(cleanJsonOutput(1234)).toBe('');
      // If codeBlockMatch matches but we have text outside
      expect(cleanJsonOutput('some text ```json\n{"a": 1}\n``` other text')).toBe('{"a": 1}');
    });

    it('parseStage2Questions edge cases: non-string input or empty matching line', () => {
      expect(parseStage2Questions(123)).toEqual([]);
      expect(parseStage2Questions(null)).toEqual([]);
      expect(parseStage2Questions('Front:\nFront:   ')).toEqual([]);
    });

    it('runStage3 edge cases: prompts.schema_enforcement override empty and root level AJV validation error', async () => {
      // Missing 'title' root property, prompting a root-level error '/'
      const mockResultObj = {
        topic: 'React',
        difficulty: 'Basic',
        cards: [],
      };

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const runId = 'run-root-error';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-root',
      });

      // Pass empty schema_enforcement to test DEFAULT_ENFORCEMENT fallback
      await expect(
        runStage3({
          runId,
          questionId: 'q-root-error',
          synthesisResult: 'Front: What is React?',
          prompts: { defaults: { schema_enforcement: '' } },
          config,
          keys,
          clients,
          throttledFetch,
          maxEnforcementRetries: 1,
        }),
      ).rejects.toThrow("/: must have required property 'title'");
    });

    it('runStage3 edge cases: cards array is missing in json response', async () => {
      // Result missing cards property entirely
      const mockResultObj = {
        title: 'React Basics',
        topic: 'React',
        difficulty: 'Basic',
      };

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const runId = 'run-missing-cards';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-missing-cards',
      });

      await expect(
        runStage3({
          runId,
          questionId: 'q-missing-cards',
          synthesisResult: 'Front: What is React?',
          config,
          keys,
          clients,
          throttledFetch,
          maxEnforcementRetries: 1,
        }),
      ).rejects.toThrow("/: must have required property 'cards'");
    });
  });
});
