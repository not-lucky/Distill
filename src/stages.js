import { resolveProviderModel, callLLM } from './providers.js';
import { addPipelineStep } from './database.js';
import { resolvePrompts } from './prompts.js';

/**
 * Executes Stage 1 of the pipeline: Parallel Generation.
 * For a given chunk/topic, queries all configured generation models in parallel.
 *
 * @param {Object} params
 * @param {string} params.runId Active execution run ID.
 * @param {string} params.questionId Unique identifier for this chunk/topic (e.g. topic name).
 * @param {string} params.content Source text content or topic description.
 * @param {string} params.deckPath The parsed double-colon deck path.
 * @param {string} params.cardType Layout format ('standard' or 'mcq').
 * @param {string} params.subject Explicit subject name passed to the pipeline.
 * @param {Object} params.prompts Loaded prompts configuration from yaml file.
 * @param {Object} params.config The merged system configuration.
 * @param {Object} params.keys Loaded API keys.
 * @param {Map<string, OpenAI>} params.clients Initialized provider clients.
 * @param {Function} params.throttledFetch Concurrency-throttled fetch wrapper.
 * @returns {Promise<Array<Object>>} Array of model responses.
 */
export async function runStage1({
  runId,
  questionId,
  content,
  cardType = 'standard',
  subject = '',
  prompts = {},
  config,
  keys,
  clients,
  throttledFetch,
}) {
  const models = config.pipeline?.generation?.models || [];
  if (models.length === 0) {
    throw new Error('No generation models configured in config.pipeline.generation.models');
  }

  const resolvedPrompts = resolvePrompts(prompts, subject, cardType);
  const systemPrompt = resolvedPrompts.generation;
  const userPrompt = `Source Content:\n${content}`;

  // Construct user messages for LLM processing
  const messages = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt },
  ];

  // Maps each configured model to an asynchronous generation promise.
  // These promises execute concurrently when resolved with Promise.all.
  const promises = models.map(async (modelString) => {
    // Resolve model identifier into provider name and specific model name
    const { provider, model } = resolveProviderModel(modelString);

    // Call the LLM provider. callLLM handles concurrency throttling,
    // network timeouts, exponential backoff retries, and API key cycling.
    const output = await callLLM({
      provider,
      model,
      messages,
      config,
      keys,
      clients,
      throttledFetch,
    });

    // Log the completed step to the pipeline_steps table.
    // This allows run auditing and run resumption (skipping already completed queries on crash).
    addPipelineStep({
      runId,
      questionId,
      stage: 'generation',
      provider,
      model,
      inputData: JSON.stringify(messages),
      outputData: output,
    });

    return { provider, model, output };
  });

  // Await execution of all concurrent model requests
  return Promise.all(promises);
}
