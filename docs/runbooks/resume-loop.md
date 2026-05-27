# Runbook: Resume loop

## Symptoms

- `node src/cli.js run <subject> --resume <run-id>` finishes "successfully"
  but the same `run-id` keeps coming up when you check
  `node src/cli.js cache stats`
- Repeated re-runs do not advance past the same question
- The verbose log shows the same question ID being re-tried on every
  pipeline start

## Triage

```bash
# 1. Inspect the run's steps table
sqlite3 distill.db \
  "SELECT question_id, stage, status, error
     FROM steps
     WHERE run_id = '<run-id>'
     ORDER BY updated_at DESC
     LIMIT 20;"

# 2. Look for the failure pattern
sqlite3 distill.db \
  "SELECT question_id, COUNT(*) AS attempts
     FROM steps
     WHERE run_id = '<run-id>' AND status = 'failed'
     GROUP BY question_id
     ORDER BY attempts DESC
     LIMIT 10;"
```

If a single `question_id` is being re-attempted far more times than the
retry budget (default 3 for Stage 3), you are in a resume loop.

## Mitigation

1. **Identify the question that won't finish.** The triage query above
   will show it. Open the synthesis output for that question:

   ```bash
   sqlite3 distill.db \
     "SELECT output FROM api_outputs
        WHERE run_id = '<run-id>' AND question_id = '<offender>'
          AND stage = 'synthesis';" | tee /tmp/synthesis.txt
   ```

2. **Decide between manual repair and exclusion.**

   - If the synthesis output is salvageable, hand-craft a Stage 3
     payload that conforms to the
     [Stage 3 JSON contract](../reference/stage3-json.md) and write it
     directly to the `api_outputs` table with `stage = 'enforcement'`
     and `status = 'success'`. Then re-run with `--resume`.
   - If the question is broken (e.g. the source material is truncated),
     the cleanest fix is to skip it. Update the `runs` table to mark
     the offending `question_id` as `skipped` and resume — the
     orchestrator will move on.

3. **Tighten the retry budget** for the duration of the incident so
   future failures bail out faster:

   ```yaml
   # config.yaml
   global:
     enforcement_max_attempts: 2 # was 3
   ```

## Root cause

Resume loops almost always come from one of:

- A persistently broken source chunk (e.g. a PDF page that did not
  extract cleanly) that produces the same broken synthesis every time
- A schema drift that the Stage 3 retry loop cannot resolve (see
  [Schema drift](schema-drift.md))
- A bug in the orchestrator that re-marks a `success` step as `pending`
  on every resume

The third cause is the only one that warrants a code change. If you can
reproduce it, open an issue with the `runs`/`steps` dump from step 1 of
triage and the orchestrator log.

## Postmortem checklist

- [ ] The affected run completes end-to-end on a fresh resume
- [ ] The root cause has been identified (source bug / schema drift /
      orchestrator bug) and a follow-up issue is filed if appropriate
- [ ] If the source chunk is at fault, the ingestion step is updated to
      either skip the chunk or surface a clearer error
- [ ] If the orchestrator is at fault, a regression test has been added
      that simulates the resume state and asserts forward progress
