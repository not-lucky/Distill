import crypto from 'crypto';

export function computeCacheKey({ provider, model, messages, temperature, schema }) {
  const data = JSON.stringify({
    provider,
    model,
    messages,
    temperature: temperature !== undefined ? temperature : null,
    schema: schema !== undefined ? schema : null,
  });
  return crypto.createHash('sha256').update(data).digest('hex');
}

export function computePromptHash(messages) {
  const data = JSON.stringify(messages);
  return crypto.createHash('sha256').update(data).digest('hex');
}
