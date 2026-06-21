import { setTimeout as sleep } from 'node:timers/promises';
import { zodTextFormat, zodResponseFormat } from 'openai/helpers/zod';
import { getLogger } from '../logger.js';
import { isValidTimeout } from '../config.js';
import { resolveClientTimeoutSec } from './client.js';
import { computeCacheKey, computePromptHash } from './cache.js';
import { checkCache, writeCache } from './cache-io.js';
import { getNextKey } from './keys.js';

const logger = getLogger(['providers']);

const DEFAULT_TEMPERATURE = 0.3;
const MAX_RETRY_DELAY_MS = 10000;
const BASE_RETRY_DELAY_MS = 1000;

/**
 * Returns the temperature to use for a request, falling back through
 * the explicit argument, the provider config, and finally a hard default.
 */
function resolveTemperature(temperature, providerConfig) {
  if (temperature !== undefined) return temperature;
  if (providerConfig.temperature !== undefined) return providerConfig.temperature;
  return DEFAULT_TEMPERATURE;
}

/**
 * Detects whether the request should target the Responses API (Zod schema +
 * client capability + not forced to legacy completions).
 */
function shouldUseResponsesApi({ schema, client, forceCompletionApi }) {
  if (!schema || typeof schema.safeParse !== 'function') return false;
  if (forceCompletionApi) return false;
  return Boolean(client.responses && typeof client.responses.create === 'function');
}

/**
 * Builds the Responses-API request payload (input + text.format).
 */
function buildResponsesParams({ model, temperature, messages, schema }) {
  return {
    model,
    temperature,
    input: messages,
    text: { format: zodTextFormat(schema, 'card_deck') },
  };
}

/**
 * Builds the chat.completions request payload, including response_format
 * when a schema is provided (Zod or raw JSON Schema).
 */
function buildChatCompletionsParams({ model, temperature, messages, schema }) {
  const params = { model, temperature, messages };
  if (!schema) return params;
  if (typeof schema.safeParse === 'function') {
    params.response_format = zodResponseFormat(schema, 'card_deck');
  } else {
    params.response_format = { type: 'json_schema', json_schema: schema };
  }
  return params;
}

/**
 * Resolves the per-call client options: rotated API key (if any) and
 * a millisecond timeout derived from the provider/global config.
 *
 * A resolved timeout of `null` (no timeout configured) results in the
 * `timeout` key being omitted from the per-request options so the OpenAI
 * SDK falls back to its own no-timeout default.
 */
function buildRequestOptions({ provider, providerKeys, providerConfig, globalConfig }) {
  const options = {};
  const rotatedKey = getNextKey(provider, providerKeys);
  if (rotatedKey !== undefined) options.apiKey = rotatedKey;

  const resolvedSec = resolveClientTimeoutSec(providerConfig, globalConfig);
  if (isValidTimeout(resolvedSec)) {
    options.timeout = resolvedSec * 1000;
  }

  return options;
}

/**
 * Extracts the textual content from either a Responses API completion
 * (output_text) or a chat.completions completion (choices[0].message.content).
 */
function extractContent(completion, isResponsesApi) {
  if (isResponsesApi) return completion.output_text;
  return completion.choices?.[0]?.message?.content;
}

/**
 * Dispatches a single LLM call through the supplied throttle wrapper
 * and returns the response content. Throws on empty payloads so the
 * retry loop can decide whether to back off.
 */
async function invokeLlmOnce({ client, params, options, isResponsesApi, throttledFetch }) {
  const completion = isResponsesApi
    ? await throttledFetch(() => client.responses.create(params, options))
    : await throttledFetch(() => client.chat.completions.create(params, options));
  const content = extractContent(completion, isResponsesApi);
  if (content === null || content === undefined || content.trim() === '') {
    throw new Error('Empty response payload');
  }
  return content;
}

/**
 * Heuristic retry classifier. HTTP 429 and 5xx are retryable;
 * everything else that surfaces a `.status` is treated as terminal.
 * Errors without a `.status` (network, parse, etc.) are retried.
 */
function isRetryableError(error) {
  if (error.status) {
    return error.status === 429 || error.status >= 500;
  }
  return true;
}

/**
 * Exponential backoff with a hard cap. Each attempt doubles the
 * previous delay, starting at 1s and topping out at 10s.
 */
function computeBackoffDelay(attempt) {
  return Math.min(BASE_RETRY_DELAY_MS * 2 ** attempt, MAX_RETRY_DELAY_MS);
}

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
  forceCompletionApi = false,
}) {
  const cacheKey = computeCacheKey({ provider, model, messages, temperature, schema });
  const cachedResponse = await checkCache(cacheKey);
  if (cachedResponse !== null) {
    return cachedResponse;
  }

  const client = clients.get(provider);
  if (!client) {
    throw new Error(`No initialized client found for provider "${provider}".`);
  }

  const providerConfig = config.providers[provider] || {};
  const isResponsesApi = shouldUseResponsesApi({ schema, client, forceCompletionApi });
  const actualTemperature = resolveTemperature(temperature, providerConfig);

  const paramBuilder = isResponsesApi ? buildResponsesParams : buildChatCompletionsParams;
  const params = paramBuilder({
    model,
    temperature: actualTemperature,
    messages,
    schema,
  });
  const options = buildRequestOptions({
    provider,
    providerKeys: keys[provider],
    providerConfig,
    globalConfig: config.global,
  });

  const promptHash = computePromptHash(messages);
  logger.debug`Calling LLM [${provider}/${model}] (Responses API: ${isResponsesApi}) with prompt hash: ${promptHash}, temp: ${actualTemperature}`;

  let attempt = 0;
  while (true) {
    try {
      logger.debug`LLM Attempt ${attempt + 1}/${retries + 1} for [${provider}/${model}]...`;
      const content = await invokeLlmOnce({
        client,
        params,
        options,
        isResponsesApi,
        throttledFetch,
      });
      logger.debug`LLM [${provider}/${model}] call succeeded on attempt ${attempt + 1}. Response length: ${content.length} chars.`;

      await writeCache({ cacheKey, provider, model, promptHash, response: content });
      return content;
    } catch (error) {
      attempt++;
      if (attempt > retries) {
        logger.debug`LLM [${provider}/${model}] all attempts failed. Error: ${error.message}`;
        throw error;
      }
      if (!isRetryableError(error)) {
        logger.debug`LLM [${provider}/${model}] failed with non-retryable error: ${error.message}`;
        throw error;
      }
      const delay = computeBackoffDelay(attempt);
      logger.debug`LLM [${provider}/${model}] attempt ${attempt} failed with retryable error: ${error.message}. Retrying in ${delay}ms...`;
      await sleep(delay);
    }
  }
}
