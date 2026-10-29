const { test, expect } = require('@playwright/test');
const path = require('path');

const scriptsPath = path.resolve(__dirname, '../../src/main/resources/static/scripts');

test('plots created in the same millisecond have distinct DOM and workspace identities', async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-01-01T00:00:00Z'));
  await page.setContent('<div class="OutputPanelTemplate"><div class="outputPanelBody"></div></div><main></main>');
  for (const script of [
    'external/jquery-4.0.0.min.js', 'external/logger.js', 'common.js',
    'htmlControls.js', 'outputPanels/outputPanel.js'
  ]) {
    await page.addScriptTag({ path: path.join(scriptsPath, script) });
  }
  const ids = await page.evaluate(() => {
    const panel = new OutputPanel('workflowPanel', 'OutputPanelTemplate', $('main'));
    return Array.from({ length: 20 }, () => panel.generatePlotId('source.evt_PDS'));
  });
  expect(new Set(ids).size).toBe(ids.length);
  for (const id of ids) expect(id).toMatch(/^\w+$/);
});
