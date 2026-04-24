import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';

/**
 * Module-level database connection state.
 * @type {Database.Database|null}
 */
let dbConn = null;

/**
 * Returns the current database connection if initialized, otherwise throws an error.
 * @returns {Database.Database} The active SQLite database connection.
 * @throws {Error} If database is not initialized.
 */
export function getDb() {
  if (!dbConn) {
    throw new Error('Database is not initialized. Call initDatabase(dbPath) first.');
  }
  return dbConn;
}

/**
 * Initializes the SQLite database:
 * - Safely closes any existing connection to prevent resource leaks.
 * - Ensures parent directory exists.
 * - Opens the connection.
 * - Sets pragmas for foreign keys and WAL mode.
 * - Creates tables and indices if they do not exist.
 *
 * @param {string} dbPath Path to the SQLite database file.
 * @returns {Database.Database} The initialized database connection.
 */
export function initDatabase(dbPath) {
  // Prevent resource leaks: close the current active connection if re-initializing
  if (dbConn) {
    try {
      dbConn.close();
    } catch (error) {
      // Ignore errors during cleanup of stale connection
    }
    dbConn = null;
  }

  // Ensure the directory exists
  const dir = path.dirname(dbPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  dbConn = new Database(dbPath);

  // WAL (Write-Ahead Logging) mode allows concurrent reads and writes by writing changes to
  // a separate log. This prevents SQLite database locking or busy issues when parallel
  // async operations perform database writes.
  // Foreign keys are enabled explicitly on every connection because SQLite disables
  // them by default. This ensures cascade deletions ON DELETE CASCADE are correctly propagated.
  dbConn.pragma('foreign_keys = ON');
  dbConn.pragma('journal_mode = WAL');

  // Define schemas
  // CHECK constraints enforce that data fields conform to specified layout structures and states.
  const schemaSql = `
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        subject TEXT NOT NULL,
        card_type TEXT NOT NULL CHECK(card_type IN ('standard', 'mcq')),
        status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
        config_hash TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS pipeline_steps (
        step_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        stage TEXT NOT NULL CHECK(stage IN ('generation', 'synthesis', 'translation', 'enforcement')),
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        input_data TEXT NOT NULL,
        output_data TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS run_questions (
        question_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        current_stage TEXT NOT NULL,
        input_content TEXT,
        latest_prompt TEXT,
        latest_response TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (run_id, question_id),
        FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS llm_cache (
        cache_key TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        prompt_hash TEXT NOT NULL,
        response TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_pipeline_steps_lookup ON pipeline_steps(run_id, question_id);
    CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
  `;

  dbConn.exec(schemaSql);

  return dbConn;
}

/**
 * Safely closes the active database connection.
 */
export function closeDatabase() {
  if (dbConn) {
    dbConn.close();
    dbConn = null;
  }
}

/**
 * Creates a new execution run record in the database.
 *
 * @param {Object} params
 * @param {string} params.runId Unique identifier for the run.
 * @param {string} params.subject Name of the subject or directory path.
 * @param {string} params.cardType Layout format ('standard' or 'mcq').
 * @param {string} params.status Run status ('running', 'completed', 'failed').
 * @param {string} params.configHash Hash representing current system configuration.
 * @returns {Database.RunResult} Result of the insertion operation.
 */
export function createRun({
  runId, subject, cardType, status, configHash,
}) {
  const db = getDb();
  const stmt = db.prepare(`
    INSERT INTO runs (run_id, subject, card_type, status, config_hash)
    VALUES (?, ?, ?, ?, ?)
  `);
  return stmt.run(runId, subject, cardType, status, configHash);
}

/**
 * Updates the execution status of a run.
 *
 * @param {string} runId
 * @param {string} status ('running', 'completed', 'failed')
 * @returns {Database.RunResult}
 * @throws {Error} If the run does not exist.
 */
export function updateRunStatus(runId, status) {
  const db = getDb();
  const stmt = db.prepare(`
    UPDATE runs SET status = ? WHERE run_id = ?
  `);
  const result = stmt.run(status, runId);
  if (result.changes === 0) {
    throw new Error(`Run with ID "${runId}" not found.`);
  }
  return result;
}

/**
 * Retrieves a run record by ID.
 *
 * @param {string} runId
 * @returns {Object|undefined} The run record or undefined if not found.
 */
export function getRun(runId) {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT run_id, created_at, subject, card_type, status, config_hash FROM runs WHERE run_id = ?
  `);
  return stmt.get(runId);
}

/**
 * Deletes a run record and cascades deletions to all associated pipeline steps.
 *
 * @param {string} runId
 * @returns {Database.RunResult}
 */
export function deleteRun(runId) {
  const db = getDb();
  const stmt = db.prepare(`
    DELETE FROM runs WHERE run_id = ?
  `);
  return stmt.run(runId);
}

/**
 * Logs a pipeline execution step for auditing.
 *
 * @param {Object} params
 * @param {string} params.runId
 * @param {string} params.questionId
 * @param {string} params.stage ('generation', 'synthesis', 'translation', 'enforcement')
 * @param {string} params.provider
 * @param {string} params.model
 * @param {string} params.inputData
 * @param {string} params.outputData
 * @returns {Database.RunResult}
 */
export function addPipelineStep({
  runId, questionId, stage, provider, model, inputData, outputData,
}) {
  const db = getDb();
  const stmt = db.prepare(`
    INSERT INTO pipeline_steps (run_id, question_id, stage, provider, model, input_data, output_data)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  return stmt.run(runId, questionId, stage, provider, model, inputData, outputData);
}

/**
 * Upserts a question entry to maintain a single record per question.
 *
 * @param {Object} params
 * @param {string} params.runId
 * @param {string} params.questionId
 * @param {string} params.currentStage
 * @param {string} [params.inputContent]
 * @param {string} [params.latestPrompt]
 * @param {string} [params.latestResponse]
 * @returns {Database.RunResult}
 */
export function upsertQuestionEntry({
  runId, questionId, currentStage, inputContent = null, latestPrompt = null, latestResponse = null,
}) {
  const db = getDb();
  const stmt = db.prepare(`
    INSERT INTO run_questions (run_id, question_id, current_stage, input_content, latest_prompt, latest_response)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(run_id, question_id) DO UPDATE SET
      current_stage = excluded.current_stage,
      input_content = COALESCE(excluded.input_content, input_content),
      latest_prompt = COALESCE(excluded.latest_prompt, latest_prompt),
      latest_response = COALESCE(excluded.latest_response, latest_response),
      updated_at = CURRENT_TIMESTAMP
  `);
  return stmt.run(runId, questionId, currentStage, inputContent, latestPrompt, latestResponse);
}

/**
 * Retrieves all step audits for a specific question within a run.
 *
 * @param {string} runId
 * @param {string} questionId
 * @returns {Array<Object>} List of pipeline step audit records.
 */
export function getPipelineSteps(runId, questionId) {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT step_id, run_id, question_id, stage, provider, model, input_data, output_data, timestamp
    FROM pipeline_steps
    WHERE run_id = ? AND question_id = ?
    ORDER BY timestamp ASC, step_id ASC
  `);
  return stmt.all(runId, questionId);
}

/**
 * Retrieves all step audits associated with a run.
 *
 * @param {string} runId
 * @returns {Array<Object>} List of pipeline step audit records.
 */
export function getPipelineStepsForRun(runId) {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT step_id, run_id, question_id, stage, provider, model, input_data, output_data, timestamp
    FROM pipeline_steps
    WHERE run_id = ?
    ORDER BY timestamp ASC, step_id ASC
  `);
  return stmt.all(runId);
}

/**
 * Retrieves a cached response by key.
 *
 * @param {string} cacheKey SHA256 request parameter hash.
 * @returns {Object|undefined} Cached record or undefined if cache miss.
 */
export function getCache(cacheKey) {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT cache_key, provider, model, prompt_hash, response, created_at FROM llm_cache WHERE cache_key = ?
  `);
  return stmt.get(cacheKey);
}

/**
 * Inserts or updates a cached response.
 * Implements an upsert policy: if the cache key already exists, updates the fields
 * with the new LLM output and resets the created_at timestamp.
 *
 * @param {Object} params
 * @param {string} params.cacheKey
 * @param {string} params.provider
 * @param {string} params.model
 * @param {string} params.promptHash
 * @param {string} params.response
 * @returns {Database.RunResult}
 */
export function setCache({
  cacheKey, provider, model, promptHash, response,
}) {
  const db = getDb();
  const stmt = db.prepare(`
    INSERT INTO llm_cache (cache_key, provider, model, prompt_hash, response)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(cache_key) DO UPDATE SET
      provider = excluded.provider,
      model = excluded.model,
      prompt_hash = excluded.prompt_hash,
      response = excluded.response,
      created_at = CURRENT_TIMESTAMP
  `);
  return stmt.run(cacheKey, provider, model, promptHash, response);
}

/**
 * Clears all cached LLM response entries.
 *
 * @returns {Database.RunResult}
 */
export function clearCache() {
  const db = getDb();
  const stmt = db.prepare(`
    DELETE FROM llm_cache
  `);
  return stmt.run();
}

/**
 * Retrieves cache utilization metrics.
 *
 * @returns {{ count: number }} Cache metrics.
 */
export function getCacheStats() {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT COUNT(*) as count FROM llm_cache
  `);
  return stmt.get();
}

/**
 * Executes a callback inside a transaction scope.
 * - If the callback throws an error, the transaction is automatically rolled back.
 * - If the callback completes successfully, the transaction is committed.
 * - better-sqlite3 automatically handles nested transactions using SAVEPOINTs.
 *
 * @param {Function} callback Callback containing DB queries to execute.
 * @returns {*} Result of the callback execution.
 */
export function transaction(callback) {
  const db = getDb();
  // db.transaction returns a transactional wrapper function which is immediately called.
  return db.transaction(callback)();
}
