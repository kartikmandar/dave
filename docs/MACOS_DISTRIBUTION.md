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


## Intermediate Oxanium candidate and acceptance kit, 2026-10-30

The initial notarized app above is retained as historical evidence. The owner
authorized replacing Archangelsk after no redistribution permission could be
confirmed. The current candidate uses unmodified Oxanium SemiBold under OFL-1.1,
with the full license, copyright, pinned source URLs and hashes inside the app.
Splash/navbar brand size, position and colors are retained, along with all other
UI controls and scientific workflows.

The replacement app is staged at
`build/release-2.0.0-arm64-oxanium-candidate/DAVE.app`. Apple accepted submission
`1456fc85-02e0-4e79-a6a0-dd989e9baeee`, with status code 0 and no issues. The ticket
is stapled and validates; Gatekeeper accepts Notarized Developer ID. Its signed
code identity is `d415aa38bfe9c1e238cb138d6603c633d9708afa`.

The intermediate container was prepared in
`build/release-2.0.0-arm64-oxanium-prepublication`, with THIRD_PARTY_NOTICES beside
the app. `docs/releases/2.0.0-macos-arm64.SHA256SUMS` tracks its app ZIP checksum.
ASSET_SHA256SUMS also covers the companion runtime sources and clean-Mac kit.
This is a fresh signed/notarized font build; the earlier notices-only container
and its checksum are superseded.

See [PREPUBLICATION_REVIEW.md](PREPUBLICATION_REVIEW.md) for dependency remediation,
notice provenance and remaining publication holds. See
[CLEAN_MAC_INSTALL_TEST.md](CLEAN_MAC_INSTALL_TEST.md) for the prepared separate-Mac
test. The historical font-only build retained Logger.js/Canvas2Image provenance
gaps; the replacement batch below resolves them. Final source/runtime advisory
disposition and the separate clean-Mac test remain open. The release stays a draft.


## Historical font-only version-stamped candidate, accepted 2026-10-30

The final signed copy is
`build/release-2.0.0-arm64-oxanium-versioned-candidate/DAVE.app`, with code identity
`4dc0eb342b3ec269c5cd6e57adc762db8cd6a812`. Its packaged splash displays Version: 2.0.0;
development's label remains unchanged. Preflight rejects a missing or mismatched
packaged label, and all 13 release-safety regressions pass. Code commit 5f205bf
passed Linux, macOS, Windows and security CI:
https://github.com/kartikmandar/dave/actions/runs/40991526221.

Apple accepted final submission `dd056b04-f6f3-41f1-ad80-43251827f610`, with status
code 0 and no issues. Its ticket is stapled and Gatekeeper accepts Notarized
Developer ID. The initial accelerated transfer had aborted with an S3 timeout;
its allocated record 793274c2-8c8a-417e-b29f-5367e0c9b2fc is not used as proof of
a successful upload. The cached archive was extracted and its deep signatures
and code identity checked before the regional retry. Apple's endpoint guidance:
https://developer.apple.com/documentation/security/customizing-the-notarization-workflow.

The final distribution is staged in `build/release-2.0.0-arm64-final`, with
THIRD_PARTY_NOTICES beside the app, a runtime-source companion and the standalone
`build/clean-mac-test-kit-final`. Source, notice and app checksums are verified
after extraction and against GitHub's uploaded asset digests. The clean-Mac kit
checks the final 4dc0eb342b3ec269c5cd6e57adc762db8cd6a812 identity.

The earlier candidates above remain historical evidence and are superseded.
The release remained a draft at that checkpoint. The replacement batch below
resolves Logger.js/Canvas2Image provenance; final source/runtime advisory disposition
and the separate clean-Mac test remain open.


## Licensed browser component replacement batch

The owner authorized replacing the two remaining browser components with uncertain
redistribution provenance. New DAVE-owned logPanel.js and canvasExport.js modules
carry Apache-2.0 declarations and the full project license. Former vendor files
are physically removed. Current templates use the new modules and the existing
log panel styles and controls. The separate Electron/Python logger is unchanged.

Visual export validation found that html2canvas captured SVG plots as blank
images. Existing PNG/PDF menu actions now use the bundled MIT-licensed Plotly
renderer. Regression tests inspect actual trace-colored pixels in both formats;
the one-page portrait PDF was rendered and checked for clipping. Numerical
analysis, CSV export and workspace workflows remain unchanged.

The new signed candidate is
`build/release-2.0.0-arm64-licensed-export/DAVE.app`. Its identity is
`eeeb5e4bcfac8456317be12c7eec57b1a27de608`. The native runtime and ASAR are retained
from the previously verified build; changed resources and their hashes are listed
in resource-update-manifest.json. Notarization uses a fresh submission for this
changed resource seal, and the release stays a draft throughout.

The clean-Mac test now includes the log panel and opening real PNG/PDF exports.
The separate-machine test is still not run. Remaining publication holds are final
source-obligation/runtime advisory disposition and clean-Mac acceptance; the two
former browser asset permission gaps are resolved in the new candidate.


### Accepted replacement distribution, 2026-10-30

Apple accepted `2752730b-1768-4dbe-97fe-564707c6003d` with no issues. All 1,004 native
signatures, hardened runtime, staple and Gatekeeper passed before and after final
ZIP extraction. The current code identity is eeeb5e4bcfac8456317be12c7eec57b1a27de608.
The final app ZIP is in `build/release-2.0.0-arm64-licensed-final` and has SHA-256
`d618d3b2ce7bbd79be042b48c0addea159140d16ec0b189291248d09af15f19c`.
It includes the regenerated THIRD_PARTY_NOTICES; source and clean-Mac kit archives accompany it. The kit checks this same current code identity.

Implementation f8273fd and validation documentation 386a376 passed all-platform
and security CI. The final read-only extraction passed the expanded independent
Stingray workflow in 43.2 seconds, with checkout and Homebrew reads denied.
Real PNG/PDF plotted content, log controls, 288 light-curve rows, 15 PDS rows and
fresh-process workspace reopen passed. The separate clean-Mac test remains not run.
The GitHub Release remains a draft with the final source/runtime advisory and
clean-Mac publication holds explicitly retained.


## Runtime-source and browser advisory review batch

The previous replacement app remains the current draft download until the next
signed/notarized asset set is verified. The new batch removes jsPDF in favor of an original Apache-2.0 single-image PDF
writer, and updates Async to 2.6.4 and MathJax to 2.7.9 with local TeX/accessibility
modules and Safe configuration. Obsolete Plotly/html2canvas copies are removed.
See security/BROWSER_ADVISORY_REVIEW.md for the exact remaining disputed MathJax
exception and scripts/audit-browser-vendors.py --live for fresh registry checks.

The source companion now includes Python/ncurses sources and exact conda recipes
as well as the Readline/libiconv/GCC sources, and an exact DAVE source snapshot.
RUNTIME_SOURCE_OBLIGATIONS.md records license scope, continuing source availability
and modification rights. LGPL_REBUILD_EXAMPLE.md records the tested rebuild path.
An independently compiled modified libiconv loaded in a private locally signed
copy, which passed the full Electron workflow in 42.0 s without the publisher key.
The official app's native runtime is unchanged.

For future builds, collect notices against the unsigned staging app, resolve
sources, and run prepare-distribution-notices.py with --source-commit and
--replacement-evidence. Then run bundle-app-notices.py --app STAGING_APP --notices
NOTICE_DIR before macos-release.py sign. Signing preflight rejects missing local
notices. The existing Help > View License menu opens the local license/notice page
in packaged builds. Full notices remain available inside the app after moving it
to Applications. Preserve the companion source archive alongside each binary.

These engineering review items are resolved in the new source and final
notarized app; acceptance and final archive validation are recorded below. The separate physical
clean-Mac acceptance test remains open, and the release stays a draft.


### Final reviewed runtime/browser distribution, 2026-10-30

Apple accepted 24d53508-003b-40f4-8ad1-444ecff9d09a with status 0 and one AppleDouble packaging warning (no errors). Its
successful regional upload is acknowledged and Apple's archive SHA matches.
The first SIGBUS-failed allocation is retained as diagnostic evidence only.
The current signed/stapled app is `build/release-2.0.0-arm64-obligations/DAVE.app`,
code identity e23b4f6d1700d628f1540257d24afa78f37a1531. Native signatures, hardened
runtime, ticket and Gatekeeper passed before and after final extraction.

Final folder: `build/release-2.0.0-arm64-obligations-final-clean`.
App ZIP SHA-256: `7e0c263be7da58004786a76a7979bbab1fe1339bc6f85f2b1e798fceb57a9e61`.
The final read-only extraction passed the full Stingray workflow in 41.8 s,
including real PNG/PDF content, log controls and workspace reopen. All 288 LC and
15 PDS rows match independent references; all 200 web hashes and notice/source/
archive checksums pass. The prepared obligations clean-Mac kit checks this same
code identity; the physical browser-download/offline Finder test remains not run.

Binary source is 90db6da19cff2f721781047a725687ea62072ac5; verification fixes through
f37f1896fbdcb4fede06ba28d35b9f5f6a922cec passed all-platform/security CI 41035296804
and accompany the exact binary source snapshot as a documented patch. Shared-library
replacement was independently built and executed, not merely inferred. Runtime
source engineering obligations and legacy advisory disposition are complete.
Retain the one explicit maintainer-disputed MathJax exception and keep the source
companion available alongside the binary. The release remains a draft for the
separate clean-Mac acceptance test. Earlier artifact descriptions are historical.
