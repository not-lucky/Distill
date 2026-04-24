import {
  vi, describe, it, expect, beforeEach, afterEach,
} from 'vitest';
import fs from 'fs';
import path from 'path';

// Now import program and mock functions
import { program } from '../src/cli.js';
import { loadConfig } from '../src/config.js';
import {
  initDatabase, closeDatabase, clearCache, getCacheStats,
} from '../src/database.js';
import { runPipeline, spawnCompiler } from '../src/orchestrator.js';
import { ingestDirectory, loadPreset } from '../src/ingestion.js';

// Mocking dependencies first
vi.mock('../src/config.js', () => ({
  loadConfig: vi.fn(),
}));
vi.mock('../src/database.js', () => ({
  initDatabase: vi.fn(),
  closeDatabase: vi.fn(),
  clearCache: vi.fn(),
  getCacheStats: vi.fn(),
}));
vi.mock('../src/orchestrator.js', () => ({
  runPipeline: vi.fn(),
  spawnCompiler: vi.fn(),
}));
vi.mock('../src/ingestion.js', () => ({
  ingestDirectory: vi.fn(),
  loadPreset: vi.fn(),
  formatNamespaceComponent: (val) => (val ? val.replace(/\s+/g, '_') : ''),
}));

describe('CLI Commands Integration', () => {
  let exitSpy;
  let logSpy;
  let errorSpy;
  let existsSyncSpy;
  let statSyncSpy;

  beforeEach(() => {
    vi.clearAllMocks();
    exitSpy = vi.spyOn(process, 'exit').mockImplementation(() => {});
    logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    existsSyncSpy = vi.spyOn(fs, 'existsSync').mockImplementation(() => true);
    statSyncSpy = vi.spyOn(fs, 'statSync').mockImplementation(() => ({
      isDirectory: () => true,
      isFile: () => false,
    }));
  });

  afterEach(() => {
    exitSpy.mockRestore();
    logSpy.mockRestore();
    errorSpy.mockRestore();
    existsSyncSpy.mockRestore();
    statSyncSpy.mockRestore();
  });

  describe('run command', () => {
    it('should route preset subjects correctly', async () => {
      const mockPrompts = {
        subjects: {
          leetcode: {
            categories: [
              null,
              {
                name: 'Null topics category',
                topics: null,
              },
              {
                name: 'Two Pointers',
                topics: ['Valid Palindrome'],
              },
            ],
          },
        },
      };

      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: { openai: 'key' },
        prompts: mockPrompts,
      });

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'test-run-id',
        results: [],
        hasFailures: false,
      });

      // Execute leetcode preset
      await program.parseAsync(['node', 'src/cli.js', 'run', 'leetcode']);

      expect(loadConfig).toHaveBeenCalledWith('./config.yaml');
      expect(initDatabase).toHaveBeenCalledWith(path.resolve('./llm2deck.db'));
      expect(runPipeline).toHaveBeenCalledWith({
        config: expect.any(Object),
        keys: { openai: 'key' },
        prompts: mockPrompts,
        questions: [
          {
            questionId: 'leetcode::Two_Pointers::Valid_Palindrome',
            topic: 'Valid Palindrome',
            categoryName: 'Two Pointers',
            content: '',
          },
        ],
        subject: 'leetcode',
        cardType: 'standard',
        resumeRunId: null,
        dryRun: false,
        outputPath: null,
        outputDir: path.resolve('./output'),
      });
      expect(closeDatabase).toHaveBeenCalled();
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should map local directory path and ingest its files', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: { openai: 'key' },
        prompts: {},
      });

      const mockQuestions = [
        { filePath: '/a/b.txt', deckPath: 'b', content: 'hello' },
      ];
      vi.mocked(ingestDirectory).mockResolvedValue(mockQuestions);

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'test-run-id',
        results: [],
        hasFailures: false,
      });

      // Execute run command on a path
      await program.parseAsync(['node', 'src/cli.js', 'run', './my-docs', '--subject', 'cs']);

      expect(ingestDirectory).toHaveBeenCalledWith(path.resolve('./my-docs'));
      expect(runPipeline).toHaveBeenCalledWith({
        config: expect.any(Object),
        keys: { openai: 'key' },
        prompts: {},
        questions: mockQuestions,
        subject: 'cs',
        cardType: 'standard',
        resumeRunId: null,
        dryRun: false,
        outputPath: null,
        outputDir: path.resolve('./output'),
      });
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should map local YAML preset file and parse its categories', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: { openai: 'key' },
        prompts: {},
      });

      existsSyncSpy.mockReturnValue(true);
      statSyncSpy.mockImplementation(() => ({
        isDirectory: () => false,
        isFile: () => true,
      }));

      vi.mocked(loadPreset).mockResolvedValue({
        name: 'Physics',
        categories: [
          null,
          {
            name: 'Null topics category',
            topics: null,
          },
          {
            name: 'Mechanics',
            topics: ['Gravity'],
          },
        ],
      });

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'test-run-id',
        results: [],
        hasFailures: false,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './physics-preset.yaml']);

      expect(loadPreset).toHaveBeenCalledWith(path.resolve('./physics-preset.yaml'));
      expect(runPipeline).toHaveBeenCalledWith({
        config: expect.any(Object),
        keys: expect.any(Object),
        prompts: {},
        questions: [
          {
            questionId: 'Physics::Mechanics::Gravity',
            topic: 'Gravity',
            categoryName: 'Mechanics',
            content: '',
          },
        ],
        subject: 'Physics',
        cardType: 'standard',
        resumeRunId: null,
        dryRun: false,
        outputPath: null,
        outputDir: path.resolve('./output'),
      });
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should handle errors if local path is not YAML/YML preset and not directory', async () => {
      existsSyncSpy.mockReturnValue(true);
      statSyncSpy.mockImplementation(() => ({
        isDirectory: () => false,
        isFile: () => true,
      }));

      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: {},
        prompts: {},
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './notes.txt']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('is a file but not a YAML/YML preset file'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should exit with 1 if no questions are loaded', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: {},
        prompts: {},
      });
      vi.mocked(ingestDirectory).mockResolvedValue([]);

      await program.parseAsync(['node', 'src/cli.js', 'run', './empty-docs']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('No questions/topics found to process'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should handle invalid card type', async () => {
      await program.parseAsync(['node', 'src/cli.js', 'run', 'leetcode', '--card-type', 'invalid']);
      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Invalid card-type "invalid"'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should handle non-existent source path', async () => {
      existsSyncSpy.mockReturnValue(false);
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: {} },
        keys: {},
        prompts: {},
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './invalid-path']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('does not exist, and is not a known subject preset'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should process resume, dry-run options and handle failures', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: {},
        prompts: {
          subjects: {
            leetcode: {
              categories: [
                {
                  name: 'Two Pointers',
                  topics: ['Valid Palindrome'],
                },
              ],
            },
          },
        },
      });

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'resume-run',
        results: [],
        hasFailures: true,
      });

      await program.parseAsync([
        'node',
        'src/cli.js',
        'run',
        'leetcode',
        '--resume',
        'some-run-id',
        '--dry-run',
      ]);

      expect(runPipeline).toHaveBeenCalledWith(
        expect.objectContaining({
          resumeRunId: 'some-run-id',
          dryRun: true,
        }),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Pipeline completed with failures'),
      );
    });

    it('should handle runPipeline throwing error', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
        keys: {},
        prompts: {
          subjects: {
            leetcode: {
              categories: [
                {
                  name: 'Two Pointers',
                  topics: ['Valid Palindrome'],
                },
              ],
            },
          },
        },
      });

      vi.mocked(runPipeline).mockRejectedValue(new Error('Network error'));

      await program.parseAsync(['node', 'src/cli.js', 'run', 'leetcode']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Pipeline failed: Network error'),
      );
      expect(closeDatabase).toHaveBeenCalled();
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should exit with 1 if preset has empty categories', async () => {
      // Test when prompt.subjects configuration has an empty category list
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
        keys: {},
        prompts: { subjects: { empty_preset: { categories: [] } } },
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'empty_preset']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('No questions/topics found to process'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should exit with 1 if preset has missing categories property', async () => {
      // Test when prompt.subjects configuration has a subject preset
      // but categories property is missing
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
        keys: {},
        prompts: { subjects: { nocat_preset: { name: 'NoCat' } } },
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'nocat_preset']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('No questions/topics found to process'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should exit with 1 if standalone preset has empty or missing categories', async () => {
      // Setup file system stubs
      existsSyncSpy.mockReturnValue(true);
      statSyncSpy.mockImplementation(() => ({
        isDirectory: () => false,
        isFile: () => true,
      }));

      // Test 1: Preset with empty categories array
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
        keys: {},
        prompts: {},
      });

      vi.mocked(loadPreset).mockResolvedValueOnce({
        name: 'EmptyPreset',
        categories: [],
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './empty-preset.yaml']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('No questions/topics found to process'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);

      // Test 2: Preset with completely missing categories property
      vi.mocked(loadPreset).mockResolvedValueOnce({
        name: 'NoCatsPreset',
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './no-cats-preset.yaml']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('No questions/topics found to process'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });
  });

  describe('compile command', () => {
    it('should spawn compiler with default output dir', async () => {
      existsSyncSpy.mockReturnValue(true);
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { output_dir: './output' } },
      });
      vi.mocked(spawnCompiler).mockResolvedValue({
        code: 0,
        stdout: 'Success print',
        stderr: '',
      });

      await program.parseAsync(['node', 'src/cli.js', 'compile', 'input.json']);

      expect(spawnCompiler).toHaveBeenCalledWith(
        path.resolve('input.json'),
        path.resolve('./output'),
      );
      expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Success print'));
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should spawn compiler with custom output option', async () => {
      existsSyncSpy.mockReturnValue(true);
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { output_dir: './output' } },
      });
      vi.mocked(spawnCompiler).mockResolvedValue({
        code: 0,
        stdout: '',
        stderr: 'Warning print',
      });

      await program.parseAsync([
        'node',
        'src/cli.js',
        'compile',
        'input.json',
        '-o',
        './custom.apkg',
      ]);

      expect(spawnCompiler).toHaveBeenCalledWith(
        path.resolve('input.json'),
        './custom.apkg',
      );
      expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('Warning print'));
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should fail if input JSON file does not exist', async () => {
      existsSyncSpy.mockReturnValue(false);

      await program.parseAsync(['node', 'src/cli.js', 'compile', 'missing.json']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('JSON file "missing.json" does not exist'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should handle compiler throwing error', async () => {
      existsSyncSpy.mockReturnValue(true);
      vi.mocked(loadConfig).mockReturnValue({ config: { global: {} } });
      vi.mocked(spawnCompiler).mockRejectedValue(new Error('Subprocess crash'));

      await program.parseAsync(['node', 'src/cli.js', 'compile', 'input.json']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Compilation failed: Subprocess crash'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });
  });

  describe('cache command', () => {
    it('should stats the cache correctly', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
      });
      vi.mocked(getCacheStats).mockReturnValue({ count: 42 });

      await program.parseAsync(['node', 'src/cli.js', 'cache', 'stats']);

      expect(initDatabase).toHaveBeenCalledWith(path.resolve('./llm2deck.db'));
      expect(getCacheStats).toHaveBeenCalled();
      expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Total cached queries: 42'));
      expect(closeDatabase).toHaveBeenCalled();
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should clear the cache correctly', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
      });

      await program.parseAsync(['node', 'src/cli.js', 'cache', 'clear']);

      expect(initDatabase).toHaveBeenCalledWith(path.resolve('./llm2deck.db'));
      expect(clearCache).toHaveBeenCalled();
      expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Cache cleared successfully'));
      expect(closeDatabase).toHaveBeenCalled();
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should fail with invalid cache action', async () => {
      await program.parseAsync(['node', 'src/cli.js', 'cache', 'invalid']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Invalid action "invalid"'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should handle cache DB error gracefully', async () => {
      vi.mocked(loadConfig).mockReturnValue({ config: { global: {} } });
      vi.mocked(getCacheStats).mockImplementation(() => {
        throw new Error('Disk read failure');
      });

      await program.parseAsync(['node', 'src/cli.js', 'cache', 'stats']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Cache command failed: Disk read failure'),
      );
      expect(closeDatabase).toHaveBeenCalled();
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should ignore closeDatabase errors in cache command catch block', async () => {
      // Test db close error recovery in cache action error handler
      vi.mocked(loadConfig).mockReturnValue({ config: { global: {} } });
      vi.mocked(getCacheStats).mockImplementation(() => {
        throw new Error('Stats failed');
      });
      vi.mocked(closeDatabase).mockImplementation(() => {
        throw new Error('Database close failed');
      });

      await program.parseAsync(['node', 'src/cli.js', 'cache', 'stats']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Cache command failed: Stats failed'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });
  });

  describe('edge cases', () => {
    it('should handle source path that is neither directory nor file', async () => {
      // Stub fs to return an item that is neither directory nor normal file (e.g. socket)
      existsSyncSpy.mockReturnValue(true);
      statSyncSpy.mockImplementation(() => ({
        isDirectory: () => false,
        isFile: () => false,
      }));

      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: {},
        prompts: {},
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './special-device-path']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('is not a valid directory or preset file'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should ignore closeDatabase errors in run pipeline catch block', async () => {
      // Test db close error recovery in run action error handler
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
        keys: {},
        prompts: {
          subjects: {
            leetcode: {
              categories: [
                {
                  name: 'Two Pointers',
                  topics: ['Valid Palindrome'],
                },
              ],
            },
          },
        },
      });

      vi.mocked(runPipeline).mockRejectedValue(new Error('Pipeline error'));
      vi.mocked(closeDatabase).mockImplementation(() => {
        throw new Error('Database close failed');
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'leetcode']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Pipeline failed: Pipeline error'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should run program.parse when executed directly', async () => {
      // Clear modules cache to force re-evaluation of cli.js
      vi.resetModules();

      // Setup arguments to simulate direct invocation of node src/cli.js --help
      const originalArgv = process.argv;
      const cliPath = path.resolve('src/cli.js');
      process.argv = ['node', cliPath, '--help'];

      // Dynamically import the module statically named path so Vite can analyze it,
      // triggering the top-level direct execution check.
      await import('../src/cli.js');

      expect(exitSpy).toHaveBeenCalledWith(0);
      process.argv = originalArgv;
    });
  });
});
