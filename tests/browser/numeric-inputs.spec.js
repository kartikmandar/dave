const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const resourcesPath = path.resolve(__dirname, '../../src/main/resources');
const template = fs.readFileSync(path.join(resourcesPath, 'templates/master_page.html'), 'utf8');
const jqueryAsset = template.match(/filename='scripts\/(external\/jquery-[\d.]+\.min\.js)'/)[1];
const jqueryUiAsset = template.match(/filename='scripts\/(external\/jquery-ui-[\d.]+\.min\.js)'/)[1];

test.beforeEach(async ({ page }) => {
  await page.setContent('<!doctype html><html><body><input id="numeric"><button>Apply</button></body></html>');
  // Use the app's actual vendored libraries and global scripts in template order.
  // Omit the application entry point, which requires a running Python backend.
  for (const script of [
    jqueryAsset,
    jqueryUiAsset,
    'logPanel.js',
    'config.js',
    'schema.js',
    'common.js',
    'htmlControls.js',
    'tabPanels/tabpanel.js',
    'selectors/binSelector.js',
    'plots/plotter.js',
    'plots/plot.js',
    'plots/plotWithSettings.js',
    'plots/lcPlot.js'
  ]) {
    await page.addScriptTag({ path: path.join(resourcesPath, 'static/scripts', script) });
  }
});

test('uses the active jQuery 4 asset without restoring its removed API', async ({ page }) => {
  expect(await page.evaluate(() => ({ version: $.fn.jquery, isNumeric: typeof $.isNumeric })))
    .toEqual({ version: '4.0.0', isNumeric: 'undefined' });
});

test('accepts typed decimal and scientific float values, including decimal commas', async ({ page }) => {
  for (const [text, expected] of [
    ['0.25', 0.25], ['0,25', 0.25], ['.5', 0.5], ['1.', 1],
    ['-.5', -0.5], ['+2', 2], [' 2.5 ', 2.5], ['1e-3', 0.001], ['2E+4', 20000]
  ]) {
    await page.locator('#numeric').fill(text);
    const result = await page.evaluate(() => {
      const input = $('#numeric');
      return { value: getInputFloatValue(input, 7), invalid: input.hasClass('wrongValue') };
    });
    expect(result, text).toEqual({ value: expected, invalid: false });
  }
  await page.locator('#numeric').fill('1,25');
  await page.evaluate(() => getInputFloatValue($('#numeric'), 7));
  await expect(page.locator('#numeric')).toHaveValue('1.25');
});

test('preserves integer truncation and the existing parseInt exponent behavior', async ({ page }) => {
  for (const [text, expected] of [['12.9', 12], ['-12.9', -12], ['12,9', 12], ['1e2', 1]]) {
    await page.locator('#numeric').fill(text);
    expect(await page.evaluate(() => getInputIntValue($('#numeric'), 7)), text).toBe(expected);
    await expect(page.locator('#numeric')).not.toHaveClass(/wrongValue/);
  }
});

test('rejects blank, nonfinite and malformed input while retaining the default', async ({ page }) => {
  for (const text of ['', '  ', 'NaN', 'Infinity', '-Infinity', '1e309', '0x10', '12foo', '1.2.3', '1,2,3', '1e', '--1']) {
    await page.locator('#numeric').fill(text);
    expect(await page.evaluate(() => getInputFloatValue($('#numeric'), 7)), text).toBe(7);
    await expect(page.locator('#numeric')).toHaveClass(/wrongValue/);
  }
  await page.locator('#numeric').fill('0.25');
  expect(await page.evaluate(() => getInputFloatValue($('#numeric'), 7))).toBe(0.25);
  await expect(page.locator('#numeric')).not.toHaveClass(/wrongValue/);
});

test('keeps cropped numeric controls clamped and updates their displayed values', async ({ page }) => {
  for (const [text, type, expected] of [
    ['12.9', 'float', 5], ['-12.9', 'float', 0], ['3.9', 'int', 3], ['bad', 'float', 1]
  ]) {
    await page.locator('#numeric').fill(text);
    expect(await page.evaluate((kind) => kind === 'int'
      ? getInputIntValueCropped($('#numeric'), 1, 0, 5)
      : getInputFloatValueCropped($('#numeric'), 1, 0, 5), type), text).toBe(expected);
    await expect(page.locator('#numeric')).toHaveValue(String(expected));
    await expect(page.locator('#numeric')).not.toHaveClass(/wrongValue/);
  }
});

test('typing a bin size changes the real selector and its change notification', async ({ page }) => {
  await page.evaluate(() => {
    window.numericSelector = new BinSelector('numericRegression', 'Bin size', 0.01, 10, 0.01, 1, function () {
      document.body.dataset.binSize = String(window.numericSelector.value);
    });
    document.body.append(window.numericSelector.$html[0]);
  });
  await page.locator('#from_numericRegression').fill('0,25');
  await page.locator('#from_numericRegression').press('Tab');
  expect(await page.evaluate(() => window.numericSelector.value)).toBe(0.25);
  await expect(page.locator('#from_numericRegression')).toHaveValue('0.25');
  await expect(page.locator('body')).toHaveAttribute('data-bin-size', '0.25');
});

test('converts CSV overlay numeric columns while retaining annotation text', async ({ page }) => {
  expect(await page.evaluate(() => extractDatafromCSVContents('1,2.5,0.1,peak\n2,3e1,0.2,trough')))
    .toEqual([[1, 2.5, 0.1, 'peak'], [2, 30, 0.2, 'trough']]);
});

test('extracts the energy range from real RATE-style FITS metadata', async ({ page }) => {
  expect(await page.evaluate(() => extractEnergyRangeTextRateTable({
    DSTYP1: 'PI', DSUNI1: 'eV', DSVAL1: '500:2000'
  }))).toBe('0.5 - 2 keV');
});

test('retains numeric overlay error columns and text annotations in the base plot', async ({ page }) => {
  const result = await page.evaluate(() => {
    const plot = new Plot('numericOverlay', { styles: { labels: ['Time', 'Counts'] } });
    const defaults = plot.getDefaultPlotlyConfig();
    plot.setExtraData([[1, 2], [10, 20], [0.1, 0.2], [0.3, 0.4], ['peak', 'trough']]);
    const config = plot.addExtraDataConfig({ data: [{ x: [1, 2], y: [10, 20] }] }, defaults);
    return {
      xErrors: config.data[0].error_x.array,
      yErrors: config.data[0].error_y.array,
      annotations: plot.annotations.map(annotation => annotation.text)
    };
  });
  expect(result).toEqual({ xErrors: [0.1, 0.2], yErrors: [0.3, 0.4], annotations: ['peak', 'trough'] });
});

test('retains numeric overlay error columns in a lightcurve plot', async ({ page }) => {
  const result = await page.evaluate(() => {
    const plot = new LcPlot('numericLightcurveOverlay', { styles: { labels: ['Time', 'Counts'] } });
    plot.extraData = [[1, 2], [10, 20], [0.1, 0.2]];
    return plot.addExtraDataConfig({ data: [] }, plot.getDefaultPlotlyConfig()).data[0].error_y.array;
  });
  expect(result).toEqual([0.1, 0.2]);
});
