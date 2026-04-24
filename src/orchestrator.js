import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import {
  initDatabase,
  getDb,
  createRun,
  updateRunStatus,
  getRun,
  closeDatabase,
} from './database.js';
import { createProviderClients, createThrottledFetcher } from './providers.js';
import { runStage1, runStage2, runStage3 } from './stages.js';
import { postProcess } from './postProcess.js';

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
 * @param {number} [params.maxEnforcementRetries=5] Max Stage 3 schema recovery attempts.
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
  maxEnforcementRetries = 5,
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

    if (resumeRunId) {
      const existingRun = getRun(resumeRunId);
      if (!existingRun) {
        throw new Error(`Run with ID "${resumeRunId}" not found in database.`);
      }
      runId = resumeRunId;
      if (!dryRun) {
        // Update database run status back to 'running' during resumption
        updateRunStatus(runId, 'running');
      }
      completedQuestions = getCompletedQuestions(runId);
    } else {
      runId = crypto.randomUUID();
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
        });
      }
    }

    const clients = createProviderClients(config, keys);
    const throttledFetch = createThrottledFetcher(config);
    const resolvedPrompts = prompts || {};

    const results = [];
    let hasFailures = false;

    for (const question of questions) {
      const qId = question.questionId || question.topic || question.deckPath || '';
      const qContent = question.content || '';

      if (!qId) {
        console.warn('Skipping question because it is missing a valid identifier.');
        hasFailures = true;
        continue;
      }

      if (completedQuestions.has(qId)) {
        console.info(`Skipping already completed question: ${qId}`);
        results.push({ questionId: qId, skipped: true });
        continue;
      }

      if (dryRun) {
        console.info(`[Dry-Run] Would process question: ${qId}`);
        results.push({ questionId: qId, dryRun: true });
        continue;
      }

      try {
        console.info(`Processing question: ${qId}`);

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

        const sanitizedQId = sanitizeFilename(qId);
        const jsonFilename = `${runId}_${sanitizedQId}.json`;
        const jsonPath = path.join(outputDir, jsonFilename);

        if (!fs.existsSync(outputDir)) {
          fs.mkdirSync(outputDir, { recursive: true });
        }

        fs.writeFileSync(jsonPath, JSON.stringify(postProcessedResult, null, 2), 'utf8');
        results.push({ questionId: qId, jsonPath });
      } catch (error) {
        console.error(`Error processing question "${qId}":`, error);
        hasFailures = true;
      }
    }

    // Compile successfully processed files
    const compileResults = results.filter((r) => r.jsonPath);
    if (!dryRun && compileResults.length > 0) {
      const compilationPromises = compileResults.map(async (res) => {
        const sanitizedQId = sanitizeFilename(res.questionId);
        let outputApkgPath;

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
            outputApkgPath = path.join(outputPath, `${sanitizedQId}.apkg`);
          } else if (compileResults.length > 1) {
            const ext = path.extname(outputPath);
            const dir = path.dirname(outputPath);
            const base = path.basename(outputPath, ext);
            outputApkgPath = path.join(dir, `${base}_${sanitizedQId}${ext}`);
          } else {
            outputApkgPath = outputPath;
          }
        } else {
          outputApkgPath = res.jsonPath.replace(/\.json$/, '.apkg');
        }

        try {
          console.info(`Compiling deck for: ${res.questionId}`);
          await spawnCompiler(res.jsonPath, outputApkgPath, {
            deckName,
            subject,
            source,
            timeout: config?.global?.compiler_timeout,
          });
          res.apkgPath = outputApkgPath;
        } catch (err) {
          console.error(`Compilation failed for ${res.questionId}:`, err);
          hasFailures = true;
        }
      });

      await Promise.all(compilationPromises);
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
