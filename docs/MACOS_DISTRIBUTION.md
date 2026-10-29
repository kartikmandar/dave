# macOS distribution

DAVE distributes directly as a ZIP containing `DAVE.app`. Users extract it and
drag the app to Applications. This is a Developer ID distribution, outside the
Mac App Store. The UI, scientific calculations, import/export dialogs and workspace
workflow remain the same. Updates currently require downloading a new release;
packaged automatic update checks remain disabled until a signed update feed exists.

## Account setup needed from the owner

1. Active paid Apple Developer Program membership and accepted account agreements.
2. Your **Team ID** (10 characters) and the developer/organization name users should
   see in Gatekeeper. Confirm that this account is authorized to distribute DAVE.
3. A **Developer ID Application** signing certificate, with its matching private
   key installed in this Mac's Keychain. Create/import it yourself using Xcode or
   Keychain Access. Provide the identity's display name, for example
   `Developer ID Application: Example Organization (ABCDEFGHIJ)`.
4. A validated **notarytool Keychain profile name**, for example `dave-notary`.
   Create this interactively in your own terminal:

   ```bash
   xcrun notarytool store-credentials dave-notary --apple-id YOUR_APPLE_ID --team-id YOUR_TEAM_ID --keychain "$HOME/Library/Keychains/login.keychain-db"
   ```

   Enter an Apple app-specific password at the terminal prompt. An App Store
   Connect API key stored with `notarytool store-credentials` is another option.
   Only the profile name is needed by the release script.
5. Confirm the public release version (the current candidate is `2.0.0`) and bundle
   ID `science.stingray.dave`. Keep that bundle ID stable for subsequent releases.
   Also confirm the public download destination and whether Intel builds are needed.

Do not paste passwords, private keys, `.p8`/`.p12` files or recovery codes into chat
or the repository. The scripts accept Keychain references, never secret files.
No Developer ID Installer certificate, App Store app record, provisioning profile,
or Mac App Store sandbox is required for this ZIP workflow.

Apple references: [Developer ID](https://developer.apple.com/developer-id/),
[notarization overview](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution),
[Keychain credential setup](https://developer.apple.com/documentation/technotes/tn3147-migrating-to-the-latest-notarization-tool).

## Build and inspect

Use macOS, Xcode Command Line Tools with `notarytool` and `stapler`, the locked
native Pixi environment, Node 22 or 24, and the build dependencies in
`scripts/macos-build-requirements.txt`. Build separately on Apple Silicon and Intel;
an arm64 Python environment cannot produce an Intel or universal app.

```bash
PYTHONPATH=build/macos-tools .pixi/envs/default/bin/python scripts/build-standalone-macos.py --node /path/to/node24 --version 2.0.0
python3 scripts/macos-release.py preflight --app build/standalone/DAVE-darwin-arm64/DAVE.app --node /path/to/node24 > build/standalone/release-preflight.json
```

The build expands Python before signing and writes matching bundle/build/embedded
package versions in the staged copy. It preserves source package metadata. The
runtime does not call `conda-unpack` or modify its own files on launch. Caches,
uploads and logs live in Application Support. All native executables, libraries
and Python extensions are visible to the signing and notarization tools.

Preflight rejects archived/mutable runtimes, inconsistent versions, unexpected
bundle IDs, external native dependencies/search paths and escaping symlinks.
It inventories native code and checks the Electron support policy. The supported
majors reviewed on **2026-10-29** are 43, 44 and 45; refresh that policy against
the [official releases](https://releases.electronjs.org/?channel=stable) before
future releases. The candidate uses Electron 43.8.4. Do not treat a stale major
allowlist as ongoing proof of security support.

## Sign a staging copy

```bash
python3 scripts/macos-release.py sign --app build/standalone/DAVE-darwin-arm64/DAVE.app --node /path/to/node24 --output build/release-2.0.0-arm64 --team-id ABCDEFGHIJ --identity 'Developer ID Application: Example Organization (ABCDEFGHIJ)'
```

This creates a separate `DAVE.app` and `signing-report.json`. Existing destinations
are refused. Native code is signed with secure timestamps and hardened runtime,
then `@electron/osx-sign` seals helper, framework and application containers from
the inside out. Timestamp requests are limited to eight concurrent native files.
Data files and symlink aliases are excluded.
Electron receives the JIT entitlement; Python also receives unsigned executable
memory for the LLVM/Numba JIT. No debugging or library-validation exemption is
requested. These entitlements require validation with the real Developer ID
signature; an unsigned scientific workflow cannot establish hardened-runtime
compatibility. There is no `--deep` signing shortcut.

```bash
python3 scripts/macos-release.py verify-signature --app build/release-2.0.0-arm64/DAVE.app
```

This checks each native signature, matching Developer ID team and hardened runtime
on executables; notarization and Gatekeeper acceptance are checked separately.

## Validate the signed app, then notarize

First run the complete packaged workflow on the signed staging app, including
Stingray comparison, light curve, averaged PDS, CSV export and save/reopen:

```bash
cd tests
DAVE_PACKAGED_APP=/absolute/path/to/build/release-2.0.0-arm64/DAVE.app npm run test:workflow
DAVE_PACKAGED_APP=/absolute/path/to/build/release-2.0.0-arm64/DAVE.app node release/normal-launch.cjs
```

Return to the repository root, then explicitly submit to Apple:

```bash
python3 scripts/macos-release.py notarize --app build/release-2.0.0-arm64/DAVE.app --node /path/to/node24 --output build/release-2.0.0-arm64 --keychain-profile dave-notary --keychain "$HOME/Library/Keychains/login.keychain-db"
```

The script uploads a temporary ZIP, waits for Apple, saves the submission result
and log, and requires status `Accepted`. It staples the ticket to the app,
validates the staple, checks signatures and Gatekeeper acceptance, and creates a
new distribution ZIP containing the stapled app. It extracts that ZIP into a
temporary directory and repeats signature, ticket and Gatekeeper validation.
ZIP files themselves cannot be
stapled. Outputs include the versioned ZIP, `SHA256SUMS` and `release-report.json`.
The submission ZIP is retained as evidence; distribute only the versioned ZIP.

If `notarytool` reports that it cannot find the profile, supply the same explicit
Keychain used for credential storage with `--keychain /absolute/path/to/login.keychain-db`.
The script passes that reference to Apple; it never reads credential files itself.
After correcting credentials, use `--reuse-submission` to verify and reuse the
existing upload ZIP. The script extracts it, verifies every native signature and
requires its app code-directory hash to match the current signed candidate before
uploading. A missing profile produces a clear diagnostic and is never recorded as
a successful submission.

If submission fails or times out, retain the output directory. Use `notarytool info`
and `notarytool log` with the saved submission ID and Keychain profile to diagnose
the existing submission. Do not discard the evidence or repeatedly resubmit an
unchanged rejected app. Use a fresh output directory for a new candidate.

If Apple is still processing after the submit command's 30-minute wait, keep the
same submission ID. To check that existing request and finish stapling/packaging
once it is Accepted, run:

```bash
python3 scripts/macos-release.py finalize --app build/release-2.0.0-arm64-candidate/DAVE.app --node /path/to/node24 --output build/release-2.0.0-arm64-candidate --submission-id 21f817d1-9801-495e-8b28-ad863f628fe1 --keychain-profile dave-notary --keychain "$HOME/Library/Keychains/login.keychain-db"
```

`finalize` never submits an archive. Pending requests remain pending; rejected or
unknown results cannot be stapled or labeled distributable. Once Apple accepts
the request, the command revalidates the signed app, fetches the log and performs
the same staple, Gatekeeper and final ZIP verification steps as `notarize`.

```bash
python3 scripts/macos-release.py verify --app build/release-2.0.0-arm64/DAVE.app
```

The scripts do not publish to GitHub, change account settings, import certificates,
or disable Gatekeeper. No unsigned or rejected app is labeled distributable.

## Public release gate

- Repeat the complete scientific workflow on the final signed/notarized app.
- Download the final ZIP through a browser on a separate clean Mac, retain its
  quarantine attribute, move the app to Applications, and launch through Finder.
  Also validate offline first launch with the stapled ticket. Do not remove
  quarantine or use “Open Anyway” as acceptance evidence.
- Confirm the oldest macOS version to advertise using actual target machines.
  Testing on this development Mac alone does not establish a minimum supported OS.
- Build and validate Intel separately before advertising Intel support.
- Review bundled dependency licenses/attributions and the final shipped files.
  The application LICENSE is included; that alone does not establish completion of
  all third-party notice obligations.
- Review production dependency audit results and the current Electron support
  window. Recheck Python/scientific dependency advisories for the release.
- Publish only the versioned, stapled ZIP and its checksum, with installation
  instructions, architecture, tested macOS versions and release notes.

The two legacy cross-platform workflows no longer build/upload macOS artifacts.
Their Linux/Windows behavior is retained. Their overlapping tag triggers still
need consolidation before adopting a single automated cross-platform release.
macOS publication is manual until that workflow and signing credentials are
explicitly configured. A signed app, Apple acceptance, a stapled ticket, a clean
Mac launch, and public publication are separate verification steps.

## Initial signed candidate evidence, 2026-10-29

This first snapshot predates the successful notarization recorded below.

The Apple Silicon candidate at `build/release-2.0.0-arm64-candidate/DAVE.app`
was signed with the existing `Developer ID Application: Kartik Mandar (BQN364P8SY)`
Keychain identity. All 1,004 native files passed signature verification with the
same Developer ID team; executable files enable hardened runtime. The candidate
uses bundle/package version `2.0.0` and Electron `43.8.4`.

A read-only copy at `/tmp/dave-signed-release-validation/DAVE.app` passed the full
isolated scientific workflow against Stingray, including exports and a fresh
workspace reopen. Normal launch without the test sandbox flag and an independent
signed Numba JIT calculation also passed. Testing was on macOS 27.2, arm64.
The 16 browser regressions and nine release/runtime safety regressions passed.

Evidence is recorded in `build/standalone/release-validation.json`,
`signed-workflow.log`, `signed-normal-launch.json`, `signed-jit.json`, and the
candidate directory's `signing-report.json`. Gatekeeper reports
`Unnotarized Developer ID`; no submission, staple, second-Mac acceptance test or
publication has occurred. A notarytool Keychain profile is still needed.

The production Node audit reported zero findings. The broader development/build
tool audit still reported 47 findings (including one critical `tar` advisory in
the legacy tool dependency tree); no blanket dependency-security clearance is
claimed. Review these before enabling automated publishing. Third-party notice
review and a separate clean-Mac installation test remain release checklist items.

The owner selected Kartik Mandar, version 2.0.0, GitHub Releases and Apple Silicon
first. The destination is the writable fork `kartikmandar/dave`, not its read-only
upstream. An initial missing-profile error was resolved by storing credentials in
the explicit login Keychain. A transient HTTP 403 agreement error subsequently
cleared on an account-access recheck. The release script now checks account access
before the lengthy artifact checks, and does not retain unrelated submission history.

The reused submission ZIP passed native signature checks and its app code-directory
hash matched the signed candidate. Apple acknowledged submission
`21f817d1-9801-495e-8b28-ad863f628fe1` on 2026-10-29 and subsequently returned
`Accepted`, status code 0, `Ready for distribution`, with no issues. The ticket
was stapled successfully and Gatekeeper accepts the app as `Notarized Developer ID`.

## Notarized distribution evidence, 2026-10-29

The final asset is
`build/release-2.0.0-arm64-candidate/DAVE-2.0.0-macOS-arm64.zip`, 569,825,260 bytes.
Its SHA-256 is
`2d1bd34a8005b3dd15fbecc18106d294e8608e975c5fd28414eca9eb1d5f19db`.
`SHA256SUMS` was independently verified. The final ZIP was extracted and its
contents passed all native signature, stapled-ticket and Gatekeeper checks.

A separate read-only extraction at `/tmp/dave-notarized-release-validation/DAVE.app`
passed the complete scientific Electron workflow against Stingray in 41.0 seconds,
including CSV exports and fresh workspace reopen. Normal app launch also passed.
Its code-directory hash matches both the signed candidate and the app before
notarization: `7e97e30c7e9ffa19bd9af3efea8933da8eb2693a`. Application code, UI and
workflows were not changed by notarization.

Evidence includes `notary-result.json`, `notary-log.json`, `release-report.json`
and `SHA256SUMS` in the candidate folder, plus `notarized-workflow.log`,
`notarized-normal-launch.json`, `notarized-code-identity.json` and
`release-validation.json` under `build/standalone`. The release-tool Python suite
now has 12 passing tests, including pending-status and finalization safety checks.

Upload-ready assets target `kartikmandar/dave`. Release notes and the asset checksum
are tracked under `docs/releases/`. Associate the GitHub draft with the reviewed
source commit; publication remains a separate manual decision. Legacy release
jobs also create drafts rather than publishing automatically. A separate clean-Mac
browser download/install test and third-party notice review remain release
checklist items. Intel and older macOS versions have not been validated.
