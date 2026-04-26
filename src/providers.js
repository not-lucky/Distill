import crypto from 'crypto';
import OpenAI from 'openai';
import { zodTextFormat, zodResponseFormat } from 'openai/helpers/zod';
import pLimit from 'p-limit';
import { getCache, setCache } from './database.js';

// Counter map for round-robin key rotation per provider
const _keyCounters = new Map();

/**
 * Resets the key counters (used for testing).
 */
export function _resetKeyCounters() {
  _keyCounters.clear();
}

/**
 * Computes a deterministic SHA256 hex digest for cache indexing.
 * Hashes the stringified representation of provider, model, messages, temperature, and schema.
 *
 * @param {Object} params
 * @param {string} params.provider
 * @param {string} params.model
 * @param {Array<Object>} params.messages
 * @param {number} [params.temperature]
 * @param {Object} [params.schema]
 * @returns {string} SHA256 hex hash.
 */
export function computeCacheKey({
  provider, model, messages, temperature, schema,
}) {
  const data = JSON.stringify({
    provider,
    model,
    messages,
    temperature: temperature !== undefined ? temperature : null,
    schema: schema !== undefined ? schema : null,
  });
  return crypto.createHash('sha256').update(data).digest('hex');
}

/**
 * Computes a SHA256 hex digest of just the messages array.
 *
 * @param {Array<Object>} messages
 * @returns {string} SHA256 hex hash.
 */
export function computePromptHash(messages) {
  const data = JSON.stringify(messages);
  return crypto.createHash('sha256').update(data).digest('hex');
}

/**
 * Checks the database cache for a previously saved response.
 *
 * @param {string} cacheKey
 * @returns {Promise<string|null>} The response content on hit, otherwise null.
 */
export async function checkCache(cacheKey) {
  try {
    const entry = getCache(cacheKey);
    return entry ? entry.response : null;
  } catch (error) {
    // If database is not initialized, ignore cache read
    return null;
  }
}

/**
 * Writes a response to the database cache.
 *
 * @param {Object} params
 * @param {string} params.cacheKey
 * @param {string} params.provider
 * @param {string} params.model
 * @param {string} params.promptHash
 * @param {string} params.response
 */
export async function writeCache({
  cacheKey, provider, model, promptHash, response,
}) {
  try {
    setCache({
      cacheKey, provider, model, promptHash, response,
    });
  } catch (error) {
    // If database is not initialized, ignore cache write
  }
}

/**
 * Creates OpenAI SDK client instances for each configured provider.
 *
 * @param {Object} config The system configuration object.
 * @param {Object} keys The API keys object mapping provider -> key(s).
 * @returns {Map<string, OpenAI>} Map of provider names to OpenAI clients.
 */
export function createProviderClients(config, keys) {
  const clients = new Map();
  const declaredProviders = Object.keys(config.providers || {});

  for (const provider of declaredProviders) {
    const providerConfig = config.providers[provider] || {};
    const baseURL = providerConfig.base_url;
    const timeoutSec = providerConfig.timeout || config.global.default_timeout;

    // Get the first key from configuration for initialization
    let apiKey = 'ollama'; // Default for local Ollama
    if (provider !== 'ollama_local') {
      const providerKeys = keys[provider];
      if (Array.isArray(providerKeys) && providerKeys.length > 0) {
        const [firstKey] = providerKeys;
        apiKey = firstKey;
      } else if (typeof providerKeys === 'string' && providerKeys.trim().length > 0) {
        apiKey = providerKeys;
      }
    }

    const client = new OpenAI({
      baseURL,
      apiKey,
      timeout: timeoutSec ? timeoutSec * 1000 : undefined,
    });

    clients.set(provider, client);
  }

  return clients;
}

/**
 * Creates a throttled fetcher using p-limit that enforces concurrency limits
 * and staggers request start times.
 *
 * @param {Object} config The system configuration object.
 * @returns {Function} A wrapper function that limits concurrent executions.
 */
export function createThrottledFetcher(config) {
  const concurrencyLimit = config.global.concurrency_limit || 8;
  const requestDelay = config.global.request_delay !== undefined
    ? config.global.request_delay
    : 1.0;

  const limit = pLimit(concurrencyLimit);
  let lastStartTime = 0;

  return (fn) => limit(async () => {
    const delayMs = requestDelay * 1000;
    if (delayMs > 0) {
      const now = Date.now();
      const nextStart = lastStartTime + delayMs;
      const diff = nextStart - now;

      if (diff > 0) {
        lastStartTime = nextStart;
        await new Promise((resolve) => { setTimeout(resolve, diff); });
      } else {
        lastStartTime = now;
      }
    }
    return fn();
  });
}

/**
 * Resolves a model string identifier into provider and model name.
 *
 * @param {string} modelString Model path (e.g. "openai/gpt-4o")
 * @returns {{ provider: string, model: string }} Parsed parts.
 * @throws {Error} If format is invalid.
 */
export function resolveProviderModel(modelString) {
  if (typeof modelString !== 'string') {
    throw new Error('Model identifier must be a string.');
  }
  const slashIdx = modelString.indexOf('/');
  if (slashIdx <= 0 || slashIdx === modelString.length - 1) {
    throw new Error(`Invalid model format: "${modelString}". Must be in "provider/model" format.`);
  }
  const provider = modelString.substring(0, slashIdx);
  const model = modelString.substring(slashIdx + 1);
  return { provider, model };
}

/**
 * Main entry point to invoke an LLM with caching, throttling, backoff retries, and key rotation.
 *
 * @param {Object} params
 * @param {string} params.provider
 * @param {string} params.model
 * @param {Array<Object>} params.messages
 * @param {number} [params.temperature]
 * @param {Object} [params.schema]
 * @param {Object} params.config
 * @param {Object} params.keys
 * @param {Map<string, OpenAI>} params.clients
 * @param {Function} params.throttledFetch
 * @param {number} [params.retries]
 * @returns {Promise<string>} Model response content.
 */
export async function callLLM({
  provider,
  model,
  messages,
  temperature,
  schema,
  config,
  keys,
  clients,
  throttledFetch,
  retries = 5,
}) {
  // 1. Check cache first
  const cacheKey = computeCacheKey({
    provider, model, messages, temperature, schema,
  });
  const cachedResponse = await checkCache(cacheKey);
  if (cachedResponse !== null) {
    return cachedResponse;
  }

  const client = clients.get(provider);
  if (!client) {
    throw new Error(`No initialized client found for provider "${provider}".`);
  }

  const providerConfig = config.providers[provider] || {};
  let actualTemperature = temperature;
  if (actualTemperature === undefined) {
    actualTemperature = providerConfig.temperature !== undefined
      ? providerConfig.temperature
      : 0.3;
  }

  // Check if the schema provided is a Zod schema (has safeParse function).
  const isZod = schema && typeof schema.safeParse === 'function';

  // Determine if we should use the new OpenAI Responses API.
  // This is used for OpenAI model calls that support structured text output.
  // We check if the schema is a Zod schema and if the client SDK supports Responses API.
  const isResponsesApi = isZod && client.responses && typeof client.responses.create === 'function';

  // Build the request body params.
  // The Responses API uses different parameters (input/text.format) compared to
  // standard chat completions (messages/response_format).
  const params = {
    model,
    temperature: actualTemperature,
  };

  if (isResponsesApi) {
    // For the Responses API, the prompt history goes into the 'input' parameter,
    // and the format goes into 'text.format' utilizing 'zodTextFormat'.
    params.input = messages;
    params.text = {
      format: zodTextFormat(schema, 'card_deck'),
    };
  } else {
    // Fall back to standard Chat Completions parameters.
    params.messages = messages;
    if (schema) {
      if (isZod) {
        // If it's a Zod schema but the client doesn't support the Responses API,
        // use OpenAI's zodResponseFormat helper.
        params.response_format = zodResponseFormat(schema, 'card_deck');
      } else {
        // Fall back to the traditional JSON Schema response format object.
        params.response_format = {
          type: 'json_schema',
          json_schema: schema,
        };
      }
    }
  }

  // 2. Setup options per-request including rotated key
  const options = {};
  const providerKeys = keys[provider];
  if (providerKeys && provider !== 'ollama_local') {
    if (Array.isArray(providerKeys) && providerKeys.length > 0) {
      const counter = _keyCounters.get(provider) || 0;
      options.apiKey = providerKeys[counter % providerKeys.length];
      _keyCounters.set(provider, counter + 1);
    } else if (typeof providerKeys === 'string' && providerKeys.trim().length > 0) {
      options.apiKey = providerKeys;
    }
  }

  const timeoutSec = providerConfig.timeout || config.global.default_timeout;
  if (timeoutSec) {
    options.timeout = timeoutSec * 1000;
  }

  // 3. Retry loop with exponential backoff
  let attempt = 0;
  const baseDelay = 1000;
  const maxDelay = 10000;

  while (true) {
    try {
      let content;
      if (isResponsesApi) {
        // Use Responses API client method. The resulting structured text response
        // is populated inside the `output_text` field.
        const completion = await throttledFetch(
          () => client.responses.create(params, options),
        );
        content = completion.output_text;
      } else {
        // Fall back to the traditional chat completions flow and pull content
        // from the standard chat choices array.
        const completion = await throttledFetch(
          () => client.chat.completions.create(params, options),
        );
        content = completion.choices?.[0]?.message?.content;
      }

      if (content === null || content === undefined || content.trim() === '') {
        throw new Error('Empty response payload');
      }

      // Write to cache
      const promptHash = computePromptHash(messages);
      await writeCache({
        cacheKey, provider, model, promptHash, response: content,
      });

      return content;
    } catch (error) {
      attempt++;
      if (attempt > retries) {
        throw error;
      }

      // Check if error is retryable (429, 5xx, timeouts, network errors,
      // or empty responses)
      let isRetryable = false;
      if (error.status) {
        if (error.status === 429 || error.status >= 500) {
          isRetryable = true;
        }
      } else {
        isRetryable = true;
      }

      if (!isRetryable) {
        throw error;
      }

      const delay = Math.min(baseDelay * 2 ** attempt, maxDelay);
      await new Promise((resolve) => { setTimeout(resolve, delay); });
    }
  }
}
