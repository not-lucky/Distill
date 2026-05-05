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
  removeNullValues,
  CARD_ZOD_SCHEMA,
  normalizeJsonObj,
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

describe('Stage 3 - AJV Schema Enforcement', () => {
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
        model_concurrency: 0,
        topic_concurrency: 1,
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

      const inputWithJs = '```javascript\n{"key": "value"}\n```';
      expect(cleanJsonOutput(inputWithJs)).toBe('{"key": "value"}');

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

  describe('normalizeJsonObj helper', () => {
    it('should pass non-objects straight through', () => {
      expect(normalizeJsonObj(null, 'q')).toBeNull();
      expect(normalizeJsonObj(123, 'q')).toBe(123);
      expect(normalizeJsonObj('str', 'q')).toBe('str');
    });

    it('should recover missing title, topic, and difficulty properties', () => {
      const input = {
        cards: [],
      };
      const result = normalizeJsonObj(input, 'leetcode::Arrays_&_Hashing::Two_Sum');
      expect(result.title).toBe('Two Sum');
      expect(result.topic).toBe('leetcode/Arrays_&_Hashing/Two_Sum');
      expect(result.difficulty).toBe('Intermediate');
    });

    it('should prune options and correct_answer from Basic and Cloze cards, and back from MCQ/Cloze cards', () => {
      const input = {
        title: 'Title',
        topic: 'Topic',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            front: 'Q',
            back: 'A',
            options: ['Option A'],
            correct_answer: 'A',
          },
          {
            card_format: 'Cloze',
            card_type: 'Concept',
            front: '{{c1::Cloze}} statement',
            back: 'should be pruned',
            options: ['Option B'],
            correct_answer: 'B',
          },
          {
            card_format: 'MCQ',
            card_type: 'Concept',
            front: 'MCQ Q',
            back: 'should be pruned',
            options: ['Option A', 'Option B'],
            correct_answer: 'A',
          },
        ],
      };

      const result = normalizeJsonObj(input, 'q');
      expect(result.cards[0].options).toBeUndefined();
      expect(result.cards[0].correct_answer).toBeUndefined();
      expect(result.cards[0].back).toBe('A');

      expect(result.cards[1].back).toBeUndefined();
      expect(result.cards[1].options).toBeUndefined();
      expect(result.cards[1].correct_answer).toBeUndefined();

      expect(result.cards[2].back).toBeUndefined();
      expect(result.cards[2].options).toEqual(['Option A', 'Option B']);
      expect(result.cards[2].correct_answer).toBe('A');
    });

    it('should enforce tags array format and filter out invalid tags', () => {
      const input = {
        cards: [
          {
            card_format: 'Basic',
            tags: null,
          },
          {
            card_format: 'Basic',
            tags: ['valid-tag', 'invalid tag with spaces'],
          },
        ],
      };

      const result = normalizeJsonObj(input, 'q');
      expect(result.cards[0].tags).toEqual([]);
      expect(result.cards[1].tags).toEqual(['valid-tag']);
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

    it('should enforce MCQ correct_answer D rules correctly', async () => {
      // MCQ with correct_answer "D" but only 3 options (invalid)
      const mockInvalidD = {
        title: 'Invalid MCQ D',
        topic: 'JS',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'MCQ',
            card_type: 'Behavior',
            tags: ['types'],
            front: 'Question',
            options: ['Option A', 'Option B', 'Option C'],
            correct_answer: 'D',
            explanation: 'Explanation',
          },
        ],
      };

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockInvalidD) } }],
      });

      const runId = 'run-mcq-invalid-d';
      createRun({
        runId,
        subject: 'JSPreset',
        cardType: 'mcq',
        status: 'running',
        configHash: 'hash-mcq-inv-d',
      });

      await expect(
        runStage3({
          runId: 'run-mcq-invalid-d',
          questionId: 'q-mcq-d',
          synthesisResult: 'Front: Question',
          config,
          keys,
          clients,
          throttledFetch,
          maxEnforcementRetries: 1,
        }),
      ).rejects.toThrow('options must NOT have fewer than 4 items');
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
      expect(secondCallParams.messages[3].content).toContain('Invalid input: expected string, received undefined');
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

    it('should save failed recovery attempts to the database pipeline steps and run questions tables', async () => {
      const openaiClient = clients.get('openai');
      const mockCompletions = vi.spyOn(openaiClient.chat.completions, 'create');

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

      // Mock first response as malformed JSON, second response as valid
      mockCompletions
        .mockResolvedValueOnce({
          choices: [{ message: { content: 'This is invalid JSON output {{{\n' } }],
        })
        .mockResolvedValueOnce({
          choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
        });

      const runId = 'run-failed-save-test';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-failed-save',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-failed-save',
        synthesisResult: 'Front: What is React?',
        config,
        keys,
        clients,
        throttledFetch,
        maxEnforcementRetries: 3,
      });

      expect(result).toEqual(mockResultObj);
      expect(mockCompletions).toHaveBeenCalledTimes(2);

      // Verify that 2 pipeline steps were logged (1 for failed attempt, 1 for successful attempt)
      const steps = getPipelineStepsForRun(runId);
      expect(steps).toHaveLength(2);
      expect(steps[0].stage).toBe('enforcement');
      expect(steps[0].output_data).toBe('This is invalid JSON output {{{\n');
      expect(steps[0].status).toBe('failed');
      expect(steps[0].errors).toContain('JSON Parsing Error');
      expect(steps[1].stage).toBe('enforcement');
      expect(steps[1].output_data).toBe(JSON.stringify(mockResultObj));
      expect(steps[1].status).toBe('success');
      expect(steps[1].errors).toBeNull();
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
      // Missing 'cards' root property, prompting a root-level error '/'
      const mockResultObj = {
        title: 'React Basics',
        topic: 'React',
        difficulty: 'Basic',
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
      ).rejects.toThrow('/cards: Invalid input: expected array, received undefined');
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
      ).rejects.toThrow('/cards: Invalid input: expected array, received undefined');
    });

    it('runStage3 edge cases: root-level validation error (empty path)', async () => {
      const mockResultObj = 'not-an-object-just-a-string';

      const openaiClient = clients.get('openai');
      vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const runId = 'run-root-val-error';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-root-val-error',
      });

      await expect(
        runStage3({
          runId: 'run-root-val-error',
          questionId: 'q-root-val-error',
          synthesisResult: 'Front: What is React?',
          config,
          keys,
          clients,
          throttledFetch,
          maxEnforcementRetries: 1,
        }),
      ).rejects.toThrow('/: Invalid input: expected object, received string');
    });

    it('should use chat.completions.create instead of client.responses.create when use_completion_api is true in config', async () => {
      const mockResultObj = {
        title: 'React Basics',
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
      // Mock both completions and responses so we can see which one gets called
      openaiClient.responses = {
        create: vi.fn().mockResolvedValue({ output_text: JSON.stringify(mockResultObj) }),
      };
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: JSON.stringify(mockResultObj) } }],
      });

      const configWithCompletion = {
        ...config,
        pipeline: {
          schema_enforcement: {
            model: 'openai/gpt-3.5-turbo',
            use_completion_api: true,
          },
        },
      };

      const runId = 'run-completion-api-config';
      createRun({
        runId,
        subject: 'ReactPreset',
        cardType: 'standard',
        status: 'running',
        configHash: 'hash-completion-api',
      });

      const result = await runStage3({
        runId,
        questionId: 'q-completion-api',
        synthesisResult: 'Front: What is React?',
        config: configWithCompletion,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toEqual(mockResultObj);
      expect(createSpy).toHaveBeenCalledTimes(1);
      expect(openaiClient.responses.create).not.toHaveBeenCalled();

      // Clean up mock
      delete openaiClient.responses;
    });
  });

  describe('removeNullValues helper', () => {
    it('should recursively strip null and undefined fields', () => {
      const input = {
        title: 'Title',
        topic: 'Topic',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            front: 'What is A?',
            back: 'B',
            options: null,
            correct_answer: null,
            explanation: 'Expl',
          },
          {
            card_format: 'MCQ',
            front: 'What is MCQ?',
            back: null,
            options: ['A', 'B'],
            correct_answer: 'A',
            explanation: 'Expl 2',
          },
        ],
        extraField: undefined,
      };

      const expected = {
        title: 'Title',
        topic: 'Topic',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            front: 'What is A?',
            back: 'B',
            explanation: 'Expl',
          },
          {
            card_format: 'MCQ',
            front: 'What is MCQ?',
            options: ['A', 'B'],
            correct_answer: 'A',
            explanation: 'Expl 2',
          },
        ],
      };

      expect(removeNullValues(input)).toEqual(expected);
    });

    it('should handle primitives and arrays correctly', () => {
      expect(removeNullValues(null)).toBeNull();
      expect(removeNullValues(undefined)).toBeUndefined();
      expect(removeNullValues('string')).toBe('string');
      expect(removeNullValues(123)).toBe(123);
      expect(removeNullValues([1, null, 2, { a: null, b: 3 }])).toEqual([1, null, 2, { b: 3 }]);
    });
  });

  describe('CARD_ZOD_SCHEMA parse verification', () => {
    it('should parse valid card decks with nullable fields', () => {
      const validDeck = {
        title: 'JS Basics',
        topic: 'Javascript',
        difficulty: 'Basic',
        cards: [
          {
            card_format: 'Basic',
            card_type: 'Concept',
            tags: ['javascript', 'basics'],
            front: 'What is a closure?',
            back: 'A closure is a function combined with its lexical environment.',
            options: null,
            correct_answer: null,
            explanation: 'Closures are created at function creation time.',
          },
          {
            card_format: 'MCQ',
            card_type: 'Syntax',
            tags: ['js', 'syntax'],
            front: 'Which keyword defines a constant?',
            back: null,
            options: ['var', 'let', 'const'],
            correct_answer: 'C',
            explanation: 'const is block scoped and cannot be reassigned.',
          },
        ],
      };

      const result = CARD_ZOD_SCHEMA.safeParse(validDeck);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validDeck);
      }
    });

    it('should fail parsing if required fields are missing', () => {
      const invalidDeck = {
        title: 'JS Basics',
        topic: 'Javascript',
        // difficulty is missing
        cards: [],
      };

      const result = CARD_ZOD_SCHEMA.safeParse(invalidDeck);
      expect(result.success).toBe(false);
    });
  });
});
