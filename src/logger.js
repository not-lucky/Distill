import {
  configure,
  getConsoleSink,
  getLogger as logtapeGetLogger,
  dispose as logtapeDispose,
} from '@logtape/logtape';

/**
 * Configure LogTape logging.
 * Can be called multiple times using reset: true to update the configuration.
 *
 * @param {Object} options
 * @param {string} [options.level='info'] - Log level ('debug', 'info', etc.)
 * @param {string|null} [options.logDir=null] - Optional log folder
 */
export async function setupLogging(options = {}) {
  const { level = 'info', logDir = null } = options;

  const sinks = {
    console: getConsoleSink(),
  };

  const isTest = process.env.NODE_ENV === 'test';

  const loggers = [
    {
      category: ['llm2deck'],
      sinks: ['console'],
      lowestLevel: isTest ? null : level,
    },
    {
      category: ['logtape', 'meta'],
      sinks: ['console'],
      lowestLevel: isTest ? null : 'warning',
    },
  ];

  if (logDir) {
    try {
      const { getTimeRotatingFileSink } = await import('@logtape/file');
      sinks.file = getTimeRotatingFileSink({
        directory: logDir,
        interval: 'daily',
      });
      loggers[0].sinks.push('file');
    } catch (err) {
      console.error(`Failed to initialize file logging in directory "${logDir}":`, err);
    }
  }

  await configure({
    sinks,
    loggers,
    reset: true,
  });
}

/**
 * Get a logger for a specific subcategory under the root 'llm2deck' category.
 *
 * @param {string[]} [subcategory=[]] - Subcategory path, e.g., ['orchestrator']
 * @returns {import('@logtape/logtape').Logger} LogTape logger instance
 */
export function getLogger(subcategory = []) {
  return logtapeGetLogger(['llm2deck', ...subcategory]);
}

/**
 * Dispose of LogTape. Flushes all sinks.
 * @returns {Promise<void>}
 */
export async function dispose() {
  await logtapeDispose();
}
