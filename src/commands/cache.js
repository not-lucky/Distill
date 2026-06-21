import path from 'node:path';
import { loadConfig } from '../config.js';
import { initDatabase, closeDatabase, clearCache, getCacheStats } from '../database.js';
import { setupLogging, getLogger } from '../logger.js';
import { resolveLogLevel } from './_log.js';

const logger = getLogger(['cli']);

export async function cacheAction(action, options, exit) {
  try {
    if (action !== 'clear' && action !== 'stats') {
      console.error(`Error: Invalid action "${action}". Must be "clear" or "stats".`);
      await exit(1);
    }

    const { config } = loadConfig();

    const level = resolveLogLevel(options, config.global.log_level);
    await setupLogging({ level, logDir: config.global.log_dir || null });

    logger.debug`Starting cache command with action: ${action}`;
    const dbPath = path.resolve(process.cwd(), config.global.cache_db_path || './distill.db');
    initDatabase(dbPath);

    if (action === 'clear') {
      clearCache();
      console.log('Cache cleared successfully.');
    } else {
      const stats = getCacheStats();
      console.log(`Total cached queries: ${stats.count}`);
    }

    closeDatabase();
    await exit(0);
  } catch (error) {
    console.error(`Cache command failed: ${error.message}`);
    try {
      closeDatabase();
    } catch (_) {
      /* ignore */
    }
    await exit(1);
  }
}
