import { createProviderClients } from './llm/client.js';
import { createThrottledFetcher } from './llm/throttle.js';

export function createPipelineContext({
  config,
  keys,
  prompts,
  runId,
  subject = '',
  cardType = 'standard',
  maxEnforcementRetries = 3,
}) {
  const clients = createProviderClients(config, keys);
  const throttledFetch = createThrottledFetcher(config);

  return {
    config,
    keys,
    prompts: prompts || {},
    clients,
    throttledFetch,
    runId,
    subject,
    cardType,
    maxEnforcementRetries,
  };
}
