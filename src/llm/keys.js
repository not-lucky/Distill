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

const _keyCounters = new Map();

export function _resetKeyCounters() {
  _keyCounters.clear();
}

export function getNextKey(provider, providerKeys) {
  if (!providerKeys || provider === 'ollama_local') {
    return undefined;
  }
  if (Array.isArray(providerKeys) && providerKeys.length > 0) {
    const counter = _keyCounters.getOrInsert(provider, 0);
    const key = providerKeys[counter % providerKeys.length];
    _keyCounters.set(provider, counter + 1);
    return key;
  }
  if (typeof providerKeys === 'string' && providerKeys.trim().length > 0) {
    return providerKeys;
  }
  return undefined;
}
