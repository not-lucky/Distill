# Getting started

This page walks you through installing Distill, configuring providers and
keys, and running the pipeline on a real subject.

## Prerequisites

- **Node.js** v20 or newer (the project uses native ESM)
- **Python** 3.12 or newer
- **uv** for Python dependency management — <https://docs.astral.sh/uv/>
- An OpenAI-compatible API endpoint and a valid key (or any combination of
  the providers supported via the OpenAI SDK)

## Install

Clone the repository and install the JavaScript and Python dependencies:

```bash
git clone https://github.com/not-lucky/Distill.git
cd Distill
npm install
uv sync
```

## Configure

Distill reads three YAML files from the project root:

| File           | Purpose                                   | Committed? |
| -------------- | ----------------------------------------- | ---------- |
| `config.yaml`  | Pipeline, providers, concurrency settings | Yes        |
| `keys.yaml`    | API keys                                  | No         |
| `prompts.yaml` | Default prompts and subject presets       | Yes        |

Drop-in examples live in `examples/`:

```bash
cp examples/config.full.yaml    config.yaml
cp examples/keys.full.yaml      keys.yaml
cp examples/prompts.full.yaml   prompts.yaml
```

Edit the copies to set your real API keys and provider base URLs. See
[Configuration](configuration.md) for the full reference.

## Run

The CLI exposes three subcommands: `run`, `compile`, and `cache`.

```bash
# Generate cards for the bundled "leetcode" topic-mode subject
node src/cli.js run leetcode

# Ingest local documents under ./scratch/notes
node src/cli.js run ./scratch/notes

# Compile an existing Stage 3 JSON file directly to .apkg
node src/cli.js compile ./output/LeetCode.json -o ./output/LeetCode.apkg

# Inspect the request cache
node src/cli.js cache stats
```

Use `-v` for verbose (`debug`-level) logs and `-q` to silence anything
below `error`.

## Resume an interrupted run

Each run is assigned a stable `run_id` and persisted to SQLite. If the
process is killed mid-flight, re-run with `--resume`:

```bash
node src/cli.js run leetcode --resume "run-12345"
```

The orchestrator will skip questions that already have a cached Stage 1,
Stage 2, or Stage 3 output and pick up at the next pending question.

## Test the install

```bash
npm test           # JS + Python
npm run lint       # ESLint + Prettier + Ruff + Black check
npm run coverage   # JS coverage report (HTML in coverage/)
```

The full test suite is ~250 Vitest cases plus the Python suite and the
end-to-end CLI integration tests in `tests/integration/`. Coverage
thresholds are 80% lines/statements/functions and 70% branches for JS, and
80% lines for Python (`--cov-fail-under=80`).
