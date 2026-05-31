/**
 * Direct unit tests for the helpers exported from src/postProcess.js.
 *
 * These tests are imported by knip's consumer analysis: without them, knip
 * flags `normalizeTags`, `normalizeQuestion`, `deduplicateCards`,
 * `injectMetadata`, and `unescapeNewlines` as unused exports because the
 * only callers in src/ and tests/integration/ reach them indirectly via
 * the top-level `postProcess()` aggregator.
 *
 * Style mirrors tests/ingestion.test.js: explicit Vitest imports, flat
 * describe blocks per helper, and small focused cases.
 */
import { describe, it, expect } from 'vitest';
import {
  normalizeTags,
  normalizeQuestion,
  deduplicateCards,
  injectMetadata,
  unescapeNewlines,
} from '../src/postProcess.js';

describe('normalizeTags', () => {
  it('strips all whitespace from each string tag', () => {
    const cards = [{ tags: ['Trade Off', '  React  ', 'state management'] }];
    const [result] = normalizeTags(cards);
    expect(result.tags).toEqual(['TradeOff', 'React', 'statemanagement']);
  });

  it('strips internal whitespace from slash-separated tags', () => {
    const cards = [{ tags: ['performance /  benchmarks', 'cpu  /  memory'] }];
    const [result] = normalizeTags(cards);
    expect(result.tags).toEqual(['performance/benchmarks', 'cpu/memory']);
  });

  it('leaves non-string tag entries untouched', () => {
    const numericTag = 42;
    const cards = [{ tags: ['React', numericTag, null] }];
    const [result] = normalizeTags(cards);
    expect(result.tags).toEqual(['React', numericTag, null]);
  });

  it('returns [] for non-array input', () => {
    expect(normalizeTags(null)).toEqual([]);
    expect(normalizeTags(undefined)).toEqual([]);
    expect(normalizeTags('not-an-array')).toEqual([]);
    expect(normalizeTags({})).toEqual([]);
  });

  it('skips null/undefined entries inside the array', () => {
    const cards = [null, undefined, { tags: ['a b'] }];
    const result = normalizeTags(cards);
    expect(result).toHaveLength(3);
    expect(result[0]).toBeNull();
    expect(result[1]).toBeUndefined();
    expect(result[2].tags).toEqual(['ab']);
  });

  it('returns a shallow clone of cards that have no tags array', () => {
    const card = { front: 'Q', back: 'A' };
    const [result] = normalizeTags([card]);
    expect(result).not.toBe(card);
    expect(result).toEqual({ front: 'Q', back: 'A' });
  });

  it('does not mutate the original card objects', () => {
    const card = { tags: ['Trade Off'] };
    const original = { tags: ['Trade Off'] };
    normalizeTags([card]);
    expect(card).toEqual(original);
    expect(card.tags).toEqual(['Trade Off']);
  });
});

describe('normalizeQuestion', () => {
  it('lowercases and strips all non-alphanumeric characters', () => {
    expect(normalizeQuestion('What are hooks?')).toBe('whatarehooks');
    expect(normalizeQuestion('Hello, World!')).toBe('helloworld');
    expect(normalizeQuestion('  Spaces  & Punct. ')).toBe('spacespunct');
  });

  it('returns "" for non-string input', () => {
    expect(normalizeQuestion(null)).toBe('');
    expect(normalizeQuestion(undefined)).toBe('');
    expect(normalizeQuestion(42)).toBe('');
    expect(normalizeQuestion({})).toBe('');
  });

  it('returns the same string when it is already normalized', () => {
    expect(normalizeQuestion('plaintext')).toBe('plaintext');
    expect(normalizeQuestion('abc123')).toBe('abc123');
  });
});

describe('deduplicateCards', () => {
  it('removes duplicate fronts, case/punctuation/whitespace insensitive', () => {
    const cards = [
      { front: 'What are hooks?', explanation: 'same-len' },
      { front: 'WHAT ARE HOOKS?', explanation: 'same-len' },
      { front: 'What is JSX?', explanation: 'A syntax extension.' },
    ];
    const result = deduplicateCards(cards);
    expect(result).toHaveLength(2);
    const fronts = result.map((c) => c.front);
    // First occurrence wins on equal-length tie, so original casing is kept
    expect(fronts).toEqual(['What are hooks?', 'What is JSX?']);
  });

  it('keeps the longer explanation when duplicates differ in length', () => {
    const cards = [
      { front: 'What are hooks?', explanation: 'short' },
      { front: 'What are hooks?', explanation: 'a much longer explanation' },
    ];
    const result = deduplicateCards(cards);
    expect(result).toHaveLength(1);
    expect(result[0].explanation).toBe('a much longer explanation');
  });

  it('keeps the first occurrence on equal-length ties and preserves order', () => {
    const cards = [
      { front: 'A?', explanation: 'same' },
      { front: 'a?', explanation: 'same' },
      { front: 'B?', explanation: 'b' },
    ];
    const result = deduplicateCards(cards);
    expect(result.map((c) => c.front)).toEqual(['A?', 'B?']);
    expect(result[0].explanation).toBe('same');
  });

  it('preserves the relative order of unique cards by first occurrence', () => {
    const cards = [
      { front: 'C?', explanation: 'c' },
      { front: 'A?', explanation: 'a' },
      { front: 'B?', explanation: 'b' },
    ];
    const result = deduplicateCards(cards);
    expect(result.map((c) => c.front)).toEqual(['C?', 'A?', 'B?']);
  });

  it('returns [] for non-array input', () => {
    expect(deduplicateCards(null)).toEqual([]);
    expect(deduplicateCards(undefined)).toEqual([]);
    expect(deduplicateCards('not-an-array')).toEqual([]);
  });

  it('skips null/undefined entries inside the array', () => {
    const cards = [null, { front: 'Q?', explanation: 'a' }, undefined];
    const result = deduplicateCards(cards);
    expect(result).toHaveLength(1);
    expect(result[0].front).toBe('Q?');
  });

  it('treats non-string fronts as a stable empty key', () => {
    const cards = [
      { front: null, explanation: 'first' },
      { front: null, explanation: 'second-longer' },
    ];
    const result = deduplicateCards(cards);
    expect(result).toHaveLength(1);
    expect(result[0].explanation).toBe('second-longer');
  });
});

describe('injectMetadata', () => {
  it('sets all three metadata fields when provided', () => {
    const data = { title: 'Topic' };
    const result = injectMetadata(data, {
      categoryName: 'React',
      categoryIndex: 0,
      problemIndex: 1,
    });
    expect(result).toEqual({
      title: 'Topic',
      category_name: 'React',
      category_index: 0,
      problem_index: 1,
    });
  });

  it('skips undefined and null metadata values', () => {
    const data = { title: 'Topic', category_name: 'Existing' };
    const result = injectMetadata(data, {
      categoryName: undefined,
      categoryIndex: null,
      problemIndex: 5,
    });
    expect(result.category_name).toBe('Existing');
    expect(result.category_index).toBeUndefined();
    expect(result.problem_index).toBe(5);
  });

  it('returns a shallow clone and does not mutate the input', () => {
    const data = { title: 'Topic' };
    const result = injectMetadata(data, { categoryName: 'X' });
    expect(result).not.toBe(data);
    expect(data.category_name).toBeUndefined();
  });

  it('returns the input unchanged for non-object data', () => {
    expect(injectMetadata(null)).toBeNull();
    expect(injectMetadata(undefined)).toBeUndefined();
    expect(injectMetadata('not-an-object')).toBe('not-an-object');
  });
});

describe('unescapeNewlines', () => {
  it('replaces literal \\n with real newlines in front, back, and explanation', () => {
    const cards = [
      {
        front: 'Line1\\nLine2',
        back: 'A\\nB\\nC',
        explanation: 'ex\\nplanation',
      },
    ];
    const [result] = unescapeNewlines(cards);
    expect(result.front).toBe('Line1\nLine2');
    expect(result.back).toBe('A\nB\nC');
    expect(result.explanation).toBe('ex\nplanation');
  });

  it('replaces literal \\n in string entries of the options array', () => {
    const cards = [{ options: ['choice\\none', 'choice two', 'choice\\nthree'] }];
    const [result] = unescapeNewlines(cards);
    expect(result.options).toEqual(['choice\none', 'choice two', 'choice\nthree']);
  });

  it('leaves non-string options entries untouched', () => {
    const numericOpt = 42;
    const cards = [{ options: ['a\\nb', numericOpt] }];
    const [result] = unescapeNewlines(cards);
    expect(result.options).toEqual(['a\nb', numericOpt]);
  });

  it('returns [] for non-array input', () => {
    expect(unescapeNewlines(null)).toEqual([]);
    expect(unescapeNewlines(undefined)).toEqual([]);
    expect(unescapeNewlines(42)).toEqual([]);
  });

  it('skips null/undefined entries inside the array', () => {
    const cards = [null, { front: 'a\\nb' }, undefined];
    const result = unescapeNewlines(cards);
    expect(result).toHaveLength(3);
    expect(result[0]).toBeNull();
    expect(result[1].front).toBe('a\nb');
    expect(result[2]).toBeUndefined();
  });

  it('does not mutate the original card objects', () => {
    const card = { front: 'a\\nb', back: 'c\\nd' };
    unescapeNewlines([card]);
    expect(card.front).toBe('a\\nb');
    expect(card.back).toBe('c\\nd');
  });
});
