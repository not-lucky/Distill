import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import pLimit from 'p-limit';
import {
  initDatabase,
  getDb,
  createRun,
  updateRunStatus,
  getRun,
  closeDatabase,
} from './database.js';
import { createProviderClients, createThrottledFetcher } from './providers.js';
import {
  runStage1, runStage2, runStage3, cleanJsonOutput,
} from './stages.js';
import { postProcess } from './postProcess.js';
import { getLogger } from './logger.js';

const logger = getLogger(['orchestrator']);

/**
 * Retrieves all completed enforcement step outputs from the database for the given runId,
 * parses them, and returns a Map mapping questionId to the parsed JSON.
 * This is crucial during resumption to pull previously generated card data out of the DB,
 * ensuring all completed topics of the run are merged into the final consolidated output files.
 *
 * @param {string} runId
 * @returns {Map<string, Object>} Map mapping question ID to conforming JSON object.
 */
export function getCompletedStage3Results(runId) {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT question_id, latest_response FROM run_questions
    WHERE run_id = ? AND current_stage = 'enforcement'
  `);
  const rows = stmt.all(runId);
  const results = new Map();
  for (const row of rows) {
    if (!row || !row.latest_response) continue;
    try {
      const cleaned = cleanJsonOutput(row.latest_response);
      results.set(row.question_id, JSON.parse(cleaned));
    } catch (err) {
      logger.error`Failed to parse completed question ${row.question_id} response from DB: ${err}`;
    }
  }
  return results;
}

/**
 * Sanitizes a string to make it safe for use as a filename.
 * Strips non-alphanumeric characters (except hyphens and underscores).
 *
 * @param {string} name String to sanitize.
 * @returns {string} Sanitized string.
 */
export function sanitizeFilename(name) {
  if (typeof name !== 'string') return '';
  return name.replace(/[^a-zA-Z0-9-_]/g, '_');
}

/**
 * Wraps child_process.spawn to execute the Python compilation step.
 * Implements execution timeouts to prevent process hangs.
 *
 * @param {string} jsonPath Path to the input JSON file.
 * @param {string} outputPath Path to output .apkg file.
 * @param {Object} [options={}] Optional metadata overrides and process controls.
 * @param {string} [options.deckName] Optional deck name override.
 * @param {string} [options.subject] Optional subject metadata.
 * @param {string} [options.source] Optional source file override.
 * @param {number} [options.timeout=60000] Process execution timeout in milliseconds.
 * @returns {Promise<{ code: number, stdout: string, stderr: string }>}
 */
export function spawnCompiler(jsonPath, outputPath, options = {}) {
  const timeoutMs = options.timeout !== undefined ? options.timeout : 60000;

  return new Promise((resolve, reject) => {
    const args = ['run', 'src/compile.py', jsonPath];
    if (outputPath) {
      args.push('-o', outputPath);
    }
    if (options.deckName) {
      args.push('--deck-name', options.deckName);
    }
    if (options.subject) {
      args.push('--subject', options.subject);
    }
    if (options.source) {
      args.push('--source', options.source);
    }

    const child = spawn('uv', args);
    let stdout = '';
    let stderr = '';
    let timedOut = false;

    // Initialize execution timeout guard to prevent locking resources
    let timer = null;
    if (timeoutMs > 0) {
      timer = setTimeout(() => {
        timedOut = true;
        child.kill('SIGTERM');
        reject(new Error(`Compiler execution timed out after ${timeoutMs}ms.`));
      }, timeoutMs);
    }

    child.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('close', (code) => {
      if (timer) {
        clearTimeout(timer);
      }
      // If the timeout timer already fired, ignore this event to avoid duplicate promise rejection
      if (timedOut) return;

      if (code === 0) {
        resolve({ code, stdout, stderr });
      } else {
        const error = new Error(`Compiler process exited with code ${code}.\nStderr: ${stderr}`);
        error.code = code;
        error.stdout = stdout;
        error.stderr = stderr;
        reject(error);
      }
    });

    child.on('error', (err) => {
      if (timer) {
        clearTimeout(timer);
      }
      if (timedOut) return;
      reject(err);
    });
  });
}

/**
 * Queries the pipeline_steps table for completed question IDs under the given runId.
 * A question is completed if it has an 'enforcement' stage step logged.
 *
 * @param {string} runId
 * @returns {Set<string>} Set of completed question IDs.
 */
export function getCompletedQuestions(runId) {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT question_id FROM run_questions
    WHERE run_id = ? AND current_stage = 'enforcement'
  `);
  const rows = stmt.all(runId);
  return new Set(rows.map((row) => row.question_id));
}

/**
 * Runs the full parallel flashcard generation & compilation pipeline.
 *
 * @param {Object} params
 * @param {Object} params.config The merged system configuration.
 * @param {Object} params.keys Loaded API keys.
 * @param {Array<Object>} params.questions Array of question/topic objects to process.
 * @param {string} params.subject Case-insensitive subject configuration name.
 * @param {string} [params.cardType='standard'] Card layout format ('standard' or 'mcq').
 * @param {string} [params.outputPath] Final path for compiled apkg output.
 * @param {string} [params.outputDir='./output'] Output directory for intermediate JSONs.
 * @param {string} [params.resumeRunId] Run ID to resume execution from.
 * @param {boolean} [params.dryRun=false] If true, validate and log without LLM queries/compilation.
 * @param {string} [params.deckName] Optional override for compiled deck name.
 * @param {string} [params.source] Optional override for source file.
 * @param {number} [params.maxEnforcementRetries=3] Max Stage 3 schema recovery attempts.
 * @returns {Promise<{ runId: string, results: Array<Object>, hasFailures: boolean }>}
 */
export async function runPipeline({
  config,
  keys,
  prompts,
  questions,
  subject,
  cardType = 'standard',
  outputPath,
  outputDir = './output',
  resumeRunId = null,
  dryRun = false,
  deckName = null,
  source = null,
  maxEnforcementRetries = 3,
}) {
  if (!config) {
    throw new Error('Configuration object is required.');
  }
  if (!Array.isArray(questions)) {
    throw new Error('Questions parameter must be an array.');
  }

  let dbInitialized = false;
  try {
    getDb();
  } catch (err) {
    const dbPath = config?.global?.cache_db_path || './llm2deck.db';
    initDatabase(dbPath);
    dbInitialized = true;
  }

  // Wrap the pipeline's execution block in a try-finally block to ensure
  // database cleanup operations run even if setup functions throw exceptions.
  try {
    let runId;
    let completedQuestions = new Set();
    let completedStage3Results = new Map();
    let createdAtIso;

    if (resumeRunId) {
      const existingRun = getRun(resumeRunId);
      if (!existingRun) {
        throw new Error(`Run with ID "${resumeRunId}" not found in database.`);
      }
      runId = resumeRunId;
      createdAtIso = existingRun.created_at || new Date().toISOString();
      if (!dryRun) {
        // Update database run status back to 'running' during resumption
        updateRunStatus(runId, 'running');
      }
      completedQuestions = getCompletedQuestions(runId);
      completedStage3Results = getCompletedStage3Results(runId);
    } else {
      runId = crypto.randomUUID();
      createdAtIso = new Date().toISOString();
      if (!dryRun) {
        const pipelineConfig = config.pipeline || {};
        const providersConfig = config.providers || {};
        const hash = crypto.createHash('sha256');
        hash.update(JSON.stringify({ pipeline: pipelineConfig, providers: providersConfig }));
        const configHash = hash.digest('hex');

        createRun({
          runId,
          subject,
          cardType,
          status: 'running',
          configHash,
          createdAt: createdAtIso,
        });
      }
    }

    const clients = createProviderClients(config, keys);
    const throttledFetch = createThrottledFetcher(config);
    const resolvedPrompts = prompts || {};

    const results = [];
    const mergedTopics = [];
    let hasFailures = false;

    // Read topic_concurrency (defaulting to 1 for sequential topic processing).
    // Handles invalid, zero, negative, or non-numeric values defensively by falling back to 1.
    // Creates a p-limit pool to process multiple topics/documents concurrently.
    let topicConcurrency = config.global?.topic_concurrency;
    if (typeof topicConcurrency !== 'number' || topicConcurrency < 1 || Number.isNaN(topicConcurrency)) {
      topicConcurrency = 1;
    }
    const limit = pLimit(topicConcurrency);

    // Map each question/topic to a concurrency-limited pipeline execution task.
    // Note that while topics are processed concurrently up to topic_concurrency,
    // the individual stages for any single topic (Stage 1 -> Stage 2 -> Stage 3)
    // execute in strict sequential order.
    const promises = questions.map((question) => limit(async () => {
      const qId = question.questionId || question.topic || question.deckPath || '';
      const qContent = question.content || '';

      if (!qId) {
        logger.warn`Skipping question because it is missing a valid identifier.`;
        hasFailures = true;
        return { failure: true };
      }

      if (completedQuestions.has(qId)) {
        logger.info`Skipping already completed question: ${qId}`;
        if (dryRun) {
          return { questionId: qId, dryRun: true };
        }

        const completedResult = completedStage3Results.get(qId);
        if (completedResult) {
          const metadata = question.metadata || {};
          const postProcessedResult = postProcess(completedResult, {
            categoryName: metadata.categoryName || question.categoryName,
            categoryIndex: metadata.categoryIndex !== undefined
              ? metadata.categoryIndex
              : question.categoryIndex,
            problemIndex: metadata.problemIndex !== undefined
              ? metadata.problemIndex
              : question.problemIndex,
          });
          return { questionId: qId, skipped: true, postProcessedResult };
        }
        logger.warn`Could not retrieve completed result for question: ${qId} from DB. Will re-process.`;
      }

      if (dryRun) {
        logger.info`[Dry-Run] Would process question: ${qId}`;
        return { questionId: qId, dryRun: true };
      }

      try {
        logger.info`Processing question: ${qId}`;

        const stage1Results = await runStage1({
          runId,
          questionId: qId,
          topicName: question.topic,
          content: qContent,
          cardType,
          subject,
          prompts: resolvedPrompts,
          config,
          keys,
          clients,
          throttledFetch,
        });

        const synthesisResult = await runStage2({
          runId,
          questionId: qId,
          stage1Results,
          cardType,
          subject,
          prompts: resolvedPrompts,
          config,
          keys,
          clients,
          throttledFetch,
        });

        const stage3Result = await runStage3({
          runId,
          questionId: qId,
          synthesisResult,
          cardType,
          subject,
          prompts: resolvedPrompts,
          config,
          keys,
          clients,
          throttledFetch,
          maxEnforcementRetries,
        });

        const metadata = question.metadata || {};
        const postProcessedResult = postProcess(stage3Result, {
          categoryName: metadata.categoryName || question.categoryName,
          categoryIndex: metadata.categoryIndex !== undefined
            ? metadata.categoryIndex
            : question.categoryIndex,
          problemIndex: metadata.problemIndex !== undefined
            ? metadata.problemIndex
            : question.problemIndex,
        });

        return { questionId: qId, postProcessedResult };
      } catch (error) {
        logger.error`Error processing question "${qId}": ${error}`;
        hasFailures = true;
        return { questionId: qId, error: true };
      }
    }));

    const taskResults = await Promise.all(promises);

    for (const res of taskResults) {
      /* v8 ignore next */
      if (!res) continue;
      if (res.failure) {
        continue;
      }
      if (res.dryRun) {
        results.push({ questionId: res.questionId, dryRun: true });
        continue;
      }
      if (res.skipped) {
        /* v8 ignore next 3 */
        if (res.postProcessedResult) {
          mergedTopics.push(res.postProcessedResult);
        }
        results.push({ questionId: res.questionId, skipped: true });
        continue;
      }
      if (res.error) {
        continue;
      }
      /* v8 ignore next 3 */
      if (res.postProcessedResult) {
        mergedTopics.push(res.postProcessedResult);
      }
      results.push({ questionId: res.questionId });
    }

    // Compile successfully processed files
    if (!dryRun && mergedTopics.length > 0) {
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }

      const safeIsoDate = createdAtIso.replace(/[:.]/g, '-');
      const jsonFilename = `${safeIsoDate}_${runId}.json`;
      const jsonPath = path.join(outputDir, jsonFilename);

      fs.writeFileSync(jsonPath, JSON.stringify(mergedTopics, null, 2), 'utf8');

      // Update results list with the jsonPath
      for (const res of results) {
        res.jsonPath = jsonPath;
      }

      let outputApkgPath;
      const defaultApkgFilename = `${safeIsoDate}_${runId}.apkg`;

      if (outputPath) {
        let isDirectory = false;
        if (fs.existsSync(outputPath)) {
          isDirectory = fs.statSync(outputPath).isDirectory();
        } else {
          isDirectory = !path.extname(outputPath);
        }

        if (isDirectory) {
          if (!fs.existsSync(outputPath)) {
            fs.mkdirSync(outputPath, { recursive: true });
          }
          outputApkgPath = path.join(outputPath, defaultApkgFilename);
        } else {
          outputApkgPath = outputPath;
        }
      } else {
        outputApkgPath = path.join(outputDir, defaultApkgFilename);
      }

      try {
        logger.info`Compiling deck for run: ${runId}`;
        await spawnCompiler(jsonPath, outputApkgPath, {
          deckName,
          subject,
          source,
          timeout: config?.global?.compiler_timeout,
        });

        // Update results list with the apkgPath
        for (const res of results) {
          res.apkgPath = outputApkgPath;
        }
      } catch (err) {
        logger.error`Compilation failed for run ${runId}: ${err}`;
        hasFailures = true;
      }
    }

    if (!dryRun) {
      const finalStatus = hasFailures ? 'failed' : 'completed';
      updateRunStatus(runId, finalStatus);
    }

    return { runId, results, hasFailures };
  } finally {
    if (dbInitialized) {
      closeDatabase();
    }
  }
}
