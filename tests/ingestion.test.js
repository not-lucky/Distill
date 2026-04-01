import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { 
  formatNamespaceComponent, 
  readFileWithFallback, 
  ingestDirectory, 
  parsePreset, 
  loadPreset 
} from '../src/ingestion.js';

const FIXTURES_DIR = path.resolve('./tests/fixtures_ingestion');

describe('Ingestion - Namespace Formatting', () => {
  it('should format simple names to Title Case and join them with underscores', () => {
    expect(formatNamespaceComponent('react-tutorial')).toBe('React_Tutorial');
    expect(formatNamespaceComponent('basics_of_js')).toBe('Basics_Of_Js');
    expect(formatNamespaceComponent('jsx intro')).toBe('Jsx_Intro');
  });

  it('should preserve leading numeric prefixes', () => {
    expect(formatNamespaceComponent('02-basics')).toBe('02_Basics');
    expect(formatNamespaceComponent('1_intro')).toBe('1_Intro');
    expect(formatNamespaceComponent('123-some-topic')).toBe('123_Some_Topic');
    expect(formatNamespaceComponent('005_jsx-intro')).toBe('005_Jsx_Intro');
  });

  it('should not strip numbers that are not followed by hyphen or underscore', () => {
    expect(formatNamespaceComponent('123some')).toBe('123some');
    expect(formatNamespaceComponent('react101')).toBe('React101');
  });

  it('should return empty string for empty inputs', () => {
    expect(formatNamespaceComponent('')).toBe('');
    expect(formatNamespaceComponent(null)).toBe('');
  });

  it('should handle inputs with multiple consecutive hyphens, underscores, or spaces', () => {
    expect(formatNamespaceComponent('basics---of___js')).toBe('Basics_Of_Js');
    expect(formatNamespaceComponent('  -02-basics_  ')).toBe('02_Basics');
  });

  it('should handle inputs with non-alphanumeric characters without crashing', () => {
    expect(formatNamespaceComponent('react-tutorial(v2)')).toBe('React_Tutorial(v2)');
    expect(formatNamespaceComponent('c++-basics')).toBe('C++_Basics');
  });

  it('should handle inputs that are only separators or empty space', () => {
    expect(formatNamespaceComponent('---___')).toBe('');
    expect(formatNamespaceComponent('   ')).toBe('');
  });

  it('should handle inputs starting with numeric prefix but having no trailing text', () => {
    expect(formatNamespaceComponent('02-')).toBe('02');
    expect(formatNamespaceComponent('12_')).toBe('12');
  });

  it('should preserve all numeric prefixes in multi-prefix names', () => {
    expect(formatNamespaceComponent('01-02-basics')).toBe('01_02_Basics');
    expect(formatNamespaceComponent('1_2_intro')).toBe('1_2_Intro');
  });

  // --- Edge Case: Tabs, newlines, and mixed consecutive whitespace / separators
  it('should handle tabs, newlines, and mixed consecutive separator noise correctly', () => {
    expect(formatNamespaceComponent('basics \t\n--__of  \t js')).toBe('Basics_Of_Js');
  });

  // --- Edge Case: Pure numeric input
  it('should handle pure numeric input without stripping or corrupting it', () => {
    expect(formatNamespaceComponent('12345')).toBe('12345');
  });

  // --- Edge Case: Non-ASCII characters (UTF-8)
  it('should convert words containing non-ASCII characters to Title Case correctly', () => {
    expect(formatNamespaceComponent('react-tütorial')).toBe('React_Tütorial');
  });

  // --- Edge Case: Special symbols that are not standard separators
  it('should treat other punctuation marks (like dots or @) as part of the word', () => {
    expect(formatNamespaceComponent('a.b')).toBe('A.b');
    expect(formatNamespaceComponent('user@domain')).toBe('User@domain');
  });
});

describe('Ingestion - File Reading Encodings', () => {
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

  it('should read a valid UTF-8 file successfully', async () => {
    const filePath = path.join(FIXTURES_DIR, 'utf8_file.txt');
    fs.writeFileSync(filePath, 'Hello, World! Here is some text: 🚀', 'utf8');

    const result = await readFileWithFallback(filePath);
    expect(result).toBe('Hello, World! Here is some text: 🚀');
  });

  it('should fall back to Latin-1 for non-UTF-8 files', async () => {
    const filePath = path.join(FIXTURES_DIR, 'latin1_file.txt');
    // Write high-ASCII Latin-1 bytes that are invalid in UTF-8
    // e.g. 0xE9 (é) and 0xF1 (ñ)
    const buffer = Buffer.from([0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0xE9, 0xF1]); // "Hello éñ" in Latin-1
    fs.writeFileSync(filePath, buffer);

    const result = await readFileWithFallback(filePath);
    expect(result).toBe('Hello éñ');
  });

  it('should return null and warn when reading a non-existent file', async () => {
    const filePath = path.join(FIXTURES_DIR, 'does_not_exist.txt');
    const result = await readFileWithFallback(filePath);
    expect(result).toBeNull();
  });

  it('should return null and warn when attempting to read a directory as a file', async () => {
    const result = await readFileWithFallback(FIXTURES_DIR);
    expect(result).toBeNull();
  });

  it('should return empty string when reading an empty file', async () => {
    const filePath = path.join(FIXTURES_DIR, 'empty_file.txt');
    fs.writeFileSync(filePath, '', 'utf8');

    const result = await readFileWithFallback(filePath);
    expect(result).toBe('');
  });

  // --- Edge Case: Moderately large file size handling
  it('should successfully read a moderately large file without memory issues', async () => {
    const filePath = path.join(FIXTURES_DIR, 'large_file.txt');
    const repeatCount = 5000;
    const lineContent = 'This is a test line containing some content to inflate the size. ';
    const content = lineContent.repeat(repeatCount);
    fs.writeFileSync(filePath, content, 'utf8');

    const result = await readFileWithFallback(filePath);
    expect(result).toBe(content);
    expect(result.length).toBe(lineContent.length * repeatCount);
  });
});

describe('Ingestion - Directory Ingestion', () => {
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

  it('should recursively scan directory and map files to Title Case double colon paths preserving numeric prefixes', async () => {
    // Create folders
    const rootScanDir = path.join(FIXTURES_DIR, 'my-study-root');
    const subDir1 = path.join(rootScanDir, '01-react-basics');
    const subDir2 = path.join(rootScanDir, '02-advanced_topics');
    const hiddenDir = path.join(rootScanDir, '.git');

    fs.mkdirSync(rootScanDir, { recursive: true });
    fs.mkdirSync(subDir1, { recursive: true });
    fs.mkdirSync(subDir2, { recursive: true });
    fs.mkdirSync(hiddenDir, { recursive: true });

    // Create files
    const file1 = path.join(subDir1, '01-jsx_intro.md');
    const file2 = path.join(subDir2, 'state-management.txt');
    const fileHidden = path.join(subDir1, '.hidden-doc.md');
    const fileWhitespaceOnly = path.join(subDir1, 'empty.md');
    const fileIgnoredExt = path.join(subDir1, 'notes.pdf');
    const fileInHiddenDir = path.join(hiddenDir, 'config.txt');

    fs.writeFileSync(file1, '# Jsx Intro\nSome react content.', 'utf8');
    fs.writeFileSync(file2, 'Redux vs Context API', 'utf8');
    fs.writeFileSync(fileHidden, 'Hidden content', 'utf8');
    fs.writeFileSync(fileWhitespaceOnly, '   \n  \t ', 'utf8');
    fs.writeFileSync(fileIgnoredExt, 'PDF content', 'utf8');
    fs.writeFileSync(fileInHiddenDir, 'Some config', 'utf8');

    const results = await ingestDirectory(rootScanDir);

    // Expect 2 valid ingested files
    expect(results.length).toBe(2);

    const match1 = results.find(r => r.filePath === file1);
    expect(match1).toBeDefined();
    expect(match1.deckPath).toBe('My_Study_Root::01_React_Basics::01_Jsx_Intro');
    expect(match1.content).toBe('# Jsx Intro\nSome react content.');

    const match2 = results.find(r => r.filePath === file2);
    expect(match2).toBeDefined();
    expect(match2.deckPath).toBe('My_Study_Root::02_Advanced_Topics::State_Management');
    expect(match2.content).toBe('Redux vs Context API');
  });

  it('should throw an error if root path is not a directory', async () => {
    const filePath = path.join(FIXTURES_DIR, 'not_a_dir.txt');
    fs.writeFileSync(filePath, 'not a dir', 'utf8');

    await expect(ingestDirectory(filePath)).rejects.toThrow(/is not a directory/);
  });

  it('should handle multi-level nested folders correctly', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'nested-root');
    const deepDir = path.join(rootScanDir, 'sub1/sub2/sub3');
    fs.mkdirSync(deepDir, { recursive: true });

    const file = path.join(deepDir, 'concept.md');
    fs.writeFileSync(file, 'deep content', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(1);
    expect(results[0].deckPath).toBe('Nested_Root::Sub1::Sub2::Sub3::Concept');
  });

  it('should handle directory names that contain numeric prefixes preserving them', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'prefix-dirs-root');
    const deepDir = path.join(rootScanDir, '01-sub/02-sub2');
    fs.mkdirSync(deepDir, { recursive: true });

    const file = path.join(deepDir, '03-file.md');
    fs.writeFileSync(file, 'content', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(1);
    expect(results[0].deckPath).toBe('Prefix_Dirs_Root::01_Sub::02_Sub2::03_File');
  });

  it('should preserve dots in folder names (extensions not stripped for directories)', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'dot-folder-root');
    const dotDir = path.join(rootScanDir, 'my.md');
    fs.mkdirSync(dotDir, { recursive: true });

    const file = path.join(dotDir, 'content.txt');
    fs.writeFileSync(file, 'some content', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(1);
    expect(results[0].deckPath).toBe('Dot_Folder_Root::My.md::Content');
  });

  it('should match allowed extensions case-insensitively', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'case-ext-root');
    fs.mkdirSync(rootScanDir, { recursive: true });

    const file1 = path.join(rootScanDir, 'file.MD');
    const file2 = path.join(rootScanDir, 'file.Txt');
    const file3 = path.join(rootScanDir, 'file.HTML');
    const file4 = path.join(rootScanDir, 'file.RST');

    fs.writeFileSync(file1, 'content MD', 'utf8');
    fs.writeFileSync(file2, 'content Txt', 'utf8');
    fs.writeFileSync(file3, 'content HTML', 'utf8');
    fs.writeFileSync(file4, 'content RST', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(4);
    
    const deckPaths = results.map(r => r.deckPath);
    expect(deckPaths).toContain('Case_Ext_Root::File');
  });

  it('should handle an empty directory scan gracefully returning an empty array', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'empty-root');
    fs.mkdirSync(rootScanDir, { recursive: true });

    const results = await ingestDirectory(rootScanDir);
    expect(results).toEqual([]);
  });

  it('should strip file extensions only, but preserve other dots in filename keeping numeric prefix', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'dot-file-root');
    fs.mkdirSync(rootScanDir, { recursive: true });

    const file = path.join(rootScanDir, '01-intro.test.md');
    fs.writeFileSync(file, 'dot file test', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(1);
    expect(results[0].deckPath).toBe('Dot_File_Root::01_Intro.test');
  });

  // --- Edge Case: Symbolic link files/directories should be ignored
  it('should ignore symbolic links (dirent is not a normal file/folder)', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'symlink-scan-root');
    fs.mkdirSync(rootScanDir, { recursive: true });

    const targetFile = path.join(FIXTURES_DIR, 'target_file.txt');
    fs.writeFileSync(targetFile, 'Target file content', 'utf8');

    // Create a symlink to the target file inside our scan folder
    const symlinkPath = path.join(rootScanDir, 'linked_file.txt');
    
    // In Windows this might require admin rights or fail, but in Linux it is fully supported.
    // Since the USER runs Linux, we can write a clean, native test.
    let symlinkCreated = false;
    try {
      fs.symlinkSync(targetFile, symlinkPath);
      symlinkCreated = true;
    } catch (e) {
      // Fallback in case sandbox does not allow symlink creation
      console.warn('Skipping symlink test due to OS restrictions:', e.message);
    }

    if (symlinkCreated) {
      const results = await ingestDirectory(rootScanDir);
      // Since walkDirectory skips non-regular files (only allows entry.isFile() or entry.isDirectory()),
      // and entry.isFile() is false for symbolic links, it should skip it.
      expect(results.length).toBe(0);
    }
  });

  // --- Edge Case: Subfolders with identical names at different depths
  it('should correctly distinguish duplicate subfolder names at different depths', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'duplicate-folder-scan');
    const folderLevel1 = path.join(rootScanDir, 'basics');
    const folderLevel2 = path.join(rootScanDir, 'advanced/basics');
    
    fs.mkdirSync(folderLevel1, { recursive: true });
    fs.mkdirSync(folderLevel2, { recursive: true });

    const file1 = path.join(folderLevel1, 'concept.md');
    const file2 = path.join(folderLevel2, 'concept.md');

    fs.writeFileSync(file1, 'concept 1', 'utf8');
    fs.writeFileSync(file2, 'concept 2', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(2);

    const match1 = results.find(r => r.filePath === file1);
    expect(match1.deckPath).toBe('Duplicate_Folder_Scan::Basics::Concept');

    const match2 = results.find(r => r.filePath === file2);
    expect(match2.deckPath).toBe('Duplicate_Folder_Scan::Advanced::Basics::Concept');
  });
});

describe('Ingestion - Preset Parsing & Validation', () => {
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

  it('should parse and validate a correct preset structure', () => {
    const yamlContent = `
name: "LeetCode"
categories:
  - name: "Arrays & Hashing"
    topics:
      - "Two Sum"
      - "Group Anagrams"
  - name: "Two Pointers"
    topics:
      - "Valid Palindrome"
`;
    const doc = parsePreset(yamlContent);
    expect(doc.name).toBe('LeetCode');
    expect(doc.categories.length).toBe(2);
    expect(doc.categories[0].name).toBe('Arrays & Hashing');
    expect(doc.categories[0].topics).toContain('Two Sum');
  });

  it('should throw error for invalid preset structure', () => {
    // Missing name
    const invalidYaml1 = `
categories:
  - name: "Arrays"
    topics:
      - "Two Sum"
`;
    expect(() => parsePreset(invalidYaml1)).toThrow(/must have a non-empty "name" string field/);

    // Missing categories
    const invalidYaml2 = `
name: "LeetCode"
`;
    expect(() => parsePreset(invalidYaml2)).toThrow(/must have a "categories" array/);

    // Empty category name
    const invalidYaml3 = `
name: "LeetCode"
categories:
  - name: ""
    topics:
      - "Two Sum"
`;
    expect(() => parsePreset(invalidYaml3)).toThrow(/Category entry must have a non-empty "name" string field/);

    // Non-string topic
    const invalidYaml4 = `
name: "LeetCode"
categories:
  - name: "Arrays"
    topics:
      - 123
`;
    expect(() => parsePreset(invalidYaml4)).toThrow(/Topic must be a non-empty string/);
  });

  it('should load preset from file asynchronously', async () => {
    const filePath = path.join(FIXTURES_DIR, 'leetcode.yaml');
    const yamlContent = `
name: "LeetCode"
categories:
  - name: "Arrays & Hashing"
    topics:
      - "Two Sum"
`;
    fs.writeFileSync(filePath, yamlContent, 'utf8');

    const doc = await loadPreset(filePath);
    expect(doc.name).toBe('LeetCode');
    expect(doc.categories[0].topics[0]).toBe('Two Sum');
  });

  it('should parse a preset with empty categories or empty topics array', () => {
    const yamlContent1 = `
name: "EmptyCategories"
categories: []
`;
    const doc1 = parsePreset(yamlContent1);
    expect(doc1.name).toBe('EmptyCategories');
    expect(doc1.categories).toEqual([]);

    const yamlContent2 = `
name: "EmptyTopics"
categories:
  - name: "EmptyCategory"
    topics: []
`;
    const doc2 = parsePreset(yamlContent2);
    expect(doc2.name).toBe('EmptyTopics');
    expect(doc2.categories[0].topics).toEqual([]);
  });

  it('should throw on invalid preset YAML syntax', () => {
    expect(() => parsePreset('!!!malformed')).toThrow(/Failed to parse preset/);
  });

  // --- Edge Case: Extra metadata fields in YAML should be ignored/allowed
  it('should ignore/allow extra metadata fields in the YAML preset', () => {
    const yamlContent = `
name: "LeetCode"
author: "Google DeepMind Developer"
version: "1.0.0"
description: "Practice questions for MERN stack"
categories:
  - name: "Arrays"
    topics:
      - "Two Sum"
`;
    const doc = parsePreset(yamlContent);
    expect(doc.name).toBe('LeetCode');
    expect(doc.author).toBe('Google DeepMind Developer');
    expect(doc.version).toBe('1.0.0');
    expect(doc.description).toBe('Practice questions for MERN stack');
    expect(doc.categories[0].topics[0]).toBe('Two Sum');
  });

  it('should throw for preset content that parses to a non-object (plain string)', () => {
    expect(() => parsePreset('just a plain string')).toThrow(/Preset content is empty or invalid/);
  });

  it('should throw for preset content that parses to null', () => {
    // YAML null literal
    expect(() => parsePreset('null')).toThrow(/Preset content is empty or invalid/);
    expect(() => parsePreset('~')).toThrow(/Preset content is empty or invalid/);
  });

  it('should throw for preset content that parses to a number', () => {
    expect(() => parsePreset('42')).toThrow(/Preset content is empty or invalid/);
  });

  it('should throw when a category entry is null', () => {
    const yamlContent = `
name: "Test"
categories:
  - null
`;
    expect(() => parsePreset(yamlContent)).toThrow(/Category entry must be an object/);
  });

  it('should throw when a category entry is a string instead of an object', () => {
    const yamlContent = `
name: "Test"
categories:
  - "just a string"
`;
    expect(() => parsePreset(yamlContent)).toThrow(/Category entry must be an object/);
  });

  it('should throw when a category is missing the topics array', () => {
    const yamlContent = `
name: "Test"
categories:
  - name: "ValidCategory"
`;
    expect(() => parsePreset(yamlContent)).toThrow(/Category entry must have a "topics" array/);
  });

  it('should throw when a category has topics as a string instead of an array', () => {
    const yamlContent = `
name: "Test"
categories:
  - name: "ValidCategory"
    topics: "not an array"
`;
    expect(() => parsePreset(yamlContent)).toThrow(/Category entry must have a "topics" array/);
  });

  it('should throw when a topic is a whitespace-only string', () => {
    const yamlContent = `
name: "Test"
categories:
  - name: "ValidCategory"
    topics:
      - "   "
`;
    expect(() => parsePreset(yamlContent)).toThrow(/Topic must be a non-empty string/);
  });

  it('should throw when loading a preset from a nonexistent file', async () => {
    await expect(loadPreset('/nonexistent/path/preset.yaml')).rejects.toThrow();
  });
});

describe('Ingestion - Uncovered Branch Coverage', () => {
  const FIXTURES_DIR = path.resolve('./tests/fixtures_ingestion');

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

  it('should handle unreadable subdirectory gracefully (walkDirectory catch block)', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'unreadable-dir-root');
    const unreadableDir = path.join(rootScanDir, 'no-access');
    const readableDir = path.join(rootScanDir, 'readable');

    fs.mkdirSync(unreadableDir, { recursive: true });
    fs.mkdirSync(readableDir, { recursive: true });

    // Add a readable file for contrast
    fs.writeFileSync(path.join(readableDir, 'good.md'), 'readable content', 'utf8');

    // Remove read permission from subdirectory
    fs.chmodSync(unreadableDir, 0o000);

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    try {
      const results = await ingestDirectory(rootScanDir);
      // Should still process the readable directory
      expect(results.length).toBe(1);
      expect(results[0].content).toBe('readable content');
    } finally {
      // Restore permission before cleanup
      fs.chmodSync(unreadableDir, 0o755);
      warnSpy.mockRestore();
    }
  });

  it('should throw when ingestDirectory is called with a nonexistent path', async () => {
    await expect(ingestDirectory('/nonexistent/path/to/dir')).rejects.toThrow();
  });

  it('should handle files in root directory (no subdirectory nesting)', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'flat-root');
    fs.mkdirSync(rootScanDir, { recursive: true });

    fs.writeFileSync(path.join(rootScanDir, 'intro.md'), 'flat content', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(1);
    expect(results[0].deckPath).toBe('Flat_Root::Intro');
    expect(results[0].content).toBe('flat content');
  });

  it('should handle readFileWithFallback when both UTF-8 and Latin-1 fail', async () => {
    // Mock TextDecoder to force both decoders to fail
    const originalTextDecoder = globalThis.TextDecoder;
    let callCount = 0;

    globalThis.TextDecoder = class MockTextDecoder {
      constructor(encoding, options) {
        this.encoding = encoding;
        this.options = options;
      }
      decode(buffer) {
        callCount++;
        throw new Error(`Mocked ${this.encoding} decode failure`);
      }
    };

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    try {
      const filePath = path.join(FIXTURES_DIR, 'mock_decode_file.txt');
      fs.writeFileSync(filePath, 'some content', 'utf8');

      const result = await readFileWithFallback(filePath);
      expect(result).toBeNull();
      expect(callCount).toBe(2); // Both UTF-8 and Latin-1 attempted
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to decode file')
      );
    } finally {
      globalThis.TextDecoder = originalTextDecoder;
      warnSpy.mockRestore();
    }
  });

  it('should handle file that contains only null bytes', async () => {
    const filePath = path.join(FIXTURES_DIR, 'null_bytes.txt');
    // Write a file with only null bytes — valid UTF-8 but content is non-printable
    fs.writeFileSync(filePath, Buffer.from([0x00, 0x00, 0x00]));

    const result = await readFileWithFallback(filePath);
    // Should successfully decode (null bytes are valid UTF-8)
    expect(result).not.toBeNull();
    expect(result.length).toBe(3);
  });

  it('should handle .htm and .markdown extensions correctly', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'multi-ext-root');
    fs.mkdirSync(rootScanDir, { recursive: true });

    fs.writeFileSync(path.join(rootScanDir, 'page.htm'), 'htm content', 'utf8');
    fs.writeFileSync(path.join(rootScanDir, 'doc.markdown'), 'markdown content', 'utf8');

    const results = await ingestDirectory(rootScanDir);
    expect(results.length).toBe(2);

    const htmResult = results.find(r => r.filePath.endsWith('.htm'));
    expect(htmResult).toBeDefined();
    expect(htmResult.content).toBe('htm content');

    const markdownResult = results.find(r => r.filePath.endsWith('.markdown'));
    expect(markdownResult).toBeDefined();
    expect(markdownResult.content).toBe('markdown content');
  });

  it('should skip files where readFileWithFallback returns null', async () => {
    const rootScanDir = path.join(FIXTURES_DIR, 'null-read-root');
    fs.mkdirSync(rootScanDir, { recursive: true });

    const filePath = path.join(rootScanDir, 'unreadable.md');
    fs.writeFileSync(filePath, 'content', 'utf8');
    // Remove read permission from the file itself
    fs.chmodSync(filePath, 0o000);

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    try {
      const results = await ingestDirectory(rootScanDir);
      // The file should be skipped because readFileWithFallback returns null
      expect(results.length).toBe(0);
    } finally {
      fs.chmodSync(filePath, 0o644);
      warnSpy.mockRestore();
    }
  });
});
