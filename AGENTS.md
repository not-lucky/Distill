# AGENTS.md — AI Coding Agent Instructions

## Project Overview

Distill is a hybrid Node.js (ESM) + Python flashcard generation pipeline. It converts study materials into Anki `.apkg` decks through a four-stage pipeline: parallel generation, synthesis, schema enforcement, and compilation.

## Stack

- **Runtime**: Node.js v26+ (ESM), Python 3.12+
- **JS Testing**: Vitest (`npx vitest run`) — ~250 tests, 80%+ statement coverage
- **N+1 Detection**: `tests/n_plus_one.test.js` instruments better-sqlite3
  prepared-statement calls to assert bulk read paths stay O(1) per query
- **Python Testing**: Pytest (`uv run pytest`)
- **JS Linting**: ESLint 10 with flat config (`eslint.config.js`) — `@eslint/js` recommended + `eslint-plugin-import-x` + `eslint-plugin-n` + `eslint-plugin-boundaries`
- **JS Formatting**: Prettier 3 (`.prettierrc.json`)
- **Python Linting**: Ruff (`uv run ruff check` + `uv run ruff format`)
- **Python Type Checking**: ty (Astral's fast type checker, `uv run ty check src`)
- **Python Dead Code**: Vulture (`uv run vulture src`)
- **Python Unused Deps**: deptry (`uv run deptry .`)
- **JS Dead Code**: knip (`npx knip`)
- **JS Unused Deps**: depcheck (`npx depcheck`)
- **Duplicate Code**: jscpd (`npx jscpd`)
- **Tech-debt Tracking**: `npm run todo:scan` (enforces `TODO(TICKET-123)` format)
- **Pre-commit Hooks**: husky + lint-staged (`.husky/pre-commit`); Python side via `.pre-commit-config.yaml`
- **Dependency Update Policy**: Renovate (`renovate.json`) with a 7-day `minimumReleaseAge` to mitigate supply-chain risk
- **Package Manager**: npm (JS), uv (Python)
- **Dependencies**: All pinned to exact versions in `package.json` (no `^` or `~`)

## Commands

```bash
npm test              # Run all tests (JS + Python)
npm run test:js       # Run JS tests only
npm run test:py       # Run Python tests only
npm run lint          # Full lint (ESLint + Prettier + Ruff check + Ruff format check)
npm run lint:fix      # Auto-fix lint and formatting issues
npm run format        # Format JS/JSON/MD/YAML with Prettier
npm run format:check  # Verify formatting only
npm run typecheck     # Run ty on src/
npm run deadcode       # Run knip to detect unused exports/files
npm run deps:check     # Run depcheck for unused JS deps
npm run duplication    # Run jscpd to detect copy-paste code
npm run todo:scan      # Scan for unannotated TODO/FIXME markers
npm run oversize       # Fail if any src/ *.js or *.py file exceeds 500 lines
npm run coverage       # JS test coverage report
npm run schemas:export # Publish JSON Schema files under schemas/ from the in-tree Zod source
npm run agents:validate # Fail if AGENTS.md references a missing path or unrecognised command
npm run docs:build     # Build the MkDocs Material documentation site
npm run verify         # Run schemas:export, agents:validate, and docs:build as a single check

# Python tools (run via uv):
uv run pytest         # Run Python tests
uv run ruff check     # Python lint
uv run ruff format    # Python format
uv run ty check src   # Python type check
uv run vulture src    # Python dead code
uv run deptry .       # Python unused deps
```

## Dependency Update Policy

This project uses [Renovate](https://docs.renovatebot.com/) with a **7-day
`minimumReleaseAge`** for both npm and Python dependencies. This means a new
release of any dependency must be at least 7 days old before Renovate will
propose an update. The waiting window reduces the risk of pulling in
supply-chain attacks that are typically discovered and patched within the
first few days of release.

Configuration lives in `renovate.json`. Override the policy locally by
editing the `minimumReleaseAge` field (or set `stabilityDays` for older
Renovate versions).

## Code Conventions

- **Module system**: ESM with `.js` extensions on all relative imports (enforced by `import-x/extensions` rule)
- **Unused variables**: Prefix with `_` (e.g., `_error`, `_unused`) — enforced by `no-unused-vars` with `argsIgnorePattern: ^_`
- **Error handling**: Always attach `{ cause: error }` when rethrowing caught errors
- **No default exports**: Use named exports throughout
- **Logging**: Use `getLogger(['category'])` from `src/logger.js` — tagged template literals for message interpolation (e.g., `` logger.debug`message: ${value}` ``)
- **Console**: Only `console.log` and `console.error` are permitted (for user-facing CLI output)

## Architecture

```
src/
  cli.js                      — CLI entry point (commander-based, delegates to commands/)
  config.js                   — YAML config loading and validation
  context.js                  — PipelineContext factory (shared state for stage functions)
  database.js                 — SQLite schema and queries (better-sqlite3)
  ingestion.js                — Document ingestion (file/directory reading)
  logger.js                   — LogTape logging setup
  postProcess.js              — Post-pipeline card processing (dedup, tag normalization)
  prompts.js                  — Default prompts and prompt resolution
  compile.py                  — Anki deck compilation entry point (re-exports from compile/)
  compile/                   — Anki deck compilation package (genanki + Catppuccin CSS)
    deck.py                  — Top-level compile_deck() orchestrator
    models.py                — genanki Model factories (Basic/Cloze/MCQ)
    notes.py                 — genanki Note construction from card dicts
    tags.py                  — Anki tag builder
    mcq.py                   — MCQ option shuffling
    html.py                  — Markdown rendering and HTML sanitization
    ids.py                   — Deterministic ID generation
    loader.py                — JSON input loading and deck-name resolution
    styles.py                — Catppuccin Mocha CSS theme

  scripts/
    scan-todos.js            — Tech-debt marker scanner (TODO(TICKET-123) enforcer)

  commands/                   — CLI command handlers
    run.js                    — Pipeline run command
    compile.js                — Standalone compile command
    cache.js                  — Cache management command

  pipeline/                   — Pipeline orchestration
    orchestrator.js           — Coordinates stages, manages runs, handles output
    compiler.js               — Python compiler process spawning
    validation.js             — JSON normalization, output cleaning, content-loss audit
    stages/                   — Pipeline stage implementations
      stage1-generation.js    — Parallel multi-model generation
      stage2-synthesis.js     — Frontier model consolidation
      stage3-enforcement.js   — Zod schema enforcement with retry loop
    schemas/                  — Card schema definitions
      card-zod.js             — Zod schemas (for structured outputs and validation)
      card-json.js            — JSON Schema (for enforcement prompt injection)

  llm/                        — LLM provider abstraction
    caller.js                 — callLLM with retry, caching, and key rotation
    client.js                 — OpenAI SDK client creation
    throttle.js               — Request staggering (p-limit based)
    cache.js                  — Cache key hashing (SHA256)
    cache-io.js               — Cache read/write via database
    keys.js                   — API key rotation and model string parsing
```

### Key Design Patterns

- **PipelineContext**: Stage functions take `(context, { questionId, ... })` instead of 10+ individual parameters. Created by `createPipelineContext()` in `src/context.js`.

## Key Files

| File                              | Purpose                                                    |
| --------------------------------- | ---------------------------------------------------------- |
| `config.yaml`                     | Runtime configuration (providers, models, concurrency)     |
| `keys.yaml`                       | API keys (gitignored)                                      |
| `prompts.yaml`                    | Prompt overrides and subject presets                       |
| `eslint.config.js`                | ESLint flat config                                         |
| `pyproject.toml`                  | Python project metadata and dependencies                   |
| `mkdocs.yml`                      | MkDocs Material documentation site config                  |
| `docs/`                           | Hand-written and auto-generated documentation              |
| `schemas/stage3-deck.schema.json` | Published JSON Schema for the Stage 3 deck contract        |
| `scripts/export-schemas.js`       | Regenerates the published JSON Schemas from the Zod source |
| `scripts/validate-agents-md.js`   | CI check that AGENTS.md references still resolve           |

## Testing

- Test files live in `tests/` and follow `*.test.js` naming
- Tests use Vitest with explicit imports (`import { describe, it, expect } from 'vitest'`)
- Mock LLM providers using `vi.mock` — never make real API calls in tests
- Database tests use in-memory SQLite (`:memory:`)
- Python tests for `compile.py` are in `tests/test_compile.py`

### Test Quality (signals: integration_tests_exist, test_performance_tracking, test_coverage_thresholds, flaky_test_detection)

- **Coverage thresholds** (`vitest.config.js`): 80% lines/statements/functions, 70% branches. Python: 80% line coverage via `pytest --cov-fail-under=80`. 100% coverage is **not** the goal; depth and integration value are. A drop below the thresholds fails CI.
- **Integration tests** live in `tests/integration/` and are run as part of the normal test suite. The Python E2E suite is `tests/test_e2e_compile_cli.py`. They drive the real CLI + real `compile.py` subprocess (no mocks of the LLM stages are still mocked, but the compile pipeline, SQLite, postProcess, and ingest are real).
- **Performance tracking**: `vitest` runs with the `verbose` reporter in CI; pytest uses `--durations=10` to surface the 10 slowest tests. Both also write a coverage XML/HTML report that is uploaded as a CI artifact.
- **Flaky test handling**: `vitest --retry=2` and `pytest --reruns=2 --reruns-delay=1` re-run flaky tests and emit retry counters in the log. Root-cause fixing is preferred over retry, but transient I/O and timing flakes are absorbed automatically.
- **Run only E2E** (faster local dev loop): `npm run test:e2e` (JS integration only), or run pytest on a specific file: `uv run pytest tests/test_e2e_compile_cli.py`.

## Commit Conventions

- `feat:` — new features
- `fix:` — bug fixes
- `refactor:` — code restructuring without behavior change
- `test:` — test additions or changes
- `chore:` — build, CI, dependency, or tooling changes
- `ci:` — CI/CD pipeline changes
- `docs:` — documentation only

## Runbooks

When something breaks in production, start in [`docs/runbooks/`](docs/runbooks/).
The index lists the most common incident scenarios (compilation failure,
schema drift, API key rotation, database corruption, resume loop) and
links to a per-symptom playbook.

## Pre-commit Hooks

This project uses `husky` + `lint-staged` (JS) and `pre-commit` (Python) to
enforce quality checks before commits land:

- **JS**: `eslint --fix` and `prettier --write` on staged `*.js`/`*.json`/`*.md`/`*.yml`
- **Python**: `ruff check --fix` and `ruff format` on staged `*.py`

Install hooks with: `npm install` (husky) and `uv run pre-commit install`
(Python side; requires the `pre-commit` package, not yet a project dep — see
`.pre-commit-config.yaml`).
