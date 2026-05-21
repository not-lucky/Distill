import fs from 'fs';
import path from 'path';
import { loadConfig } from '../config.js';
import { initDatabase, closeDatabase } from '../database.js';
import { runPipeline } from '../orchestrator.js';
import {
  ingestDirectory,
  loadPreset,
  formatNamespaceComponent,
  ingestDocumentSources,
} from '../ingestion.js';
import { setupLogging, getLogger } from '../logger.js';
import { resolveLogLevel } from './_log.js';

const logger = getLogger(['cli']);

/**
 * Validates the CLI `--card-type` value and exits with a clear error
 * if the value is not one of the supported layouts.
 */
async function assertValidCardType(cardType, exit) {
  if (cardType === 'standard' || cardType === 'mcq') return;
  console.error(`Error: Invalid card-type "${cardType}". Must be 'standard' or 'mcq'.`);
  await exit(1);
}

/**
 * Pushes the resolved question + content payload into the questions array
 * with the namespace-prefixed questionId, and copies the deckPath into
 * the topic and categoryName fields so downstream stages can use them.
 */
function pushDocumentQuestion(questions, namespacePrefix, doc) {
  questions.push({
    questionId: `${namespacePrefix}::${doc.deckPath}`,
    topic: doc.deckPath,
    content: doc.content,
    categoryName: doc.deckPath,
  });
}

/**
 * Materialises a topic-mode preset's categories/topics into a flat
 * list of question descriptors. Used for both the YAML preset path
 * and the prompts.yaml subject-preset topic path.
 */
function buildTopicQuestions(presetName, categories) {
  const fmtName = formatNamespaceComponent(presetName);
  const questions = [];
  for (const cat of categories) {
    if (!cat || !Array.isArray(cat.topics)) continue;
    const fmtCat = formatNamespaceComponent(cat.name);
    for (const topic of cat.topics) {
      const fmtTopic = formatNamespaceComponent(topic);
      questions.push({
        questionId: `${fmtName}::${fmtCat}::${fmtTopic}`,
        topic,
        categoryName: cat.name,
        content: '',
      });
    }
  }
  return { questions, fmtName };
}

/**
 * Ingests the configured document sources (folder / files) for a
 * document-mode preset and converts each result into a question
 * descriptor keyed by the preset's namespace.
 */
async function buildDocumentQuestions(presetName, preset, resolvedPresetPath) {
  const fmtName = formatNamespaceComponent(presetName);
  const baseDir = resolvedPresetPath ? path.dirname(resolvedPresetPath) : process.cwd();
  const sources = {};
  if (preset.folder) sources.folder = path.resolve(baseDir, preset.folder);
  if (preset.files) sources.files = preset.files.map((f) => path.resolve(baseDir, f));
  const docs = await ingestDocumentSources(sources);
  const questions = [];
  for (const doc of docs) pushDocumentQuestion(questions, fmtName, doc);
  return { questions, sources, fmtName, mode: 'document' };
}

/**
 * Resolves a single preset object (from a YAML file or prompts.yaml
 * subject block) into question descriptors + a mode marker. Returns
 * null when the preset is empty or has no usable questions.
 */
async function presetToQuestions(preset, presetName, resolvedPresetPath) {
  if (!preset) return null;
  if (preset.mode === 'document') {
    return buildDocumentQuestions(presetName, preset, resolvedPresetPath);
  }
  if (Array.isArray(preset.categories)) {
    const { questions, fmtName } = buildTopicQuestions(presetName, preset.categories);
    return { questions, sources: null, fmtName, mode: 'topic' };
  }
  return null;
}

/**
 * Case-insensitive lookup of a subject key inside the prompts.yaml
 * subjects map. Returns the original (case-preserved) key on match,
 * or null when no entry matches.
 */
function findSubjectKey(subjects, subjectQuery) {
  if (!subjects) return null;
  const target = subjectQuery.toLowerCase();
  return Object.keys(subjects).find((k) => k.toLowerCase() === target) || null;
}

/**
 * Loads questions + active subject from a prompts.yaml subject preset.
 * Both the document and topic branches live here; the caller is left
 * with a normalised { questions, activeSubject } pair.
 */
async function loadFromSubjectPreset(sourcePath, subjectKey, subjectPreset) {
  const activeSubject = subjectKey;
  if (subjectPreset && subjectPreset.mode === 'document') {
    if (!subjectPreset.files && !subjectPreset.folder) {
      return {
        error: `Error: Subject preset "${subjectKey}" is configured in document mode but is missing both "files" and "folder" settings.`,
      };
    }
    const sources = {};
    if (subjectPreset.folder) sources.folder = path.resolve(process.cwd(), subjectPreset.folder);
    if (subjectPreset.files) {
      sources.files = subjectPreset.files.map((f) => path.resolve(process.cwd(), f));
    }
    const docs = await ingestDocumentSources(sources);
    const questions = [];
    for (const doc of docs) pushDocumentQuestion(questions, subjectKey, doc);
    return { questions, activeSubject };
  }
  if (subjectPreset && Array.isArray(subjectPreset.categories)) {
    const { questions } = buildTopicQuestions(subjectKey, subjectPreset.categories);
    return { questions, activeSubject };
  }
  return { questions: [], activeSubject };
}

/**
 * Loads questions + active subject from a path on disk: a YAML preset,
 * a directory (recursive scan), or a non-YAML file (error).
 */
async function loadFromPath(sourcePath, explicitSubject) {
  const resolvedPath = path.resolve(sourcePath);
  if (!fs.existsSync(resolvedPath)) {
    return {
      error: `Error: Source path "${sourcePath}" does not exist, and is not a known subject preset.`,
    };
  }

  const stats = fs.statSync(resolvedPath);
  if (stats.isDirectory()) {
    const questions = await ingestDirectory(resolvedPath);
    return { questions, activeSubject: explicitSubject };
  }
  if (!stats.isFile()) {
    return {
      error: `Error: Source path "${sourcePath}" is not a valid directory or preset file.`,
    };
  }
  const ext = path.extname(resolvedPath).toLowerCase();
  if (ext !== '.yaml' && ext !== '.yml') {
    return {
      error: `Error: Source path "${sourcePath}" is a file but not a YAML/YML preset file.`,
    };
  }

  const preset = await loadPreset(resolvedPath);
  const activeSubject = explicitSubject || preset.name;
  const result = await presetToQuestions(preset, preset.name, resolvedPath);
  if (!result) return { questions: [], activeSubject };

  if (result.mode === 'document') {
    if (!result.sources.folder && !result.sources.files) {
      return {
        error: `Error: Preset file "${preset.name}" is configured in document mode but is missing both "files" and "folder" settings.`,
      };
    }
    const docs = await ingestDocumentSources(result.sources);
    const questions = [];
    for (const doc of docs) pushDocumentQuestion(questions, result.fmtName, doc);
    return { questions, activeSubject };
  }
  return { questions: result.questions, activeSubject };
}

/**
 * Top-level: decides whether `sourcePath` is a known subject preset
 * or a filesystem path, then routes to the appropriate loader.
 */
async function resolveQuestions({ sourcePath, options, prompts }) {
  const subjectKey = findSubjectKey(prompts?.subjects, sourcePath);
  if (subjectKey) {
    return loadFromSubjectPreset(sourcePath, subjectKey, prompts.subjects[subjectKey]);
  }
  return loadFromPath(sourcePath, options.subject || null);
}

/**
 * Initialises the SQLite database at the configured path and runs the
 * full pipeline. Closes the database on the way out (success or fail).
 */
async function executePipeline({ config, keys, prompts, questions, subject, cardType, options }) {
  const dbPath = path.resolve(process.cwd(), config.global.cache_db_path || './llm2deck.db');
  initDatabase(dbPath);

  const result = await runPipeline({
    config,
    keys,
    prompts,
    questions,
    subject: subject || '',
    cardType,
    resumeRunId: options.resume || null,
    dryRun: !!options.dryRun,
    outputPath: null,
    outputDir: path.resolve(process.cwd(), config.global.output_dir || './output'),
  });
  return result;
}

function reportPipelineResult(result, exit) {
  if (result.hasFailures) {
    console.error('Pipeline completed with failures.');
    return exit(1);
  }
  console.log('Pipeline completed successfully.');
  return exit(0);
}

export async function runAction(sourcePath, options, exit) {
  try {
    const { cardType } = options;
    await assertValidCardType(cardType, exit);

    const { config, keys, prompts } = loadConfig(options.config);
    const level = resolveLogLevel(options, config.global.log_level);
    await setupLogging({ level, logDir: config.global.log_dir || null });

    logger.debug`Starting run command with sourcePath: ${sourcePath}, cardType: ${cardType}, resume: ${options.resume}, dryRun: ${options.dryRun}`;

    const loaded = await resolveQuestions({ sourcePath, options, prompts });
    if (loaded.error) {
      console.error(loaded.error);
      await exit(1);
    }
    const { questions, activeSubject } = loaded;

    if (questions.length === 0) {
      console.error('Error: No questions/topics found to process.');
      await exit(1);
    }

    const result = await executePipeline({
      config,
      keys,
      prompts,
      questions,
      subject: activeSubject,
      cardType,
      options,
    });

    closeDatabase();
    await reportPipelineResult(result, exit);
  } catch (error) {
    console.error(`Pipeline failed: ${error.message}`);
    try {
      closeDatabase();
    } catch (_) {
      /* ignore */
    }
    await exit(1);
  }
}
