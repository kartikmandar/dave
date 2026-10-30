# DAVE 2.0.0 pre-publication review

Status: **draft; clean-Mac acceptance remains open**. Runtime-source engineering
obligations and the legacy browser advisory review are resolved in the new source
and signed candidate described below. Its new Apple submission and draft asset
refresh are pending. The draft download remains the previously verified app
until acceptance and final archive verification. Existing UI and workflows remain.

## Runtime-source and browser advisory review candidate

Candidate: `build/release-2.0.0-arm64-obligations/DAVE.app`, version 2.0.0, arm64,
Kartik Mandar Developer ID, code identity
`e23b4f6d1700d628f1540257d24afa78f37a1531`. Implementation source commit is
`90db6da19cff2f721781047a725687ea62072ac5`; current CI is
https://github.com/kartikmandar/dave/actions/runs/41033664639.
All 1,004 native signatures passed. A read-only /tmp candidate passed the full
Stingray import/light-curve/PDS/CSV/PNG/PDF/workspace workflow in 51.5 seconds,
with checkout/Homebrew reads denied. The rendered PDF retains the same image,
portrait A4 page and margins; its parser reports no JavaScript, forms or encryption.
All 27 browser regressions and 18 release-safety tests pass.

Actual shipped changes: Async 2.6.4 replaces vulnerable 2.5.0; MathJax 2.7.9 plus
local TeX/accessibility modules and Safe configuration replaces 2.7.0. Obsolete
Plotly 1.30.1/backup/2.35.2 and html2canvas copies are removed. jsPDF is removed,
including its unused HTML/forms/encryption code and ambiguously licensed MD5
helper. Original Apache-2.0 imagePDF.js preserves the existing single-image PDF
export. Its pixel content, byte offsets, fit bounds and input rejection are tested.
The vendor manifest pins every served vendor asset and safety configuration;
CI rejects unreviewed inventory changes. The notice inventory has 200 web/font/
attribution/first-party files and no unresolved asset grants. Full notices are
inside the app and available through the existing Help > View License menu.

Exactly one live registry report remains: MathJax GHSA-v638-q856-grg8, whose
maintainer disputes applicability. It handles internal message templates; DAVE
has no relevant user-message/configuration path. The exact exception, evidence,
conditions for renewed review and live audit are recorded in
[security/BROWSER_ADVISORY_REVIEW.md](security/BROWSER_ADVISORY_REVIEW.md).
This is an explicit bounded disposition, not an assertion of zero registry findings.

The runtime-source companion includes exact Python/ncurses sources and recipes
alongside Readline/libiconv/GCC/zlib, all declared patches, an exact DAVE source
snapshot, source commit, dependency lock, relocation/build/replacement scripts and
license/modification-rights documentation. Hashes and patch presence pass. Only
credential/environment filenames are excluded from the source snapshot, without
reading their contents; omissions are recorded. DAVE's source/runtime code is supplied.

LGPL shared-library replacement is demonstrated: libiconv 1.18 plus the supplied
macOS encoding patch was independently compiled with an added exported marker.
The marker loaded in a private locally signed app without the publisher key;
bundled libxml2 used it to decode ISO-8859-2 correctly, and the full scientific/
workspace workflow passed in 42.0 seconds. The official native runtime remains
unchanged. See [RUNTIME_SOURCE_OBLIGATIONS.md](RUNTIME_SOURCE_OBLIGATIONS.md) and
[LGPL_REBUILD_EXAMPLE.md](LGPL_REBUILD_EXAMPLE.md) for direct source distribution,
continuing availability, modification rights and LGPL section 6(b) mechanics.
A byte-for-byte rebuild of every scientific dependency is not claimed.

The remaining separate-machine acceptance test is **not run**. The prepared kit
checks this candidate identity and includes direct-Stingray references. It must
still cover a real browser download, quarantine, offline Finder launch and the
full scientific/workspace workflow on a clean Mac. Keep the release as a draft.

## Previous browser-component replacement draft app

The current app is `build/release-2.0.0-arm64-licensed-export/DAVE.app`, code identity
`eeeb5e4bcfac8456317be12c7eec57b1a27de608`. Apple accepted submission
`2752730b-1768-4dbe-97fe-564707c6003d`, status code 0, with no issues. All 1,004 native
signatures, hardened runtime, stapled ticket and Gatekeeper verification passed.
Final notices-bearing ZIP extraction passed these checks with the same code identity.

The final distribution is `build/release-2.0.0-arm64-licensed-final`.
App ZIP SHA-256: `d618d3b2ce7bbd79be042b48c0addea159140d16ec0b189291248d09af15f19c`.
All 164 web/font/attribution/first-party asset hashes and companion notice/source
checksums match this candidate. Removed vendor logger.js/canvas2image.js are absent.
The native runtime and ASAR are unchanged from the earlier validated font build.

Implementation commit f8273fd and validation-documentation commit 386a376 passed
Linux, macOS, Windows and security CI:
https://github.com/kartikmandar/dave/actions/runs/41003174855 and
https://github.com/kartikmandar/dave/actions/runs/41003870165.
Local checks passed 24 browser regressions, six Node release/runtime regressions
and 13 Python release-safety tests. The expanded source workflow passed in 21.2 s;
the read-only signed candidate passed in 43.1 s; the final archive extraction
passed in 43.2 s outside the checkout with checkout/Homebrew reads denied.
This includes independent Stingray numerical comparisons, 288 light-curve and 15
PDS CSV rows, log controls, real plot pixels in PNG/PDF, shutdown and workspace reopen.

At that earlier checkpoint, clean-Mac, source and legacy-advisory review were
open; the new batch above resolves the latter two engineering items. The two replaced asset permission gaps are resolved.

## Previously notarized app and verification

Historical font-only app (superseded) is staged at
`build/release-2.0.0-arm64-oxanium-versioned-candidate/DAVE.app`. Its bundle,
embedded package and packaged splash all use version 2.0.0. Its code identity is
`4dc0eb342b3ec269c5cd6e57adc762db8cd6a812`.

Apple accepted submission `dd056b04-f6f3-41f1-ad80-43251827f610`, with status code 0,
Ready for distribution and no issues. The regional endpoint was used after the
accelerated upload aborted; failed-transfer diagnostics are retained separately.
An allocated submission ID alone is not proof of a completed upload or acceptance.
Use an accepted existing request for finalization rather than uploading it again.

Code commit `5f205bfd76745d900663902dbbebea4ca76cfd1e` passed all Linux, macOS,
Windows and security CI: https://github.com/kartikmandar/dave/actions/runs/40991526221.
Local supporting checks passed: 554 Python tests, 16 browser regressions, six Node
release/runtime tests and 13 Python release-safety tests. The source scientific
workflow passed in 30.1 seconds after the shutdown-test fix. The optional Vite
production build passed into temporary output without replacing shipped assets.

A normal launch of the new-font build, without a debugger and with only system
PATH entries, loaded the main UI and bundled backend. Native-menu Quit exited
with code 0 before the watchdog. The version-stamp follow-up changes only DAVE's
own version resource and its application signature. Final extracted-app workflow
and container verification are recorded alongside the distribution report.

## Licensed font and packaging fixes

Archangelsk was removed and replaced with unmodified Oxanium SemiBold 2.000 by
Severin Meyer. The full OFL-1.1 license, copyright, pinned source URLs and hashes
accompany the font inside the app and companion notices. Splash/navbar branding
retains its sizes, positions and colors. The font loads locally without network
requests. Source: https://github.com/sevmeyer/oxanium/tree/a8f39e0c71186190027a093e9001459410192d1e.

Packager 20 required its object-based hook API. Its default resource copy rewrote
relative Python symlinks to absolute checkout paths, so the runtime is now copied
with verbatim symlinks. All 1,606 rebuilt-app symlinks stayed inside the app. Local
Electron ZIP creation excludes AppleDouble metadata that otherwise breaks framework
signature restoration. The standalone build passed with official Node 24.22.1,
whose archive matched Node's published SHA-256. Use ordinary Node 22 or 24; a
hardened app's embedded Node can reject the packager's native module.

Signing uses osx-sign 2's current API. App main executables are sealed with their
containers after the 999 independent native files, avoiding concurrent bundle
signing. All 1,004 native signatures passed verification. The staging hook stamps
the splash version without altering development's label; preflight rejects a
missing or mismatched splash version before external signing tools run.

The workflow helper detaches its test inspector before calling the real app.quit()
and requires the actual child-process close event within 30 seconds. No app API
is mocked and no forced exit substitutes for successful shutdown. This resolves
an intermittent debugger-controlled quit stall while retaining normal quit/reopen
coverage. The macOS CI job also runs the release-safety regressions.

## Build dependency audit

Electron remains pinned to 43.8.4. Forge tools are aligned at 8.0.1 with fuses
2.1.3, Packager 20.3.0 and osx-sign 2.7.2. Safe transitive fixes are locked in all
three npm trees. Optional Vite dependencies use Bootstrap 5.3.8, jsPDF 4.2.1 and
Plotly 4.2.0; these do not replace the browser files loaded by the shipped app.

| Dependency tree | Critical/high/moderate | Low | Treatment |
| --- | --- | --- | --- |
| Optional frontend build | 0 | 0 | Locked updates |
| Electron production | 0 | 0 | Pinned runtime |
| Browser/Electron test runner | 0 | 0 | Locked safe updates |
| Electron full build tree | 0 | 6 | Deepmerge plus five propagated Jest reports; local backport verified |

Image-size is pinned and overridden to 2.0.4 for the malformed ICNS infinite-loop
fix. Appdmg's legacy callback API is adapted to the modern file API. Deepmerge
4.3.1 has no upstream fixed release for GHSA-gcqx-w48m-w2h4; a narrow local backport
defines own data properties without invoking inherited setters. Hash-checked
postinstall patches fail on unknown source. Tests exercise prototype poisoning
in CommonJS/UMD builds, malformed ICNS rejection with a timeout and DAVE's real icon.

`audit-build-dependencies.cjs` retains raw registry counts, verifies all patch
hashes and accepts only the six exact low reports traceable to that advisory.
New findings fail the check. Do not describe this as npm audit zero. Install root,
Electron and tests dependencies before running `pixi run audit-build-deps`;
`pixi run test-build-tools` and `pixi run test-release-tools` run regressions.
Advisories: https://github.com/advisories/GHSA-gcqx-w48m-w2h4 and
https://github.com/advisories/GHSA-w3rx-r6r6-pgpr.

The npm scan does **not** cover vendored Plotly 3.6.0, jsPDF 1.3.3, the unused html2canvas
0.5.0-beta3 copy or other legacy copies. DAVE exposes scientific scatter/timing plots, not
map popups; PDF export uses an internally generated Plotly JPEG through
jsPDF.addImage/save, with Node integration disabled. These observations constrain
exposure but are not complete advisory clearance. Vendor replacement requires its
own visual/PDF regression checks and a newly signed/notarized app. Final legacy
runtime-advisory disposition remains a publication item.

## Notice and source collection

The new-font app inventory covers 253 conda packages, 138 Python distributions
(overlapping conda packages), 48 production npm packages, Electron 43.8.4 and 164
vendored web/font/attribution files. The version-stamp-only follow-up changes no
third-party component. Package and upstream source archives are SHA-256 verified.
Collectors restrict archive paths and exclude credential/key filenames.

Electron's license and Chromium notices were missing from the app resource
folder. They now accompany the app at the ZIP root in THIRD_PARTY_NOTICES. Other
texts come from installed distributions, exact conda packages, versioned source
archives or explicitly recorded primary upstream copies, with provenance hashes.
Do not mistake a conda recipe's BSD license for its upstream project's license.

pylru 1.3.1's installed SPDX/module and license are MIT, matching PyPI; the conda
GPL-2.0 metadata is stale. FreeType is used under its FTL option with its required
attribution. Font Awesome's separate font/code licenses are retained. References:
https://pypi.org/project/pylru/ and
https://github.com/freetype/freetype/blob/master/docs/FTL.TXT.

The source companion includes hash-verified readline 8.3, libiconv 1.18, GCC 15.2.0
and its zlib build source, exact conda recipes/build scripts and all declared
patches. It has not been independently rebuilt. Final source completeness, LGPL
relinking requirements and continuing source availability require review before
public distribution. This collection is evidence, not blanket legal clearance.

The two former browser asset provenance gaps are resolved by owner-authorized replacements:

| Asset | Evidence gap | Required resolution |
| --- | --- | --- |
| Former Logger.js | Removed from the app; original DAVE logPanel.js under Apache-2.0 | Compatibility API and existing styles retained |
| Former Canvas2Image v0.1 | Removed from the app; original DAVE canvasExport.js under Apache-2.0 | Native canvas compatibility helpers; Plotly's existing MIT image renderer for plot exports |

See [FIRST_PARTY_COMPONENTS.md](FIRST_PARTY_COMPONENTS.md) for source provenance and
API contracts. The former files must be absent in a new app; the notice collector
rejects them and stale notice headers. The new modules carry explicit SPDX and
copyright declarations, and the full DAVE Apache license accompanies the app.
The notice manifest records both replacements and no unresolved asset grants.

Actual exported images exposed a pre-existing html2canvas SVG capture problem:
the file was a valid PNG but blank. PNG/PDF menu actions now use Plotly.toImage;
PDFs retain the portrait page and fit the plot within margins without clipping.
The old html2canvas script is no longer loaded. Tests inspect plotted pixels in
both PNG and PDF's embedded image, as well as the menu, logger controls, numerical
CSV results and workspace reopen. A rendered one-page A4 PDF was visually checked.
The application layout and export menu remain unchanged.

At this checkpoint, all 24 browser regressions and the expanded source Electron
workflow passed (21.2 seconds). The updated signed candidate also passed the complete workflow in 43.1 seconds
from a read-only /tmp copy, with checkout and Homebrew reads denied. All 164 web
asset hashes and companion notice/source checksums match this candidate; both
former vendor files are absent. Notarization, stapling and final archive validation
have passed. The verified notices, runtime sources and clean-Mac kit accompany
the final ZIP. Final source-obligation/runtime advisory disposition and the
separate clean-Mac acceptance test remain publication holds.

## Reproduce and complete acceptance

Use locked Pixi Python and installed Electron build dependencies. Collect against
the app into a new directory outside its signature seal using
`collect-runtime-notices.py`, `collect-electron-notices.cjs`,
`resolve-notice-sources.py` and `collect-web-notices.py`. The source resolver's
historical libmagic FTP gap is resolved by the web collector's exact FILE5_47
COPYING. `prepare-distribution-notices.py` verifies this resolution and all
selected source hashes/patches, and records publishable: false in review.json.

`assemble-draft-distribution.py --draft --expected-cdhash` requires the reviewed
candidate identity, validates signatures/ticket/Gatekeeper before and after ZIP
extraction, verifies notice checksums and creates source/test-kit companions.
It has no publication operation.

See [CLEAN_MAC_INSTALL_TEST.md](CLEAN_MAC_INSTALL_TEST.md). The standalone kit
contains synthetic GTI data, direct-Stingray CSV references, stock-macOS checks
and a not-run result template. No Python, Node, Homebrew, checkout or Xcode is
required on the test Mac. Use dt 0.5 s, Leahy normalization, 16 s segments, eight
segments and a 0.25 Hz peak; compare exports before and after fresh workspace reopen.
A quarantined browser download and first Finder launch offline on a separate
clean Mac remain required. Local diagnostics correctly flag missing quarantine;
negative CSV checks reject altered values, missing rows and NaNs. No automatic
script certifies that a machine is clean.


Current final extraction evidence: all 164 web/font/attribution/first-party hashes
match the inventory, removed vendor components and old font are absent, the packaged
version is 2.0.0 and the production ASAR is unchanged. A read-only final extraction
passed the complete workflow in 43.2 seconds, including 288 light-curve and 15
PDS rows against independent references, PNG/PDF content, log controls, normal
shutdown and fresh workspace recalculation. Signatures, ticket and Gatekeeper
passed on the same extraction. ASSET_SHA256SUMS covers all three archives.
Earlier font-only artifacts and their checksums are historical and superseded.
