export function removeNullValues(obj) {
  if (Array.isArray(obj)) {
    return obj.map(removeNullValues);
  }
  if (obj !== null && typeof obj === 'object') {
    const newObj = {};
    for (const key of Object.keys(obj)) {
      if (obj[key] !== null && obj[key] !== undefined) {
        newObj[key] = removeNullValues(obj[key]);
      }
    }
    return newObj;
  }
  return obj;
}

const VALID_DIFFICULTIES = ['Basic', 'Intermediate', 'Advanced'];
const VALID_CARD_TYPES = [
  'Concept',
  'Code',
  'Procedure',
  'Syntax',
  'Behavior',
  'Constraint',
  'ErrorHandling',
  'TradeOff',
];
const VALID_CARD_FORMATS = ['Basic', 'Cloze', 'MCQ'];
const VALID_CORRECT_LETTERS = ['A', 'B', 'C', 'D'];
const DEFAULT_MCQ_OPTIONS = ['Option A', 'Option B'];
const CLOZE_FRONT_PATTERN = /\{\{c[0-9]+::/;
const TAG_PATTERN = /^[A-Za-z0-9-_/]+$/;

/**
 * Returns the last ::-separated segment of the question id, with
 * underscores replaced by spaces. Used as a fallback deck title.
 */
function deriveTitleFromQuestionId(questionId) {
  const parts = questionId.split('::');
  const lastPart = parts[parts.length - 1];
  return lastPart ? lastPart.replace(/_/g, ' ') : 'Flashcards';
}

/**
 * Populates obj.title / obj.topic / obj.difficulty with sensible
 * defaults when the model returned an empty/missing value. Idempotent.
 */
function applyDeckEnvelopeDefaults(obj, questionId) {
  if (typeof obj.title !== 'string' || !obj.title.trim()) {
    obj.title = deriveTitleFromQuestionId(questionId);
  }
  if (typeof obj.topic !== 'string' || !obj.topic.trim()) {
    obj.topic = questionId.replace(/::/g, '/');
  }
  if (!VALID_DIFFICULTIES.includes(obj.difficulty)) {
    obj.difficulty = 'Intermediate';
  }
}

/**
 * Filters card.tags to alphanumeric/dash/underscore/slash strings.
 * Returns an empty array when tags is missing or not an array.
 */
function sanitizeTags(tags) {
  if (!Array.isArray(tags)) return [];
  return tags.filter((t) => typeof t === 'string' && TAG_PATTERN.test(t));
}

/**
 * Forces the card_type to a known valid value. Falls back to "Concept".
 */
function applyCardTypeDefault(card) {
  if (!VALID_CARD_TYPES.includes(card.card_type)) {
    card.card_type = 'Concept';
  }
}

/**
 * Returns the explicit card_format, or infers one from the
 * available fields (MCQ if options+correct_answer, Cloze if the
 * front contains cloze syntax, otherwise Basic).
 */
function resolveCardFormat(card) {
  if (VALID_CARD_FORMATS.includes(card.card_format)) return card.card_format;
  if (card.options && card.correct_answer) return 'MCQ';
  if (card.front && CLOZE_FRONT_PATTERN.test(card.front)) return 'Cloze';
  return 'Basic';
}

/**
 * Strips MCQ/Cloze-only fields from a Basic card.
 */
function applyBasicShape(card) {
  delete card.options;
  delete card.correct_answer;
}

/**
 * Strips Basic/MCQ-only fields from a Cloze card.
 */
function applyClozeShape(card) {
  delete card.back;
  delete card.options;
  delete card.correct_answer;
}

/**
 * Strips the Basic-only `back` field from an MCQ card and ensures
 * the options/answer fields carry sane defaults.
 */
function applyMcqShape(card) {
  delete card.back;
  if (!Array.isArray(card.options)) {
    card.options = [...DEFAULT_MCQ_OPTIONS];
  }
  if (!VALID_CORRECT_LETTERS.includes(card.correct_answer)) {
    card.correct_answer = 'A';
  }
}

/**
 * Applies tag sanitisation, card_type defaulting, and the per-format
 * field-shape rules to a single card. Returns a shallow clone, leaving
 * the input untouched.
 */
function normalizeCard(card) {
  if (!card || typeof card !== 'object') return card;
  const c = { ...card };
  c.tags = sanitizeTags(c.tags);
  applyCardTypeDefault(c);
  c.card_format = resolveCardFormat(c);
  if (c.card_format === 'Basic') applyBasicShape(c);
  else if (c.card_format === 'Cloze') applyClozeShape(c);
  else applyMcqShape(c);
  return c;
}

// eslint-disable-next-line no-unused-vars
export function normalizeJsonObj(jsonObj, questionId, subject = '') {
  if (!jsonObj || typeof jsonObj !== 'object') {
    return jsonObj;
  }

  const obj = structuredClone(jsonObj);
  applyDeckEnvelopeDefaults(obj, questionId);

  if (Array.isArray(obj.cards)) {
    obj.cards = obj.cards.map(normalizeCard);
  }

  return obj;
}

export function cleanJsonOutput(text) {
  if (typeof text !== 'string') return '';
  let cleaned = text.trim();

  if (!cleaned.startsWith('{') && !cleaned.startsWith('[')) {
    const codeBlockMatch = cleaned.match(/```[a-z]*\s*([\s\S]*?)\s*```/i);
    if (codeBlockMatch) {
      cleaned = codeBlockMatch[1].trim();
    }
  }

  return cleaned;
}

export function parseStage2Questions(text) {
  if (typeof text !== 'string') return [];
  const lines = text.split('\n');
  const questions = [];
  for (const line of lines) {
    const trimmed = line.trim();
    const regexPattern =
      '^(?:\\*\\*|)?(?:Card\\s*\\d+\\s*:?\\s*)?' +
      '(?:Front|Q(?:uestion)?)\\s*:\\s*(?:\\*\\*|)?(.*)';
    const questionRegex = new RegExp(regexPattern, 'i');
    const match = trimmed.match(questionRegex);
    if (match) {
      let qText = match[1].trim();
      qText = qText.replace(/\*\*$/, '').trim();
      if (qText) {
        questions.push(qText);
      }
    }
  }
  return questions;
}

export function verifyContentLoss(stage2Questions, stage3Cards) {
  const missingQuestions = [];
  if (!Array.isArray(stage3Cards)) {
    return [...stage2Questions];
  }

  for (const s2Q of stage2Questions) {
    const normalizedS2 = s2Q.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (!normalizedS2) continue;

    let found = false;
    for (const card of stage3Cards) {
      if (card && typeof card.front === 'string') {
        const normalizedS3 = card.front.toLowerCase().replace(/[^a-z0-9]/g, '');
        if (normalizedS3.includes(normalizedS2) || normalizedS2.includes(normalizedS3)) {
          found = true;
          break;
        }
      }
    }
    if (!found) {
      missingQuestions.push(s2Q);
    }
  }
  return missingQuestions;
}
