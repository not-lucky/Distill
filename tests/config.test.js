import {
  describe, it, expect, beforeAll, afterAll, vi,
} from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadConfig, deepMerge } from '../src/config.js';

// Absolute path to temporary test fixtures directory
const FIXTURES_DIR = path.resolve('./tests/fixtures');

describe('Configuration Loader - Edge Cases & Robustness', () => {
  // Ensure the fixtures directory exists before running tests
  beforeAll(() => {
    if (!fs.existsSync(FIXTURES_DIR)) {
      fs.mkdirSync(FIXTURES_DIR, { recursive: true });
    }
  });

  // Clean up any generated fixtures after tests finish
  afterAll(() => {
    if (fs.existsSync(FIXTURES_DIR)) {
      fs.rmSync(FIXTURES_DIR, { recursive: true, force: true });
    }
  });

  it('should fall back to defaults when config and keys files do not exist', () => {
    const nonExistentConfig = path.join(FIXTURES_DIR, 'does_not_exist_config.yaml');
    const nonExistentKeys = path.join(FIXTURES_DIR, 'does_not_exist_keys.yaml');

    const { config, keys, warnings } = loadConfig(nonExistentConfig, nonExistentKeys);

    // Verify default fallback configuration properties
    expect(config.global.concurrency_limit).toBe(8);
    expect(config.global.request_delay).toBe(1.0);
    expect(config.global.default_timeout).toBe(500.0);
    expect(config.global.output_dir).toBe('./output');
    expect(config.global.cache_db_path).toBe('./llm2deck.db');

    // Keys map should be empty
    expect(keys).toEqual({});

    // Warnings should contain file missing messages
    expect(warnings.some((w) => w.includes('Config file not found'))).toBe(true);
    expect(warnings.some((w) => w.includes('Keys file not found'))).toBe(true);
  });

  it('should successfully parse valid config and keys yaml files', () => {
    const configPath = path.join(FIXTURES_DIR, 'valid_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'valid_keys.yaml');

    const configContent = `
global:
  concurrency_limit: 4
  request_delay: 2.5
  default_timeout: 90.0
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
`;
    const keysContent = `
openai:
  - "sk-my-secret-key"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { config, keys, warnings } = loadConfig(configPath, keysPath);

    expect(config.global.concurrency_limit).toBe(4);
    expect(config.global.request_delay).toBe(2.5);
    expect(config.global.default_timeout).toBe(90.0);
    expect(config.global.output_dir).toBe('./output'); // fell back to default

    expect(keys.openai).toEqual(['sk-my-secret-key']);
    expect(warnings.length).toBe(0); // No warnings since active provider "openai" has a key
  });

  it('should load default config and keys files from project root when no arguments are provided', () => {
    // Mock the filesystem to return virtual config and keys content for the default paths
    const existsSpy = vi.spyOn(fs, 'existsSync').mockImplementation((filePath) => {
      if (filePath === './config.yaml' || filePath === './keys.yaml') {
        return true;
      }
      return false;
    });

    const readSpy = vi.spyOn(fs, 'readFileSync').mockImplementation((filePath, encoding) => {
      if (filePath === './config.yaml') {
        return `
global:
  keys_file_path: "./keys.yaml"
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
`;
      }
      if (filePath === './keys.yaml') {
        return `
openai:
  - "sk-my-key"
`;
      }
      return fs.readFileSync(filePath, encoding);
    });

    try {
      // Calling loadConfig with default arguments should read actual config.yaml and keys.yaml
      const { config, keys, warnings } = loadConfig();

      // Verify root files were loaded (should contain spec-defined values)
      expect(config.global.keys_file_path).toBe('./keys.yaml');
      expect(config.pipeline.generation.models).toContain('openai/gpt-3.5-turbo');

      // Since we initialized keys.yaml with template placeholder keys,
      // active providers should have keys
      expect(keys.openai).toBeDefined();

      // There should be no warnings in a clean base environment setup
      expect(warnings.length).toBe(0);
    } finally {
      existsSpy.mockRestore();
      readSpy.mockRestore();
    }
  });

  it('should handle empty config yaml and empty keys yaml files gracefully', () => {
    const configPath = path.join(FIXTURES_DIR, 'empty_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'empty_keys.yaml');

    // Write empty strings to simulate blank files
    fs.writeFileSync(configPath, '', 'utf8');
    fs.writeFileSync(keysPath, '', 'utf8');

    const { config, keys, warnings } = loadConfig(configPath, keysPath);

    // Should fall back to standard defaults for global config
    expect(config.global.concurrency_limit).toBe(8);
    expect(keys).toEqual({});

    // Warn about empty/invalid structures
    expect(warnings.some((w) => w.includes('empty or invalid'))).toBe(true);
  });

  it('should issue warning if active provider has missing keys', () => {
    const configPath = path.join(FIXTURES_DIR, 'warning_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'warning_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
  cerebras:
    base_url: "https://api.cerebras.ai/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
      - "cerebras/llama-3.1"
`;
    // keys file only has openai key, cerebras is missing
    const keysContent = `
openai:
  - "sk-some-key"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { keys, warnings } = loadConfig(configPath, keysPath);

    expect(keys.openai).toEqual(['sk-some-key']);
    expect(warnings.some((w) => w.includes('Missing API key for active provider: cerebras'))).toBe(true);
    expect(warnings.some((w) => w.includes('Missing API key for active provider: openai'))).toBe(false);
  });

  it('should issue warning if keys array is empty or contains only empty strings', () => {
    const configPath = path.join(FIXTURES_DIR, 'empty_key_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'empty_key_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  synthesis:
    model: "openai/gpt-4o"
`;
    const keysContent = `
openai:
  - " "
  - ""
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);

    // Warn because all keys in the list are whitespace/empty
    expect(warnings.some((w) => w.includes('Missing API key for active provider: openai'))).toBe(true);
  });

  it('should not warn if at least one key in the array is valid', () => {
    const configPath = path.join(FIXTURES_DIR, 'mixed_key_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'mixed_key_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  synthesis:
    model: "openai/gpt-4o"
`;
    const keysContent = `
openai:
  - ""
  - "sk-valid-key"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);

    // No warning should be issued because a valid API key exists in the array
    expect(warnings.length).toBe(0);
  });

  it('should successfully validate key specified as a single string instead of an array', () => {
    const configPath = path.join(FIXTURES_DIR, 'single_str_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'single_str_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  synthesis:
    model: "openai/gpt-4o"
`;
    // Key specified as a single string instead of a list
    const keysContent = `
openai: "sk-single-secret"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);

    // Valid string should satisfy validation check
    expect(warnings.length).toBe(0);
  });

  it('should not warn for local providers like ollama_local', () => {
    const configPath = path.join(FIXTURES_DIR, 'local_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'local_keys.yaml');

    const configContent = `
providers:
  ollama_local:
    base_url: "http://localhost:11434/v1"
pipeline:
  generation:
    models:
      - "ollama_local/llama3"
`;
    const keysContent = `
openai:
  - "sk-my-key"
`; // ollama_local keys not defined

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);

    // No warnings should be issued for missing ollama_local keys
    expect(warnings.length).toBe(0);
  });

  it('should throw an error for malformed model format in pipeline', () => {
    const configPath = path.join(FIXTURES_DIR, 'malformed_models_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'malformed_models_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "openai"
`;
    const keysContent = `
openai:
  - "sk-key"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    expect(() => loadConfig(configPath, keysPath)).toThrow(/Invalid model format/);
  });

  it('should throw an error for undeclared provider in pipeline model', () => {
    const configPath = path.join(FIXTURES_DIR, 'undeclared_provider_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'undeclared_provider_keys.yaml');

    const configContent = `
providers:
  cerebras:
    base_url: "https://api.cerebras.ai/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
`;
    const keysContent = `
openai:
  - "sk-key"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    expect(() => loadConfig(configPath, keysPath)).toThrow(/Undeclared provider: "openai"/);
  });

  it('should ignore file paths in pipeline configuration and not parse them as providers', () => {
    const configPath = path.join(FIXTURES_DIR, 'file_paths_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'file_paths_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
  some_custom_stage:
    template_path: "./templates/stage.txt"
    absolute_path: "/var/templates/stage.txt"
`;
    const keysContent = `
openai:
  - "sk-key"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);

    // Should not output any warnings about missing keys for "." or "templates" or "var"
    const bogusWarnings = warnings.filter((w) => w.includes('Missing API key for active provider'));
    expect(bogusWarnings.length).toBe(0);
  });

  it('should handle malformed or empty config/keys files gracefully', () => {
    const configPath = path.join(FIXTURES_DIR, 'malformed_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'malformed_keys.yaml');

    fs.writeFileSync(configPath, '!!!malformed yaml', 'utf8');
    fs.writeFileSync(keysPath, '!!!malformed yaml', 'utf8');

    const { config, warnings } = loadConfig(configPath, keysPath);

    expect(config.global.concurrency_limit).toBe(8); // fell back to default
    expect(warnings.some((w) => w.includes('Error reading config file') || w.includes('invalid'))).toBe(true);
    expect(warnings.some((w) => w.includes('Error reading keys file') || w.includes('invalid'))).toBe(true);
  });

  it('should correctly merge custom global and provider structures', () => {
    const configPath = path.join(FIXTURES_DIR, 'custom_merge_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'custom_merge_keys.yaml');

    const configContent = `
global:
  concurrency_limit: 10
  custom_field: "custom-value"
providers:
  openai:
    base_url: "https://custom.openai.api"
    extra_field: "hello"
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, '', 'utf8');

    const { config } = loadConfig(configPath, keysPath);

    // Verify fields merged correctly
    expect(config.global.concurrency_limit).toBe(10);
    expect(config.global.request_delay).toBe(1.0); // default preserved
    expect(config.global.custom_field).toBe('custom-value'); // custom field allowed
    expect(config.providers.openai.base_url).toBe('https://custom.openai.api');
    expect(config.providers.openai.extra_field).toBe('hello');
  });
});

describe('deepMerge utility', () => {
  it('should deeply merge source into target without mutating target', () => {
    const target = {
      a: 1,
      b: {
        c: 2,
        d: 3,
      },
      arr: [1, 2],
    };
    const source = {
      b: {
        d: 4,
        e: 5,
      },
      arr: [3, 4],
    };

    const merged = deepMerge(target, source);

    expect(merged).toEqual({
      a: 1,
      b: {
        c: 2,
        d: 4,
        e: 5,
      },
      arr: [3, 4],
    });

    // Verify non-mutation
    expect(target.b.d).toBe(3);
    expect(source.b.d).toBe(4);
  });

  it('should ignore null and undefined values from source', () => {
    const target = {
      a: 1,
      b: { c: 2 },
    };
    const source = {
      a: undefined,
      b: null,
    };

    const merged = deepMerge(target, source);

    expect(merged).toEqual({
      a: 1,
      b: { c: 2 },
    });
  });

  it('should prevent prototype pollution by ignoring keys like __proto__', () => {
    const target = {
      a: 1,
    };
    const source = JSON.parse('{"__proto__": {"polluted": true}, "constructor": {"prototype": {"polluted": true}}, "prototype": {"polluted": true}, "b": 2}');

    const merged = deepMerge(target, source);

    expect(merged.b).toBe(2);
    expect(merged.polluted).toBeUndefined();
    expect({}.polluted).toBeUndefined();
  });

  it('should return source when target is null, undefined, or a non-object', () => {
    const source = { a: 1 };
    expect(deepMerge(null, source)).toEqual(source);
    expect(deepMerge(undefined, source)).toEqual(source);
    expect(deepMerge('string', source)).toEqual(source);
    expect(deepMerge(42, source)).toEqual(source);
    expect(deepMerge(false, source)).toEqual(source);
  });

  it('should return target when source is null, undefined, or a non-object', () => {
    const target = { a: 1 };
    expect(deepMerge(target, null)).toEqual(target);
    expect(deepMerge(target, undefined)).toEqual(target);
    expect(deepMerge(target, 'string')).toEqual(target);
    expect(deepMerge(target, 42)).toEqual(target);
    expect(deepMerge(target, false)).toEqual(target);
  });

  it('should handle source overriding a primitive target value with an object', () => {
    const target = { a: 1, b: 'text' };
    const source = { b: { nested: true } };
    const merged = deepMerge(target, source);
    expect(merged.b).toEqual({ nested: true });
  });
});

describe('Configuration Loader - Uncovered Branch Coverage', () => {
  beforeAll(() => {
    if (!fs.existsSync(FIXTURES_DIR)) {
      fs.mkdirSync(FIXTURES_DIR, { recursive: true });
    }
  });

  afterAll(() => {
    if (fs.existsSync(FIXTURES_DIR)) {
      fs.rmSync(FIXTURES_DIR, { recursive: true, force: true });
    }
  });

  it('should handle pipeline with null/undefined/empty object gracefully (extractActiveProviders early return)', () => {
    const configPath = path.join(FIXTURES_DIR, 'null_pipeline_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'null_pipeline_keys.yaml');

    // Config with no pipeline section at all — pipeline defaults to {}
    const configContent = `
global:
  concurrency_limit: 2
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, '', 'utf8');

    const { config, warnings } = loadConfig(configPath, keysPath);
    expect(config.global.concurrency_limit).toBe(2);
    // Should not throw and should have no provider-related warnings
    const providerWarnings = warnings.filter((w) => w.includes('Missing API key'));
    expect(providerWarnings.length).toBe(0);
  });

  it('should traverse pipeline values that are numbers, booleans, or null without error', () => {
    const configPath = path.join(FIXTURES_DIR, 'mixed_pipeline_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'mixed_pipeline_keys.yaml');

    // Pipeline contains non-string, non-array, non-object values (numbers, booleans)
    // These should be silently skipped by the traverse function
    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    temperature: 0.7
    enabled: true
    max_tokens: 2048
    model: "openai/gpt-4"
`;
    const keysContent = `
openai:
  - "sk-key"
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);
    // Only the model field is parsed as a provider; numbers and booleans are skipped
    expect(warnings.length).toBe(0);
  });

  it('should log warnings via console.warn when NODE_ENV is not test', () => {
    // Missing config and keys files will generate warnings
    const originalNodeEnv = process.env.NODE_ENV;
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    try {
      process.env.NODE_ENV = 'development';
      const { warnings } = loadConfig(
        path.join(FIXTURES_DIR, 'nonexistent_config.yaml'),
        path.join(FIXTURES_DIR, 'nonexistent_keys.yaml'),
      );

      expect(warnings.length).toBeGreaterThan(0);
      // console.warn should have been called for each warning
      expect(warnSpy).toHaveBeenCalled();
      expect(warnSpy.mock.calls.some((call) => call[0].includes('[Config Warning]'))).toBe(true);
    } finally {
      process.env.NODE_ENV = originalNodeEnv;
      warnSpy.mockRestore();
    }
  });

  it('should warn for a single whitespace-only string key', () => {
    const configPath = path.join(FIXTURES_DIR, 'ws_key_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'ws_key_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  synthesis:
    model: "openai/gpt-4o"
`;
    // Key is a single whitespace string (not an array)
    const keysContent = `
openai: "   "
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);
    expect(warnings.some((w) => w.includes('Missing API key for active provider: openai'))).toBe(true);
  });

  it('should handle config that parses to a non-object value (e.g. bare string)', () => {
    const configPath = path.join(FIXTURES_DIR, 'string_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'string_config_keys.yaml');

    // A YAML file that parses to a plain string, not an object
    fs.writeFileSync(configPath, 'just a plain string', 'utf8');
    fs.writeFileSync(keysPath, '', 'utf8');

    const { config, warnings } = loadConfig(configPath, keysPath);
    expect(config.global.concurrency_limit).toBe(8); // defaults
    expect(warnings.some((w) => w.includes('empty or invalid'))).toBe(true);
  });

  it('should handle config that parses to a number', () => {
    const configPath = path.join(FIXTURES_DIR, 'number_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'number_config_keys.yaml');

    fs.writeFileSync(configPath, '42', 'utf8');
    fs.writeFileSync(keysPath, '', 'utf8');

    const { config, warnings } = loadConfig(configPath, keysPath);
    expect(config.global.concurrency_limit).toBe(8);
    expect(warnings.some((w) => w.includes('empty or invalid'))).toBe(true);
  });

  it('should handle keys file that parses to a non-object value (e.g. a string)', () => {
    const configPath = path.join(FIXTURES_DIR, 'keys_nonobj_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'keys_nonobj_keys.yaml');

    const configContent = `
global:
  concurrency_limit: 4
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, 'just a string not an object', 'utf8');

    const { keys, warnings } = loadConfig(configPath, keysPath);
    expect(keys).toEqual({});
    expect(warnings.some((w) => w.includes('empty or invalid'))).toBe(true);
  });

  it('should throw for model ending with slash (e.g. "openai/")', () => {
    const configPath = path.join(FIXTURES_DIR, 'trailing_slash_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'trailing_slash_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    model: "openai/"
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, '', 'utf8');

    expect(() => loadConfig(configPath, keysPath)).toThrow(/Invalid model format/);
  });

  it('should throw for model starting with slash (e.g. "/gpt-4")', () => {
    const configPath = path.join(FIXTURES_DIR, 'leading_slash_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'leading_slash_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    model: "/gpt-4"
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, '', 'utf8');

    expect(() => loadConfig(configPath, keysPath)).toThrow(/Invalid model format/);
  });

  it('should not warn for provider keys that are neither string nor array (e.g. number, object)', () => {
    const configPath = path.join(FIXTURES_DIR, 'nonstandard_keys_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'nonstandard_keys_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    model: "openai/gpt-4"
`;
    // Key value is a number — not a string or array, so hasKey stays false
    const keysContent = `
openai: 12345
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);
    expect(warnings.some((w) => w.includes('Missing API key for active provider: openai'))).toBe(true);
  });

  it('should handle duplicate providers in pipeline without duplication in validation', () => {
    const configPath = path.join(FIXTURES_DIR, 'dup_provider_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'dup_provider_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  stage1:
    model: "openai/gpt-4"
  stage2:
    model: "openai/gpt-3.5-turbo"
  stage3:
    models:
      - "openai/gpt-4o"
`;
    const keysContent = `
openai:
  - "sk-key"
`;
    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);
    // Only one provider "openai", deduplicated by Set
    expect(warnings.length).toBe(0);
  });
});
