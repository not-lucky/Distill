# Runbook: SQLite cache corruption

## Symptoms

- `SqliteError: database disk image is malformed`
- `SqliteError: file is not a database` (the file is empty or zero-byte)
- Cache commands fail: `node src/cli.js cache stats` exits non-zero
- Runs cannot resume (`--resume <run-id>` cannot find the run)

## Triage

```bash
# 1. Confirm the database is broken
sqlite3 distill.db "PRAGMA integrity_check;"
# Expected on a healthy DB: "ok"
# Anything else means corruption.

# 2. Check the file size and last-modified time
ls -la distill.db
file distill.db
```

## Mitigation

The cache is a **performance and resumability** layer, not the source of
truth. A corrupted cache should never cause data loss — the source
material lives in your repository. The recovery path is:

1. **Stop the pipeline.** If a run is in flight, kill it (Ctrl-C, then
   `kill -9 <pid>` if needed). Do not let it keep writing to the broken
   DB.

2. **Move the corrupted file aside** (do not delete it; you may need it
   for forensics):

   ```bash
   mv distill.db distill.db.corrupt.$(date +%Y%m%d-%H%M%S)
   ```

3. **Restart the run from scratch.** Distill will re-create the
   database on the next `node src/cli.js run …`. Cache hits will be
   missed for the first run, so the next run will be slower (and
   slightly more expensive) but otherwise identical.

   ```bash
   node src/cli.js run <subject>
   ```

4. **Reconcile.** If you suspect a partial write to the corrupt file,
   compare its `runs` and `steps` tables against the new database and
   port any rows that are missing:

   ```bash
   sqlite3 distill.db.corrupt.<timestamp> .dump > old.sql
   sqlite3 distill.db <new> old.sql   # manual reconciliation
   ```

   In most cases this step is unnecessary — the corruption is usually
   limited to the SQLite header or to a single page, and the data
   inside is intact.

## Root cause

The most common root causes are:

- The process was killed mid-write (SIGKILL, OOM, power loss)
- The disk ran out of space while SQLite was flushing the WAL
- An external tool (e.g. `sqlite3 … VACUUM INTO`) was run against the
  file while Distill was also writing to it

## Prevention

- Use `PRAGMA journal_mode = WAL;` (set automatically by
  `src/database.js`) and `PRAGMA synchronous = NORMAL;` so that crashes
  never corrupt the main DB file.
- Make sure `output_dir` and the directory containing `distill.db` are
  on a filesystem with at least 1 GB of free headroom.
- Do not run `sqlite3 distill.db …` while a pipeline run is in flight.

## Postmortem checklist

- [ ] A new, healthy `distill.db` has been created
- [ ] At least one end-to-end run has completed since the recovery
- [ ] The corrupted file is archived (not deleted) until the incident
      is closed
- [ ] The `disk_free` check in the pipeline's pre-flight has been
      confirmed to fire on the affected machine
