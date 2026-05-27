# Runbook: Schema drift

## Symptoms

- Stage 3 retries the same question repeatedly (visible as
  `enforcement attempt N/3` in the verbose log)
- The same `ZodError` keeps appearing with no variation
- The synthesised Stage 2 output is well-formed markdown but Stage 3
  cannot parse it

## Triage

```bash
# 1. See the latest synthesis output for the failing question
sqlite3 distill.db \
  "SELECT question_id, output FROM api_outputs
   WHERE stage = 'synthesis' AND run_id = '<run-id>'
   ORDER BY created_at DESC LIMIT 5;"

# 2. See the latest enforcement attempt and its error
sqlite3 distill.db \
  "SELECT question_id, error FROM steps
   WHERE stage = 'enforcement' AND status = 'failed'
   ORDER BY updated_at DESC LIMIT 5;"

# 3. Manually re-run enforcement against the synthesis output
node -e "
  const { validateCardOutput } = await import('./src/pipeline/validation.js');
  console.log(validateCardOutput(<paste-synthesis-output-here>));
"
```

## Mitigation

The default retry budget in `src/pipeline/stages/stage3-enforcement.js` is
3 attempts. When the budget is exhausted, the question is marked
`enforcement_failed` and the run moves on. To recover:

1. **Tighten the enforcement prompt.** Add a "Common mistakes" section to
   the `enforcement` block in `prompts.yaml` that calls out the most
   frequent violations (e.g. `correct_answer: 'a'` lowercase, MCQ with
   fewer than 2 options, Cloze `front` without `{{c1::…}}`).
2. **Switch to a stronger model.** The default Stage 3 model is cost-
   optimised. Override `pipeline.schema_enforcement.model` in
   `config.yaml` with a frontier model (e.g. `openai/gpt-4o`) for the
   duration of the incident.
3. **Manually repair the synthesis output** in `prompts.yaml` or a one-off
   patch script, then resume:

   ```bash
   node src/cli.js run <subject> --resume <run-id>
   ```

## Root cause

Schema drift usually means the Stage 2 prompt evolved (a new example
format, a new field, etc.) faster than the Stage 3 prompt or the Zod
schema. Pin the Stage 3 prompt to the published
[Stage 3 JSON contract](../reference/stage3-json.md) and add a unit test
that re-runs the synthesis fixture through the validator whenever
`src/pipeline/schemas/card-zod.js` changes.

## Postmortem checklist

- [ ] The failing run can be resumed end-to-end
- [ ] The enforcement prompt in `prompts.yaml` mentions the field(s) that
      were causing the loop
- [ ] A regression test has been added under `tests/` that exercises the
      previously drifting input
- [ ] The `card-zod.js` schema is reviewed and any field changes are
      mirrored in the published JSON Schema at
      `schemas/stage3-deck.schema.json`
