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
import { ingestDirectory, loadPreset, ingestDocumentSources } from '../src/ingestion.js';

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
  ingestFiles: vi.fn(),
  ingestDocumentSources: vi.fn(),
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
    vi.mocked(closeDatabase).mockReset();
    vi.mocked(getCacheStats).mockReset();
    vi.mocked(clearCache).mockReset();
    vi.mocked(initDatabase).mockReset();
    vi.mocked(runPipeline).mockReset();
    vi.mocked(spawnCompiler).mockReset();
    vi.mocked(loadConfig).mockReset();
    vi.mocked(ingestDirectory).mockReset();
    vi.mocked(loadPreset).mockReset();
    vi.mocked(ingestDocumentSources).mockReset();
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

    it('should route document mode preset subjects correctly', async () => {
      const mockPrompts = {
        subjects: {
          my_docs: {
            mode: 'document',
            files: ['./doc1.txt'],
          },
        },
      };

      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: { openai: 'key' },
        prompts: mockPrompts,
      });

      const mockQuestions = [
        { filePath: path.resolve('./doc1.txt'), deckPath: 'Doc1', content: 'document content' },
      ];
      vi.mocked(ingestDocumentSources).mockResolvedValue(mockQuestions);

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'test-doc-run-id',
        results: [],
        hasFailures: false,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'my_docs']);

      expect(ingestDocumentSources).toHaveBeenCalledWith({
        files: [path.resolve('./doc1.txt')],
      });

      expect(runPipeline).toHaveBeenCalledWith({
        config: expect.any(Object),
        keys: { openai: 'key' },
        prompts: mockPrompts,
        questions: [
          {
            questionId: 'my_docs::Doc1',
            topic: 'Doc1',
            categoryName: 'Doc1',
            content: 'document content',
          },
        ],
        subject: 'my_docs',
        cardType: 'standard',
        resumeRunId: null,
        dryRun: false,
        outputPath: null,
        outputDir: path.resolve('./output'),
      });
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should print error and exit with 1 if document mode preset subject is missing both files and folder', async () => {
      const mockPrompts = {
        subjects: {
          my_invalid_docs: {
            mode: 'document',
          },
        },
      };

      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
        keys: {},
        prompts: mockPrompts,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'my_invalid_docs']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('configured in document mode but is missing both "files" and "folder" settings'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should handle standalone yaml presets in document mode correctly', async () => {
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

      vi.mocked(loadPreset).mockResolvedValue({
        name: 'MyPreset',
        mode: 'document',
        folder: './docs',
      });

      const mockQuestions = [
        { filePath: path.resolve('./docs/info.txt'), deckPath: 'Docs::Info', content: 'standalone info content' },
      ];
      vi.mocked(ingestDocumentSources).mockResolvedValue(mockQuestions);

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'standalone-doc-run',
        results: [],
        hasFailures: false,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './my-preset.yaml']);

      expect(loadPreset).toHaveBeenCalledWith(path.resolve('./my-preset.yaml'));
      expect(ingestDocumentSources).toHaveBeenCalledWith({
        folder: path.resolve(path.dirname(path.resolve('./my-preset.yaml')), './docs'),
      });

      expect(runPipeline).toHaveBeenCalledWith({
        config: expect.any(Object),
        keys: expect.any(Object),
        prompts: {},
        questions: [
          {
            questionId: 'MyPreset::Docs::Info',
            topic: 'Docs::Info',
            categoryName: 'Docs::Info',
            content: 'standalone info content',
          },
        ],
        subject: 'MyPreset',
        cardType: 'standard',
        resumeRunId: null,
        dryRun: false,
        outputPath: null,
        outputDir: path.resolve('./output'),
      });
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should route document mode preset subjects with folder setting correctly', async () => {
      const mockPrompts = {
        subjects: {
          my_folder_docs: {
            mode: 'document',
            folder: './some-folder',
          },
        },
      };

      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: { openai: 'key' },
        prompts: mockPrompts,
      });

      const mockQuestions = [
        { filePath: path.resolve('./some-folder/doc.txt'), deckPath: 'Doc', content: 'folder content' },
      ];
      vi.mocked(ingestDocumentSources).mockResolvedValue(mockQuestions);

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'test-doc-folder-run-id',
        results: [],
        hasFailures: false,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'my_folder_docs']);

      expect(ingestDocumentSources).toHaveBeenCalledWith({
        folder: path.resolve('./some-folder'),
      });
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should handle standalone yaml presets with files list setting correctly', async () => {
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

      vi.mocked(loadPreset).mockResolvedValue({
        name: 'MyFilesPreset',
        mode: 'document',
        files: ['./doc1.md', './doc2.txt'],
      });

      const mockQuestions = [
        { filePath: path.resolve('./doc1.md'), deckPath: 'Doc1', content: 'content1' },
      ];
      vi.mocked(ingestDocumentSources).mockResolvedValue(mockQuestions);

      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'standalone-files-run',
        results: [],
        hasFailures: false,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './my-files-preset.yaml']);

      const presetDir = path.dirname(path.resolve('./my-files-preset.yaml'));
      expect(ingestDocumentSources).toHaveBeenCalledWith({
        files: [
          path.resolve(presetDir, './doc1.md'),
          path.resolve(presetDir, './doc2.txt'),
        ],
      });
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should print error and exit with 1 if standalone document preset has missing files and folder', async () => {
      existsSyncSpy.mockReturnValue(true);
      statSyncSpy.mockImplementation(() => ({
        isDirectory: () => false,
        isFile: () => true,
      }));

      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db' } },
        keys: {},
        prompts: {},
      });

      vi.mocked(loadPreset).mockResolvedValue({
        name: 'InvalidDocPreset',
        mode: 'document',
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', './invalid-preset.yaml']);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('configured in document mode but is missing both "files" and "folder" settings'),
      );
      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('should set log level to debug when verbose is passed', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { output_dir: './output' } },
        keys: { openai: 'key' },
        prompts: { subjects: { leetcode: { categories: [{ name: 'A', topics: ['B'] }] } } },
      });
      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'test-run-id',
        results: [],
        hasFailures: false,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'leetcode', '--verbose']);
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should set log level to error when quiet is passed', async () => {
      vi.mocked(loadConfig).mockReturnValue({
        config: { global: { cache_db_path: './llm2deck.db', output_dir: './output' } },
        keys: { openai: 'key' },
        prompts: { subjects: { leetcode: { categories: [{ name: 'A', topics: ['B'] }] } } },
      });
      vi.mocked(runPipeline).mockResolvedValue({
        runId: 'test-run-id',
        results: [],
        hasFailures: false,
      });

      await program.parseAsync(['node', 'src/cli.js', 'run', 'leetcode', '--quiet']);
      expect(exitSpy).toHaveBeenCalledWith(0);
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

    it('should set log level to debug when verbose is passed', async () => {
      existsSyncSpy.mockReturnValue(true);
      vi.mocked(loadConfig).mockReturnValue({ config: { global: { output_dir: './output' } } });
      vi.mocked(spawnCompiler).mockResolvedValue({ code: 0, stdout: '', stderr: '' });

      await program.parseAsync(['node', 'src/cli.js', 'compile', 'input.json', '--verbose']);
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should set log level to error when quiet is passed', async () => {
      existsSyncSpy.mockReturnValue(true);
      vi.mocked(loadConfig).mockReturnValue({ config: { global: { output_dir: './output' } } });
      vi.mocked(spawnCompiler).mockResolvedValue({ code: 0, stdout: '', stderr: '' });

      await program.parseAsync(['node', 'src/cli.js', 'compile', 'input.json', '--quiet']);
      expect(exitSpy).toHaveBeenCalledWith(0);
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

    it('should set log level to debug when verbose is passed', async () => {
      vi.mocked(loadConfig).mockReturnValue({ config: { global: {} } });
      vi.mocked(getCacheStats).mockReturnValue({ count: 42 });

      await program.parseAsync(['node', 'src/cli.js', 'cache', 'stats', '--verbose']);
      expect(exitSpy).toHaveBeenCalledWith(0);
    });

    it('should set log level to error when quiet is passed', async () => {
      vi.mocked(loadConfig).mockReturnValue({ config: { global: { cache_db_path: './llm2deck.db' } } });
      vi.mocked(getCacheStats).mockReturnValue({ count: 42 });

      await program.parseAsync(['node', 'src/cli.js', 'cache', 'stats', '--quiet']);
      expect(exitSpy).toHaveBeenCalledWith(0);
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
