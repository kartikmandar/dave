// Version- and hash-checked fixes for build-only dependencies. No app code is patched.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const base = path.resolve(__dirname, '../src/main/js/electron/node_modules');
const manifestPath = path.join(__dirname, 'build-tool-patches.json');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const originals = {
  'appdmg/lib/appdmg.js': '79a540d3f10581e553e741caeb6d3b4b66213dde15e973e36890ea31e61e0153',
  'deepmerge/index.js': '12440c84957c1990ea2d5e33dc0091722dc1dc1585c6d20e0c780e568ffa9d30',
  'deepmerge/dist/cjs.js': '2e5160f84a1141bd927264afe4d15766f1e6cf07daef182b37ff53fea121de7d',
  'deepmerge/dist/umd.js': 'f33e6596482d1fb5c7c427f8ef92f2aa849eea9223acd974176b2fb27ddbf73a',
};

function transform(file, source) {
  if (file.startsWith('appdmg/')) {
    const original = "const sizeOf = require('image-size')";
    if (!source.includes(original)) throw new Error('Unknown appdmg image-size call');
    return source.replace(original,
      "// DAVE build compatibility: use the patched image-size 2.x file API.\n" +
      "const { imageSizeFromFile } = require('image-size/fromFile')\n" +
      "const sizeOf = (filename, callback) => imageSizeFromFile(filename).then(value => callback(null, value), callback)");
  }
  let count = 0;
  const result = source.replace(/^([ \t]*)destination\[key\] = (.*)$/gm, (_, indent, expression) => {
    count++;
    return indent + 'Object.defineProperty(destination, key, { value: ' + expression.replace(/;$/, '') +
      ', enumerable: true, writable: true, configurable: true });';
  });
  if (count !== 3) throw new Error('Unknown deepmerge assignment layout');
  return result;
}

function record() {
  const entries = Object.entries(originals).map(([file, before]) => {
    const source = fs.readFileSync(path.join(base, file), 'utf8');
    if (hash(source) !== before) throw new Error(`Refusing to approve unknown source: ${file}`);
    return { file, before, after: hash(transform(file, source)) };
  });
  fs.writeFileSync(manifestPath, JSON.stringify({ entries }, null, 2) + '\n');
}

function apply() {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  for (const entry of manifest.entries) {
    const file = path.join(base, entry.file);
    if (!fs.existsSync(file)) continue; // Production-only installs omit these build tools.
    const source = fs.readFileSync(file, 'utf8');
    if (hash(source) === entry.after) continue;
    if (entry.before !== originals[entry.file] || hash(source) !== entry.before) {
      throw new Error(`Build dependency changed; review patch before installing: ${entry.file}`);
    }
    const patched = transform(entry.file, source);
    if (hash(patched) !== entry.after) throw new Error(`Patch hash mismatch: ${entry.file}`);
    fs.writeFileSync(file, patched);
    console.log(`Applied reviewed build-tool patch: ${entry.file}`);
  }
}

if (require.main === module) {
  if (process.argv.includes('--record')) record();
  else apply();
}
module.exports = { apply, transform };
