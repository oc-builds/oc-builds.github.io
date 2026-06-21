// ESLint flat configuration for the CS360 Inventory Server.
// Author: Sanjay Chauhan
// Date: 2026-06-20
// CS499 Capstone final-portfolio polish of Enhancement One.
//
// Purpose: enforce a consistent style and catch common mistakes (unused
// variables, accidental debugging output) across the Node/Express backend.
// Run with `npm run lint` from the server/ directory.
//
// The legitimate startup/seed/error console output is allowed: console.warn and
// console.error are permitted everywhere, and the seed script is exempted from
// the no-console rule entirely because reporting demo credentials and seed
// progress to the terminal is its job.

import js from '@eslint/js';

export default [
  js.configs.recommended,
  {
    files: ['**/*.js'],
    ignores: ['node_modules/**'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        process: 'readonly',
        console: 'readonly',
      },
    },
    rules: {
      // Disallow stray debugging logs, but keep warnings and errors.
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'no-debugger': 'error',
      eqeqeq: ['error', 'always'],
      'prefer-const': 'error',
    },
  },
  {
    // The seed script's whole job is to print progress and demo credentials.
    files: ['seed.js'],
    rules: { 'no-console': 'off' },
  },
];
