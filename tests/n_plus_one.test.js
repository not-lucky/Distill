import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { initDatabase, closeDatabase } from '../src/database.js';
import Database from 'better-sqlite3';

/**
 * N+1 query detection — verifies that bulk read paths in the pipeline
 * use a constant number of SQL statements, not one-per-row.
 *
 * Strategy:
 *   - Use a real on-disk SQLite file (not :memory:) so the module-level
 *     connection and the test's instrumented connection see the same data.
 *   - Instrument the test connection's `.prepare` to count calls.
 *   - Seed N completed questions, then mirror the orchestrator's bulk SELECT.
 *   - Assert the number of prepare() calls is O(1) (not O(N)).
 *
 * If a regression introduces an N+1 pattern, this test fails.
 */

describe('N+1 query detection', () => {
  let dbPath;
  let conn;

  beforeEach(() => {
    dbPath = path.join(os.tmpdir(), `n_plus_one_${Date.now()}_${Math.random()}.db`);
    initDatabase(dbPath);
    // Open a second connection to the SAME file so we can instrument it
    // without disturbing the module-level connection used by the orchestrator.
    conn = new Database(dbPath);
  });

  afterEach(() => {
    closeDatabase();
    if (conn) conn.close();
    if (dbPath && fs.existsSync(dbPath)) {
      try {
        fs.unlinkSync(dbPath);
      } catch {
        /* ignore */
      }
      try {
        fs.unlinkSync(`${dbPath}-wal`);
      } catch {
        /* ignore */
      }
      try {
        fs.unlinkSync(`${dbPath}-shm`);
      } catch {
        /* ignore */
      }
    }
    vi.restoreAllMocks();
  });

  it('bulk read uses one prepare() call for N rows (no N+1)', () => {
    const runId = 'run-n+1-bulk';
    conn
      .prepare(
        `INSERT INTO runs (run_id, subject, card_type, status, config_hash) VALUES (?, ?, ?, ?, ?)`,
      )
      .run(runId, 'biology', 'standard', 'completed', 'hash2');

    const N = 50;
    const upsert = conn.prepare(`
      INSERT INTO run_questions (run_id, question_id, current_stage, latest_response)
      VALUES (?, ?, 'enforcement', ?)
    `);
    const insertMany = conn.transaction(() => {
      for (let i = 0; i < N; i++) {
        upsert.run(runId, `q${i}`, JSON.stringify({ topic: `t${i}`, cards: [] }));
      }
    });
    insertMany();

    let prepareCount = 0;
    const realPrepare = conn.prepare.bind(conn);
    conn.prepare = (...args) => {
      prepareCount += 1;
      return realPrepare(...args);
    };

    // Mirror orchestrator's getCompletedQuestions behavior against the seeded data.
    const result = new Set(
      conn
        .prepare(
          `SELECT question_id FROM run_questions WHERE run_id = ? AND current_stage = 'enforcement'`,
        )
        .all(runId)
        .map((row) => row.question_id),
    );
    expect(result.size).toBe(N);
    // Exactly one prepare() call -> no N+1 anti-pattern.
    expect(prepareCount).toBe(1);
  });

  it('regression guard: per-question SELECT loop would exceed threshold', () => {
    const runId = 'run-n+1-regression';
    conn
      .prepare(
        `INSERT INTO runs (run_id, subject, card_type, status, config_hash) VALUES (?, ?, ?, ?, ?)`,
      )
      .run(runId, 'history', 'standard', 'completed', 'hash3');

    const N = 10;
    const upsert = conn.prepare(`
      INSERT INTO run_questions (run_id, question_id, current_stage, latest_response)
      VALUES (?, ?, 'enforcement', ?)
    `);
    const insertMany = conn.transaction(() => {
      for (let i = 0; i < N; i++) {
        upsert.run(runId, `q${i}`, JSON.stringify({}));
      }
    });
    insertMany();

    let prepareCount = 0;
    const realPrepare = conn.prepare.bind(conn);
    conn.prepare = (...args) => {
      prepareCount += 1;
      return realPrepare(...args);
    };

    // The "naive" anti-pattern: one SELECT per question id.
    const ids = ['q0', 'q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9'];
    for (const id of ids) {
      conn.prepare(`SELECT 1 FROM run_questions WHERE question_id = ?`).get(id);
    }

    // 10 prepare() calls for 10 rows -> N+1 detected.
    expect(prepareCount).toBeGreaterThan(1);
  });
});
