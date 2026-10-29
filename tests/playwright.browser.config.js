const { defineConfig } = require('@playwright/test');

// Browser regressions load local frontend assets directly. They do not start,
// stop, or connect to the Python server or use the Electron global setup.
module.exports = defineConfig({
  testDir: './browser',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  outputDir: './test-results/browser',
  use: {
    browserName: 'chromium',
    headless: true
  }
});
