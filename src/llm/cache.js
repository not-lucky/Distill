import crypto from 'node:crypto';

export function computeCacheKey({ provider, model, messages, temperature, schema }) {
  const data = JSON.stringify({
    provider,
    model,
    messages,
    temperature: temperature !== undefined ? temperature : null,
    schema: schema !== undefined ? schema : null,
  });
  return crypto.hash('sha256', data, 'hex');
}

export function computePromptHash(messages) {
  const data = JSON.stringify(messages);
  return crypto.hash('sha256', data, 'hex');
}
