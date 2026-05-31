import { defineConfig } from 'vitest/config';

// Coverage thresholds (signal: test_coverage_thresholds) are tuned for value
// over completeness: 80% lines/statements/functions, 70% branches. 100% is
// not the goal; depth of integration testing and clarity of unit tests are.
//
// retry: 2  (signal: flaky_test_detection) — surfaces transient flakiness in
// the CI log as retry counters and re-runs the test up to twice.
//
// reporters include 'verbose' (signal: test_performance_tracking) so test
// durations are visible in CI output.
export default defineConfig({
  test: {
    globals: false,
    include: ['tests/**/*.test.js', 'tests/integration/**/*.test.js'],
    exclude: ['node_modules/**', 'coverage/**', 'output/**', 'logs/**'],
    reporters: process.env.CI ? ['default', 'verbose'] : ['default'],
    retry: 2,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.js'],
      // Exclude entry-point/loader modules where coverage is exercised
      // through their callers rather than the modules themselves.
      exclude: ['src/cli.js', 'src/logger.js'],
      thresholds: {
        lines: 80,
        branches: 70,
        functions: 80,
        statements: 80,
      },
    },
  },
});
