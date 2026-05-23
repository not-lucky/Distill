# Runbooks

This directory contains step-by-step playbooks for the most common
incident scenarios in LLM2Deck. Each playbook follows the same structure:

1. **Symptoms** — what you'll see in the logs or the CLI output
2. **Triage** — quick checks to confirm the diagnosis
3. **Mitigation** — the smallest change that gets the pipeline running
   again
4. **Root cause** — why it happened and how to prevent it
5. **Postmortem checklist** — what to verify before closing the incident

If you don't see a playbook for your symptom, file an issue and link the
log output — the goal is to grow this section over time.

## Available playbooks

- [Compilation failure (`compile_deck` raises)](compilation-failure.md) —
  when the Python subprocess throws on a JSON input that previously worked
- [Schema drift (Stage 3 Zod validation loops forever)](schema-drift.md) —
  when the LLM repeatedly produces JSON that doesn't match the contract
- [API key rotation (429 / auth errors)](api-key-rotation.md) — how to
  rotate keys in `keys.yaml` without losing resume state
- [SQLite cache corruption (`database disk image is malformed`)](database-corruption.md) —
  when `llm2deck.db` is unreadable and runs can't resume
- [Resume loop (run never finishes)](resume-loop.md) — when `--resume`
  keeps picking up the same question

## Escalation

If none of the playbooks resolve the issue, gather:

1. `git rev-parse HEAD` and the output of `git status --porcelain`
2. The last 200 lines of the verbose log (`-v` / `--verbose`)
3. The exact `node src/cli.js …` command line, with redacted keys
4. The output of `node src/cli.js cache stats`

…and open an issue at <https://github.com/not-lucky/LLM2Deck/issues>.
