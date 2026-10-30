const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const output = path.resolve(process.argv[2] || path.join(root, 'build/dependency-review'));
fs.mkdirSync(output, { recursive: true });
const patches = JSON.parse(fs.readFileSync(path.join(__dirname, 'build-tool-patches.json'), 'utf8'));
for (const entry of patches.entries) {
  const actual = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'src/main/js/electron/node_modules', entry.file))).digest('hex');
  if (actual !== entry.after) throw new Error(`Required build-tool patch is absent or modified: ${entry.file}`);
}
const allowedBackportFindings = new Set(['deepmerge', '@jest/core', 'create-jest', 'jest', 'jest-cli', 'jest-config']);
const results = [];
let failed = false;
for (const [name, directory, production] of [
  ['frontend-build', root, false],
  ['electron-build', path.join(root, 'src/main/js/electron'), false],
  ['electron-production', path.join(root, 'src/main/js/electron'), true],
  ['test-runner', path.join(root, 'tests'), false],
]) {
  const run = spawnSync('npm', ['audit', '--json', ...(production ? ['--omit=dev'] : [])], { cwd: directory, encoding: 'utf8' });
  if (!run.stdout) throw new Error(`npm audit unavailable: ${name}`);
  const report = JSON.parse(run.stdout);
  if (report.error || !report.metadata) throw new Error(`npm audit failed: ${name}`);
  fs.writeFileSync(path.join(output, name + '.json'), JSON.stringify(report, null, 2) + '\n');
  const findings = Object.values(report.vulnerabilities || {});
  const isVerifiedBackport = (item, seen = new Set()) => {
    if (!item || item.severity !== 'low' || !allowedBackportFindings.has(item.name) || seen.has(item.name)) return false;
    const next = new Set([...seen, item.name]);
    return item.via.length > 0 && item.via.every(cause => typeof cause === 'string'
      ? isVerifiedBackport(report.vulnerabilities[cause], next)
      : cause.url === 'https://github.com/advisories/GHSA-gcqx-w48m-w2h4' &&
        item.nodes.every(node => node === 'node_modules/deepmerge'));
  };
  const unaddressed = findings.filter(item => !(name === 'electron-build' && isVerifiedBackport(item)));
  if (unaddressed.length) failed = true;
  results.push({ name, registryCounts: report.metadata.vulnerabilities,
    locallyPatchedRegistryFindings: findings.filter(item => !unaddressed.includes(item)).map(item => item.name),
    unaddressed: unaddressed.map(item => ({ name: item.name, severity: item.severity })) });
}
const result = { registryScanOnly: true, verifiedLocalBackports: patches.entries, results,
  note: 'Registry counts are retained. The deepmerge backport is validated separately; npm has no upstream patched release to recognize. This does not audit already-vendored browser assets or certify the whole app.' };
fs.writeFileSync(path.join(output, 'summary.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(results, null, 2));
if (failed) process.exitCode = 1;
