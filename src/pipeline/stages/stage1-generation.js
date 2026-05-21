import pLimit from 'p-limit';
import { resolveProviderModel, callLLM } from '../../llm/index.js';
import { addPipelineStep, upsertQuestionEntry } from '../../database.js';
import { resolvePrompts } from '../../prompts.js';
import { getLogger } from '../../logger.js';

const logger = getLogger(['stages']);

/**
 * Returns the per-model concurrency limit for Stage 1, validating the
 * value from config is a non-negative finite number. A value of 0 means
 * "no limit" (all configured models run in parallel unthrottled).
 */
function resolveModelConcurrency(globalConfig) {
  const value = globalConfig?.model_concurrency;
  if (typeof value !== 'number' || value < 0 || Number.isNaN(value)) return 0;
  return value;
}

/**
 * Builds the user-side prompt for Stage 1. When source content is
 * supplied, the prompt embeds it directly; otherwise it falls back to
 * a topic-name-driven instruction.
 */
function buildUserPrompt({ topicName, questionId, content }) {
  if (content && content.trim().length > 0) {
    return `Source Content:\n${content}`;
  }
  const target = topicName || questionId.replace(/_/g, ' ');
  return `Please generate comprehensive flashcards for the following topic: ${target}`;
}

/**
 * Executes a single Stage 1 generation call against one model and
 * records the step + question outcome in the database. Returns the
 * { provider, model, output } descriptor for the caller.
 */
async function runGenerationTask({ modelString, questionId, content, messages, context }) {
  const { config, keys, clients, throttledFetch, runId } = context;
  const { provider, model } = resolveProviderModel(modelString);

  logger.debug`Stage 1 parallel call started for model ${modelString} on question ${questionId}`;

  const output = await callLLM({
    provider,
    model,
    messages,
    config,
    keys,
    clients,
    throttledFetch,
  });

  addPipelineStep({
    runId,
    questionId,
    stage: 'generation',
    provider,
    model,
    inputData: JSON.stringify(messages),
    outputData: output,
  });

  upsertQuestionEntry({
    runId,
    questionId,
    currentStage: 'generation',
    inputContent: content,
    latestPrompt: JSON.stringify(messages),
    latestResponse: output,
  });

  logger.debug`Stage 1 call finished for model ${modelString} (response length: ${output.length} chars)`;
  return { provider, model, output };
}

export async function runStage1(context, { questionId, topicName, content }) {
  const { config, prompts, subject, cardType } = context;
  const models = config.pipeline?.generation?.models || [];
  if (models.length === 0) {
    throw new Error('No generation models configured in config.pipeline.generation.models');
  }

  const resolvedPrompts = resolvePrompts(prompts, subject, cardType);
  const messages = [
    { role: 'system', content: resolvedPrompts.generation },
    { role: 'user', content: buildUserPrompt({ topicName, questionId, content }) },
  ];

  const concurrency = resolveModelConcurrency(config.global);
  const limit = concurrency > 0 ? pLimit(concurrency) : null;

  logger.debug`Starting Stage 1 (Parallel Generation) for question ID: ${questionId} using ${models.length} model(s)`;

  const tasks = models.map((modelString) => {
    const task = () => runGenerationTask({ modelString, questionId, content, messages, context });
    return limit ? limit(task) : task();
  });

  return Promise.all(tasks);
}
