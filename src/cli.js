#!/usr/bin/env node
/* eslint-disable no-console */

import { Command } from 'commander';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { loadConfig } from './config.js';
import {
  initDatabase,
  closeDatabase,
  clearCache,
  getCacheStats,
} from './database.js';
import { runPipeline, spawnCompiler } from './orchestrator.js';
import { ingestDirectory, loadPreset, formatNamespaceComponent } from './ingestion.js';

const program = new Command();

program
  .name('llm2deck')
  .description('LLM2Deck: LLM-powered flashcard generation pipeline')
  .version('1.0.0');

program
  .command('run <source_path>')
  .description('Initiates card generation pipelines for presets or local files.')
  .option('--config <path>', 'Path to custom configuration YAML', './config.yaml')
  .option('--card-type <type>', 'Sets target card generation layout (standard|mcq)', 'standard')
  .option('--subject <subject>', 'Explicitly specifies the subject preset from prompts.yaml')
  .option('--resume <run_id>', 'Resumes an interrupted run')
  .option('--dry-run', 'Performs file/directory scanning and config validation without executing LLM requests', false)
  .action(async (sourcePath, options) => {
    try {
      const { cardType } = options;
      if (cardType !== 'standard' && cardType !== 'mcq') {
        console.error(`Error: Invalid card-type "${cardType}". Must be 'standard' or 'mcq'.`);
        process.exit(1);
      }

      const { config, keys, prompts } = loadConfig(options.config);

      let questions = [];
      let activeSubject = options.subject || null;

      const subjectKey = sourcePath.toLowerCase();
      let matchedSubjectKey = null;

      if (prompts && prompts.subjects) {
        matchedSubjectKey = Object.keys(prompts.subjects).find(
          (k) => k.toLowerCase() === subjectKey,
        );
      }

      if (matchedSubjectKey) {
        activeSubject = activeSubject || matchedSubjectKey;
        const subjectPreset = prompts.subjects[matchedSubjectKey];
        if (subjectPreset && Array.isArray(subjectPreset.categories)) {
          for (const cat of subjectPreset.categories) {
            if (cat && Array.isArray(cat.topics)) {
              for (const topic of cat.topics) {
                const fmtCat = formatNamespaceComponent(cat.name);
                const fmtTopic = formatNamespaceComponent(topic);
                questions.push({
                  questionId: `${matchedSubjectKey}::${fmtCat}::${fmtTopic}`,
                  topic,
                  categoryName: cat.name,
                  content: '',
                });
              }
            }
          }
        }
      } else {
        const resolvedPath = path.resolve(sourcePath);
        if (!fs.existsSync(resolvedPath)) {
          console.error(`Error: Source path "${sourcePath}" does not exist, and is not a known subject preset.`);
          process.exit(1);
        }

        const stats = fs.statSync(resolvedPath);
        if (stats.isDirectory()) {
          questions = await ingestDirectory(resolvedPath);
        } else if (stats.isFile()) {
          const ext = path.extname(resolvedPath).toLowerCase();
          if (ext === '.yaml' || ext === '.yml') {
            const preset = await loadPreset(resolvedPath);
            activeSubject = activeSubject || preset.name;
            if (preset.categories && Array.isArray(preset.categories)) {
              for (const cat of preset.categories) {
                if (cat && Array.isArray(cat.topics)) {
                  for (const topic of cat.topics) {
                    const fmtPresetName = formatNamespaceComponent(preset.name);
                    const fmtCat = formatNamespaceComponent(cat.name);
                    const fmtTopic = formatNamespaceComponent(topic);
                    questions.push({
                      questionId: `${fmtPresetName}::${fmtCat}::${fmtTopic}`,
                      topic,
                      categoryName: cat.name,
                      content: '',
                    });
                  }
                }
              }
            }
          } else {
            console.error(`Error: Source path "${sourcePath}" is a file but not a YAML/YML preset file.`);
            process.exit(1);
          }
        } else {
          console.error(`Error: Source path "${sourcePath}" is not a valid directory or preset file.`);
          process.exit(1);
        }
      }

      if (questions.length === 0) {
        console.error('Error: No questions/topics found to process.');
        process.exit(1);
      }

      const subjectParam = activeSubject || '';
      const dbPath = path.resolve(process.cwd(), config.global.cache_db_path || './llm2deck.db');
      initDatabase(dbPath);

      const result = await runPipeline({
        config,
        keys,
        questions,
        subject: subjectParam,
        cardType,
        resumeRunId: options.resume || null,
        dryRun: !!options.dryRun,
        outputPath: null,
        outputDir: path.resolve(process.cwd(), config.global.output_dir || './output'),
      });

      closeDatabase();

      if (result.hasFailures) {
        console.error('Pipeline completed with failures.');
        process.exit(1);
      } else {
        console.log('Pipeline completed successfully.');
        process.exit(0);
      }
    } catch (error) {
      console.error(`Pipeline failed: ${error.message}`);
      try {
        closeDatabase();
      } catch (_) {
        // ignore close error
      }
      process.exit(1);
    }
  });

program
  .command('compile <json_file>')
  .description('Compiles a pre-existing structured JSON file into the Anki package database format.')
  .option('-o, --output <path>', 'Directory or file path for the output .apkg file')
  .action(async (jsonFile, options) => {
    try {
      const resolvedJson = path.resolve(jsonFile);
      if (!fs.existsSync(resolvedJson)) {
        console.error(`Error: JSON file "${jsonFile}" does not exist.`);
        process.exit(1);
      }

      const { config } = loadConfig();
      const defaultOutputDir = path.resolve(process.cwd(), config?.global?.output_dir || './output');
      const outputPath = options.output || defaultOutputDir;

      console.log(`Compiling "${jsonFile}" to "${outputPath}"...`);
      const result = await spawnCompiler(resolvedJson, outputPath);
      console.log('Compilation succeeded.');
      if (result.stdout) console.log(result.stdout);
      if (result.stderr) console.error(result.stderr);
      process.exit(0);
    } catch (error) {
      console.error(`Compilation failed: ${error.message}`);
      process.exit(1);
    }
  });

program
  .command('cache <action>')
  .description('Manages cache SQLite DB tables. Action can be "clear" or "stats".')
  .action((action) => {
    try {
      if (action !== 'clear' && action !== 'stats') {
        console.error(`Error: Invalid action "${action}". Must be "clear" or "stats".`);
        process.exit(1);
      }

      const { config } = loadConfig();
      const dbPath = path.resolve(process.cwd(), config?.global?.cache_db_path || './llm2deck.db');
      initDatabase(dbPath);

      if (action === 'clear') {
        clearCache();
        console.log('Cache cleared successfully.');
      } else if (action === 'stats') {
        const stats = getCacheStats();
        console.log(`Total cached queries: ${stats.count}`);
      }

      closeDatabase();
      process.exit(0);
    } catch (error) {
      console.error(`Cache command failed: ${error.message}`);
      try {
        closeDatabase();
      } catch (_) {
        // ignore close error
      }
      process.exit(1);
    }
  });

// Expose program for testing
export { program };

// Run program if called directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  program.parse(process.argv);
}
