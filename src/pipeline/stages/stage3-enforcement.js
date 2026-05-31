import { resolveProviderModel } from '../../llm/keys.js';
import { callLLM } from '../../llm/caller.js';
import { addPipelineStep, upsertQuestionEntry } from '../../database.js';
import { resolvePrompts } from '../../prompts.js';
import { getLogger } from '../../logger.js';
import { CARD_ZOD_SCHEMA, CARD_VALIDATION_SCHEMA } from '../schemas/card-zod.js';
import { CARD_JSON_SCHEMA } from '../schemas/card-json.js';
import {
  removeNullValues,
  normalizeJsonObj,
  cleanJsonOutput,
  parseStage2Questions,
  verifyContentLoss,
} from '../validation.js';

const logger = getLogger(['stages']);

/**
 * Pulls the schema_enforcement model string from config, throwing a
 * clear error if it is missing. Centralised so callers fail fast.
 */
function resolveEnforcementModel(pipelineConfig) {
  const modelString = pipelineConfig?.schema_enforcement?.model;
  if (!modelString) {
    throw new Error(
      'No schema enforcement model configured in config.pipeline.schema_enforcement.model',
    );
  }
  return modelString;
}

/**
 * Composes the system + user message pair for an enforcement call.
 * The system message embeds the JSON Schema and an explicit "no markdown"
 * instruction; the user message carries the consolidated card list.
 */
function buildEnforcementMessages(enforcementBase, synthesisResult) {
  const systemPrompt = `${enforcementBase}\n\nYou must output a JSON object conforming strictly to this JSON Schema:\n${JSON.stringify(CARD_JSON_SCHEMA, null, 2)}\n\nIMPORTANT: Output ONLY the raw JSON string. Do NOT wrap the JSON in markdown code blocks or backticks (e.g. do NOT use \`\`\`json ... \`\`\`).`;
  return [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: `Consolidated Text Flashcard List:\n\n${synthesisResult}` },
  ];
}

/**
 * Parses the raw LLM output, applies the Zod schema, and runs the
 * content-loss audit. Returns a structured { jsonObj, errorsList } pair
 * so the caller can decide whether to retry or commit the result.
 */
function validateEnforcementOutput({ rawOutput, questionId, subject, stage2Questions }) {
  const errorsList = [];
  const cleanedOutput = cleanJsonOutput(rawOutput);
  let jsonObj;

  try {
    jsonObj = JSON.parse(cleanedOutput);
    if (jsonObj) {
      jsonObj = removeNullValues(jsonObj);
      jsonObj = normalizeJsonObj(jsonObj, questionId, subject);
    }
  } catch (parseError) {
    logger.debug`Stage 3 JSON Parsing Error: ${parseError.message}`;
    errorsList.push(`JSON Parsing Error: ${parseError.message}`);
  }

  if (jsonObj) {
    const valResult = CARD_VALIDATION_SCHEMA.safeParse(jsonObj);
    if (!valResult.success) {
      const schemaErrors = valResult.error.issues.map((issue) => {
        const pathStr = issue.path.length > 0 ? `/${issue.path.join('/')}` : '/';
        return `${pathStr}: ${issue.message}`;
      });
      errorsList.push(...schemaErrors);
    }
  }

  if (jsonObj) {
    const missing = verifyContentLoss(stage2Questions, jsonObj.cards || []);
    if (missing.length > 0) {
      errorsList.push(
        `Content Loss Audit Error: The following questions from Stage 2 are missing in the Stage 3 JSON cards array:\n${missing
          .map((q) => `- ${q}`)
          .join('\n')}`,
      );
    }
  }

  return { jsonObj, errorsList };
}

/**
 * Records a successful enforcement outcome on both the per-step audit
 * table and the per-question state table.
 */
function recordEnforcementSuccess({
  runId,
  questionId,
  provider,
  model,
  messages,
  rawOutput,
  jsonObj,
}) {
  addPipelineStep({
    runId,
    questionId,
    stage: 'enforcement',
    provider,
    model,
    inputData: JSON.stringify(messages),
    outputData: rawOutput,
  });
  upsertQuestionEntry({
    runId,
    questionId,
    currentStage: 'enforcement',
    latestPrompt: JSON.stringify(messages),
    latestResponse: rawOutput,
  });
  return jsonObj;
}

/**
 * Records a failed enforcement attempt. The step table stores the
 * raw output and the error string; the per-question table is rewound
 * to 'synthesis' so a future resume re-runs from the synthesis stage.
 */
function recordEnforcementFailure({
  runId,
  questionId,
  provider,
  model,
  messages,
  rawOutput,
  errorString,
}) {
  addPipelineStep({
    runId,
    questionId,
    stage: 'enforcement',
    provider,
    model,
    inputData: JSON.stringify(messages),
    outputData: rawOutput,
    status: 'failed',
    errors: errorString,
  });
  upsertQuestionEntry({
    runId,
    questionId,
    currentStage: 'synthesis',
    latestPrompt: JSON.stringify(messages),
    latestResponse: rawOutput,
    errors: errorString,
  });
}

/**
 * Appends a corrective user/assistant exchange so the next LLM turn
 * sees both the previous (bad) output and a precise list of fixes.
 */
function appendRetryFeedback(messages, rawOutput, lastErrorMsg) {
  messages.push({ role: 'assistant', content: rawOutput });
  messages.push({
    role: 'user',
    content: `Your previous output did not conform to the schema or failed the Content Loss Audit. Please fix the following errors and output the entire, corrected JSON matching the schema:\n\n${lastErrorMsg}`,
  });
}

export async function runStage3(context, { questionId, synthesisResult }) {
  const {
    config,
    keys,
    clients,
    throttledFetch,
    prompts,
    subject,
    cardType,
    runId,
    maxEnforcementRetries = 5,
  } = context;

  if (typeof synthesisResult !== 'string' || !synthesisResult.trim()) {
    throw new Error('Stage 2 synthesis result is missing or empty');
  }

  const modelString = resolveEnforcementModel(config?.pipeline);
  const { provider, model } = resolveProviderModel(modelString);

  const resolvedPrompts = resolvePrompts(prompts, subject, cardType);
  const messages = buildEnforcementMessages(resolvedPrompts.enforcement, synthesisResult);
  const stage2Questions = parseStage2Questions(synthesisResult);

  const useCompletionApi = config?.pipeline?.schema_enforcement?.use_completion_api === true;

  logger.debug`Starting Stage 3 (Schema Enforcement) for ${questionId} using model ${modelString} (max retries: ${maxEnforcementRetries}, useCompletionApi: ${useCompletionApi}). Parsed Stage 2 questions: ${stage2Questions.length}`;

  let attempt = 0;
  let lastErrorMsg = '';

  while (attempt < maxEnforcementRetries) {
    attempt++;
    logger.debug`Stage 3 attempt ${attempt}/${maxEnforcementRetries} for ${questionId}...`;

    const rawOutput = await callLLM({
      provider,
      model,
      messages,
      schema: CARD_ZOD_SCHEMA,
      config,
      keys,
      clients,
      throttledFetch,
      forceCompletionApi: useCompletionApi,
    });

    const { jsonObj, errorsList } = validateEnforcementOutput({
      rawOutput,
      questionId,
      subject,
      stage2Questions,
    });

    if (errorsList.length === 0) {
      logger.debug`Stage 3 enforcement succeeded on attempt ${attempt}. Generated ${jsonObj.cards?.length} card(s).`;
      return recordEnforcementSuccess({
        runId,
        questionId,
        provider,
        model,
        messages,
        rawOutput,
        jsonObj,
      });
    }

    lastErrorMsg = errorsList.join('\n');
    recordEnforcementFailure({
      runId,
      questionId,
      provider,
      model,
      messages,
      rawOutput,
      errorString: lastErrorMsg,
    });

    logger.debug`Stage 3 attempt ${attempt} failed. Retrying... Errors:\n${lastErrorMsg}`;
    appendRetryFeedback(messages, rawOutput, lastErrorMsg);
  }

  throw new Error(
    `Stage 3 Schema Enforcement failed after ${maxEnforcementRetries} attempts.\nLast Errors:\n${lastErrorMsg}`,
  );
}
