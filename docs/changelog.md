# Changelog

All notable changes to Distill are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- MkDocs Material documentation site (auto-generated API reference via
  `mkdocstrings`, runbooks, and full configuration/architecture guides).
- `runbooks/` directory with incident playbooks for compilation failures,
  API key rotation, schema drift, database corruption, and resume-loop
  detection.
- `scripts/validate-agents-md.js` — CI step that verifies `AGENTS.md`
  references still resolve to existing files and listed commands still
  exist.
- `schemas/stage3-deck.schema.json` — published, machine-readable
  JSON Schema for the Stage 3 deck input contract (mirrors the Zod
  schema in `src/pipeline/schemas/card-zod.js`).

### Changed

- CI workflow now builds and uploads the documentation site, validates
  `AGENTS.md` accuracy, and runs the new JSON Schema validation test.

## [1.0.0] — 2025-06-15

### Added

- Four-stage pipeline: parallel generation, synthesis, schema
  enforcement, Anki compilation.
- SQLite-backed resumable runs and SHA256 request cache.
- Polymorphic Zod card schema (Basic, Cloze, MCQ) with `null` sanitisation.
- Catppuccin Mocha CSS theme and option-shuffled MCQ cards.
