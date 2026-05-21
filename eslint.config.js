import js from '@eslint/js';
import globals from 'globals';
import importX from 'eslint-plugin-import-x';
import n from 'eslint-plugin-n';
import boundaries from 'eslint-plugin-boundaries';

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.node,
      },
    },
    plugins: {
      'import-x': importX,
      n,
      boundaries,
    },
    settings: {
      'boundaries/elements': [
        { type: 'entry', pattern: 'src/cli.js' },
        { type: 'command', pattern: 'src/commands/**' },
        { type: 'pipeline', pattern: 'src/pipeline/**' },
        { type: 'llm', pattern: 'src/llm/**' },
        { type: 'core', pattern: 'src/*.{js,mjs,cjs}' },
        { type: 'barrel', pattern: 'src/(stages|providers|orchestrator).js' },
      ],
    },
    rules: {
      // ---- Existing project rules ----
      'n/no-missing-import': 'error',
      'import-x/extensions': [
        'error',
        'ignorePackages',
        {
          js: 'always',
          jsx: 'always',
          ts: 'always',
          tsx: 'always',
        },
      ],
      'import-x/prefer-default-export': 'off',
      'no-underscore-dangle': 'off',
      'no-await-in-loop': 'off',
      'no-console': ['error', { allow: ['log', 'error'] }],
      'no-unused-expressions': 'off',
      'no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      'no-restricted-syntax': ['error', 'ForInStatement', 'LabeledStatement', 'WithStatement'],
      'no-plusplus': 'off',
      'no-nested-ternary': 'off',
      'no-constant-condition': ['error', { checkLoops: false }],
      'no-use-before-define': ['error', { functions: false, classes: true, variables: true }],
      'no-continue': 'off',
      // ---- Cyclomatic complexity (signal: cyclomatic_complexity) ----
      complexity: ['warn', { max: 12 }],
      'max-depth': ['warn', { max: 4 }],
      'max-lines-per-function': ['warn', { max: 80, skipComments: true, skipBlankLines: true }],
      // ---- Large file detection (signal: large_file_detection) ----
      'max-lines': ['warn', { max: 500, skipComments: true, skipBlankLines: true }],
      // ---- Module boundaries (signal: code_modularization) ----
      'boundaries/dependencies': [
        'error',
        {
          default: 'disallow',
          rules: [
            // CLI entry may depend on commands and barrel re-exports
            {
              from: { type: 'entry' },
              allow: [
                { to: { type: 'command' } },
                { to: { type: 'barrel' } },
                { to: { type: 'core' } },
              ],
            },
            // Commands orchestrate pipelines and may use core/barrel
            {
              from: { type: 'command' },
              allow: [
                { to: { type: 'pipeline' } },
                { to: { type: 'core' } },
                { to: { type: 'barrel' } },
                { to: { type: 'llm' } },
              ],
            },
            // Pipeline stages can use LLM helpers and core utilities
            {
              from: { type: 'pipeline' },
              allow: [
                { to: { type: 'llm' } },
                { to: { type: 'core' } },
                { to: { type: 'barrel' } },
              ],
            },
            // LLM helpers depend on core only
            { from: { type: 'llm' }, allow: [{ to: { type: 'core' } }] },
            // Core utilities must remain framework-agnostic (no upward deps)
            { from: { type: 'core' }, allow: [{ to: { type: 'core' } }] },
            // Barrel re-exports may only point into the rest of the graph
            {
              from: { type: 'barrel' },
              allow: [
                { to: { type: 'pipeline' } },
                { to: { type: 'llm' } },
                { to: { type: 'core' } },
                { to: { type: 'command' } },
              ],
            },
          ],
        },
      ],
    },
  },
  {
    files: ['tests/**/*.test.js', 'tests/**/*.spec.js'],
    rules: {
      'import-x/no-extraneous-dependencies': 'off',
      complexity: 'off',
      'max-lines-per-function': 'off',
      'max-lines': 'off',
      'max-depth': 'off',
    },
  },
  {
    files: ['scripts/**/*.{js,mjs,cjs}'],
    rules: {
      'max-lines-per-function': 'off',
      'max-lines': 'off',
    },
  },
  {
    ignores: [
      'node_modules/',
      '.archived/',
      '.venv/',
      'coverage/',
      'examples/',
      'output/',
      'scratch/',
      'logs/',
      'reports/',
      'site/',
      'schemas/',
    ],
  },
];
