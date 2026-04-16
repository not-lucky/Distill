import { describe, it, expect } from 'vitest';
import {
  normalizeTags,
  normalizeQuestion,
  deduplicateCards,
  injectMetadata,
  unescapeNewlines,
  postProcess,
} from '../src/postProcess.js';

describe('Post-Processing Module', () => {
  describe('normalizeTags', () => {
    it('should strip all whitespace characters from tag strings', () => {
      const cards = [
        { tags: ['Trade Off', '  Error Handling  ', 'react-hooks'] },
        { tags: ['cleanCode', '  '] },
      ];
      const result = normalizeTags(cards);
      expect(result).toEqual([
        { tags: ['TradeOff', 'ErrorHandling', 'react-hooks'] },
        { tags: ['cleanCode', ''] },
      ]);
    });

    it('should return empty array if cards is not an array', () => {
      expect(normalizeTags(null)).toEqual([]);
      expect(normalizeTags(undefined)).toEqual([]);
      expect(normalizeTags({})).toEqual([]);
    });

    it('should handle card without tags or tags as non-array gracefully', () => {
      const cards = [
        { front: 'Q1' },
        null,
        undefined,
        { tags: null },
        { tags: 'not-an-array' },
      ];
      expect(normalizeTags(cards)).toEqual([
        { front: 'Q1' },
        null,
        undefined,
        { tags: null },
        { tags: 'not-an-array' },
      ]);
    });

    it('should skip non-string items in tags array', () => {
      const cards = [
        { tags: ['Trade Off', 123, null, undefined] },
      ];
      expect(normalizeTags(cards)).toEqual([
        { tags: ['TradeOff', 123, null, undefined] },
      ]);
    });
  });

  describe('normalizeQuestion', () => {
    it('should convert to lowercase, strip spaces and punctuation', () => {
      expect(normalizeQuestion('What is React?')).toBe('whatisreact');
      expect(normalizeQuestion('Explain the Event Loop (microtasks vs macrotasks).')).toBe('explaintheeventloopmicrotasksvsmacrotasks');
      expect(normalizeQuestion('   Trim and punctuation!!! ... ')).toBe('trimandpunctuation');
      expect(normalizeQuestion('')).toBe('');
    });

    it('should return empty string for non-string inputs', () => {
      expect(normalizeQuestion(null)).toBe('');
      expect(normalizeQuestion(undefined)).toBe('');
      expect(normalizeQuestion(1234)).toBe('');
      expect(normalizeQuestion({})).toBe('');
    });
  });

  describe('deduplicateCards', () => {
    it('should keep the card with the longer explanation when duplicate questions occur', () => {
      const cards = [
        { front: 'What is React?', explanation: 'A library.' },
        { front: 'what is react?', explanation: 'React is a popular frontend JavaScript library developed by Facebook.' },
        { front: 'What is React!?', explanation: 'Short desc.' },
      ];
      const result = deduplicateCards(cards);
      expect(result).toHaveLength(1);
      expect(result[0].explanation).toBe('React is a popular frontend JavaScript library developed by Facebook.');
    });

    it('should preserve original order of unique cards based on their first appearance', () => {
      const cards = [
        { front: 'Q1', explanation: 'A1' },
        { front: 'Q2', explanation: 'A2' },
        { front: 'q1', explanation: 'A1 - longer version' },
        { front: 'Q3', explanation: 'A3' },
      ];
      const result = deduplicateCards(cards);
      expect(result).toEqual([
        { front: 'q1', explanation: 'A1 - longer version' },
        { front: 'Q2', explanation: 'A2' },
        { front: 'Q3', explanation: 'A3' },
      ]);
    });

    it('should handle undefined or null explanation by treating length as 0', () => {
      const cards = [
        { front: 'Q1', explanation: null },
        { front: 'q1', explanation: 'Explanation' },
        { front: 'Q2' },
        { front: 'q2', explanation: 'Longer' },
      ];
      const result = deduplicateCards(cards);
      expect(result).toEqual([
        { front: 'q1', explanation: 'Explanation' },
        { front: 'q2', explanation: 'Longer' },
      ]);
    });

    it('should return empty array if input cards is not an array', () => {
      expect(deduplicateCards(null)).toEqual([]);
      expect(deduplicateCards(undefined)).toEqual([]);
    });

    it('should skip null/undefined card entries gracefully', () => {
      const cards = [
        { front: 'Q1', explanation: 'A1' },
        null,
        undefined,
        { front: 'Q2', explanation: 'A2' },
      ];
      expect(deduplicateCards(cards)).toEqual([
        { front: 'Q1', explanation: 'A1' },
        { front: 'Q2', explanation: 'A2' },
      ]);
    });
  });

  describe('injectMetadata', () => {
    it('should inject category index, category name, and problem index into the data object', () => {
      const data = { title: 'Valid Palindrome', topic: 'Two Pointers' };
      const metadata = {
        categoryName: 'Arrays & Hashing',
        categoryIndex: 1,
        problemIndex: 4,
      };
      const result = injectMetadata(data, metadata);
      expect(result).toEqual({
        title: 'Valid Palindrome',
        topic: 'Two Pointers',
        category_name: 'Arrays & Hashing',
        category_index: 1,
        problem_index: 4,
      });
    });

    it('should not inject undefined or null values', () => {
      const data = { title: 'Title' };
      const result = injectMetadata(data, {
        categoryIndex: undefined,
        categoryName: null,
      });
      expect(result).toEqual({ title: 'Title' });
    });

    it('should return input parameter if it is not a valid object', () => {
      expect(injectMetadata(null)).toBeNull();
      expect(injectMetadata(undefined)).toBeUndefined();
      expect(injectMetadata('not-an-object')).toBe('not-an-object');
    });
  });

  describe('unescapeNewlines', () => {
    it('should replace literal \\n with actual newline character in string fields', () => {
      const cards = [
        {
          front: 'Line 1\\nLine 2',
          back: 'Answer\\nwith\\nnewlines',
          explanation: 'Explanation\\nwith\\nnewlines',
          options: ['Option A\\nmultiline', 'Option B', 123],
        },
      ];
      const result = unescapeNewlines(cards);
      expect(result).toEqual([
        {
          front: 'Line 1\nLine 2',
          back: 'Answer\nwith\nnewlines',
          explanation: 'Explanation\nwith\nnewlines',
          options: ['Option A\nmultiline', 'Option B', 123],
        },
      ]);
    });

    it('should return empty array if cards is not an array', () => {
      expect(unescapeNewlines(null)).toEqual([]);
      expect(unescapeNewlines(undefined)).toEqual([]);
    });

    it('should ignore non-string options or fields gracefully', () => {
      const cards = [
        {
          front: 123,
          back: null,
          explanation: undefined,
          options: null,
        },
        null,
      ];
      expect(unescapeNewlines(cards)).toEqual([
        {
          front: 123,
          back: null,
          explanation: undefined,
          options: null,
        },
        null,
      ]);
    });
  });

  describe('postProcess orchestrator', () => {
    it('should execute full postProcess pipeline correctly', () => {
      const data = {
        title: 'Valid Palindrome',
        topic: 'Two Pointers',
        cards: [
          {
            front: 'What is React?',
            back: 'A library\\nby FB',
            explanation: 'Details',
            tags: ['React Basics', 'JS'],
          },
          {
            front: 'what is react?',
            back: 'React',
            explanation: 'Detailed explanation\\nabout React library.',
            tags: ['React Basics', 'JavaScript'],
          },
          {
            front: 'Unique Q',
            back: 'Unique A',
            explanation: 'Unique Expl',
            tags: ['Unique Tag'],
          },
        ],
      };

      const metadata = {
        categoryName: 'Two Pointers',
        categoryIndex: 2,
        problemIndex: 1,
      };

      const result = postProcess(data, metadata);

      expect(result.category_name).toBe('Two Pointers');
      expect(result.category_index).toBe(2);
      expect(result.problem_index).toBe(1);

      // Duplicate 'What is React?' should be combined keeping the longer explanation:
      // "Detailed explanation\nabout React library."
      expect(result.cards).toHaveLength(2);
      expect(result.cards[0].front).toBe('what is react?');
      expect(result.cards[0].explanation).toBe('Detailed explanation\nabout React library.');
      expect(result.cards[0].back).toBe('React'); // Wait, since we kept the second card, its back is "React"
      expect(result.cards[0].tags).toEqual(['ReactBasics', 'JavaScript']);

      expect(result.cards[1].front).toBe('Unique Q');
      expect(result.cards[1].tags).toEqual(['UniqueTag']);
    });

    it('should return input data if it is not an object', () => {
      expect(postProcess(null)).toBeNull();
      expect(postProcess(undefined)).toBeUndefined();
      expect(postProcess('test')).toBe('test');
    });

    it('should handle data without cards gracefully', () => {
      const data = { title: 'No Cards' };
      expect(postProcess(data)).toEqual({ title: 'No Cards' });
    });
  });
});
