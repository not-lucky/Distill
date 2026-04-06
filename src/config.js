import fs from 'fs';
import yaml from 'js-yaml';

const DEFAULTS = {
  global: {
    concurrency_limit: 8,
    request_delay: 1.0,
    default_timeout: 500.0,
    output_dir: './output',
    cache_db_path: './llm2deck.db',
    keys_file_path: './keys.yaml',
    prompts_file_path: './prompts.yaml',
  },
  providers: {},
  pipeline: {},
};

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
  let parsedConfig = null;

  // 1. Load and parse the config file
  try {
    if (fs.existsSync(configPath)) {
      const fileContent = fs.readFileSync(configPath, 'utf8');
      parsedConfig = yaml.load(fileContent);
      if (!parsedConfig || typeof parsedConfig !== 'object') {
        warnings.push(`Config file at ${configPath} is empty or invalid. Using defaults.`);
        parsedConfig = {};
      }
    } else {
      warnings.push(`Config file not found at ${configPath}. Using default values.`);
      parsedConfig = {};
    }
  } catch (error) {
    warnings.push(`Error reading config file at ${configPath}: ${error.message}. Using defaults.`);
    parsedConfig = {};
  }

  // 2. Merge defaults recursively
  /* v8 ignore next */
  const config = deepMerge(DEFAULTS, parsedConfig || {});

  // 3. Resolve the keys file path (argument overrides config setting)
  /* v8 ignore next */
  const resolvedKeysPath = keysPath || config.global.keys_file_path || './keys.yaml';

  // 4. Load and parse the keys file
  let keys = {};
  try {
    if (fs.existsSync(resolvedKeysPath)) {
      const fileContent = fs.readFileSync(resolvedKeysPath, 'utf8');
      const parsedKeys = yaml.load(fileContent);
      if (parsedKeys && typeof parsedKeys === 'object') {
        keys = parsedKeys;
      } else {
        warnings.push(`Keys file at ${resolvedKeysPath} is empty or invalid.`);
      }
    } else {
      warnings.push(`Keys file not found at ${resolvedKeysPath}.`);
    }
  } catch (error) {
    warnings.push(`Error reading keys file at ${resolvedKeysPath}: ${error.message}.`);
  }

  // 5. Dynamically extract all active providers referenced in the pipeline and validate them
  /* v8 ignore next */
  const activeProviders = extractActiveProviders(
    config.pipeline,
    Object.keys(config.providers || {}),
  );

  // 6. Validate that active providers have at least one non-empty API key
  for (const provider of activeProviders) {
    if (provider === 'ollama_local') {
      continue; // Local Ollama server does not require an API key
    }
    const providerKeys = keys[provider];
    let hasKey = false;
    if (Array.isArray(providerKeys)) {
      hasKey = providerKeys.some((k) => typeof k === 'string' && k.trim().length > 0);
    } else if (typeof providerKeys === 'string') {
      hasKey = providerKeys.trim().length > 0;
    }

    if (!hasKey) {
      warnings.push(`Missing API key for active provider: ${provider}`);
    }
  }

  // 7. Load and parse the prompts YAML file
  let prompts = {};
  const resolvedPromptsPath = config.global.prompts_file_path;
  try {
    if (fs.existsSync(resolvedPromptsPath)) {
      const fileContent = fs.readFileSync(resolvedPromptsPath, 'utf8');
      const parsedPrompts = yaml.load(fileContent);
      if (parsedPrompts && typeof parsedPrompts === 'object') {
        prompts = parsedPrompts;
      } else {
        warnings.push(`Prompts file at ${resolvedPromptsPath} is empty or invalid.`);
      }
    }
  } catch (error) {
    warnings.push(`Error reading prompts file at ${resolvedPromptsPath}: ${error.message}.`);
  }

  // Log warnings if not running inside a test environment
  if (warnings.length > 0 && process.env.NODE_ENV !== 'test') {
    warnings.forEach((w) => console.warn(`[Config Warning] ${w}`));
  }

  return {
    config,
    keys,
    prompts,
    warnings,
  };
}

/**
 * Recursively traverses pipeline stages to find any provider prefixes in "provider/model" format.
 * Throws an error if any model is specified in an invalid format or uses an undeclared provider.
 *
 * @param {Object} pipeline The pipeline configuration object.
 * @param {string[]} declaredProviders List of declared provider names from configuration.
 * @returns {Set<string>} Set of active provider names.
 */
function extractActiveProviders(pipeline, declaredProviders = []) {
  const providers = new Set();
  /* v8 ignore next */
  if (!pipeline || typeof pipeline !== 'object') return providers;

  function traverse(value, parentKey) {
    if (typeof value === 'string') {
      if (parentKey === 'model' || parentKey === 'models' || !parentKey) {
        const firstSlashIdx = value.indexOf('/');
        if (firstSlashIdx <= 0 || firstSlashIdx === value.length - 1) {
          throw new Error(`Invalid model format: "${value}". Must be in "provider/model" format.`);
        }
        const provider = value.substring(0, firstSlashIdx);
        const model = value.substring(firstSlashIdx + 1);
        /* v8 ignore next 3 -- Defensive guard: logically unreachable
           after the slash-index bounds check above */
        if (!provider || !model) {
          throw new Error(`Invalid model format: "${value}". Must be in "provider/model" format.`);
        }
        if (!declaredProviders.includes(provider)) {
          throw new Error(`Undeclared provider: "${provider}" referenced in model "${value}". Must be declared in the "providers" section.`);
        }
        providers.add(provider);
      }
    } else if (Array.isArray(value)) {
      for (const item of value) {
        traverse(item, parentKey);
      }
    } else if (value && typeof value === 'object') {
      for (const key of Object.keys(value)) {
        traverse(value[key], key);
      }
    }
  }

  traverse(pipeline, null);
  return providers;
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
  if (!target || typeof target !== 'object') return source;
  if (!source || typeof source !== 'object') return target;

  const result = { ...target };
  for (const key of Object.keys(source)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
      continue;
    }

    const targetVal = target[key];
    const sourceVal = source[key];

    if (sourceVal === null || sourceVal === undefined) {
      continue;
    }

    if (Array.isArray(sourceVal)) {
      result[key] = sourceVal;
    } else if (sourceVal && typeof sourceVal === 'object' && targetVal && typeof targetVal === 'object') {
      result[key] = deepMerge(targetVal, sourceVal);
    } else {
      result[key] = sourceVal;
    }
  }
  return result;
}
