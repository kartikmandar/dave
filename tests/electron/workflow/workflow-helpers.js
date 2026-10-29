const { _electron: electron } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs/promises');
const http = require('http');
const net = require('net');
const os = require('os');
const path = require('path');

const projectRoot = path.resolve(__dirname, '../../..');
const pythonPath = path.join(projectRoot, '.pixi/envs/default', process.platform === 'win32' ? 'python.exe' : 'bin/python');

async function runPython(args, options = {}) {
  const child = spawn(pythonPath, args, { cwd: projectRoot, ...options });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', data => { stdout += data; });
  child.stderr.on('data', data => { stderr += data; });
  let timer;
  try {
    await Promise.race([
      new Promise((resolve, reject) => {
        child.once('error', reject);
        child.once('exit', code => code === 0 ? resolve() : reject(new Error(`Python exited ${code}\n${stdout}\n${stderr}`)));
      }),
      new Promise((resolve, reject) => {
        timer = setTimeout(() => reject(new Error('Scientific fixture generation timed out')), 60000);
      }),
    ]);
  } finally {
    clearTimeout(timer);
    await stopChild(child);
  }
  return stdout;
}

async function availablePort() {
  const reservation = net.createServer();
  await new Promise((resolve, reject) => {
    reservation.once('error', reject);
    reservation.listen(0, '127.0.0.1', resolve);
  });
  const port = reservation.address().port;
  await new Promise(resolve => reservation.close(resolve));
  return port;
}

function health(url) {
  return new Promise((resolve, reject) => {
    const request = http.get(`${url}/health`, response => {
      let body = '';
      response.on('data', data => { body += data; });
      response.on('end', () => {
        try { resolve({ status: response.statusCode, body: JSON.parse(body) }); }
        catch (error) { reject(error); }
      });
    });
    request.once('error', reject);
    request.setTimeout(1000, () => request.destroy(new Error('Health check timed out')));
  });
}

async function stopChild(child) {
  if (!child || !child.pid || child.exitCode !== null || child.signalCode !== null) return;
  const stopped = new Promise(resolve => child.once('exit', resolve));
  child.kill('SIGTERM');
  let timer;
  await Promise.race([stopped, new Promise(resolve => { timer = setTimeout(resolve, 5000); })]);
  clearTimeout(timer);
  if (child.exitCode === null && child.signalCode === null) {
    child.kill('SIGKILL');
    await stopped;
  }
}

class WorkflowApp {
  constructor(directory) {
    this.directory = directory;
    this.server = null;
    this.app = null;
    this.page = null;
    this.pageErrors = [];
    this.serverOutput = '';
  }

  static async create() {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'dave-electron-workflow-'));
    const app = new WorkflowApp(directory);
    const source = path.join(projectRoot, 'src/main');
    const runtime = path.join(directory, 'src/main');
    await fs.mkdir(runtime, { recursive: true });
    await fs.cp(path.join(source, 'python'), path.join(runtime, 'python'), {
      recursive: true,
      filter: async item => !['__pycache__', 'uploadeddataset'].includes(path.basename(item))
        && ((await fs.stat(item)).isDirectory() || item.endsWith('.py')),
    });
    await fs.cp(path.join(source, 'resources'), path.join(runtime, 'resources'), { recursive: true });
    await fs.mkdir(path.join(directory, 'downloads'), { recursive: true });
    app.datasetDirectory = path.join(directory, 'dataset');
    await runPython([path.join(projectRoot, 'tests/electron/resources/generate_workflow_reference.py'), '--output-dir', app.datasetDirectory]);
    app.reference = JSON.parse(await fs.readFile(path.join(app.datasetDirectory, 'reference.json'), 'utf8'));
    return app;
  }

  async launch() {
    if (process.env.DAVE_PACKAGED_APP) return this.launchPackaged();
    let port;
    do { port = await availablePort(); } while (this.url === `http://127.0.0.1:${port}`);
    this.url = `http://127.0.0.1:${port}`;
    const runtimePython = path.join(this.directory, 'src/main/python');
    this.server = spawn(pythonPath, ['-u', path.join(runtimePython, 'server.py'), this.directory, runtimePython, String(port), 'electron-workflow'], {
      cwd: this.directory,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });
    this.server.stdout.on('data', data => { this.serverOutput += data; });
    this.server.stderr.on('data', data => { this.serverOutput += data; });
    let serverError;
    this.server.once('error', error => { serverError = error; });
    const deadline = Date.now() + 60000;
    let ready = false;
    while (Date.now() < deadline) {
      if (serverError) throw serverError;
      if (this.server.exitCode !== null) throw new Error(`Server exited before ready:\n${this.serverOutput}`);
      try {
        const result = await health(this.url);
        if (result.status === 200 && result.body.version === 'electron-workflow') { ready = true; break; }
      } catch (_) { /* Wait for this owned process to bind. */ }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    if (!ready) throw new Error(`Server readiness timed out:\n${this.serverOutput}`);
    const args = [`--user-data-dir=${path.join(this.directory, 'electron-profile')}`];
    if (process.platform === 'linux' && process.env.CI) args.push('--no-sandbox');
    args.push(path.join(projectRoot, 'src/main/js/electron/main.js'));
    this.app = await electron.launch({
      args,
      env: { ...process.env, NODE_ENV: 'development', DAVE_TEST_MODE: 'true', PYTHON_URL: this.url },
      timeout: 60000,
    });
    const observedPages = new WeakSet();
    const observePage = page => {
      if (observedPages.has(page)) return;
      observedPages.add(page);
      page.on('pageerror', error => { this.pageErrors.push(error.message); });
    };
    this.app.on('window', observePage);
    this.app.windows().forEach(observePage);
    await this.app.firstWindow();
    const navigationDeadline = Date.now() + 45000;
    while (Date.now() < navigationDeadline) {
      this.page = this.app.windows().find(page => !page.isClosed() && page.url().startsWith(this.url));
      if (this.page) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    if (!this.page) throw new Error('Electron did not navigate from the splash to the backend');
    await this.page.waitForFunction(() => typeof tabPanels !== 'undefined' && tabPanels.length === 1 && typeof theService !== 'undefined');
    await this.app.evaluate(({ session }, { downloadsDirectory, separator }) => {
      global.workflowDownloads = [];
      session.defaultSession.on('will-download', (event, item) => {
        const destination = downloadsDirectory + separator + item.getFilename();
        item.setSavePath(destination);
        item.once('done', (doneEvent, state) => global.workflowDownloads.push({ destination, state }));
      });
    }, { downloadsDirectory: path.join(this.directory, 'downloads'), separator: path.sep });
    return this.page;
  }

  async downloads() {
    return this.app.evaluate(() => global.workflowDownloads);
  }

  async launchPackaged() {
    const executable = path.resolve(process.env.DAVE_PACKAGED_APP, 'Contents/MacOS/dave');
    const wrapper = path.join(this.directory, 'launch-packaged.sh');
    const profile = `(version 1)(allow default)(deny file-read* (subpath ${JSON.stringify(projectRoot)}))(deny file-read* (subpath "/opt/homebrew"))`;
    const quote = value => "'" + value.replace(/'/g, "'\\''") + "'";
    await fs.writeFile(wrapper, '#!/bin/sh\nexec /usr/bin/sandbox-exec -p ' + quote(profile) + ' ' + quote(executable) + ' "$@"\n', { mode: 0o755 });
    this.app = await electron.launch({
      executablePath: wrapper,
      // macOS cannot nest Chromium's Seatbelt sandbox inside sandbox-exec.
      // The outer validation sandbox denies checkout/developer-library reads.
      args: ['--no-sandbox', `--user-data-dir=${path.join(this.directory, 'packaged-profile')}`],
      cwd: this.directory,
      env: { HOME: os.homedir(), TMPDIR: os.tmpdir(), PATH: '/usr/bin:/bin:/usr/sbin:/sbin' },
      timeout: 180000,
    });
    const observe = page => page.on('pageerror', error => this.pageErrors.push(error.message));
    this.app.on('window', observe);
    this.app.windows().forEach(observe);
    this.page = await this.app.firstWindow({ timeout: 180000 });
    await this.page.waitForURL(/^http:\/\/127\.0\.0\.1:/, { timeout: 180000 });
    this.url = new URL(this.page.url()).origin;
    await this.page.waitForFunction(() => typeof tabPanels !== 'undefined' && tabPanels.length === 1);
    const status = await this.page.evaluate(() => window.electronAPI.server.status());
    if (!status.connected || !status.processRunning || !status.pid) throw new Error('Bundled backend did not start');
    this.server = { pid: status.pid, exitCode: 0 };
    await this.app.evaluate(({ session }, directory) => {
      global.workflowDownloads = [];
      session.defaultSession.on('will-download', (event, item) => {
        const destination = directory + '/' + item.getFilename();
        item.setSavePath(destination);
        item.once('done', (event, state) => global.workflowDownloads.push({ destination, state }));
      });
    }, path.join(this.directory, 'downloads'));
    return this.page;
  }

  async close() {
    try {
      if (this.app) {
        await this.app.close();
        this.app = null;
      }
    } finally {
      await stopChild(this.server);
      this.server = null;
      await fs.writeFile(path.join(this.directory, 'server-output.log'), this.serverOutput);
    }
  }
}

module.exports = { WorkflowApp, projectRoot };
