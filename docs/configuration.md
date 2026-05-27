# Configuration

Distill reads three YAML files from the project root: `config.yaml`,
`keys.yaml`, and `prompts.yaml`. Drop-in examples live in
[`examples/`](https://github.com/not-lucky/Distill/tree/master/examples)
at three levels of detail (`minimal`, `standard`, `full`).

## `config.yaml`

The main configuration file. It defines global concurrency defaults, the
provider catalogue, and the model assignment for each pipeline stage.

### `global` keys

| Key                 | Type        | Default          | Description                                                                               |
| ------------------- | ----------- | ---------------- | ----------------------------------------------------------------------------------------- |
| `concurrency_limit` | integer     | `8`              | Max parallel API requests at any moment.                                                  |
| `request_delay`     | float       | `1.0`            | Seconds to stagger the start of each new request.                                         |
| `default_timeout`   | float\|null | `null`           | Default API request timeout in seconds. `null` (or `0`) disables the client-side timeout. |
| `output_dir`        | path        | `./output`       | Compiled Anki deck target directory.                                                      |
| `cache_db_path`     | path        | `./distill.db`   | SQLite database path for the request cache and run state.                                 |
| `keys_file_path`    | path        | `./keys.yaml`    | Path to the API keys YAML.                                                                |
| `prompts_file_path` | path        | `./prompts.yaml` | Path to the prompts YAML.                                                                 |
| `log_level`         | string      | `info`           | Min log level: `debug`, `info`, `warning`, `error`, `fatal`.                              |
| `log_dir`           | path\|null  | `null`           | Directory for rotating log files. `null` disables file logging.                           |

### `providers` catalogue

Each provider entry is keyed by an arbitrary name (e.g. `openai`,
`cerebras`, `ollama_local`) and accepts:

- `base_url` (string) — the OpenAI-compatible API base URL
- `temperature` (float) — default sampling temperature
- `timeout` (float, optional) — per-provider request timeout override.
  A positive number is interpreted as seconds. `0` or `null` explicitly
  disables the timeout for that provider (overriding the global default).
  When omitted, the provider inherits `global.default_timeout`.

The `openai` SDK is used for every provider; any OpenAI-compatible endpoint
(Ollama, vLLM, llama.cpp server, Groq, Together, etc.) works as long as
the `base_url` is set correctly.

### `pipeline` stage assignment

| Stage                | Shape                     | Notes                                                                    |
| -------------------- | ------------------------- | ------------------------------------------------------------------------ |
| `generation`         | `{ models: [string, …] }` | Stage 1 runs every model in `models` in parallel against every question. |
| `synthesis`          | `{ model: string }`       | Stage 2 uses a single frontier model.                                    |
| `schema_enforcement` | `{ model: string }`       | Stage 3 uses a single cost-efficient model.                              |

Model strings are `provider/model` (e.g. `openai/gpt-4o`,
`cerebras/llama3.1-70b`).

## `keys.yaml`

API keys. **This file is gitignored** and should never be committed.
Format:

```yaml
openai:
  - 'sk-proj-...'
  - 'sk-proj-rotate-key-...'
cerebras:
  - 'cber-...'
```

Keys can be a single string or a list. Lists enable round-robin key
rotation in `src/llm/keys.js`, which spreads load across multiple
accounts and reduces 429 rate-limit pressure.

## `prompts.yaml`

Prompt overrides and subject presets. Two top-level keys:

- `defaults` — overrides for the hard-coded prompt templates in
  `src/prompts.js`. The supported keys are `generation`,
  `generation_document`, `synthesis`, and `enforcement`.
- `subjects` — keyed by subject name (e.g. `leetcode`, `notes`).
  Each subject specifies:
  - `mode` — `topic` (default) or `document`
  - `generation`, `synthesis` — optional prompt overrides
  - `categories` (topic mode) — list of `{name, topics: [string, …]}`
  - `files` or `folder` (document mode) — paths to ingest

The `examples/prompts.full.yaml` file matches the in-source defaults
byte-for-byte, so it is a safe drop-in replacement if you want every
option in one place.

## CLI overrides

The `run`, `compile`, and `cache` commands accept:

- `-v, --verbose` — set log level to `debug`
- `-q, --quiet` — set log level to `error`

The `run` command additionally accepts:

- `--config <path>` — alternate `config.yaml`
- `--card-type <standard|mcq>` — Stage 1 output layout
- `--subject <name>` — explicit subject preset (overrides the positional
  argument when both refer to a known subject)
- `--resume <run_id>` — resume an interrupted run
- `--dry-run` — validate config and ingest sources without LLM calls
