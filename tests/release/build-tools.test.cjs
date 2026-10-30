const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const base = path.resolve(__dirname, '../../src/main/js/electron/node_modules');
require('../../scripts/patch-build-tools.cjs').apply();

for (const entry of ['deepmerge/dist/cjs.js', 'deepmerge/dist/umd.js']) {
  test(`${entry} cannot poison the merged object's prototype`, () => {
    const merge = require(path.join(base, entry));
    const target = JSON.parse('{"__proto__":{"polluted":true},"settings":{"first":1}}');
    const result = merge(target, { settings: { second: 2 } });
    assert.equal(Object.getPrototypeOf(result), Object.prototype);
    assert.equal(result.polluted, undefined);
    assert.equal({}.polluted, undefined);
    assert.deepEqual(result.settings, { first: 1, second: 2 });
    assert.deepEqual(merge({ array: [1] }, { array: [2] }), { array: [1, 2] });
  });
}

test('patched ICNS parser rejects a zero-length chunk without hanging', () => {
  const code = `const { imageSize } = require(${JSON.stringify(path.join(base, 'image-size'))});
    const buffer = Buffer.alloc(24); buffer.write('icns'); buffer.writeUInt32BE(24,4);
    buffer.write('ic07',8); buffer.writeUInt32BE(0,12);
    try { imageSize(buffer); process.exitCode=2; } catch (_) { console.log('rejected'); }`;
  assert.match(execFileSync(process.execPath, ['-e', code], { timeout: 5000, encoding: 'utf8' }), /rejected/);
});

test('image parser still reads the actual DAVE icon', async () => {
  const { imageSizeFromFile } = require(require.resolve('image-size/fromFile', { paths: [base] }));
  const result = await imageSizeFromFile(path.resolve(__dirname, '../../src/main/resources/static/img/icon.icns'));
  assert.ok(result.width > 0 && result.height > 0);
});

