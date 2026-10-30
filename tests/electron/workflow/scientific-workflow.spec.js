const { test, expect } = require('@playwright/test');
const fs = require('fs/promises');
const path = require('path');
const { WorkflowApp } = require('./workflow-helpers');

function assertArrayClose(actual, expected, description, tolerance = 1e-6) {
  expect(actual.length, `${description}: length`).toBe(expected.length);
  for (let index = 0; index < expected.length; index++) {
    expect(Number.isFinite(actual[index]), `${description}[${index}] is finite`).toBe(true);
    expect(Math.abs(actual[index] - expected[index]), `${description}[${index}]`).toBeLessThanOrEqual(tolerance);
  }
}

async function plotState(page) {
  return page.evaluate(() => {
    const tab = tabPanels.find(tab => tab.projectConfig && tab.projectConfig.hasSchema());
    if (!tab) return null;
    const lc = tab.outputPanel.plots.find(plot => plot.$html.hasClass('LcPlot'));
    const pds = tab.outputPanel.plots.find(plot => plot.$html.hasClass('PDSPlot'));
    return {
      binSize: tab.projectConfig.binSize,
      binInput: tab.toolPanel.binSelector.fromInput.attr('id'),
      filename: tab.projectConfig.filename,
      plotIds: tab.outputPanel.plots.map(plot => plot.id),
      lc: { id: lc.id, ready: !lc.isLoading && lc.data !== null, data: lc.data },
      pds: { id: pds.id, ready: !pds.isLoading && pds.data !== null, visible: pds.isVisible, config: pds.plotConfig, data: pds.data },
    };
  });
}

async function waitForReadyPlots(page, parameters) {
  await expect.poll(async () => {
    const state = await plotState(page);
    return state && state.lc.ready && state.pds.ready && state.binSize === parameters.dt
      && state.pds.config.type === parameters.pds_type
      && state.pds.config.segment_size === parameters.segment_size;
  }).toBe(true);
  return plotState(page);
}

function verifyPlots(state, reference) {
  expect(state.binSize).toBe(reference.parameters.dt);
  expect(state.pds.config.type).toBe('Avg');
  expect(state.pds.config.norm).toBe(reference.parameters.norm);
  expect(state.pds.config.segment_size).toBe(reference.parameters.segment_size);
  expect(state.pds.config.nsegm).toBe(reference.pds.m);
  expect(state.pds.config.dt).toBe(reference.parameters.dt);
  assertArrayClose(state.lc.data[0].values, reference.lightcurve.time, 'lightcurve time');
  assertArrayClose(state.lc.data[1].values, reference.lightcurve.countrate, 'lightcurve rate');
  assertArrayClose(state.lc.data[2].values, reference.lightcurve.countrate_err, 'lightcurve uncertainty');
  assertArrayClose(state.pds.data[0].values, reference.pds.freq, 'PDS frequency');
  assertArrayClose(state.pds.data[1].values, reference.pds.power, 'PDS power');
  assertArrayClose(state.pds.data[1].error_values, reference.pds.power_err, 'PDS uncertainty');
}

async function savePlotCsv(app, plotId) {
  const before = (await app.downloads()).length;
  await app.page.locator(`[id="${plotId}"] .btnSave`).click();
  await app.page.getByRole('button', { name: 'Save as CSV', exact: true }).click();
  await expect.poll(async () => (await app.downloads()).length).toBe(before + 1);
  const download = (await app.downloads())[before];
  expect(download.state).toBe('completed');
  return download.destination;
}

async function verifyCsv(filename, columns) {
  const text = await fs.readFile(filename, 'utf8');
  const rows = text.trimEnd().split(/\r?\n/).map(line => line.split(','));
  expect(rows.length).toBe(columns[0].length);
  for (const row of rows) expect(row.length).toBe(columns.length + 1); // final annotation column
  for (let column = 0; column < columns.length; column++) {
    assertArrayClose(rows.map(row => Number(row[column])), columns[column], `CSV column ${column}`);
  }
}

test('imports, analyzes, exports and reproduces a saved workspace against Stingray', async ({}, testInfo) => {
  const app = await WorkflowApp.create();
  testInfo.annotations.push({ type: 'artifacts', description: app.directory });
  try {
    let page = await app.launch();
    const reference = app.reference;
    await page.evaluate(() => { logInfo('Licensed log panel ready'); Logger.error('Diagnostic level check'); });
    await page.locator('#loggerTab').click();
    await expect(page.locator('#loggerContainer')).toHaveCSS('bottom', '0px');
    await expect(page.locator('#logger .LogError').last()).toContainText('Diagnostic level check');
    await page.locator('#loggerTab').click();
    await expect(page.locator('#loggerContainer')).toHaveCSS('bottom', '-215px');
    const requests = [];
    const observeRequests = activePage => activePage.on('request', request => {
      if (request.method() === 'POST' && /\/get_(lightcurve|power_density_spectrum)$/.test(request.url())) {
        requests.push({ url: request.url(), body: request.postDataJSON() });
      }
    });
    observeRequests(page);

    // Choose a file through the existing button and native file-input workflow.
    const importChooser = page.waitForEvent('filechooser');
    await page.locator('.btnChoose:visible').click();
    await (await importChooser).setFiles(path.join(app.datasetDirectory, 'source.evt'));
    await page.waitForFunction(() => tabPanels[0].projectConfig.hasSchema());
    expect(await page.evaluate(() => tabPanels[0].projectConfig.schema.getEventsCount())).toBe(reference.source.event_count);
    expect(await page.evaluate(() => tabPanels[0].projectConfig.filename)).toBe(path.join(app.datasetDirectory, 'source.evt'));
    console.log('Workflow: imported deterministic event file');

    await page.locator('.filterBtn:visible').click();
    let state = await plotState(page);
    expect(new Set(state.plotIds).size, 'Every plot must have a unique ID for selection and workspace restore').toBe(state.plotIds.length);
    await page.locator(`[id="${state.binInput}"]`).fill(String(reference.parameters.dt));
    await page.locator(`[id="${state.binInput}"]`).press('Tab');
    await page.locator('.btnRefresh:visible').first().click();
    await expect.poll(async () => (await plotState(page)).lc.data?.[0]?.values.length).toBe(reference.lightcurve.time.length);
    state = await plotState(page);
    assertArrayClose(state.lc.data[1].values, reference.lightcurve.countrate, 'typed-bin lightcurve rate');
    console.log('Workflow: typed-bin lightcurve matches Stingray');

    // Enable the existing PDS card from Analysis, then edit its actual settings.
    await page.locator('.analyzeBtn:visible').click();
    await page.locator('.analyzeContainer:visible .Section.PDSPlot .switch-btn').click();
    await page.locator(`.btnShow[plotId="${state.pds.id}"]`).click();
    await expect.poll(async () => (await plotState(page)).pds.ready).toBe(true);
    console.log('Workflow: enabled PDS card');
    await page.locator(`[id="${state.pds.id}"] button[title="Open plot settings"]`).click();
    expect((await plotState(page)).binSize).toBe(reference.parameters.dt);
    const settings = page.locator(`[id="${state.pds.id}"] .settings`);
    await settings.locator('label[for$="_pdsType_Avg"]').click();
    await settings.locator('input[id$="_segmSelector"]').fill(String(reference.parameters.segment_size));
    await settings.locator('input[id$="_segmSelector"]').press('Tab');
    await settings.locator('label[for$="_pdsNorm_leahy"]').click();
    expect((await plotState(page)).binSize).toBe(reference.parameters.dt);
    await page.locator(`[id="${state.pds.id}"] button[title="Close plot settings"]`).click();
    state = await waitForReadyPlots(page, reference.parameters);
    verifyPlots(state, reference);
    console.log('Workflow: averaged PDS and uncertainties match Stingray');
    expect(requests.some(request => request.url.endsWith('/get_lightcurve') && request.body.dt === reference.parameters.dt)).toBe(true);
    expect(requests.some(request => request.url.endsWith('/get_power_density_spectrum')
      && request.body.dt === reference.parameters.dt && request.body.type === 'Avg'
      && request.body.segment_size === reference.parameters.segment_size && request.body.norm === reference.parameters.norm)).toBe(true);
    await expect(page.locator(`[id="plot_${state.lc.id}"] .main-svg`).first()).toBeVisible();
    await expect(page.locator(`[id="plot_${state.pds.id}"] .main-svg`).first()).toBeVisible();

    const lcCsv = await savePlotCsv(app, state.lc.id);
    const pdsCsv = await savePlotCsv(app, state.pds.id);
    await verifyCsv(lcCsv, [reference.lightcurve.time, reference.lightcurve.countrate, reference.lightcurve.countrate_err]);
    await verifyCsv(pdsCsv, [reference.pds.freq, reference.pds.power, reference.pds.power_err]);
    console.log('Workflow: exported CSV files match Stingray');

    // Exercise the existing plot menu, real Plotly renderer and real download session.
    for (const [label, signature] of [['Save as PNG', [137, 80, 78, 71]], ['Save as PDF', [37, 80, 68, 70]]]) {
      const before = (await app.downloads()).length;
      await page.locator(`[id="${state.lc.id}"] .btnSave`).click();
      await page.getByRole('button', { name: label, exact: true }).click();
      await expect.poll(async () => (await app.downloads()).length).toBe(before + 1);
      const imageDownload = (await app.downloads())[before];
      expect(imageDownload.state).toBe('completed');
      const bytes = await fs.readFile(imageDownload.destination);
      expect([...bytes.subarray(0, 4)]).toEqual(signature);
      expect(bytes.length).toBeGreaterThan(1000);
      const image = await app.app.evaluate(({ nativeImage }, descriptor) => {
        let contents = process.getBuiltinModule('node:fs').readFileSync(descriptor.filename);
        if (descriptor.pdf) {
          const start = contents.indexOf(Buffer.from([255, 216, 255]));
          const end = contents.lastIndexOf(Buffer.from([255, 217]));
          contents = contents.subarray(start, end + 2);
        }
        const value = nativeImage.createFromBuffer(contents);
        const pixels = value.toBitmap();
        let blue = 0;
        for (let offset = 0; offset < pixels.length; offset += 4) {
          if (pixels[offset] > pixels[offset + 2] + 40 && pixels[offset] > pixels[offset + 1] + 20) blue++;
        }
        return { empty: value.isEmpty(), size: value.getSize(), blue };
      }, { filename: imageDownload.destination, pdf: label === 'Save as PDF' });
      expect(image.empty).toBe(false);
      expect(image.size.width).toBeGreaterThan(100);
      expect(image.size.height).toBeGreaterThan(100);
      expect(image.blue).toBeGreaterThan(100);
      await testInfo.attach(label, { path: imageDownload.destination });
      expect(new URL(page.url()).origin).toBe(app.url);
    }
    console.log('Workflow: log panel, PNG and PDF menu exports preserve the page');

    const downloadCount = (await app.downloads()).length;
    await page.locator('#right-navbar .saveWorkSpace').click();
    await expect.poll(async () => (await app.downloads()).length).toBe(downloadCount + 1);
    const workspaceDownload = (await app.downloads())[downloadCount];
    expect(workspaceDownload.state).toBe('completed');
    const workspacePath = workspaceDownload.destination;
    const workspace = JSON.parse(await fs.readFile(workspacePath, 'utf8'));
    expect(workspace[0].DOMAIN_URL).toBe(app.url);
    const savedPds = workspace[1].outputPanelConfig.find(plot => plot.class === 'PDSPlot');
    expect(savedPds.segment_size).toBe(reference.parameters.segment_size);
    expect(savedPds.type).toBe('Avg');
    expect(savedPds.dt).toBe(reference.parameters.dt);
    const oldUrl = app.url;
    const oldServerPid = app.server.pid;
    const previousRequestCount = requests.length;
    await page.screenshot({ path: path.join(app.directory, 'analyzed.png') });
    expect(app.pageErrors).toEqual([]);

    // A completely new Electron renderer and Python process must reload files
    // from disk and recalculate, without relying on the previous in-memory cache.
    await app.close();
    page = await app.launch();
    expect(app.server.pid).not.toBe(oldServerPid);
    expect(app.url).not.toBe(oldUrl);
    observeRequests(page);
    const chooserPromise = page.waitForEvent('filechooser');
    await page.locator('#right-navbar .loadWorkSpace').click();
    await (await chooserPromise).setFiles(workspacePath);
    state = await waitForReadyPlots(page, reference.parameters);
    verifyPlots(state, reference);
    expect(requests.slice(previousRequestCount).some(request => request.url.startsWith(app.url)
      && request.url.endsWith('/get_power_density_spectrum')
      && request.body.dt === reference.parameters.dt && request.body.type === 'Avg'
      && request.body.segment_size === reference.parameters.segment_size)).toBe(true);
    console.log('Workflow: fresh Electron/backend workspace recalculation matches Stingray');
    expect(await page.evaluate(() => CONFIG.DOMAIN_URL)).toBe(app.url);
    expect(app.pageErrors).toEqual([]);
    await page.screenshot({ path: path.join(app.directory, 'reopened.png') });
    await testInfo.attach('Stingray reference', { path: path.join(app.datasetDirectory, 'reference.json'), contentType: 'application/json' });
    await testInfo.attach('lightcurve CSV', { path: lcCsv, contentType: 'text/csv' });
    await testInfo.attach('averaged PDS CSV', { path: pdsCsv, contentType: 'text/csv' });
    await testInfo.attach('saved workspace', { path: workspacePath, contentType: 'application/json' });
    await testInfo.attach('reopened workspace', { path: path.join(app.directory, 'reopened.png'), contentType: 'image/png' });
  } catch (error) {
    if (app.page && !app.page.isClosed()) {
      await app.page.screenshot({ path: path.join(app.directory, 'failure.png') }).catch(() => {});
      await fs.writeFile(path.join(app.directory, 'failure-state.json'), JSON.stringify({ pageErrors: app.pageErrors, state: await plotState(app.page).catch(() => null) }, null, 2));
    }
    throw error;
  } finally {
    await app.close();
  }
});
