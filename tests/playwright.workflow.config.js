const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './electron/workflow',
  testMatch: '*.spec.js',
  timeout: process.env.DAVE_PACKAGED_APP ? 360000 : 180000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  outputDir: './test-results/workflow',
});
