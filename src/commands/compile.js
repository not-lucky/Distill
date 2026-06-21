import fs from 'node:fs';
import path from 'node:path';
import { loadConfig } from '../config.js';
import { spawnCompiler } from '../pipeline/compiler.js';
import { setupLogging, getLogger } from '../logger.js';
import { resolveLogLevel } from './_log.js';

const logger = getLogger(['cli']);

/**
 * Resolves the .apkg output path: an explicit `--output` flag wins,
 * otherwise the configured output_dir is used as the default location.
 */
export function resolveOutputPath(options, config) {
  if (options.output) return options.output;
  return path.resolve(process.cwd(), config?.global?.output_dir || './output');
}

export async function compileAction(jsonFile, options, exit) {
  try {
    const resolvedJson = path.resolve(jsonFile);
    if (!fs.existsSync(resolvedJson)) {
      console.error(`Error: JSON file "${jsonFile}" does not exist.`);
      await exit(1);
    }

    const { config } = loadConfig();
    const level = resolveLogLevel(options, config.global.log_level);
    await setupLogging({ level, logDir: config.global.log_dir || null });

    logger.debug`Starting compile command with jsonFile: ${jsonFile}, outputPath: ${options.output}`;

    const outputPath = resolveOutputPath(options, config);
    console.log(`Compiling "${jsonFile}" to "${outputPath}"...`);

    const result = await spawnCompiler(resolvedJson, outputPath);
    console.log('Compilation succeeded.');
    if (result.stdout) console.log(result.stdout);
    if (result.stderr) console.error(result.stderr);
    await exit(0);
  } catch (error) {
    console.error(`Compilation failed: ${error.message}`);
    await exit(1);
  }
}
