/**
 * Integration test: real disk ingestion + real post-process end-to-end.
 *
 * Third of three integration tests (signal: integration_tests_exist).
 * Writes a real nested directory of .md files, calls the real
 * `ingestDirectory`, then pipes the result through the real `postProcess`
 * pipeline. Asserts:
 *   - deckPath namespace is correctly assembled from disk layout
 *   - dedup keeps the longest explanation
 *   - newlines are unescaped
 *   - tags are normalized (whitespace stripped)
 *   - hidden directories and non-text files are skipped
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fsp from 'fs/promises';
import os from 'os';
import path from 'path';
import { ingestDirectory } from '../../src/ingestion.js';
import { postProcess } from '../../src/postProcess.js';

async function makeTree(root, structure) {
  // structure: object where keys are paths (relative to root) and values are
  // either a string (file content) or another object (subdirectory).
  for (const [relPath, value] of Object.entries(structure)) {
    const full = path.join(root, relPath);
    if (typeof value === 'string') {
      await fsp.mkdir(path.dirname(full), { recursive: true });
      await fsp.writeFile(full, value, 'utf8');
    } else if (value && typeof value === 'object') {
      await fsp.mkdir(full, { recursive: true });
      await makeTree(full, value);
    }
  }
}

describe('Integration: real disk ingestion + real postProcess', () => {
  let root;
  let docs;

  beforeEach(async () => {
    root = await fsp.mkdtemp(path.join(os.tmpdir(), 'llm2deck-it-ingest-'));
    await makeTree(root, {
      'subjects/react/basics/jsx.md': '# JSX\nWhat is JSX?',
      'subjects/react/basics/components.md':
        '# Components\nWhat is a component?\nA reusable building block.',
      'subjects/react/hooks/useState.md': 'useState lets you add state to a function component.',
      // Hidden directories should be skipped
      '.git/HEAD': 'ref: refs/heads/master',
      '.archived/old.md': 'old content',
      // Non-text file extensions should be skipped
      'subjects/react/basics/image.png': 'pretend-binary',
      // Two files with the same effective question text (after dedup) but
      // different explanation lengths
      'subjects/react/basics/hooks-intro.md': 'hooks intro\nWhat are hooks?\nshort explanation',
      'subjects/react/basics/hooks-intro-long.md':
        'hooks intro long\nWhat are hooks?\nThis is a much longer explanation that should win during dedup.',
    });
  });

  afterEach(async () => {
    if (root) {
      await fsp.rm(root, { recursive: true, force: true });
      root = null;
    }
  });

  it('walks a nested directory and builds a TitleCase double-colon deckPath', async () => {
    docs = await ingestDirectory(root);

    // Hidden directories and non-text files are excluded. The deck path
    // starts with the tempdir root name (random), so we assert on the
    // namespace tail and the hidden/extension exclusions.
    const deckPaths = docs.map((d) => d.deckPath).sort();
    expect(deckPaths).toHaveLength(5);
    for (const dp of deckPaths) {
      expect(dp).toMatch(/::Subjects::React::(Basics|Hooks)::/);
      expect(dp).not.toMatch(/::\.git::/);
      expect(dp).not.toMatch(/::\.archived::/);
      expect(dp).not.toMatch(/::Image::/);
    }
    const tails = deckPaths.map((d) => d.split('::').slice(-1)[0]);
    expect(new Set(tails)).toEqual(
      new Set(['Components', 'Hooks_Intro', 'Hooks_Intro_Long', 'Jsx', 'Usestate']),
    );

    // Each doc has a real filePath + non-empty content
    for (const doc of docs) {
      expect(doc.filePath).toMatch(/\.(md|markdown|txt|html|htm|rst)$/i);
      expect(doc.content.length).toBeGreaterThan(0);
    }
  });

  it('postProcess end-to-end: dedup, tag normalization, newline unescape', async () => {
    docs = await ingestDirectory(root);

    // Build a synthetic stage-3 output that mixes content from the two
    // hooks-intro files (which have the same front "What are hooks?") and
    // also uses literal "\\n" sequences and whitespace-laden tags.
    const hooksA = docs.find((d) => d.deckPath.endsWith('Hooks_Intro'));
    const hooksB = docs.find((d) => d.deckPath.endsWith('Hooks_Intro_Long'));
    expect(hooksA).toBeDefined();
    expect(hooksB).toBeDefined();

    const stage3 = {
      title: 'Hooks Intro',
      topic: 'React::Hooks',
      difficulty: 'Intermediate',
      cards: [
        {
          card_format: 'Basic',
          card_type: 'Concept',
          // Same front, different explanation → dedup should keep the longer one
          front: 'What are hooks?',
          back: hooksA.content,
          explanation: hooksA.content.split('\n').pop(), // short
          tags: ['Trade Off', '  React  ', 'state management'],
        },
        {
          card_format: 'Basic',
          card_type: 'Concept',
          front: 'What are hooks?',
          back: hooksB.content,
          // Use the longer explanation; '\\n' should be unescaped to '\n'
          explanation: hooksB.content.split('\n').pop(),
          tags: ['Trade Off', 'Hooks', 'state management', 'performance /  benchmarks'],
        },
        {
          card_format: 'Basic',
          card_type: 'Concept',
          front: 'What is JSX?',
          back: docs.find((d) => d.deckPath.endsWith('Jsx')).content,
          explanation: 'A syntax extension to JavaScript.',
          tags: ['React', 'jsx', 'syntax'],
        },
      ],
    };

    const processed = postProcess(stage3, {
      categoryName: 'React',
      categoryIndex: 0,
      problemIndex: 1,
    });

    // Metadata is injected
    expect(processed.category_name).toBe('React');
    expect(processed.category_index).toBe(0);
    expect(processed.problem_index).toBe(1);

    // Dedup: only 2 unique questions (hooks and JSX), not 3
    expect(processed.cards).toHaveLength(2);

    // The longer explanation won; the kept card is hooksB's
    const hooksCard = processed.cards.find((c) => c.front === 'What are hooks?');
    expect(hooksCard).toBeDefined();
    expect(hooksCard.explanation.length).toBeGreaterThan(20);

    // Tags are whitespace-stripped
    const tagSet = new Set();
    for (const card of processed.cards) for (const t of card.tags) tagSet.add(t);
    expect(tagSet.has('TradeOff')).toBe(true);
    expect(tagSet.has('React')).toBe(true);
    expect(tagSet.has('statemanagement')).toBe(true);
    expect(tagSet.has('performance/benchmarks')).toBe(true);
    expect(tagSet.has('jsx')).toBe(true);
    // No tag in the output should contain raw whitespace
    for (const t of tagSet) expect(t).not.toMatch(/\s/);
  });
});
