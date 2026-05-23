# Runbook: Compilation failure

## Symptoms

- `node src/cli.js compile …` exits with code 1 and prints
  `Compilation failed: <error>`
- The Python subprocess writes a traceback to stderr
- Recent change touched `src/compile/`, `src/prompts.js`, or
  `src/pipeline/schemas/`

## Triage

```bash
# 1. Reproduce with the failing JSON in isolation
uv run src/compile.py ./output/<failing>.json -o /tmp/test.apkg

# 2. Inspect the JSON for shape issues
jq '. | length' ./output/<failing>.json   # number of topics
jq '.[0].cards[0]' ./output/<failing>.json | head

# 3. Re-run with --verbose to see the underlying error
node src/cli.js compile ./output/<failing>.json -o /tmp/test.apkg -v
```

## Mitigation

| Error                                                | Fix                                                                                                                           |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `KeyError: 'front'` / `KeyError: 'back'`             | A card is missing a required field. Re-run Stage 3 against the synthesis output: `node src/cli.js run … --resume <run-id>`.   |
| `validation error: … expected enum`                  | A `card_format` or `card_type` is not in the allowed set. See [Card schema](../reference/card-schema.md).                     |
| `Markdown rendering failed: <tag>`                   | The card contains HTML that the bleach allow-list strips. Either sanitise the prompt or add the tag to `src/compile/html.py`. |
| `genanki.Package.write_to_file: [Errno 28] No space` | The output disk is full. Free space and re-run.                                                                               |
| `ImportError: No module named 'genanki'`             | `uv sync` was not run after pulling. Run `uv sync` and re-run.                                                                |

## Root cause

The most common root cause is a Stage 3 prompt that asks the LLM to
produce fields outside the contract (e.g. `question` instead of `front`).
Strengthen the enforcement prompt in `prompts.yaml` to call out the exact
field names, and add a regression test under `tests/integration/` that
ingests the offending fixture.

## Postmortem checklist

- [ ] The compile step succeeds with the previously failing input
- [ ] The synthesised JSON round-trips through
      `npx vitest run tests/integration`
- [ ] A regression test has been added (or an existing one updated) that
      covers the failure mode
- [ ] The runbook entry is updated with anything new you learned
