import fs from 'fs/promises';
import path from 'path';
import yaml from 'js-yaml';
import { getLogger } from './logger.js';

const logger = getLogger(['ingestion']);

/**
 * Formats a directory or file name component according to FSD mapping rules:
 * - Preserves leading numeric prefixes (e.g., "02-", "1_") to maintain study sequences
 * - Splits by separators (hyphens, underscores, spaces)
 * - Converts each word to Title Case (first letter uppercase, rest lowercase)
 * - Joins them with underscores
 *
 * @param {string} name The component name to format.
 * @returns {string} The formatted component.
 */
export function formatNamespaceComponent(name) {
  if (!name) return '';

  // 1. Trim whitespace and strip leading separator noise (hyphens, underscores) first.
  const cleaned = name.trim().replace(/^[-_\s]+/, '');

  // 2. Split on separators (hyphens, underscores, and spaces) to isolate individual words.
  const words = cleaned.split(/[-_\s]+/);

  // 3. Filter out empty tokens, convert to Title Case (capital first letter, lowercase rest),
  // and join them with underscores (e.g., "react-tutorial" becomes "React_Tutorial").
  return words
    .filter((w) => w.length > 0)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join('_');
}

/**
 * Reads a file trying UTF-8 first with fatal decode error checking,
 * falling back to Latin-1 if UTF-8 decoding fails.
 *
 * @param {string} filePath Absolute path to the file.
 * @returns {Promise<string|null>} The parsed content or null if reading/decoding fails.
 */
export async function readFileWithFallback(filePath) {
  try {
    const buffer = await fs.readFile(filePath);

    // 1. Try UTF-8 decoding in fatal mode. Standard Node buffer.toString('utf8')
    // does not throw on invalid bytes (it inserts replacement chars).
    // TextDecoder in fatal mode throws an error on invalid byte sequences,
    // allowing us to catch issues and fallback to Latin-1/Windows-1252.
    try {
      const utf8Decoder = new TextDecoder('utf-8', { fatal: true });
      return utf8Decoder.decode(buffer);
    } catch (utf8Error) {
      // 2. Fall back to Latin-1 (ISO-8859-1 / windows-1252)
      // windows-1252 maps all possible 8-bit byte values (0x00 - 0xFF) to characters,
      // which acts as a reliable fallback for single-byte legacy encodings.
      try {
        const latin1Decoder = new TextDecoder('windows-1252', { fatal: true });
        return latin1Decoder.decode(buffer);
      } catch (latin1Error) {
        logger.warn`Failed to decode file ${filePath} with UTF-8 or Latin-1: ${latin1Error.message}`;
        return null;
      }
    }
  } catch (readError) {
    // If the file does not exist, lacks permission, or is a directory, log warning and return null.
    logger.warn`Error reading file ${filePath}: ${readError.message}`;
    return null;
  }
}

/**
 * Recursively walks a directory, returning a flat list of matching absolute file paths.
 * Hidden files and directories (names starting with '.') are skipped.
 *
 * @param {string} dirPath The absolute directory path.
 * @param {string[]} allowedExtensions Suffix matches (case-insensitive, e.g. ['.txt', '.md'])
 * @returns {Promise<string[]>}
 */
async function walkDirectory(dirPath, allowedExtensions) {
  let files = [];
  try {
    const entries = await fs.readdir(dirPath, { withFileTypes: true });

    // Map entries to parallel scanning promises to optimize scanning performance
    // on massive directory trees.
    const scanPromises = entries.map(async (entry) => {
      // Skip hidden files and directories (VCS, build, or configuration assets)
      if (entry.name.startsWith('.')) {
        return [];
      }

      const fullPath = path.join(dirPath, entry.name);
      if (entry.isDirectory()) {
        return walkDirectory(fullPath, allowedExtensions);
      } if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (allowedExtensions.includes(ext)) {
          return [fullPath];
        }
      }
      return [];
    });

    const scannedLists = await Promise.all(scanPromises);
    files = scannedLists.flat();
  } catch (error) {
    logger.warn`Error reading directory ${dirPath}: ${error.message}`;
  }
  return files;
}

/**
 * Scans a local directory, parses document contents, and maps folder structures
 * to Title Case double colon path namespaces (e.g. ReactTutorial::Basics::JsxIntro).
 *
 * @param {string} rootPath Path to the root directory to scan.
 * @returns {Promise<Array<{ filePath: string, deckPath: string, content: string }>>}
 */
export async function ingestDirectory(rootPath) {
  const resolvedRoot = path.resolve(rootPath);

  // Verify directory existence/status before walking
  const stats = await fs.stat(resolvedRoot);
  if (!stats.isDirectory()) {
    throw new Error(`Path ${rootPath} is not a directory.`);
  }

  const allowedExtensions = ['.txt', '.md', '.markdown', '.html', '.htm', '.rst'];
  const filePaths = await walkDirectory(resolvedRoot, allowedExtensions);

  const rootDirName = path.basename(resolvedRoot);
  const results = [];

  for (const filePath of filePaths) {
    const content = await readFileWithFallback(filePath);

    // Skip if reading failed or if file contains only whitespace to avoid token waste
    if (content === null || content.trim().length === 0) {
      continue;
    }

    // Construct double colon namespace path
    const relativePath = path.relative(resolvedRoot, filePath);
    const parts = relativePath.split(path.sep);

    // Grab file component and strip extension case-insensitively.
    // We only strip extensions for the final file name, preserving any dots
    // in intermediate directory names.
    const fileComponent = parts[parts.length - 1];
    const ext = path.extname(fileComponent);
    const filenameWithoutExt = fileComponent.slice(0, fileComponent.length - ext.length);

    // Combine root name, nested directory names, and filename
    const allParts = [rootDirName, ...parts];
    const formattedParts = allParts.map((part, index) => {
      let name = part;
      if (index === allParts.length - 1) {
        name = filenameWithoutExt;
      }
      return formatNamespaceComponent(name);
    });

    const deckPath = formattedParts.join('::');

    results.push({
      filePath,
      deckPath,
      content,
    });
  }

  return results;
}

/**
 * Validates and parses topic presets in YAML format.
 *
 * @param {string} fileContent String content of YAML file.
 * @returns {Object} Parsed preset object.
 */
export function parsePreset(fileContent) {
  try {
    const doc = yaml.load(fileContent);
    if (!doc || typeof doc !== 'object') {
      throw new Error('Preset content is empty or invalid.');
    }
    if (typeof doc.name !== 'string' || doc.name.trim().length === 0) {
      throw new Error('Preset must have a non-empty "name" string field.');
    }
    if (!Array.isArray(doc.categories)) {
      throw new Error('Preset must have a "categories" array.');
    }

    for (const category of doc.categories) {
      if (!category || typeof category !== 'object') {
        throw new Error('Category entry must be an object.');
      }
      if (typeof category.name !== 'string' || category.name.trim().length === 0) {
        throw new Error('Category entry must have a non-empty "name" string field.');
      }
      if (!Array.isArray(category.topics)) {
        throw new Error('Category entry must have a "topics" array.');
      }
      for (const topic of category.topics) {
        if (typeof topic !== 'string' || topic.trim().length === 0) {
          throw new Error('Topic must be a non-empty string.');
        }
      }
    }

    return doc;
  } catch (error) {
    throw new Error(`Failed to parse preset: ${error.message}`);
  }
}

/**
 * Asynchronously loads and parses a YAML preset from file path.
 *
 * @param {string} filePath Path to preset file.
 * @returns {Promise<Object>}
 */
export async function loadPreset(filePath) {
  const content = await fs.readFile(filePath, 'utf8');
  return parsePreset(content);
}

/**
 * Ingests a list of file paths, reading their contents and mapping filenames to deck paths.
 *
 * @param {string[]} filePaths Array of file paths to ingest.
 * @returns {Promise<Array<{ filePath: string, deckPath: string, content: string }>>}
 */
export async function ingestFiles(filePaths) {
  if (!Array.isArray(filePaths)) {
    throw new Error('filePaths parameter must be an array.');
  }

  const results = [];
  for (const rawPath of filePaths) {
    // Gracefully ignore non-string paths in the input list
    if (typeof rawPath !== 'string') continue;

    // Resolve absolute path to ensure consistent database references and logs
    const resolvedPath = path.resolve(rawPath);

    // Attempt decoding with UTF-8 first, falling back to Latin-1
    const content = await readFileWithFallback(resolvedPath);

    // Skip missing files, unreadable files, or files containing only whitespace,
    // logging warnings to help users debug typos in config files.
    if (content === null) {
      logger.warn`Requested file "${rawPath}" was skipped because it could not be read or decoded.`;
      continue;
    }
    if (content.trim().length === 0) {
      logger.warn`Requested file "${rawPath}" was skipped because it is empty or contains only whitespace.`;
      continue;
    }

    // Strip extension and format filename as Title Case underscore components
    // (e.g. "my-doc.md" -> "My_Doc")
    const fileComponent = path.basename(resolvedPath);
    const ext = path.extname(fileComponent);
    const filenameWithoutExt = fileComponent.slice(0, fileComponent.length - ext.length);
    const deckPath = formatNamespaceComponent(filenameWithoutExt);

    results.push({
      filePath: resolvedPath,
      deckPath,
      content,
    });
  }

  return results;
}

/**
 * Orchestrates ingestion for document sources, supporting either a list of files or a folder.
 *
 * @param {Object} sources Object containing either files or folder property.
 * @param {string[]} [sources.files] Array of file paths.
 * @param {string} [sources.folder] Folder path to scan recursively.
 * @returns {Promise<Array<{ filePath: string, deckPath: string, content: string }>>}
 */
export async function ingestDocumentSources({ files, folder }) {
  if (folder) {
    return ingestDirectory(folder);
  }
  if (files) {
    return ingestFiles(files);
  }
  return [];
}
