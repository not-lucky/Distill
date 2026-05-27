# Distill

> Orchestrated parallel flashcard generation for Anki. Distill turns study
> material (textbooks, codebases, LeetCode algorithms, language specs) into
> high-density, pedagogically optimised Anki `.apkg` decks through a
> four-stage pipeline.

## What is it?

Distill avoids the failure mode of a single, expensive LLM prompt (low
detail density, high syntax-error rate) by splitting the work into four
stages:

1. **Stage 1 — Parallel Generation.** Multiple cheap/fast LLMs extract raw
   Q&A pairs from chunks of source material in parallel.
2. **Stage 2 — Synthesis.** A frontier model consolidates and deduplicates
   the raw cards into a single high-density markdown list.
3. **Stage 3 — Schema Enforcement.** A cost-efficient model parses the text
   into a strict Zod-validated JSON contract, retrying on validation
   failure and sanitising `null` values.
4. **Stage 4 — Compilation.** A Python subprocess (genanki + Catppuccin CSS)
   compiles the JSON into an Anki `.apkg` package.

## Why use it?

- **Hybrid Node.js + Python.** Fast async orchestration in Node.js (ESM);
  native Anki tooling in Python. Best of both ecosystems.
- **Resumable runs.** Every run, step, and API output is tracked in SQLite.
  Crashed runs pick up where they left off.
- **SHA256 request cache.** `(provider + model + prompts + parameters)`
  hashes prevent redundant API spend on unchanged inputs.
- **Polymorphic Zod schema.** Strict validation across Basic Q&A, Cloze
  deletions, and MCQ layouts, with built-in `null` sanitisation.
- **Battle-tested quality gates.** 100% Vitest coverage, Ruff + Black +
  ty for Python, ESLint + Prettier for JS, knip/depcheck/jscpd for dead
  code and duplication, husky + pre-commit for guard rails.

## Where to next?

- [Getting started](getting-started.md) — install, configure, and run the
  pipeline end-to-end.
- [Architecture](architecture.md) — how the four stages fit together, where
  state lives, and how resumption works.
- [Configuration](configuration.md) — the full `config.yaml` reference.
- [Runbooks](runbooks/index.md) — what to do when things go wrong
  (compilation failures, schema drift, key rotation, etc.).
- [Reference](reference/card-schema.md) — the card schema, the Stage 3
  JSON contract, and auto-generated Python/JS API docs.

## Project links

- Source: <https://github.com/not-lucky/Distill>
- Issues: <https://github.com/not-lucky/Distill/issues>
- CI: <https://github.com/not-lucky/Distill/actions/workflows/ci.yml>
