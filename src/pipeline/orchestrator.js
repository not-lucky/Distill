import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import pLimit from 'p-limit';
import {
  initDatabase,
  getDb,
  createRun,
  updateRunStatus,
  getRun,
  closeDatabase,
} from '../database.js';
import { createPipelineContext } from '../context.js';
import { resolveDbPath } from '../config.js';
import { runStage1 } from './stages/stage1-generation.js';
import { runStage2 } from './stages/stage2-synthesis.js';
import { runStage3 } from './stages/stage3-enforcement.js';
import { spawnCompiler } from './compiler.js';
import { cleanJsonOutput } from './validation.js';
import { postProcess } from '../postProcess.js';
import { getLogger } from '../logger.js';

const logger = getLogger(['orchestrator']);

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

export function getCompletedQuestions(runId) {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT question_id FROM run_questions
    WHERE run_id = ? AND current_stage = 'enforcement'
  `);
  const rows = stmt.all(runId);
  return new Set(rows.map((row) => row.question_id));
}

export { spawnCompiler };

/**
 * Extracts a stable questionId and content string from a question object.
 * Returns null if the question is missing a usable identifier.
 */
function getQuestionIdentifiers(question) {
  const qId = question.questionId || question.topic || question.deckPath || '';
  const qContent = question.content || '';
  return qId ? { qId, qContent } : null;
}

/**
 * Builds the postProcess metadata object from a question and its raw metadata.
 */
function buildPostProcessMetadata(question, metadata) {
  return {
    categoryName: metadata.categoryName || question.categoryName,
    categoryIndex:
      metadata.categoryIndex !== undefined ? metadata.categoryIndex : question.categoryIndex,
    problemIndex:
      metadata.problemIndex !== undefined ? metadata.problemIndex : question.problemIndex,
  };
}

/**
 * Handles a single question inside the concurrency-limited worker:
 * skips if already completed, otherwise runs stages 1-3 and post-processes.
 * Returns a per-question result descriptor; mutates the shared `state` object.
 */
async function processQuestion(
  question,
  context,
  completedQuestions,
  completedStage3Results,
  dryRun,
  state,
) {
  const ids = getQuestionIdentifiers(question);
  if (!ids) {
    logger.warn`Skipping question because it is missing a valid identifier.`;
    state.hasFailures = true;
    return { failure: true };
  }
  const { qId, qContent } = ids;
  const metadata = question.metadata || {};

  // Skip already-completed questions.
  if (completedQuestions.has(qId)) {
    logger.info`Skipping already completed question: ${qId}`;
    if (dryRun) return { questionId: qId, dryRun: true };
    const completedResult = completedStage3Results.get(qId);
    if (completedResult) {
      const postProcessedResult = postProcess(
        completedResult,
        buildPostProcessMetadata(question, metadata),
      );
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
    const stage1Results = await runStage1(context, {
      questionId: qId,
      topicName: question.topic,
      content: qContent,
    });
    const synthesisResult = await runStage2(context, { questionId: qId, stage1Results });
    const stage3Result = await runStage3(context, { questionId: qId, synthesisResult });
    const postProcessedResult = postProcess(
      stage3Result,
      buildPostProcessMetadata(question, metadata),
    );
    return { questionId: qId, postProcessedResult };
  } catch (error) {
    logger.error`Error processing question "${qId}": ${error}`;
    state.hasFailures = true;
    return { questionId: qId, error: true };
  }
}

/**
 * Resolves the final `.apkg` output path from the user-supplied outputPath
 * (which may be a directory or a file path) and a default filename.
 */
function resolveApkgOutputPath(outputPath, outputDir, defaultApkgFilename) {
  if (!outputPath) {
    return path.join(outputDir, defaultApkgFilename);
  }
  // throwIfNoEntry: false folds the existsSync + statSync pair into a single
  // syscall that returns undefined for a missing path instead of throwing.
  const stats = fs.statSync(outputPath, { throwIfNoEntry: false });
  const looksLikeDirectory = stats?.isDirectory() || !path.extname(outputPath);
  if (looksLikeDirectory) {
    // fs.mkdir with { recursive: true } is idempotent, so we don't need to
    // gate it behind a separate existsSync probe.
    fs.mkdirSync(outputPath, { recursive: true });
    return path.join(outputPath, defaultApkgFilename);
  }
  return outputPath;
}

/**
 * Persists the merged stage-3 JSON and compiles it to an Anki .apkg package.
 * Returns true on success, false on failure (also flips state.hasFailures).
 */
async function writeAndCompileOutput({
  mergedTopics,
  results,
  runId,
  createdAtIso,
  outputDir,
  outputPath,
  deckName,
  subject,
  source,
  config,
  state,
}) {
  if (!mergedTopics.length) return false;

  // fs.mkdir with { recursive: true } is idempotent, so we don't need a
  // pre-flight existsSync guard.
  fs.mkdirSync(outputDir, { recursive: true });
  const safeIsoDate = createdAtIso.replace(/[:.]/g, '-');
  const jsonPath = path.join(outputDir, `${safeIsoDate}_${runId}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify(mergedTopics, null, 2), 'utf8');
  for (const res of results) res.jsonPath = jsonPath;

  const apkgPath = resolveApkgOutputPath(outputPath, outputDir, `${safeIsoDate}_${runId}.apkg`);

  try {
    logger.info`Compiling deck for run: ${runId}`;
    await spawnCompiler(jsonPath, apkgPath, {
      deckName,
      subject,
      source,
      timeout: config?.global?.compiler_timeout,
    });
    for (const res of results) res.apkgPath = apkgPath;
    return true;
  } catch (err) {
    logger.error`Compilation failed for run ${runId}: ${err}`;
    state.hasFailures = true;
    return false;
  }
}

/**
 * Resolves the initial run state: either reopens a prior run for resume or
 * creates a brand-new run record. Returns { runId, createdAtIso, completedQuestions, completedStage3Results }.
 */
function resolveRunState({ resumeRunId, config, subject, cardType, dryRun }) {
  if (resumeRunId) {
    const existingRun = getRun(resumeRunId);
    if (!existingRun) {
      throw new Error(`Run with ID "${resumeRunId}" not found in database.`);
    }
    if (!dryRun) updateRunStatus(resumeRunId, 'running');
    return {
      runId: resumeRunId,
      createdAtIso:
        existingRun.created_at || Temporal.Now.instant().toString({ fractionalSecondDigits: 3 }),
      completedQuestions: getCompletedQuestions(resumeRunId),
      completedStage3Results: getCompletedStage3Results(resumeRunId),
    };
  }

  const runId = crypto.randomUUID();
  const createdAtIso = Temporal.Now.instant().toString({ fractionalSecondDigits: 3 });
  if (!dryRun) {
    const pipelineConfig = config.pipeline || {};
    const providersConfig = config.providers || {};
    const configHash = crypto.hash(
      'sha256',
      JSON.stringify({ pipeline: pipelineConfig, providers: providersConfig }),
      'hex',
    );
    createRun({
      runId,
      subject,
      cardType,
      status: 'running',
      configHash,
      createdAt: createdAtIso,
    });
  }
  return {
    runId,
    createdAtIso,
    completedQuestions: new Set(),
    completedStage3Results: new Map(),
  };
}

function getTopicConcurrency(config) {
  const value = config.global?.topic_concurrency;
  if (typeof value !== 'number' || value < 1 || Number.isNaN(value)) return 1;
  return value;
}

/**
 * Collapses per-question results into the (results, mergedTopics) outputs
 * that the rest of the pipeline consumes.
 *
 * Exported for direct unit testing.
 */
export function collectResults(taskResults) {
  const results = [];
  const mergedTopics = [];
  for (const res of taskResults) {
    if (!res) continue;
    if (res.failure || res.error) continue;
    if (res.dryRun) {
      results.push({ questionId: res.questionId, dryRun: true });
      continue;
    }
    if (res.postProcessedResult) {
      mergedTopics.push(res.postProcessedResult);
    }
    if (res.skipped) {
      results.push({ questionId: res.questionId, skipped: true });
    } else {
      results.push({ questionId: res.questionId });
    }
  }
  return { results, mergedTopics };
}

function ensureDatabaseInitialized(config) {
  try {
    getDb();
    return false;
  } catch (_err) {
    initDatabase(resolveDbPath(config));
    return true;
  }
}

function dispatchQuestions(questions, args) {
  const { context, limit, completedQuestions, completedStage3Results, dryRun, state } = args;
  return Promise.all(
    questions.map((question) =>
      limit(() =>
        processQuestion(
          question,
          context,
          completedQuestions,
          completedStage3Results,
          dryRun,
          state,
        ),
      ),
    ),
  );
}

function validatePipelineInput({ config, questions }) {
  if (!config) {
    throw new Error('Configuration object is required.');
  }
  if (!Array.isArray(questions)) {
    throw new Error('Questions parameter must be an array.');
  }
}

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
  validatePipelineInput({ config, questions });

  const dbInitialized = ensureDatabaseInitialized(config);

  try {
    const { runId, createdAtIso, completedQuestions, completedStage3Results } = resolveRunState({
      resumeRunId,
      config,
      subject,
      cardType,
      dryRun,
    });

    const context = createPipelineContext({
      config,
      keys,
      prompts,
      runId,
      subject,
      cardType,
      maxEnforcementRetries,
    });

    const state = { hasFailures: false };
    const limit = pLimit(getTopicConcurrency(config));

    const taskResults = await dispatchQuestions(questions, {
      context,
      limit,
      completedQuestions,
      completedStage3Results,
      dryRun,
      state,
    });

    const { results, mergedTopics } = collectResults(taskResults);

    if (!dryRun) {
      await writeAndCompileOutput({
        mergedTopics,
        results,
        runId,
        createdAtIso,
        outputDir,
        outputPath,
        deckName,
        subject,
        source,
        config,
        state,
      });
    }

    if (!dryRun) {
      const finalStatus = state.hasFailures ? 'failed' : 'completed';
      updateRunStatus(runId, finalStatus);
    }

    return { runId, results, hasFailures: state.hasFailures };
  } finally {
    if (dbInitialized) {
      closeDatabase();
    }
  }
}
