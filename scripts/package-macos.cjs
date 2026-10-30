const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const root = path.resolve(__dirname, '..');
const electronDir = path.join(root, 'src/main/js/electron');
const { execFileSync } = require('child_process');
const { packager } = require(require.resolve('@electron/packager', { paths: [electronDir] }));
const archive = path.join(root, 'build/standalone/python-runtime.tar.gz');
const manifest = path.join(root, 'build/standalone/runtime.json');
const runtime = path.join(root, 'build/standalone/python-runtime');
const appVersion = process.argv[2] || '2.0.0';
if (!/^\d+\.\d+\.\d+$/.test(appVersion)) throw new Error('Use a numeric major.minor.patch release version');
// Expand before signing: no executable is extracted or rewritten on customer Macs.
fs.rmSync(runtime, { recursive: true, force: true });
fs.mkdirSync(runtime, { recursive: true });
execFileSync('/usr/bin/tar', ['-xzf', archive, '-C', runtime]);
console.log(execFileSync('/usr/bin/python3', [path.join(root, 'scripts/prepare-macos-runtime.py'), runtime], { encoding: 'utf8' }).trim());
const stagedPython = path.join(root, 'build/standalone/backend/python');
fs.rmSync(stagedPython, { recursive: true, force: true });
fs.cpSync(path.join(root, 'src/main/python'), stagedPython, {
  recursive: true,
  filter: item => !['__pycache__', 'uploadeddataset'].includes(path.basename(item))
    && (fs.statSync(item).isDirectory() || item.endsWith('.py')),
});
const version = require(path.join(electronDir, 'node_modules/electron/package.json')).version;
const electronZip = path.join(root, `build/standalone/electron-v${version}-darwin-${process.arch}.zip`);
// Recreate the local Electron cache without AppleDouble files: Packager 20
// restores framework signatures, which reject stray ._ entries at framework roots.
fs.rmSync(electronZip, { force: true });
execFileSync('/usr/bin/ditto', ['-c', '-k', '--norsrc', '--noextattr', path.join(electronDir, 'node_modules/electron/dist'), electronZip]);
fs.writeFileSync(manifest, JSON.stringify({ layout: 'immutable-v1', sha256: crypto.createHash('sha256').update(fs.readFileSync(archive)).digest('hex') }));
packager({
  dir: electronDir, name: 'DAVE', executableName: 'dave', platform: 'darwin', arch: process.arch,
  electronVersion: require(path.join(electronDir, 'node_modules/electron/package.json')).version,
  electronZipDir: path.join(root, 'build/standalone'),
  out: path.join(root, 'build/standalone'), overwrite: true, asar: true, prune: true,
  appBundleId: 'science.stingray.dave', appVersion, buildVersion: appVersion,
  extendInfo: { LSApplicationCategoryType: 'public.app-category.education' },
  afterCopy: [({ buildPath }) => {
    const file = path.join(buildPath, 'package.json');
    const metadata = JSON.parse(fs.readFileSync(file, 'utf8'));
    metadata.version = appVersion;
    fs.writeFileSync(file, JSON.stringify(metadata, null, 2) + '\n');
  }],
  icon: path.join(root, 'src/main/resources/static/img/icon.icns'),
  ignore: [/^\/out($|\/)/, /^\/build($|\/)/, /__pycache__/, /\.log$/,
    /(^|\/)\.env($|\.)/, /(^|\/)credentials($|\.)/, /\.(pem|key|p8|p12)$/],
  // Packager's default extraResource copy rewrites relative symlinks to the
  // checkout. Preserve the runtime links verbatim so the app is relocatable.
  afterCopyExtraResources: [({ buildPath }) => {
    fs.cpSync(runtime, path.join(buildPath, 'DAVE.app/Contents/Resources/python-runtime'), {
      recursive: true, verbatimSymlinks: true,
    });
    // Stamp the staged resource, leaving development's label unchanged.
    fs.writeFileSync(path.join(buildPath, 'DAVE.app/Contents/Resources/resources/static/scripts/version.js'),
      'BUILD_VERSION=' + JSON.stringify(appVersion) + ';\n');
  }],
  extraResource: [manifest, stagedPython, path.join(root, 'src/main/resources'), path.join(root, 'LICENSE'), path.join(root, 'docs/FIRST_PARTY_COMPONENTS.md')],
}).then(paths => {
  if (!paths.length) throw new Error('Packager did not produce an application');
  for (const folder of paths) fs.copyFileSync(path.join(root, 'src/main/resources/static/img/icon.icns'), path.join(folder, 'DAVE.app/Contents/Resources/electron.icns'));
  console.log(paths.join('\n'));
}).catch(error => { console.error(error); process.exitCode = 1; });
