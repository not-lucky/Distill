module.exports = {
  env: {
    node: true,
    es2021: true,
    mocha: true,
  },
  extends: [
    'airbnb-base',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  rules: {
    // Node.js ESM requires file extensions for relative imports
    'import/extensions': ['error', 'ignorePackages', {
      js: 'always',
      jsx: 'always',
      ts: 'always',
      tsx: 'always',
    }],
    // Allow named exports without preferring a default export
    'import/prefer-default-export': 'off',
    // Allow leading underscores for private/internal properties and helper functions
    'no-underscore-dangle': 'off',
    // Allow await in retry/backoff loops
    'no-await-in-loop': 'off',
    // Allow console.warn / console.error for logging warnings/errors in non-test envs
    'no-console': ['error', { allow: ['warn', 'error', 'info'] }],
    // Relax rules for test files
    'no-unused-expressions': 'off',
    // Allow for...of loops in Node.js
    'no-restricted-syntax': [
      'error',
      'ForInStatement',
      'LabeledStatement',
      'WithStatement',
    ],
    // Allow unary operator ++ and --
    'no-plusplus': 'off',
    // Allow nested ternary expressions
    'no-nested-ternary': 'off',
    // Allow while(true) loops
    'no-constant-condition': ['error', { checkLoops: false }],
    // Allow function hoisting for better readability (defining helpers at the bottom)
    'no-use-before-define': ['error', { functions: false, classes: true, variables: true }],
    // Allow continue statements in loops
    'no-continue': 'off',
  },
  overrides: [
    {
      files: ['tests/**/*.test.js', 'tests/**/*.spec.js'],
      rules: {
        // Test files often import mock modules that don't need extensions or have other exceptions
        'import/no-extraneous-dependencies': 'off',
      },
    },
  ],
};
