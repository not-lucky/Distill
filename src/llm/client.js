import OpenAI from 'openai';

export function createProviderClients(config, keys) {
  const clients = new Map();
  const declaredProviders = Object.keys(config.providers || {});

  for (const provider of declaredProviders) {
    const providerConfig = config.providers[provider] || {};
    const baseURL = providerConfig.base_url;
    const timeoutSec = providerConfig.timeout || config.global.default_timeout;

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
      timeout: timeoutSec ? timeoutSec * 1000 : undefined,
    });

    clients.set(provider, client);
  }

  return clients;
}
