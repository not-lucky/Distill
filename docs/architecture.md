# Architecture

Distill is a hybrid Node.js (ESM) + Python flashcard generation pipeline.
This page explains how the four stages fit together, where state lives,
and how resumption works.

## High-level flow

```text
[Source material]
       │
       ├─► [Stage 1: Parallel Generation]   — multi-LLM raw text
       │                                       (src/pipeline/stages/stage1-generation.js)
       │
       ├─► [Stage 2: Synthesis]             — frontier LLM consolidation
       │                                       (src/pipeline/stages/stage2-synthesis.js)
       │
       ├─► [Stage 3: Schema Enforcement]    — Zod-validated JSON
       │                                       (src/pipeline/stages/stage3-enforcement.js)
       │
       └─► [Stage 4: Anki Compilation]      — Python subprocess
                                               (src/compile.py / src/compile/)
```

## Module layout

```text
src/
  cli.js                  — CLI entry point (commander, delegates to commands/)
  config.js               — YAML config loading and validation
  context.js              — PipelineContext factory
  database.js             — SQLite schema and queries (better-sqlite3)
  ingestion.js            — Document ingestion (file/directory reading)
  logger.js               — LogTape logging setup
  postProcess.js          — Post-pipeline dedup and tag normalisation
  prompts.js              — Default prompts and prompt resolution

  compile.py              — Anki deck compilation entry point
  compile/                — Anki deck compilation package (genanki + Catppuccin CSS)
    deck.py               — Top-level compile_deck() orchestrator
    models.py             — genanki Model factories (Basic/Cloze/MCQ)
    notes.py              — genanki Note construction from card dicts
    tags.py               — Anki tag builder
    mcq.py                — MCQ option shuffling
    html.py               — Markdown rendering and HTML sanitisation
    ids.py                — Deterministic ID generation
    loader.py             — JSON input loading and deck-name resolution
    styles.py             — Catppuccin Mocha CSS theme

  commands/               — CLI command handlers
  pipeline/               — Orchestration, stages, schemas, validation
  llm/                    — LLM provider abstraction (call, cache, throttle, keys)
```

## State and resumption

The SQLite database (`distill.db` by default) stores:

- `runs` — one row per `node src/cli.js run …` invocation
- `steps` — one row per (run, question, stage)
- `api_outputs` — one row per successful LLM call, keyed by the SHA256
  cache hash

When you start a run, the orchestrator scans the database for already
completed steps and skips them. Cache hits (via the SHA256 hash on
`provider + model + prompts + parameters`) are returned without
re-charging the API.

## Card contract

Stages 1 and 2 produce free-form markdown text. Stage 3 normalises that
text into a strict JSON contract — see
[Stage 3 JSON contract](reference/stage3-json.md) — which is what
`src/compile.py` consumes. The contract is enforced by Zod
(`src/pipeline/schemas/card-zod.js`) and exposed as a JSON Schema
(`src/pipeline/schemas/card-json.js`) for the LLM enforcement prompt.

## PipelineContext

Stage functions take a single `context` object created by
`createPipelineContext()` (`src/context.js`) rather than 10+ positional
parameters. The context carries the logger, LLM caller, database, prompts,
and stage-specific configuration.

## Barrel exports

For backward compatibility, the project ships thin barrel files
(`src/stages.js`, `src/providers.js`, `src/orchestrator.js`) that
re-export from the new submodule paths. New code should import directly
from the submodules.
