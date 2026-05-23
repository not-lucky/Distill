# Runbook: API key rotation

## Symptoms

- `Error 401: Incorrect API key provided` from the OpenAI SDK
- `Error 429: Rate limit reached` sustained for >10 minutes
- `keys.yaml` has stale or rate-limited keys

## Triage

```bash
# 1. Confirm the error
node src/cli.js cache stats           # should still work; uses no API
node src/cli.js run <subject> -v      # verbose will surface 401/429

# 2. Check the request cache hit rate
sqlite3 llm2deck.db \
  "SELECT provider, model, COUNT(*) AS hits
     FROM api_outputs
     WHERE created_at > datetime('now', '-1 day')
     GROUP BY provider, model
     ORDER BY hits DESC;"
```

A high cache hit rate means rotation is safer — most calls will short-
circuit and never hit the new keys.

## Mitigation

The `keys` module in `src/llm/keys.js` round-robins through the list
defined in `keys.yaml`. To rotate without losing resume state:

1. **Append the new key** to the relevant provider's list:

   ```yaml
   openai:
     - 'sk-proj-...old-...'
     - 'sk-proj-...new-...' # new key, used when old rotates out
   ```

2. **Verify rotation works** by running a single dry-run:

   ```bash
   node src/cli.js run <subject> --dry-run -v
   ```

3. **Drop the old key** only after the new one has served traffic for at
   least one full run. Until then, the old key provides a safety net if
   the new one is misconfigured.

If a key has been leaked, **revoke it at the provider first**, then
remove it from `keys.yaml` immediately. The local copy is not the source
of truth — the provider is.

## Root cause

The most common root causes are:

- A key expired or was revoked by the provider
- A provider rolled out a new key format and old keys are no longer valid
- The OpenAI SDK was upgraded to a version that requires a different env
  var name (the project uses the SDK's `apiKey` constructor argument
  exclusively, so this should not affect LLM2Deck)

## Postmortem checklist

- [ ] All keys in `keys.yaml` are confirmed valid against the provider
- [ ] `git diff keys.yaml` shows only the expected additions/removals
      (and the file is gitignored, so the diff should be empty in CI)
- [ ] At least one successful end-to-end run has completed since the
      rotation
- [ ] If a key was leaked, the provider's revocation log shows the
      revocation
