/**
 * Shared directory walker for project-local Node scripts.
 *
 * Recursively lists files under `dir` whose extension matches `exts`,
 * skipping `node_modules`, `.venv`, and `__pycache__`. Returns absolute
 * paths. Used by:
 *   - scripts/check-oversize.js (oversized-file detector)
 *   - scripts/scan-todos.js     (TODO/FIXME scanner)
 *
 * Kept dependency-free (only `node:fs` and `node:path`) so it can run
 * before `npm install` and inside lint-staged hooks.
 */

import { readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const SKIPPED_DIRS = new Set(['node_modules', '.venv', '__pycache__']);

/**
 * @param {string} dir Absolute path to the directory to walk.
 * @param {Iterable<string>} exts File extensions to include (e.g. ['.js', '.py']).
 * @returns {string[]} Absolute paths of matching files.
 */
export function walk(dir, exts) {
  const allowExts = new Set(exts);
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      if (SKIPPED_DIRS.has(entry)) continue;
      out.push(...walk(full, allowExts));
    } else if (allowExts.has(extname(entry))) {
      out.push(full);
    }
  }
  return out;
}
