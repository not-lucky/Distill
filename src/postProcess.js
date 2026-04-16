/**
 * Normalizes all tags on cards by removing spaces.
 * Only tags are normalized (not card_type).
 *
 * @param {Array<Object>} cards List of card objects.
 * @returns {Array<Object>} The cards list with normalized tags.
 */
export function normalizeTags(cards) {
  if (!Array.isArray(cards)) return [];

  // Return a new array of objects to maintain immutability and avoid mutating parameters.
  return cards.map((card) => {
    if (!card) return card;
    if (Array.isArray(card.tags)) {
      const newTags = card.tags.map((tag) => {
        if (typeof tag === 'string') {
          // Remove all spaces/whitespace from tag strings (e.g. "Trade Off" -> "TradeOff")
          return tag.replace(/\s+/g, '');
        }
        return tag;
      });
      return { ...card, tags: newTags };
    }
    return { ...card };
  });
}

/**
 * Normalizes question text for deduplication comparison by:
 * - Converting to lowercase
 * - Stripping all punctuation and whitespace
 *
 * @param {string} text Question/front text.
 * @returns {string} Normalized string.
 */
export function normalizeQuestion(text) {
  if (typeof text !== 'string') return '';
  // Match the logic in verifyContentLoss: lowercase, strip all non-alphanumeric characters.
  return text.toLowerCase().replace(/[^a-z0-9]/g, '');
}

/**
 * Deduplicates cards by comparing normalized question/front text.
 * If a duplicate is found within the list, the one with the longer explanation is kept.
 * Preserves the relative order of the first occurrence of each unique card.
 *
 * @param {Array<Object>} cards List of card objects.
 * @returns {Array<Object>} Deduplicated list of cards.
 */
export function deduplicateCards(cards) {
  if (!Array.isArray(cards)) return [];
  const seen = new Map(); // key: normalized front -> value: { card, index }

  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    if (!card) continue;
    const norm = normalizeQuestion(card.front);
    const explanationLength = typeof card.explanation === 'string'
      ? card.explanation.length
      : 0;

    if (seen.has(norm)) {
      const existing = seen.get(norm);
      const existingLength = typeof existing.card.explanation === 'string'
        ? existing.card.explanation.length
        : 0;
      // Discard shorter explanation. If new is longer, overwrite but preserve index.
      if (explanationLength > existingLength) {
        seen.set(norm, { card, index: existing.index });
      }
    } else {
      // First occurrence of this unique card: record it with index to preserve order.
      seen.set(norm, { card, index: i });
    }
  }

  // Sort back to their original input sequence using the stored first-occurrence index.
  const sortedKept = Array.from(seen.values()).sort((a, b) => a.index - b.index);
  return sortedKept.map((item) => ({ ...item.card }));
}

/**
 * Injects category/problem index and name metadata into the main topic object.
 *
 * @param {Object} data Main topic object (Stage 3 JSON output).
 * @param {Object} [metadata={}] Optional metadata choices.
 * @param {string} [metadata.categoryName] Category name index label.
 * @param {number} [metadata.categoryIndex] Category chronological index.
 * @param {number} [metadata.problemIndex] Problem chronological index within the category.
 * @returns {Object} The updated topic object.
 */
export function injectMetadata(data, metadata = {}) {
  if (!data || typeof data !== 'object') return data;

  const { categoryName, categoryIndex, problemIndex } = metadata;

  // Clone data to avoid Eslint no-param-reassign error.
  const result = { ...data };

  if (categoryIndex !== undefined && categoryIndex !== null) {
    result.category_index = categoryIndex;
  }
  if (categoryName !== undefined && categoryName !== null) {
    result.category_name = categoryName;
  }
  if (problemIndex !== undefined && problemIndex !== null) {
    result.problem_index = problemIndex;
  }

  return result;
}

/**
 * Converts literal string representations of newlines ('\\n') back to actual
 * newline characters ('\n') across front, back, explanation, and MCQ options text.
 *
 * @param {Array<Object>} cards List of card objects.
 * @returns {Array<Object>} The updated cards.
 */
export function unescapeNewlines(cards) {
  if (!Array.isArray(cards)) return [];

  // Return copies to prevent reassigning parameter object properties directly.
  return cards.map((card) => {
    if (!card) return card;
    const newCard = { ...card };

    if (typeof newCard.front === 'string') {
      newCard.front = newCard.front.replace(/\\n/g, '\n');
    }
    if (typeof newCard.back === 'string') {
      newCard.back = newCard.back.replace(/\\n/g, '\n');
    }
    if (typeof newCard.explanation === 'string') {
      newCard.explanation = newCard.explanation.replace(/\\n/g, '\n');
    }
    if (Array.isArray(newCard.options)) {
      newCard.options = newCard.options.map((opt) => {
        if (typeof opt === 'string') {
          return opt.replace(/\\n/g, '\n');
        }
        return opt;
      });
    }
    return newCard;
  });
}

/**
 * Orchestrates the full post-processing pipeline for a Stage 3 concept JSON object.
 * Mutates/enriches the object and returns it.
 *
 * @param {Object} data The parsed Stage 3 JSON object.
 * @param {Object} [metadata={}] Optional category and problem metadata.
 * @returns {Object} The finalized post-processed JSON object.
 */
export function postProcess(data, metadata = {}) {
  if (!data || typeof data !== 'object') return data;

  // 1. Inject sequence metadata (returns a shallow copy)
  let result = injectMetadata(data, metadata);

  // 2. Perform card-level cleanup if cards array exists
  if (Array.isArray(result.cards)) {
    let cleanedCards = result.cards;

    // A. Clean/normalize tags (remove spaces)
    cleanedCards = normalizeTags(cleanedCards);

    // B. Deduplicate duplicate cards (case/punctuation/whitespace insensitive)
    cleanedCards = deduplicateCards(cleanedCards);

    // C. Unescape newline sequences
    cleanedCards = unescapeNewlines(cleanedCards);

    result = {
      ...result,
      cards: cleanedCards,
    };
  }

  return result;
}
