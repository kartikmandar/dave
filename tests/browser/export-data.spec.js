const { test, expect } = require('@playwright/test');
const fs = require('fs/promises');
const path = require('path');

const resourcesPath = path.resolve(__dirname, '../../src/main/resources');

test.beforeEach(async ({ page }) => {
  await page.setContent('<!doctype html><html><body></body></html>');
  for (const script of [
    'external/jquery-4.0.0.min.js',
    'external/jquery-ui-1.14.1.min.js',
    'logPanel.js',
    'config.js',
    'common.js',
    'htmlControls.js',
    'tabPanels/tabpanel.js',
    'plots/plotter.js',
    'plots/plot.js',
    'plots/plotWithSettings.js',
    'plots/lcPlot.js',
    'plots/pdsPlot.js',
    'plots/agnPlot.js',
    'plots/dynSpPlot.js'
  ]) {
    await page.addScriptTag({ path: path.join(resourcesPath, 'static/scripts', script) });
  }
});

async function exportCsv(page, data, annotations = []) {
  const downloadPromise = page.waitForEvent('download');
  await page.evaluate(({ data, annotations }) => {
    const plot = new Plot('exportRegression', { styles: { title: 'Scientific data' } });
    plot.data = data;
    plot.annotations = annotations;
    plot.saveAsCSV();
  }, { data, annotations });
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('Scientific data.csv');
  return fs.readFile(await download.path(), 'utf8');
}

test('lightcurve CSV downloads the numerical times, rates and uncertainties', async ({ page }) => {
  const csv = await exportCsv(page, [
    { values: [0.125, 0.375, 0.625] },
    { values: [40.25, 32.5, 50.75] },
    { values: [1.234567, 2.345678, 3.456789] },
    { values: [0] },
    { values: [1] }
  ]);
  expect(csv).toBe('0.125,40.25,1.234567,\n0.375,32.5,2.345678,\n0.625,50.75,3.456789,\n');
});

test('single-frequency PDS export does not mistake duration metadata for a data column', async ({ page }) => {
  const csv = await exportCsv(page, [
    { values: [0.25] },
    { values: [2.345678], error_values: [0.123456] },
    { values: [64] },
    { values: [''] }
  ]);
  expect(csv).toBe('0.25,2.345678,0.123456,\n');
});

test('CSV download keeps annotation hash characters and subsequent numerical rows', async ({ page }) => {
  const csv = await exportCsv(page, [
    { values: [0.25, 0.5] },
    { values: [2.5, 4.75], error_values: [0.1, 0.2] },
    { values: [64] },
    { values: [''] }
  ], [{ x: 0.25, text: 'Peak #1' }]);
  expect(csv).toBe("0.25,2.5,0.1,'Peak #1'\n0.5,4.75,0.2,\n");
});

test('AGN CSV exporter writes raw numerical rows without URI escapes', async ({ page }) => {
  const downloadPromise = page.waitForEvent('download');
  await page.evaluate(() => {
    const plot = new AgnPlot('agnExportRegression', {
      dt: 0.25, styles: { title: 'AGN', labels: ['Time', 'Variability'] }
    });
    plot.data = [{ values: [0.25, 0.5] }, { values: [1.234567, 2.345678] }];
    plot.saveAsCSV();
  });
  const download = await downloadPromise;
  expect(await fs.readFile(await download.path(), 'utf8'))
    .toBe('0.25,1.234567\n0.5,2.345678\n');
});

test('dynamical spectrum CSV exporter keeps time, frequency and power columns', async ({ page }) => {
  const downloadPromise = page.waitForEvent('download');
  await page.evaluate(() => {
    const plot = new DynSpPlot('dynamicExportRegression', {
      dt: 0.25, styles: { title: 'Dynamical spectrum', labels: ['Time', 'Frequency', 'Power'] }
    });
    plot.data = [
      { values: [0.25, 0.5] },
      { values: [{ values: [1.234567, 2.345678] }, { values: [3.456789, 4.567891] }] },
      { values: [4, 8] }
    ];
    plot.saveAsCSV();
  });
  const download = await downloadPromise;
  expect(await fs.readFile(await download.path(), 'utf8'))
    .toBe('4,0.25,1.234567\n4,0.5,2.345678\n8,0.25,3.456789\n8,0.5,4.567891\n');
});
