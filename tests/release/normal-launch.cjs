// Run after the isolated scientific workflow to verify the normal launch path,
// without sandbox-exec or --no-sandbox. The supplied app is never modified.
const { _electron } = require('../node_modules/playwright');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');

(async () => {
  if (!process.env.DAVE_PACKAGED_APP) throw new Error('Set DAVE_PACKAGED_APP to an absolute .app path');
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'dave-normal-launch-'));
  let app;
  try {
    app = await _electron.launch({
      executablePath: path.join(process.env.DAVE_PACKAGED_APP, 'Contents/MacOS/dave'),
      args: [`--user-data-dir=${directory}`], cwd: os.tmpdir(),
      env: { HOME: os.homedir(), TMPDIR: os.tmpdir(), PATH: '/usr/bin:/bin:/usr/sbin:/sbin' },
      timeout: 180000,
    });
    const page = await app.firstWindow();
    await page.waitForURL(/^http:\/\/127\.0\.0\.1:/, { timeout: 180000 });
    const status = await page.evaluate(() => window.electronAPI.server.status());
    if (!status.connected || !status.processRunning) throw new Error('Bundled backend is unavailable');
    const state = await app.evaluate(({ app: electronApp, BrowserWindow }) => {
      const preferences = BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences();
      return { version: electronApp.getVersion(), nodeIntegration: preferences.nodeIntegration, webSecurity: preferences.webSecurity };
    });
    if (state.nodeIntegration !== false || state.webSecurity !== true) throw new Error('Window security preferences regressed');
    console.log(JSON.stringify({ normalLaunch: true, status, ...state }));
  } finally {
    if (app) await app.close();
    await fs.rm(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
