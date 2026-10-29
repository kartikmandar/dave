const path = require('path');
const fs = require('fs/promises');
const { execFile } = require('child_process');
const { promisify } = require('util');
const run = promisify(execFile);

async function prepareRuntime(resources, dataDirectory) {
  const manifest = JSON.parse(await fs.readFile(path.join(resources, 'runtime.json'), 'utf8'));
  if (manifest.layout === 'immutable-v1') {
    const directory = path.join(resources, 'python-runtime');
    await fs.access(path.join(directory, 'bin/python'));
    return directory;
  }
  if (manifest.layout) throw new Error(`Unsupported bundled runtime layout: ${manifest.layout}`);
  const directory = path.join(dataDirectory, 'runtimes', manifest.sha256.slice(0, 16));
  const marker = path.join(directory, '.ready');
  try { await fs.access(marker); return directory; } catch (_) { /* First launch. */ }
  await fs.rm(directory, { recursive: true, force: true });
  await fs.mkdir(directory, { recursive: true });
  await run('/usr/bin/tar', ['-xzf', path.join(resources, 'python-runtime.tar.gz'), '-C', directory], { timeout: 180000 });
  await run(path.join(directory, 'bin/python'), ['-E', '-s', path.join(directory, 'bin/conda-unpack')], { timeout: 180000 });
  await fs.writeFile(marker, manifest.sha256);
  return directory;
}

module.exports = { prepareRuntime };
