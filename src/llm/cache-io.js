import { getCache, setCache } from '../database.js';
import { getLogger } from '../logger.js';

const logger = getLogger(['providers']);

export async function checkCache(cacheKey) {
  try {
    const entry = getCache(cacheKey);
    if (entry) {
      logger.debug`Cache hit for key: ${cacheKey}`;
      return entry.response;
    }
    logger.debug`Cache miss for key: ${cacheKey}`;
    return null;
  } catch (_error) {
    logger.debug`Cache lookup ignored because DB is not initialized. Key: ${cacheKey}`;
    return null;
  }
}

export async function writeCache({ cacheKey, provider, model, promptHash, response }) {
  try {
    setCache({
      cacheKey,
      provider,
      model,
      promptHash,
      response,
    });
    logger.debug`Cache write succeeded for key: ${cacheKey}`;
  } catch (_error) {
    logger.debug`Cache write ignored because DB is not initialized. Key: ${cacheKey}`;
  }
}
