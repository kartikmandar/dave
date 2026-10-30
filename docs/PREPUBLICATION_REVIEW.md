# DAVE 2.0.0 pre-publication review

Status: **draft; publication holds remain**. The owner-authorized branding font
replacement is implemented, signed and notarized. Existing layout, controls,
analysis settings and workspace behavior are preserved. The separate clean-Mac
acceptance test is prepared but has not been performed on a separate machine.

## Current app and verification

The final app is staged at
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

The npm scan does **not** cover vendored Plotly 3.6.0, jsPDF 1.3.3, html2canvas
0.5.0-beta3 or legacy copies. DAVE exposes scientific scatter/timing plots, not
map popups; PDF export uses an internally generated JPEG through html2canvas and
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

Two assets still lack sufficient redistribution-provenance evidence:

| Asset | Evidence gap | Required resolution |
| --- | --- | --- |
| DAVE-customized Logger.js, Song Ho Ahn | Copyright/author page without a clear redistribution grant | Permission or an approved compatible replacement |
| Legacy Canvas2Image v0.1 | Stripped original header; a different fork's MIT statement is insufficient provenance | Exact original license or an approved compatible replacement |

These assets remain intact. Keep the release a draft until their disposition,
source/runtime review and separate clean-Mac acceptance are complete.

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


Final extraction evidence: all 164 third-party web/font/attribution hashes match
the inventory, the old font is absent, the packaged version resource is 2.0.0,
and the production ASAR is unchanged from the inventoried font build. A read-only
copy outside the checkout passed the complete packaged scientific workflow in
40.6 seconds, with checkout and Homebrew reads denied. All 288 light-curve rows
and 15 PDS rows match the clean-Mac kit's independent references. Both normal
shutdowns and fresh-process workspace recalculation passed. The extracted app's
code identity, deep signatures, stapled ticket and Gatekeeper assessment passed.
