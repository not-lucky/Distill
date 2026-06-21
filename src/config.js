import fs from 'node:fs';
import yaml from 'js-yaml';
import { getLogger } from './logger.js';

const logger = getLogger(['config']);

const DEFAULTS = {
  global: {
    model_concurrency: 0,
    topic_concurrency: 1,
    request_delay: 1.0,
    default_timeout: null,
    output_dir: './output',
    cache_db_path: './distill.db',
    keys_file_path: './keys.yaml',
    prompts_file_path: './prompts.yaml',
    log_level: 'info',
    log_dir: null,
  },
  providers: {},
  pipeline: {},
};

/**
 * Returns true when the supplied value is a positive, finite number of
 * seconds usable as a request timeout. `null`, `undefined`, `0`, and any
 * non-numeric or negative value are considered "not a valid timeout".
 */
function isValidTimeout(value) {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

/**
 * Reads a YAML file from disk and returns the parsed object.
 * Pushes a single warning to `warnings` and returns `{}` on any error.
 * Used for the config, keys, and prompts files which all share the
 * same "missing / invalid / unreadable" handling.
 */
function readYamlObject(filePath, warnings, errorContext) {
  if (!fs.existsSync(filePath)) {
    warnings.push(`${errorContext} not found at ${filePath}.`);
    return {};
  }
  let parsed;
  try {
    parsed = yaml.load(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    warnings.push(`Error reading ${errorContext.toLowerCase()} at ${filePath}: ${error.message}.`);
    return {};
  }
  if (!parsed || typeof parsed !== 'object') {
    warnings.push(`${errorContext} at ${filePath} is empty or invalid.`);
    return {};
  }
  return parsed;
}

/**
 * Loads the main config.yaml, applying the supplied default. Pushes a
 * warning and returns DEFAULTS-shaped object on any failure.
 */
function readConfigFile(configPath, warnings) {
  if (!fs.existsSync(configPath)) {
    warnings.push(`Config file not found at ${configPath}. Using default values.`);
    return {};
  }
  let parsed;
  try {
    parsed = yaml.load(fs.readFileSync(configPath, 'utf8'));
  } catch (error) {
    warnings.push(`Error reading config file at ${configPath}: ${error.message}. Using defaults.`);
    return {};
  }
  if (!parsed || typeof parsed !== 'object') {
    warnings.push(`Config file at ${configPath} is empty or invalid. Using defaults.`);
    return {};
  }
  return parsed;
}

/**
 * Returns true when the supplied provider-key field carries at least
 * one non-empty API key. Accepts both the array form (rotated keys)
 * and the legacy single-string form.
 */
function providerHasKey(providerKeys) {
  if (Array.isArray(providerKeys)) {
    return providerKeys.some((k) => typeof k === 'string' && k.trim().length > 0);
  }
  if (typeof providerKeys === 'string') {
    return providerKeys.trim().length > 0;
  }
  return false;
}

/**
 * Emits a "missing API key" warning for every active provider that
 * has no usable key. The 'ollama_local' provider is exempt because
 * it talks to a local server with no credentials.
 */
function checkProviderKeys(activeProviders, keys, warnings) {
  for (const provider of activeProviders) {
    if (provider === 'ollama_local') continue;
    if (!providerHasKey(keys[provider])) {
      warnings.push(`Missing API key for active provider: ${provider}`);
    }
  }
}

/**
 * Returns true when the supplied value is a non-empty trimmed string.
 * Used to gate "model is configured" warnings.
 */
function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Emits warnings for any missing or empty model declarations in the
 * pipeline's required stages. Generation expects an array; synthesis
 * and schema_enforcement expect a single string.
 */
function checkPipelineModels(pipeline, warnings) {
  const generation = pipeline?.generation;
  if (!generation || !Array.isArray(generation.models) || generation.models.length === 0) {
    warnings.push('Missing configuration: Pipeline stage "generation" has no models configured.');
  } else if (generation.models.some((m) => !isNonEmptyString(m))) {
    warnings.push(
      'Missing configuration: Pipeline stage "generation" contains empty or invalid model strings.',
    );
  }

  if (!pipeline?.synthesis || !isNonEmptyString(pipeline.synthesis.model)) {
    warnings.push('Missing configuration: Pipeline stage "synthesis" has no model configured.');
  }
  if (!pipeline?.schema_enforcement || !isNonEmptyString(pipeline.schema_enforcement.model)) {
    warnings.push(
      'Missing configuration: Pipeline stage "schema_enforcement" has no model configured.',
    );
  }
}

/**
 * Logs every accumulated warning in one pass, unless the process is
 * running in a test environment (so vitest stays quiet).
 */
function flushWarnings(warnings) {
  if (warnings.length === 0) return;
  if (process.env.NODE_ENV === 'test') return;
  for (const w of warnings) logger.warn`${w}`;
}

/**
 * Loads the prompts.yaml file if it exists. Unlike the config and
 * keys files, a missing prompts file is not a warning: prompts are
 * optional and the pipeline falls back to hardcoded defaults.
 */
function loadPromptsFile(promptsPath, warnings) {
  if (!fs.existsSync(promptsPath)) return {};
  let parsed;
  try {
    parsed = yaml.load(fs.readFileSync(promptsPath, 'utf8'));
  } catch (error) {
    warnings.push(`Error reading prompts file at ${promptsPath}: ${error.message}.`);
    return {};
  }
  if (!parsed || typeof parsed !== 'object') {
    warnings.push(`Prompts file at ${promptsPath} is empty or invalid.`);
    return {};
  }
  return parsed;
}

/**
 * Loads config.yaml and keys.yaml, merges with default values,
 * and validates that active pipeline providers have configured API keys.
 *
 * @param {string} configPath Path to the configuration YAML file.
 * @param {string|null} keysPath Path to the keys YAML file (overrides config global setting).
 * @returns {{ config: Object, keys: Object, prompts: Object, warnings: string[] }}
 */
export function loadConfig(configPath = './config.yaml', keysPath = null) {
  const warnings = [];
  const parsedConfig = readConfigFile(configPath, warnings);
  const config = deepMerge(DEFAULTS, parsedConfig || {});
  const resolvedKeysPath = keysPath || config.global.keys_file_path || './keys.yaml';
  const keys = readYamlObject(resolvedKeysPath, warnings, 'Keys file');

  const activeProviders = extractActiveProviders(
    config.pipeline,
    Object.keys(config.providers || {}),
  );
  checkProviderKeys(activeProviders, keys, warnings);
  checkPipelineModels(config.pipeline, warnings);

  const prompts = loadPromptsFile(config.global.prompts_file_path, warnings);
  flushWarnings(warnings);

  return { config, keys, prompts, warnings };
}

/**
 * Parses a single "provider/model" string, validating the slash is
 * neither at the start nor at the end. Throws on any malformed input
 * or undeclared provider prefix.
 */
function parseModelString(modelString, declaredProviders) {
  const firstSlashIdx = modelString.indexOf('/');
  if (firstSlashIdx <= 0 || firstSlashIdx === modelString.length - 1) {
    throw new Error(`Invalid model format: "${modelString}". Must be in "provider/model" format.`);
  }
  const provider = modelString.substring(0, firstSlashIdx);
  const model = modelString.substring(firstSlashIdx + 1);
  if (!provider || !model) {
    throw new Error(`Invalid model format: "${modelString}". Must be in "provider/model" format.`);
  }
  if (!declaredProviders.includes(provider)) {
    throw new Error(
      `Undeclared provider: "${provider}" referenced in model "${modelString}". Must be declared in the "providers" section.`,
    );
  }
  return provider;
}

/**
 * Walks a value (object / array / string) and records every provider
 * referenced under a `model` / `models` key. Throws on bad model
 * strings via parseModelString.
 */
function visitValue(value, parentKey, declaredProviders, providers) {
  if (Array.isArray(value)) {
    for (const item of value) visitValue(item, parentKey, declaredProviders, providers);
    return;
  }
  if (value && typeof value === 'object') {
    for (const key of Object.keys(value)) visitValue(value[key], key, declaredProviders, providers);
    return;
  }
  if (typeof value !== 'string') return;
  if (parentKey !== 'model' && parentKey !== 'models' && parentKey) return;
  if (!value.trim()) return;
  providers.add(parseModelString(value, declaredProviders));
}

/**
 * Recursively traverses pipeline stages to find any provider prefixes in "provider/model" format.
 * Throws an error if any model is specified in an invalid format or uses an undeclared provider.
 *
 * Exported for direct unit testing.
 *
 * @param {Object} pipeline The pipeline configuration object.
 * @param {string[]} declaredProviders List of declared provider names from configuration.
 * @returns {Set<string>} Set of active provider names.
 */
export function extractActiveProviders(pipeline, declaredProviders = []) {
  const providers = new Set();
  if (!pipeline || typeof pipeline !== 'object') return providers;
  visitValue(pipeline, null, declaredProviders, providers);
  return providers;
}

const UNSAFE_MERGE_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

/**
 * Returns true when both sides are plain objects, in which case
 * deepMerge should recurse rather than overwrite.
 */
function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Recursively merges source object into target object.
 * Returns a new merged object without mutating target or source.
 *
 * @param {Object} target
 * @param {Object} source
 * @returns {Object}
 */
export function deepMerge(target, source) {
  if (!isPlainObject(target)) return source;
  if (!isPlainObject(source)) return target;

  const result = { ...target };
  for (const key of Object.keys(source)) {
    if (UNSAFE_MERGE_KEYS.has(key)) continue;
    const sourceVal = source[key];
    if (sourceVal === null || sourceVal === undefined) continue;
    if (Array.isArray(sourceVal)) {
      result[key] = sourceVal;
    } else if (isPlainObject(sourceVal) && isPlainObject(target[key])) {
      result[key] = deepMerge(target[key], sourceVal);
    } else {
      result[key] = sourceVal;
    }
  }
  return result;
}

export { isValidTimeout };
