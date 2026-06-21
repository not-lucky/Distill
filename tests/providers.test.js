import { vi, describe, it, expect, beforeEach, beforeAll, afterAll } from 'vitest';
import OpenAI from 'openai';
import { z } from 'zod';
import { initDatabase, closeDatabase, clearCache, getCacheStats } from '../src/database.js';
import { computeCacheKey, computePromptHash } from '../src/llm/cache.js';
import { checkCache, writeCache } from '../src/llm/cache-io.js';
import { createProviderClients, resolveClientTimeoutSec } from '../src/llm/client.js';
import { createThrottledFetcher } from '../src/llm/throttle.js';
import { resolveProviderModel, _resetKeyCounters } from '../src/llm/keys.js';
import { callLLM } from '../src/llm/caller.js';

// callLLM uses `node:timers/promises.setTimeout` for retry backoff. The
// libuv-backed timers/promises timer is not intercepted by vitest's
// `useFakeTimers` (which only fakes the JS-land global `setTimeout`), so
// we route the setTimeout export through the global. This lets
// `vi.useFakeTimers` advance the backoff sleeps and lets the
// `vi.spyOn(global, 'setTimeout')` assertions observe the scheduled
// delays.
vi.mock('node:timers/promises', async () => {
  const actual = await vi.importActual('node:timers/promises');
  return {
    ...actual,
    // Forward all positional args (delay, value, options) to the global
    // setTimeout so callers passing the optional value/options arguments
    // don't silently lose them. The global setTimeout passes extra args to
    // its callback, and Promise#resolve uses the first one as the
    // fulfillment value (and ignores the rest), which matches
    // node:timers/promises.setTimeout's contract.
    setTimeout: (...args) => new Promise((resolve) => setTimeout(resolve, ...args)),
  };
});

vi.mock('openai', () => {
  const MockOpenAI = vi.fn().mockImplementation(function mockOpenAIConstructor(options) {
    this.baseURL = options.baseURL;
    this.apiKey = options.apiKey;
    this.timeout = options.timeout;
    this.chat = {
      completions: {
        create: vi.fn(),
      },
    };
  });
  return {
    default: MockOpenAI,
    OpenAI: MockOpenAI,
  };
});

describe('Providers Module', () => {
  let config;
  let keys;

  beforeAll(() => {
    // Initialize in-memory database for caching tests
    initDatabase(':memory:');
  });

  afterAll(() => {
    closeDatabase();
  });

  beforeEach(() => {
    clearCache();
    _resetKeyCounters();
    vi.restoreAllMocks();
    vi.useRealTimers();

    // Standard mock configurations
    config = {
      global: {
        model_concurrency: 0,
        topic_concurrency: 1,
        request_delay: 0.1, // Short delay for testing
        default_timeout: 30.0,
      },
      providers: {
        openai: {
          base_url: 'https://api.openai.com/v1',
          timeout: 10.0,
          temperature: 0.3,
        },
        cerebras: {
          base_url: 'https://api.cerebras.ai/v1',
          temperature: 0.2,
        },
        ollama_local: {
          base_url: 'http://localhost:11434/v1',
          temperature: 0.0,
        },
      },
    };

    keys = {
      openai: ['key-op-1', 'key-op-2', 'key-op-3'],
      cerebras: ['key-cer-1'],
    };
  });

  describe('resolveProviderModel', () => {
    it('should parse valid model string format correctly', () => {
      expect(resolveProviderModel('openai/gpt-4o')).toEqual({
        provider: 'openai',
        model: 'gpt-4o',
      });
      expect(resolveProviderModel('ollama_local/llama3.1:latest')).toEqual({
        provider: 'ollama_local',
        model: 'llama3.1:latest',
      });
    });

    it('should throw error on invalid formats', () => {
      expect(() => resolveProviderModel('openai')).toThrow(/Invalid model format/);
      expect(() => resolveProviderModel('openai/')).toThrow(/Invalid model format/);
      expect(() => resolveProviderModel('/gpt-4o')).toThrow(/Invalid model format/);
      expect(() => resolveProviderModel(null)).toThrow(/must be a string/);
      expect(() => resolveProviderModel(123)).toThrow(/must be a string/);
    });
  });

  describe('Caching & Hashing', () => {
    it('should generate deterministic and correct cache keys', () => {
      const messages = [{ role: 'user', content: 'test message' }];
      const hash1 = computeCacheKey({
        provider: 'openai',
        model: 'gpt-4o',
        messages,
        temperature: 0.3,
        schema: { type: 'object' },
      });

      const hash2 = computeCacheKey({
        provider: 'openai',
        model: 'gpt-4o',
        messages,
        temperature: 0.3,
        schema: { type: 'object' },
      });

      expect(hash1).toBe(hash2);
      expect(hash1).toMatch(/^[a-f0-9]{64}$/);

      // Changing any parameter should yield a different key
      const hashDifferentTemp = computeCacheKey({
        provider: 'openai',
        model: 'gpt-4o',
        messages,
        temperature: 0.4,
        schema: { type: 'object' },
      });
      expect(hash1).not.toBe(hashDifferentTemp);
    });

    it('should compute prompt hash correctly', () => {
      const messages = [{ role: 'user', content: 'test message' }];
      const hash = computePromptHash(messages);
      expect(hash).toMatch(/^[a-f0-9]{64}$/);
    });

    it('should return null on checkCache cache miss and save on writeCache', async () => {
      const cacheKey = 'dummy-cache-key';
      const miss = await checkCache(cacheKey);
      expect(miss).toBeNull();

      await writeCache({
        cacheKey,
        provider: 'openai',
        model: 'gpt-4',
        promptHash: 'prompt-hash',
        response: 'cached output',
      });

      const hit = await checkCache(cacheKey);
      expect(hit).toBe('cached output');
      expect(getCacheStats().count).toBe(1);
    });

    it('should ignore cache read if database throws an error', async () => {
      closeDatabase();
      const miss = await checkCache('dummy-key');
      expect(miss).toBeNull();
      // Re-initialize for subsequent tests
      initDatabase(':memory:');
    });

    it('should ignore cache write if database throws an error', async () => {
      closeDatabase();
      await expect(
        writeCache({
          cacheKey: 'dummy-key',
          provider: 'openai',
          model: 'gpt-4',
          promptHash: 'prompt-hash',
          response: 'cached output',
        }),
      ).resolves.not.toThrow();
      initDatabase(':memory:');
    });
  });

  describe('createProviderClients', () => {
    it('should instantiate OpenAI clients correctly for configured providers', () => {
      const clients = createProviderClients(config, keys);
      expect(clients.size).toBe(3);
      expect(clients.has('openai')).toBe(true);
      expect(clients.has('cerebras')).toBe(true);
      expect(clients.has('ollama_local')).toBe(true);

      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'https://api.openai.com/v1',
          apiKey: 'key-op-1',
          timeout: 10000, // 10s * 1000
        }),
      );

      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'http://localhost:11434/v1',
          apiKey: 'ollama', // Defaults to ollama for local provider
        }),
      );
    });

    it('should handle single string API keys correctly', () => {
      const stringKeys = {
        openai: 'key-single-openai',
        cerebras: ['key-cer-1'],
      };
      createProviderClients(config, stringKeys);
      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'https://api.openai.com/v1',
          apiKey: 'key-single-openai',
        }),
      );
    });

    it('should fall back to default apiKey if keys are empty array or empty string', () => {
      const invalidKeys = {
        openai: [],
        cerebras: '   ',
      };
      createProviderClients(config, invalidKeys);
      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'https://api.openai.com/v1',
          apiKey: 'ollama',
        }),
      );
    });

    it('should handle missing providers block in config', () => {
      const configNoProviders = {
        global: {},
      };
      const clients = createProviderClients(configNoProviders, keys);
      expect(clients.size).toBe(0);
    });

    it('should fallback to empty object if provider config is null', () => {
      const configNullProvider = {
        global: {},
        providers: {
          openai: null,
        },
      };
      const clients = createProviderClients(configNullProvider, keys);
      expect(clients.size).toBe(1);
    });

    it('should not set client timeout if both provider timeout and global default_timeout are missing', () => {
      const configNoTimeout = {
        global: {},
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
          },
        },
      };
      createProviderClients(configNoTimeout, keys);
      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          timeout: undefined,
        }),
      );
    });

    it('should leave timeout undefined when global default_timeout is null', () => {
      const configNullTimeout = {
        global: { default_timeout: null },
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
          },
        },
      };
      createProviderClients(configNullTimeout, keys);
      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          timeout: undefined,
        }),
      );
    });

    it('should leave timeout undefined when global default_timeout is 0', () => {
      const configZeroTimeout = {
        global: { default_timeout: 0 },
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
          },
        },
      };
      createProviderClients(configZeroTimeout, keys);
      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          timeout: undefined,
        }),
      );
    });

    it('should leave timeout undefined when provider timeout is 0, overriding a positive global default_timeout', () => {
      const configProviderZero = {
        global: { default_timeout: 60.0 },
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
            timeout: 0,
          },
        },
      };
      createProviderClients(configProviderZero, keys);
      expect(OpenAI).toHaveBeenCalledWith(
        expect.objectContaining({
          timeout: undefined,
        }),
      );
    });
  });

  describe('resolveClientTimeoutSec', () => {
    it('returns the provider timeout when set to a positive number', () => {
      expect(resolveClientTimeoutSec({ timeout: 12.5 }, { default_timeout: 999 })).toBe(12.5);
    });

    it('falls back to the global default_timeout when provider timeout is missing', () => {
      expect(resolveClientTimeoutSec({}, { default_timeout: 30 })).toBe(30);
    });

    it('returns null when neither provider nor global timeout is set', () => {
      expect(resolveClientTimeoutSec({}, {})).toBeNull();
    });

    it('returns null when global default_timeout is null and provider has no timeout', () => {
      expect(resolveClientTimeoutSec({}, { default_timeout: null })).toBeNull();
    });

    it('returns null when global default_timeout is 0 and provider has no timeout', () => {
      expect(resolveClientTimeoutSec({}, { default_timeout: 0 })).toBeNull();
    });

    it('treats provider timeout of 0 as no timeout, overriding a positive global default_timeout', () => {
      expect(resolveClientTimeoutSec({ timeout: 0 }, { default_timeout: 30 })).toBeNull();
    });

    it('treats negative, NaN, and non-numeric provider timeouts as no timeout', () => {
      expect(resolveClientTimeoutSec({ timeout: -1 }, { default_timeout: 30 })).toBe(30);
      expect(resolveClientTimeoutSec({ timeout: Number.NaN }, { default_timeout: 30 })).toBe(30);
      expect(resolveClientTimeoutSec({ timeout: '30' }, { default_timeout: 30 })).toBe(30);
    });

    it('tolerates missing providerConfig and globalConfig arguments', () => {
      expect(resolveClientTimeoutSec(undefined, undefined)).toBeNull();
      expect(resolveClientTimeoutSec({}, undefined)).toBeNull();
      expect(resolveClientTimeoutSec(undefined, { default_timeout: 5 })).toBe(5);
    });
  });

  describe('createThrottledFetcher', () => {
    it('should not limit concurrency when request_delay is 0', async () => {
      config.global.request_delay = 0; // Disable delay for this test
      const throttledFetch = createThrottledFetcher(config);

      let activeCount = 0;
      let maxActiveCount = 0;

      const task = async () => {
        activeCount++;
        maxActiveCount = Math.max(maxActiveCount, activeCount);
        // Simulate a brief async delay
        await new Promise((resolve) => {
          setTimeout(resolve, 50);
        });
        activeCount--;
      };

      const tasks = Array.from({ length: 5 }, () => throttledFetch(task));
      await Promise.all(tasks);

      expect(maxActiveCount).toBe(5);
    });

    it('should enforce request_delay between starts of successive tasks', async () => {
      config.global.request_delay = 0.05; // 50ms delay
      const throttledFetch = createThrottledFetcher(config);

      const startTimes = [];
      const task = async () => {
        startTimes.push(Date.now());
      };

      const tasks = Array.from({ length: 3 }, () => throttledFetch(task));
      await Promise.all(tasks);

      // Verify that the time differences between starts are at least ~50ms
      const diff1 = startTimes[1] - startTimes[0];
      const diff2 = startTimes[2] - startTimes[1];

      // Use a margin of tolerance for scheduler delays (e.g. >= 40ms)
      expect(diff1).toBeGreaterThanOrEqual(40);
      expect(diff2).toBeGreaterThanOrEqual(40);
    });

    it('should fallback to default delay of 1.0 if missing in config', () => {
      const configNoConcurrency = {
        global: {},
      };
      const throttledFetch = createThrottledFetcher(configNoConcurrency);
      expect(throttledFetch).toBeTypeOf('function');
    });

    it('should not introduce delay if delayMs is not greater than 0 (e.g. request_delay is negative)', async () => {
      config.global.request_delay = -0.5;
      const throttledFetch = createThrottledFetcher(config);
      const start = Date.now();
      await throttledFetch(async () => {});
      await throttledFetch(async () => {});
      expect(Date.now() - start).toBeLessThan(100);
    });
  });

  describe('callLLM', () => {
    let clients;
    let throttledFetch;

    beforeEach(() => {
      clients = createProviderClients(config, keys);
      throttledFetch = createThrottledFetcher(config);
    });

    it('should return cached response and skip network calls on cache hit', async () => {
      const messages = [{ role: 'user', content: 'Say hello' }];
      const cacheKey = computeCacheKey({ provider: 'openai', model: 'gpt-3.5-turbo', messages });

      // Warm cache
      await writeCache({
        cacheKey,
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        promptHash: computePromptHash(messages),
        response: 'Hello from cache!',
      });

      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create');

      const result = await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toBe('Hello from cache!');
      expect(createSpy).not.toHaveBeenCalled();
    });

    it('should complete network call, cache it, and return output on cache miss', async () => {
      const messages = [{ role: 'user', content: 'Say hello' }];
      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Hello there!' } }],
      });

      const result = await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toBe('Hello there!');
      expect(createSpy).toHaveBeenCalledTimes(1);

      // Verify cached
      const cacheKey = computeCacheKey({ provider: 'openai', model: 'gpt-3.5-turbo', messages });
      const cached = await checkCache(cacheKey);
      expect(cached).toBe('Hello there!');
    });

    it('should support structured output schema validation format', async () => {
      const messages = [{ role: 'user', content: 'Get JSON' }];
      const schema = {
        name: 'test_schema',
        schema: {
          type: 'object',
          properties: { val: { type: 'string' } },
          required: ['val'],
        },
      };

      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: '{"val": "ok"}' } }],
      });

      const result = await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        schema,
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toBe('{"val": "ok"}');
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          response_format: {
            type: 'json_schema',
            json_schema: schema,
          },
        }),
        expect.any(Object),
      );
    });

    it('should cycle API keys in round-robin fashion', async () => {
      const messages = [{ role: 'user', content: 'Key check' }];
      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      // Reset caches before each call to force network requests
      for (let i = 0; i < 4; i++) {
        clearCache();
        await callLLM({
          provider: 'openai',
          model: 'gpt-3.5-turbo',
          messages,
          config,
          keys,
          clients,
          throttledFetch,
        });
      }

      // Check the keys passed in options
      expect(createSpy).toHaveBeenNthCalledWith(
        1,
        expect.any(Object),
        expect.objectContaining({ apiKey: 'key-op-1' }),
      );
      expect(createSpy).toHaveBeenNthCalledWith(
        2,
        expect.any(Object),
        expect.objectContaining({ apiKey: 'key-op-2' }),
      );
      expect(createSpy).toHaveBeenNthCalledWith(
        3,
        expect.any(Object),
        expect.objectContaining({ apiKey: 'key-op-3' }),
      );
      expect(createSpy).toHaveBeenNthCalledWith(
        4,
        expect.any(Object),
        expect.objectContaining({ apiKey: 'key-op-1' }),
      ); // wraps around
    });

    it('should throw immediately for non-retryable HTTP errors (e.g. 401 Unauthorized)', async () => {
      const messages = [{ role: 'user', content: 'Auth check' }];
      const openaiClient = clients.get('openai');

      const authError = new Error('Unauthorized');
      authError.status = 401; // Not 429 or 5xx

      const createSpy = vi
        .spyOn(openaiClient.chat.completions, 'create')
        .mockRejectedValue(authError);

      await expect(
        callLLM({
          provider: 'openai',
          model: 'gpt-3.5-turbo',
          messages,
          config,
          keys,
          clients,
          throttledFetch,
          retries: 3,
        }),
      ).rejects.toThrow('Unauthorized');

      expect(createSpy).toHaveBeenCalledTimes(1); // No retries
    });

    it('should retry with exponential backoff on retryable status codes (e.g. 429 Rate Limit)', async () => {
      vi.useFakeTimers();

      const messages = [{ role: 'user', content: 'Retry check' }];
      const openaiClient = clients.get('openai');

      const rateLimitError = new Error('Too Many Requests');
      rateLimitError.status = 429;

      const createSpy = vi
        .spyOn(openaiClient.chat.completions, 'create')
        .mockRejectedValueOnce(rateLimitError)
        .mockRejectedValueOnce(rateLimitError)
        .mockResolvedValueOnce({
          choices: [{ message: { content: 'Success after retries' } }],
        });

      // Spy on setTimeout to capture the scheduled times
      const setTimeoutSpy = vi.spyOn(global, 'setTimeout');

      const callPromise = callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys,
        clients,
        throttledFetch,
        retries: 3,
      });

      // Await tick transitions to handle the async loops
      await vi.runAllTimersAsync();
      const result = await callPromise;

      expect(result).toBe('Success after retries');
      expect(createSpy).toHaveBeenCalledTimes(3);

      // Verify exponential backoff delays (2000ms and 4000ms for attempt 1 and 2)
      // Math.min(1000 * Math.pow(2, 1), 10000) = 2000
      // Math.min(1000 * Math.pow(2, 2), 10000) = 4000
      expect(setTimeoutSpy).toHaveBeenNthCalledWith(1, expect.any(Function), 2000);
      expect(setTimeoutSpy).toHaveBeenNthCalledWith(2, expect.any(Function), 4000);
    });

    it('should retry on empty response payload', async () => {
      vi.useFakeTimers();
      const messages = [{ role: 'user', content: 'Empty check' }];
      const openaiClient = clients.get('openai');

      const createSpy = vi
        .spyOn(openaiClient.chat.completions, 'create')
        .mockResolvedValueOnce({ choices: [{ message: { content: '' } }] }) // Empty string
        .mockResolvedValueOnce({ choices: [{ message: { content: 'Not empty' } }] });

      const callPromise = callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys,
        clients,
        throttledFetch,
        retries: 3,
      });

      await vi.runAllTimersAsync();
      const result = await callPromise;

      expect(result).toBe('Not empty');
      expect(createSpy).toHaveBeenCalledTimes(2);
    });

    it('should fail after exhausting all retries', async () => {
      vi.useFakeTimers();
      const messages = [{ role: 'user', content: 'Exhaust check' }];
      const openaiClient = clients.get('openai');

      const serverError = new Error('Server Error');
      serverError.status = 502;

      const createSpy = vi
        .spyOn(openaiClient.chat.completions, 'create')
        .mockRejectedValue(serverError);

      const callPromise = callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys,
        clients,
        throttledFetch,
        retries: 2,
      });

      const assertPromise = expect(callPromise).rejects.toThrow('Server Error');

      await vi.runAllTimersAsync();

      await assertPromise;
      expect(createSpy).toHaveBeenCalledTimes(3); // Initial (1) + Retries (2) = 3 calls
    });

    it('should throw an error if calling LLM with an uninitialized provider client', async () => {
      await expect(
        callLLM({
          provider: 'non-existent-provider',
          model: 'some-model',
          messages: [{ role: 'user', content: 'test' }],
          config,
          keys,
          clients,
          throttledFetch,
        }),
      ).rejects.toThrow(/No initialized client found for provider/);
    });

    it('should use single string API key in callLLM request options', async () => {
      const messages = [{ role: 'user', content: 'String key check' }];
      const stringKeys = {
        openai: 'key-single-op',
      };

      const customClients = createProviderClients(config, stringKeys);
      const openaiClient = customClients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      const result = await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys: stringKeys,
        clients: customClients,
        throttledFetch,
      });

      expect(result).toBe('Done');
      expect(createSpy).toHaveBeenCalledWith(
        expect.any(Object),
        expect.objectContaining({ apiKey: 'key-single-op' }),
      );
    });

    it('should accept temperature parameter when passed explicitly to callLLM', async () => {
      const messages = [{ role: 'user', content: 'Temp check' }];
      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        temperature: 0.8,
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          temperature: 0.8,
        }),
        expect.any(Object),
      );
    });

    it('should fallback to 0.3 temperature if temperature is undefined in both params and provider config', async () => {
      const messages = [{ role: 'user', content: 'Temp fallback check' }];
      const configNoTemp = {
        global: { default_timeout: 10 },
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
          },
        },
      };
      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config: configNoTemp,
        keys,
        clients,
        throttledFetch,
      });

      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          temperature: 0.3,
        }),
        expect.any(Object),
      );
    });

    it('should fallback to 0.3 temperature and empty provider config if provider is not declared in config', async () => {
      const messages = [{ role: 'user', content: 'No provider config check' }];
      const configNoProvider = {
        global: { default_timeout: 10 },
        providers: {},
      };
      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config: configNoProvider,
        keys,
        clients,
        throttledFetch,
      });

      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          temperature: 0.3,
        }),
        expect.any(Object),
      );
    });

    it('should support ollama_local provider without keys in callLLM', async () => {
      const messages = [{ role: 'user', content: 'Local Ollama check' }];
      const localOllamaClient = clients.get('ollama_local');
      const createSpy = vi.spyOn(localOllamaClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done local' } }],
      });

      const result = await callLLM({
        provider: 'ollama_local',
        model: 'llama3',
        messages,
        config,
        keys: {},
        clients,
        throttledFetch,
      });

      expect(result).toBe('Done local');
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          model: 'llama3',
        }),
        expect.not.objectContaining({
          apiKey: expect.any(String),
        }),
      );
    });

    it('should not set options.apiKey if keys are empty array or empty string', async () => {
      const messages = [{ role: 'user', content: 'Empty key check' }];
      const invalidKeys = {
        openai: [],
      };
      const customClients = createProviderClients(config, invalidKeys);
      const openaiClient = customClients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys: invalidKeys,
        clients: customClients,
        throttledFetch,
      });

      expect(createSpy).toHaveBeenCalledWith(
        expect.any(Object),
        expect.not.objectContaining({ apiKey: expect.any(String) }),
      );
    });

    it('should call client.responses.create when isResponsesApi is true', async () => {
      const messages = [{ role: 'user', content: 'test schema' }];
      const dummySchema = z.object({
        cards: z.array(z.string()),
      });

      const openaiClient = clients.get('openai');
      // Temporarily mock responses object on the client
      openaiClient.responses = {
        create: vi.fn().mockResolvedValue({ output_text: '{"cards":[]}' }),
      };

      const result = await callLLM({
        provider: 'openai',
        model: 'gpt-4o-2024-08-06',
        messages,
        schema: dummySchema,
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toBe('{"cards":[]}');
      expect(openaiClient.responses.create).toHaveBeenCalledWith(
        expect.objectContaining({
          model: 'gpt-4o-2024-08-06',
          input: messages,
          text: expect.objectContaining({
            format: expect.any(Object),
          }),
        }),
        expect.any(Object),
      );

      // Clean up mock
      delete openaiClient.responses;
    });

    it('should call chat.completions.create with zodResponseFormat when client.responses is not defined', async () => {
      const messages = [{ role: 'user', content: 'test schema' }];
      const dummySchema = z.object({
        cards: z.array(z.string()),
      });

      const openaiClient = clients.get('openai');
      // Ensure client.responses is not defined
      delete openaiClient.responses;

      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: '{"cards":[]}' } }],
      });

      const result = await callLLM({
        provider: 'openai',
        model: 'gpt-4o-2024-08-06',
        messages,
        schema: dummySchema,
        config,
        keys,
        clients,
        throttledFetch,
      });

      expect(result).toBe('{"cards":[]}');
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          model: 'gpt-4o-2024-08-06',
          messages,
          response_format: expect.objectContaining({
            type: 'json_schema',
            json_schema: expect.objectContaining({
              name: 'card_deck',
            }),
          }),
        }),
        expect.any(Object),
      );
    });

    it('should call chat.completions.create when forceCompletionApi is true even if responses API exists', async () => {
      const messages = [{ role: 'user', content: 'test schema' }];
      const dummySchema = z.object({
        cards: z.array(z.string()),
      });

      const openaiClient = clients.get('openai');
      openaiClient.responses = {
        create: vi.fn().mockResolvedValue({ output_text: '{"cards":[]}' }),
      };
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: '{"cards":[]}' } }],
      });

      const result = await callLLM({
        provider: 'openai',
        model: 'gpt-4o-2024-08-06',
        messages,
        schema: dummySchema,
        config,
        keys,
        clients,
        throttledFetch,
        forceCompletionApi: true,
      });

      expect(result).toBe('{"cards":[]}');
      expect(createSpy).toHaveBeenCalledTimes(1);
      expect(openaiClient.responses.create).not.toHaveBeenCalled();

      delete openaiClient.responses;
    });

    it('should set per-request options.timeout from provider timeout', async () => {
      const messages = [{ role: 'user', content: 'Provider timeout check' }];
      const openaiClient = clients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config,
        keys,
        clients,
        throttledFetch,
      });

      // openai provider in the test fixture has timeout: 10.0 -> 10000ms
      expect(createSpy).toHaveBeenCalledWith(
        expect.any(Object),
        expect.objectContaining({ timeout: 10000 }),
      );
    });

    it('should omit per-request options.timeout when no timeout is configured anywhere', async () => {
      const messages = [{ role: 'user', content: 'No timeout check' }];
      const noTimeoutConfig = {
        global: { default_timeout: null, request_delay: 0.1 },
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
          },
        },
      };
      const localClients = createProviderClients(noTimeoutConfig, keys);
      const openaiClient = localClients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config: noTimeoutConfig,
        keys,
        clients: localClients,
        throttledFetch,
      });

      expect(createSpy).toHaveBeenCalledWith(
        expect.any(Object),
        expect.not.objectContaining({ timeout: expect.anything() }),
      );
    });

    it('should omit per-request options.timeout when global default_timeout is 0', async () => {
      const messages = [{ role: 'user', content: 'Zero timeout check' }];
      const zeroTimeoutConfig = {
        global: { default_timeout: 0, request_delay: 0.1 },
        providers: {
          openai: {
            base_url: 'https://api.openai.com/v1',
          },
        },
      };
      const localClients = createProviderClients(zeroTimeoutConfig, keys);
      const openaiClient = localClients.get('openai');
      const createSpy = vi.spyOn(openaiClient.chat.completions, 'create').mockResolvedValue({
        choices: [{ message: { content: 'Done' } }],
      });

      await callLLM({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        messages,
        config: zeroTimeoutConfig,
        keys,
        clients: localClients,
        throttledFetch,
      });

      expect(createSpy).toHaveBeenCalledWith(
        expect.any(Object),
        expect.not.objectContaining({ timeout: expect.anything() }),
      );
    });
  });
});
