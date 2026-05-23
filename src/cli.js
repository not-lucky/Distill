#!/usr/bin/env node

import { Command } from 'commander';
import { fileURLToPath } from 'url';
import { dispose } from './logger.js';
import { runAction } from './commands/run.js';
import { compileAction } from './commands/compile.js';
import { cacheAction } from './commands/cache.js';

async function exit(code) {
  try {
    await dispose();
  } catch (_) {
    // ignore
  }
  process.exit(code);
}

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
  .option(
    '--dry-run',
    'Performs file/directory scanning and config validation without executing LLM requests',
    false,
  )
  .option('-v, --verbose', 'Enable verbose logging')
  .option('-q, --quiet', 'Enable quiet logging (errors only)')
  .action(async (sourcePath, options) => {
    await runAction(sourcePath, options, exit);
  });

program
  .command('compile <json_file>')
  .description(
    'Compiles a pre-existing structured JSON file into the Anki package database format.',
  )
  .option('-o, --output <path>', 'Directory or file path for the output .apkg file')
  .option('-v, --verbose', 'Enable verbose logging')
  .option('-q, --quiet', 'Enable quiet logging (errors only)')
  .action(async (jsonFile, options) => {
    await compileAction(jsonFile, options, exit);
  });

program
  .command('cache <action>')
  .description('Manages cache SQLite DB tables. Action can be "clear" or "stats".')
  .option('-v, --verbose', 'Enable verbose logging')
  .option('-q, --quiet', 'Enable quiet logging (errors only)')
  .action(async (action, options) => {
    await cacheAction(action, options, exit);
  });

export { program };

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  program.parse(process.argv);
}
