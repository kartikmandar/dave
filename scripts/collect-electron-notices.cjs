const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const asar = require(require.resolve('@electron/asar', { paths: [path.join(root, 'src/main/js/electron')] }));
const [app, output] = process.argv.slice(2).map(value => path.resolve(value));
if (output === app || output.startsWith(app + path.sep)) throw new Error('Stage notices outside the signed app');
fs.mkdirSync(output, { recursive: true });
const archive = path.join(app, 'Contents/Resources/app.asar');
const entries = asar.listPackage(archive).map(name => name.replace(/^\//, ''));
const packages = entries.filter(name => /(^|\/)node_modules\/(?:@[^/]+\/)?[^/]+\/package\.json$/.test(name));
const records = [];
for (const metadataFile of packages) {
  const directory = path.posix.dirname(metadataFile);
  const metadata = JSON.parse(asar.extractFile(archive, metadataFile));
  const licenses = entries.filter(name => name.startsWith(directory + '/') &&
    !name.slice(directory.length + 1).includes('node_modules/') &&
    /(^|\/)(licen[cs]e[^/]*|notice[^/]*|copying[^/]*)$/i.test(name) &&
    !/\.(pem|key|p8|p12)$/i.test(name));
  const files = [];
  for (const name of licenses) {
    const relative = name.slice(directory.length + 1);
    let data;
    try { data = asar.extractFile(archive, name); } catch (_) { continue; } // Directory entry.
    const destination = path.join(output, 'npm', directory.replaceAll('/', '__'), relative);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, data);
    files.push({ path: path.relative(output, destination), sha256: crypto.createHash('sha256').update(data).digest('hex') });
  }
  records.push({ name: metadata.name, version: metadata.version, license: metadata.license, archivePath: directory, licenseFiles: files });
}
const plist = require(require.resolve('plist', { paths: [path.join(root, 'src/main/js/electron')] }));
const bundledVersion = plist.parse(fs.readFileSync(path.join(app, 'Contents/Frameworks/Electron Framework.framework/Resources/Info.plist'), 'utf8')).CFBundleVersion;
const electronPackage = require(path.join(root, 'src/main/js/electron/node_modules/electron/package.json'));
if (electronPackage.version !== bundledVersion) throw new Error('Electron notice version does not match bundled framework');
for (const filename of ['LICENSE', 'LICENSES.chromium.html']) {
  const destination = path.join(output, 'electron', filename);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(path.join(root, 'src/main/js/electron/node_modules/electron/dist', filename), destination);
}
fs.copyFileSync(path.join(app, 'Contents/Resources/LICENSE'), path.join(output, 'DAVE-LICENSE.txt'));
fs.writeFileSync(path.join(output, 'electron-components.json'), JSON.stringify({ electronVersion: bundledVersion, npmPackages: records }, null, 2) + '\n');
console.log(JSON.stringify({ electronVersion: bundledVersion, npmPackages: records.length, missingLicenseText: records.filter(record => !record.licenseFiles.length).map(record => record.name) }));
