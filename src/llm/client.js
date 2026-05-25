import OpenAI from 'openai';
import { isValidTimeout } from '../config.js';

/**
 * Resolves the per-provider client timeout in seconds using these rules:
 *   1. If `providerConfig.timeout` is a positive number, use it.
 *   2. Otherwise fall back to `globalConfig.default_timeout` if positive.
 *   3. Otherwise return `null` (caller should pass `undefined` to OpenAI
 *      to disable the client-side timeout entirely).
 *
 * @param {{timeout?: unknown}} providerConfig
 * @param {{default_timeout?: unknown}} globalConfig
 * @returns {number|null} Resolved timeout in seconds, or `null` for "no timeout".
 */
export function resolveClientTimeoutSec(providerConfig, globalConfig) {
  const providerTimeout = providerConfig?.timeout;
  if (isValidTimeout(providerTimeout)) return providerTimeout;
  if (providerTimeout === 0 || providerTimeout === null) return null;
  if (isValidTimeout(globalConfig?.default_timeout)) return globalConfig.default_timeout;
  return null;
}

/**
 * Converts a resolved timeout (seconds or null) into the millisecond
 * value the OpenAI SDK expects. `null` becomes `undefined` so the SDK
 * falls back to its own (no-timeout) default.
 */
function timeoutMs(resolvedSec) {
  return resolvedSec === null ? undefined : resolvedSec * 1000;
}

export function createProviderClients(config, keys) {
  const clients = new Map();
  const declaredProviders = Object.keys(config.providers || {});

  for (const provider of declaredProviders) {
    const providerConfig = config.providers[provider] || {};
    const baseURL = providerConfig.base_url;
    const timeoutSec = resolveClientTimeoutSec(providerConfig, config.global);

    let apiKey = 'ollama';
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
      timeout: timeoutMs(timeoutSec),
    });

    clients.set(provider, client);
  }

  return clients;
}
