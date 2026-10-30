const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const run = require('util').promisify(execFile);
const root = path.resolve(__dirname, '..');
const electronDir = path.join(root, 'src/main/js/electron');
const resolveTool = name => require(require.resolve(name, { paths: [electronDir] }));
const [command, app, identity, planFile] = process.argv.slice(2);

function inspect() {
  const asar = resolveTool('@electron/asar');
  const metadata = JSON.parse(asar.extractFile(path.join(app, 'Contents/Resources/app.asar'), 'package.json'));
  const plist = resolveTool('plist');
  const framework = plist.parse(fs.readFileSync(path.join(app, 'Contents/Frameworks/Electron Framework.framework/Resources/Info.plist'), 'utf8'));
  const unexpectedFiles = asar.listPackage(path.join(app, 'Contents/Resources/app.asar'))
    .filter(file => /(^|\/)\.env($|\.)|(^|\/)credentials($|\.)|\.(key|p8|p12)$/.test(file));
  return { appVersion: metadata.version, electronVersion: framework.CFBundleShortVersionString || framework.CFBundleVersion, unexpectedFiles };
}

async function main() {
  if (command === 'inspect') { console.log(JSON.stringify(inspect())); return; }
  if (command !== 'sign' || !identity?.startsWith('Developer ID Application: ')) throw new Error('Use the macos-release.py entry point');
  const plan = JSON.parse(fs.readFileSync(planFile, 'utf8'));
  const codeFiles = new Set(plan.nativeFiles.map(file => path.join(app, file)));
  const interpreter = fs.realpathSync(path.join(app, 'Contents/Resources/python-runtime/bin/python'));
  const entitlements = path.join(root, 'scripts/entitlements');
  const entitlementFor = file => path.join(entitlements, file === interpreter ? 'python.plist' : 'electron.plist');
  // Individual Mach-O signatures are independent. Bound timestamp requests and
  // finish every file before sealing helper/framework/application containers.
  const native = [...codeFiles];
  let cursor = 0;
  await Promise.all(Array.from({ length: Math.min(8, native.length) }, async () => {
    while (cursor < native.length) {
      const file = native[cursor++];
      await run('/usr/bin/codesign', ['--force', '--sign', identity, '--timestamp', '--options', 'runtime', '--entitlements', entitlementFor(file), file]);
    }
  }));
  console.log(`Signed ${native.length} native files; sealing app containers`);
  const { sign } = resolveTool('@electron/osx-sign');
  await sign({
    app, identity, platform: 'darwin', type: 'distribution', version: inspect().electronVersion,
    preAutoEntitlements: false, preEmbedProvisioningProfile: false, gatekeeperAssess: false,
    // Exclude data, Mach-O object fixtures and symlink aliases; sign actual code.
    // One predicate keeps the code/data distinction explicit.
    ignore: file => {
      if (fs.lstatSync(file).isSymbolicLink()) return true;
      if (file === app || /\.(app|framework)$/.test(file)) return false;
      return true; // Native files were signed above; only containers remain.
    },
    optionsForFile: file => ({
      hardenedRuntime: true,
      entitlements: entitlementFor(file),
    }),
  });
}
main().catch(error => { console.error(error); process.exitCode = 1; });
