import { resolveProviderModel, callLLM } from '../../llm/index.js';
import { addPipelineStep, upsertQuestionEntry } from '../../database.js';
import { resolvePrompts } from '../../prompts.js';
import { getLogger } from '../../logger.js';

const logger = getLogger(['stages']);

export async function runStage2(context, { questionId, stage1Results }) {
  const { config, keys, clients, throttledFetch, prompts, subject, cardType, runId } = context;
  const modelString = config?.pipeline?.synthesis?.model;
  if (!modelString) {
    throw new Error('No synthesis model configured in config.pipeline.synthesis.model');
  }

  if (!Array.isArray(stage1Results) || stage1Results.length === 0) {
    throw new Error('No Stage 1 results provided');
  }

  const combinedContent = stage1Results
    .map((res) => {
      if (!res || typeof res.output !== 'string') {
        throw new Error('Stage 1 result item is missing a valid string output');
      }
      const providerVal = res.provider || 'unknown-provider';
      const modelVal = res.model || 'unknown-model';
      return `--- Provider: ${providerVal}, Model: ${modelVal} ---\n${res.output}`;
    })
    .join('\n\n');

  const resolvedPrompts = resolvePrompts(prompts, subject, cardType);
  const systemPrompt = resolvedPrompts.synthesis;
  const userPrompt = `Flashcard lists to consolidate:\n\n${combinedContent}`;

  const messages = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt },
  ];

  const { provider, model } = resolveProviderModel(modelString);

  logger.debug`Starting Stage 2 (Frontier Synthesis) for ${questionId} using model ${modelString}. Input length: ${combinedContent.length} chars.`;

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
    stage: 'synthesis',
    provider,
    model,
    inputData: JSON.stringify(messages),
    outputData: output,
  });

  upsertQuestionEntry({
    runId,
    questionId,
    currentStage: 'synthesis',
    latestPrompt: JSON.stringify(messages),
    latestResponse: output,
  });

  logger.debug`Stage 2 synthesis finished for ${questionId}. Output length: ${output.length} chars.`;

  return output;
}
