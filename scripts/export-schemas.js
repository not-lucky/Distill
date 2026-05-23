#!/usr/bin/env node
/**
 * Schema publisher for LLM2Deck.
 *
 * Reads the in-tree Zod definitions in src/pipeline/schemas/ and writes
 * machine-readable JSON Schema files under schemas/. The published files
 * are the public contract for downstream consumers (LLM enforcement
 * prompts, integration tests, third-party tooling).
 *
 * The deck-level file is a wrapper that allows either a single topic
 * object or an array of topics, matching what `src/compile.py` accepts.
 *
 * Run with:  node scripts/export-schemas.js
 * Wire into CI to guarantee the published schema never drifts from the
 * Zod source of truth.
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import { CARD_JSON_SCHEMA } from '../src/pipeline/schemas/card-json.js';

const ROOT = process.cwd();
const SCHEMA_DIR = join(ROOT, 'schemas');
void fileURLToPath;

function buildDeckSchema(cardSchema) {
  return {
    $schema: 'http://json-schema.org/draft-07/schema#',
    $id: 'https://github.com/not-lucky/LLM2Deck/schemas/stage3-deck.schema.json',
    title: 'LLM2Deck Stage 3 deck contract',
    description:
      'The deck-level JSON contract consumed by `src/compile.py` and produced ' +
      'by Stage 3 (schema enforcement). Accepts a single topic object or an ' +
      'array of topic objects. Each topic carries an array of cards whose ' +
      'shape is validated by the per-card oneOf in cardSchema.',
    oneOf: [
      {
        title: 'Single topic',
        ...cardSchema,
      },
      {
        title: 'Array of topics',
        type: 'array',
        minItems: 1,
        items: cardSchema,
      },
    ],
  };
}

function buildCardSchema(cardSchema) {
  return {
    $schema: 'http://json-schema.org/draft-07/schema#',
    $id: 'https://github.com/not-lucky/LLM2Deck/schemas/stage3-card.schema.json',
    title: 'LLM2Deck Stage 3 single topic (cards array)',
    description:
      'A single topic with a cards array. This is the per-topic contract; ' +
      'the deck-level wrapper at stage3-deck.schema.json allows either a ' +
      'single topic object or an array of them.',
    ...cardSchema,
  };
}

function writeJson(file, data) {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

function main() {
  const cardSchema = CARD_JSON_SCHEMA;
  const cardFile = join(SCHEMA_DIR, 'stage3-card.schema.json');
  const deckFile = join(SCHEMA_DIR, 'stage3-deck.schema.json');

  writeJson(cardFile, buildCardSchema(cardSchema));
  writeJson(deckFile, buildDeckSchema(cardSchema));

  console.log(`[export-schemas] Wrote ${relative(ROOT, cardFile)} and ${relative(ROOT, deckFile)}`);
}

main();
