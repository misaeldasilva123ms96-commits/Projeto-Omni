module.exports = [
  {
    ignores: [
      'node_modules/**',
      'frontend/**',
      'backend/**',
    ],
  },
  {
    files: ['src/**/*.js', 'js-runner/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'commonjs',
    },
    rules: {
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'no-undef': 'error',
    },
  },
];
