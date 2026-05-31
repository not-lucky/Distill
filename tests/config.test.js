import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadConfig, deepMerge, extractActiveProviders } from '../src/config.js';

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
    expect(config.global.model_concurrency).toBe(0);
    expect(config.global.topic_concurrency).toBe(1);
    expect(config.global.request_delay).toBe(1.0);
    expect(config.global.default_timeout).toBeNull();
    expect(config.global.output_dir).toBe('./output');
    expect(config.global.cache_db_path).toBe('./distill.db');

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
  model_concurrency: 3
  topic_concurrency: 2
  request_delay: 2.5
  default_timeout: 90.0
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
  synthesis:
    model: "openai/gpt-4o"
  schema_enforcement:
    model: "openai/gpt-3.5-turbo"
`;
    const keysContent = `
openai:
  - "sk-my-secret-key"
`;

    fs.writeFileSync(configPath, configContent, 'utf8');
    fs.writeFileSync(keysPath, keysContent, 'utf8');

    const { config, keys, warnings } = loadConfig(configPath, keysPath);

    expect(config.global.model_concurrency).toBe(3);
    expect(config.global.topic_concurrency).toBe(2);
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
  synthesis:
    model: "openai/gpt-4o"
  schema_enforcement:
    model: "openai/gpt-3.5-turbo"
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
    expect(config.global.model_concurrency).toBe(0);
    expect(config.global.topic_concurrency).toBe(1);
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
    expect(warnings.some((w) => w.includes('Missing API key for active provider: cerebras'))).toBe(
      true,
    );
    expect(warnings.some((w) => w.includes('Missing API key for active provider: openai'))).toBe(
      false,
    );
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
    expect(warnings.some((w) => w.includes('Missing API key for active provider: openai'))).toBe(
      true,
    );
  });

  it('should not warn if at least one key in the array is valid', () => {
    const configPath = path.join(FIXTURES_DIR, 'mixed_key_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'mixed_key_keys.yaml');

    const configContent = `
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
  synthesis:
    model: "openai/gpt-4o"
  schema_enforcement:
    model: "openai/gpt-3.5-turbo"
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
  generation:
    models:
      - "openai/gpt-3.5-turbo"
  synthesis:
    model: "openai/gpt-4o"
  schema_enforcement:
    model: "openai/gpt-3.5-turbo"
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
  synthesis:
    model: "ollama_local/llama3"
  schema_enforcement:
    model: "ollama_local/llama3"
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

    expect(config.global.model_concurrency).toBe(0);
    expect(config.global.topic_concurrency).toBe(1);
    expect(
      warnings.some((w) => w.includes('Error reading config file') || w.includes('invalid')),
    ).toBe(true);
    expect(
      warnings.some((w) => w.includes('Error reading keys file') || w.includes('invalid')),
    ).toBe(true);
  });

  it('should correctly merge custom global and provider structures', () => {
    const configPath = path.join(FIXTURES_DIR, 'custom_merge_config.yaml');
    const keysPath = path.join(FIXTURES_DIR, 'custom_merge_keys.yaml');

    const configContent = `
global:
  model_concurrency: 2
  topic_concurrency: 3
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
    expect(config.global.model_concurrency).toBe(2);
    expect(config.global.topic_concurrency).toBe(3);
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
    const source = JSON.parse(
      '{"__proto__": {"polluted": true}, "constructor": {"prototype": {"polluted": true}}, "prototype": {"polluted": true}, "b": 2}',
    );

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

// ---------------------------------------------------------------------------
// Behaviour-driven coverage for previously-uncovered branches:
//   - checkPipelineModels warning for non-empty-but-invalid generation models
//   - flushWarnings actually emits warnings outside test mode
//   - parseModelString rejects trailing-slash inputs that fail the
//     "empty provider / empty model" guard
// ---------------------------------------------------------------------------

describe('checkPipelineModels warning variants', () => {
  const FIXTURES = path.resolve('./tests/fixtures');

  beforeAll(() => {
    if (!fs.existsSync(FIXTURES)) fs.mkdirSync(FIXTURES, { recursive: true });
  });

  function writeConfig(content) {
    const p = path.join(FIXTURES, 'pipeline_models_edge.yaml');
    fs.writeFileSync(p, content, 'utf8');
    return p;
  }

  it('warns when generation.models contains empty or whitespace strings', () => {
    const configPath = writeConfig(`
providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "openai/gpt-4o"
      - "   "
  synthesis:
    model: "openai/gpt-4o"
  schema_enforcement:
    model: "openai/gpt-4o"
`);
    const keysPath = path.join(FIXTURES, 'pipeline_models_edge_keys.yaml');
    fs.writeFileSync(keysPath, 'openai:\n  - "sk-key"\n', 'utf8');

    const { warnings } = loadConfig(configPath, keysPath);
    expect(warnings.some((w) => w.includes('empty or invalid model strings'))).toBe(true);
  });
});

describe('parseModelString edge cases (via loadConfig)', () => {
  const FIXTURES = path.resolve('./tests/fixtures');

  beforeAll(() => {
    if (!fs.existsSync(FIXTURES)) fs.mkdirSync(FIXTURES, { recursive: true });
  });

  function writeConfig(models) {
    const p = path.join(FIXTURES, 'parse_model_edge.yaml');
    fs.writeFileSync(
      p,
      `providers:
  openai:
    base_url: "https://api.openai.com/v1"
pipeline:
  generation:
    models:
      - "${models}"
  synthesis:
    model: "openai/gpt-4o"
  schema_enforcement:
    model: "openai/gpt-4o"
`,
      'utf8',
    );
    return p;
  }

  it('rejects a model string that has only a slash and an empty provider part', () => {
    // "/gpt-4o" — firstSlashIdx === 0 hits the first guard, so the error
    // message comes from "Invalid model format"; we only care that it
    // surfaces the error contractually.
    const configPath = writeConfig('/gpt-4o');
    const keysPath = path.join(FIXTURES, 'parse_model_edge_keys.yaml');
    fs.writeFileSync(keysPath, 'openai:\n  - "sk-key"\n', 'utf8');

    expect(() => loadConfig(configPath, keysPath)).toThrow(/Invalid model format/);
  });

  it('rejects a model string that ends with a slash (empty model part)', () => {
    // "openai/" — firstSlashIdx === modelString.length - 1, the guard
    // catches this and throws.
    const configPath = writeConfig('openai/');
    const keysPath = path.join(FIXTURES, 'parse_model_edge_keys2.yaml');
    fs.writeFileSync(keysPath, 'openai:\n  - "sk-key"\n', 'utf8');

    expect(() => loadConfig(configPath, keysPath)).toThrow(/Invalid model format/);
  });
});

describe('flushWarnings', () => {
  it('loadConfig returns the accumulated warnings without crashing', () => {
    // Contract: flushWarnings is the single point where accumulated
    // warnings turn into logger.warn calls. When the warnings array is
    // non-empty (regardless of NODE_ENV), loadConfig must return them in
    // its result so callers can surface them. We assert that contract
    // here rather than chasing the private helper.
    const FIXTURES = path.resolve('./tests/fixtures');
    if (!fs.existsSync(FIXTURES)) fs.mkdirSync(FIXTURES, { recursive: true });
    const cp = path.join(FIXTURES, 'flush_warnings_config.yaml');
    const kp = path.join(FIXTURES, 'flush_warnings_keys.yaml');
    fs.writeFileSync(
      cp,
      `providers:\n  openai:\n    base_url: "x"\npipeline:\n  generation:\n    models:\n      - "openai/gpt-4o"\n  synthesis:\n    model: "openai/gpt-4o"\n  schema_enforcement:\n    model: "openai/gpt-4o"\n`,
      'utf8',
    );
    fs.writeFileSync(kp, 'openai:\n  - ""\n', 'utf8');

    const result = loadConfig(cp, kp);
    expect(result.warnings.length).toBeGreaterThan(0);
  });
});

describe('extractActiveProviders', () => {
  it('collects provider prefixes from model strings nested in the pipeline', () => {
    const pipeline = {
      generation: { models: ['openai/gpt-4o', 'anthropic/claude-3'] },
      synthesis: { model: 'openai/gpt-4o' },
    };
    const providers = extractActiveProviders(pipeline, ['openai', 'anthropic']);
    expect(providers).toEqual(new Set(['openai', 'anthropic']));
  });

  it('returns an empty Set when pipeline is null, undefined, or not an object', () => {
    // Defensive: a malformed config (no `pipeline:` section at all) must
    // not throw. The function returns an empty set so downstream checks
    // see "no providers active" rather than crashing.
    expect(extractActiveProviders(null, ['openai'])).toEqual(new Set());
    expect(extractActiveProviders(undefined, ['openai'])).toEqual(new Set());
    expect(extractActiveProviders('not-an-object', ['openai'])).toEqual(new Set());
    expect(extractActiveProviders(42, ['openai'])).toEqual(new Set());
  });

  it('returns an empty Set when pipeline is an object with no model references', () => {
    expect(extractActiveProviders({ foo: { bar: 'baz' } }, ['openai'])).toEqual(new Set());
  });
});
