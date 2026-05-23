/**
 * Resolves the log level from the CLI's --verbose / --quiet options,
 * falling back to the configured default when neither is set.
 *
 * Exported separately so the run and compile commands can share it
 * without each declaring a private copy.
 */
export function resolveLogLevel(options, defaultLevel) {
  if (options.verbose) return 'debug';
  if (options.quiet) return 'error';
  return defaultLevel || 'info';
}
