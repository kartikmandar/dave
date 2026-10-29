const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { prepareRuntime } = require('../../src/main/js/electron/bundled-runtime');

test('immutable runtime is returned without creating or modifying user data', async () => {
  const resources = await fs.mkdtemp(path.join(os.tmpdir(), 'dave-runtime-'));
  try {
    await fs.mkdir(path.join(resources, 'python-runtime/bin'), { recursive: true });
    await fs.writeFile(path.join(resources, 'python-runtime/bin/python'), 'runtime executable');
    await fs.writeFile(path.join(resources, 'runtime.json'), JSON.stringify({ layout: 'immutable-v1' }));
    const data = path.join(resources, 'absent-user-data');
    assert.equal(await prepareRuntime(resources, data), path.join(resources, 'python-runtime'));
    await assert.rejects(fs.access(data), { code: 'ENOENT' });
    assert.equal(await fs.readFile(path.join(resources, 'python-runtime/bin/python'), 'utf8'), 'runtime executable');
  } finally { await fs.rm(resources, { recursive: true, force: true }); }
});

test('unknown runtime layouts fail before extraction', async () => {
  const resources = await fs.mkdtemp(path.join(os.tmpdir(), 'dave-runtime-'));
  try {
    await fs.writeFile(path.join(resources, 'runtime.json'), JSON.stringify({ layout: 'future-v2' }));
    await assert.rejects(prepareRuntime(resources, resources), /Unsupported bundled runtime layout/);
  } finally { await fs.rm(resources, { recursive: true, force: true }); }
});
