# DAVE 2.0.0 pre-publication review

Status: **draft; not ready for publication**. The owner authorized replacing
Archangelsk after no original redistribution permission could be found. Oxanium
SemiBold is bundled unmodified under OFL-1.1 with copyright, license and pinned
source hashes. Splash/navbar brand sizes, colors and placement are retained;
analysis settings, controls and workspace behavior are preserved. This resource
change requires a fresh signed and notarized app.

## Build dependency remediation

Electron remains pinned to 43.8.4. Forge tools are aligned at 8.0.1, with fuses
2.1.3, Packager 20.3.0 and osx-sign 2.7.2. The packaging hook and signing API are
updated for those versions. The local Electron ZIP is recreated without resource
fork/extended-attribute AppleDouble entries, which otherwise break framework
signature restoration in Packager 20. Its default extra-resource copy also
rewrites relative symlinks to absolute checkout paths; an explicit runtime copy
preserves them verbatim so the Python interpreter remains inside the relocated app.
Use ordinary Node 22 or 24; a hardened app's
embedded Node can reject the packager's native module because of library validation.

The optional Vite build dependencies use Bootstrap 5.3.8, jsPDF 4.2.1 and Plotly
4.2.0. Safe transitive updates are locked in all three npm trees. These optional
bundler packages do not replace the browser files loaded by the shipped application.

`image-size` is overridden to 2.0.4 for the malformed ICNS infinite-loop fix.
Appdmg 0.6.6 requires its old callback API, so a hash-checked adapter uses the new
file API. Deepmerge 4.3.1 has no upstream fixed release for GHSA-gcqx-w48m-w2h4.
A narrowly scoped, hash-checked local backport defines own data properties rather
than invoking inherited setters. It preserves ordinary nested merge/array behavior.

The postinstall patch fails on unknown source hashes. Regression tests exercise
prototype poisoning in both packaged CommonJS and UMD builds, reject a malformed
ICNS with a timeout, and parse DAVE's real icon. CI runs these checks on all three
platforms. A production-only install may omit these build tools.

Registry audit results after remediation:

| Dependency tree | Critical/high/moderate | Low | Treatment |
| --- | --- | --- | --- |
| Optional frontend build | 0 | 0 | Locked updates |
| Electron production | 0 | 0 | Unchanged runtime version |
| Browser/Electron test runner | 0 | 0 | Locked safe updates |
| Electron full build tree | 0 | 6 | Deepmerge advisory plus five propagated Jest findings; local backport verified |

`node scripts/audit-build-dependencies.cjs` retains the raw registry counts and
checks every backport hash. It accepts only the six exact low findings traceable
to that advisory; new findings fail the check. Do not describe this as npm audit
zero. Run `pixi run test-build-tools` after `pixi run install-node-deps`.
Install root and tests dependencies before the full audit (`npm ci` and
`npm --prefix tests ci`); run `pixi run audit-build-deps`.

Advisories: https://github.com/advisories/GHSA-gcqx-w48m-w2h4 and
https://github.com/advisories/GHSA-w3rx-r6r6-pgpr.

## Actual runtime notice review

The collection is against `build/release-2.0.0-arm64-oxanium-candidate/DAVE.app`, not merely
the development lock. It inventories 253 conda packages, 138 Python distributions
(overlapping conda packages), 48 production npm packages, Electron 43.8.4 and 162
vendored web/font files. Exact package archives and upstream source archives are
SHA-256 verified. The collector restricts archive members and excludes secrets.

Electron's own license and Chromium notices were absent from the packaged resource
directory. They are restored in an accompanying `THIRD_PARTY_NOTICES` folder at the
app ZIP root, outside the app's signature seal. Other texts come from the installed
distributions, exact conda package licenses, versioned upstream sources or explicitly
recorded primary upstream license files. The inventories preserve the provenance
and hashes, including unresolved rights rather than manufacturing grants.

pylru 1.3.1's actual SPDX/module and installed license are MIT, matching PyPI;
its conda GPL-2.0 field is stale. FreeType is used under the FTL option and its
required attribution is included. Font Awesome's distinct font/code licenses are
retained. See https://pypi.org/project/pylru/ and
https://github.com/freetype/freetype/blob/master/docs/FTL.TXT.

A companion runtime-source archive includes verified readline 8.3, libiconv 1.18,
GCC 15.2.0 and its zlib build source, with the exact conda recipes/build scripts
and all declared patches. This has not been independently rebuilt. Review source
completeness, LGPL relinking requirements and continuing source availability before
public distribution; the collection is evidence, not blanket legal clearance.

Two assets still lack adequate evidence of redistribution permission:

| Asset | Evidence gap | Required resolution |
| --- | --- | --- |
| DAVE-customized Logger.js, Song Ho Ahn | Copyright/author page without a clear license grant | Author permission or separately approved compatible replacement |
| Legacy Canvas2Image v0.1 | Stripped original header; another fork's MIT statement is insufficient provenance | Recover the exact original license or approve a compatible replacement |

Logger.js and Canvas2Image remain intact. Keep the release private/draft while
their provenance items remain unresolved. The owner explicitly authorized the font
replacement. The old font is removed from the distribution, and Oxanium copyright
and license accompany the new font inside the app as well as the companion notices.
Source: https://github.com/sevmeyer/oxanium/tree/a8f39e0c71186190027a093e9001459410192d1e.

This npm audit does **not** cover the vendored runtime Plotly 3.6.0, jsPDF 1.3.3,
html2canvas 0.5.0-beta3 or legacy copies. Optional Vite dependency upgrades do not
patch those files. The supported DAVE plots use fixed scientific scatter/timing
paths, not map popups; PDF export uses an internally generated JPEG through
html2canvas and jsPDF.addImage/save. Electron disables Node integration. These
observations constrain relevant exposure, but are not a complete advisory clearance.
Any vendor replacement needs its own visual/PDF regression checks and a new signed,
notarized app. Final runtime-advisory disposition remains a publication review item.

## Reproduce the notice materials

Use the locked Pixi Python environment (PyYAML, fontTools, zstd support) and installed
Electron build dependencies. Stage into new directories outside the signed app:

```sh
pixi run python scripts/collect-runtime-notices.py --app build/release-2.0.0-arm64-oxanium-candidate/DAVE.app --output build/third-party-review/THIRD_PARTY_NOTICES
node scripts/collect-electron-notices.cjs build/release-2.0.0-arm64-oxanium-candidate/DAVE.app build/third-party-review/THIRD_PARTY_NOTICES
pixi run python scripts/resolve-notice-sources.py --notices build/third-party-review/THIRD_PARTY_NOTICES
pixi run python scripts/collect-web-notices.py --app build/release-2.0.0-arm64-oxanium-candidate/DAVE.app --output build/third-party-review/THIRD_PARTY_NOTICES
pixi run python scripts/prepare-distribution-notices.py --notices build/third-party-review/THIRD_PARTY_NOTICES --sources build/third-party-review/RUNTIME-SOURCES
```

The source resolver reports libmagic as unresolved because its historical FTP
source is unavailable; the web collector supplies COPYING from exact tag FILE5_47.
The assembly script verifies that explicit resolution and all selected source hashes
and patch files. It records `publishable: false` in `review.json`.

`assemble-draft-distribution.py --draft` requires the reviewed application code
identity, validates signatures/ticket/Gatekeeper before and after ZIP extraction,
verifies extracted notice hashes and builds companion source/test-kit assets.
It has no publication operation. The assembler requires the expected code identity of the newly signed candidate.
The font replacement is a rebuilt/re-notarized binary; the former candidate is
retained separately as historical evidence.

## Clean-Mac acceptance

See [CLEAN_MAC_INSTALL_TEST.md](CLEAN_MAC_INSTALL_TEST.md). Generate the standalone
kit with `pixi run python scripts/prepare-clean-mac-test.py --output build/clean-mac-test-kit`.
It includes synthetic GTI data, independent Stingray light-curve/PDS references,
stock-macOS shell checks and a result template. No Python/Node is required on the
test Mac. Expected results: dt 0.5 s, Leahy normalization, 16 s segments, eight
segments and a 0.25 Hz peak. Compare CSVs before and after fresh workspace reopen.

The separate-machine test is **not run**. The local diagnostic verifies the app's
signature and notarized identity but correctly returns incomplete for missing
browser quarantine. Negative checks reject altered values, missing rows and NaNs;
writing diagnostic output inside the signed app is refused. Neither local checks
nor an automated workflow substitute for a quarantined browser download and first
Finder launch offline on a Mac without the checkout or development tools.

## Initial tooling-batch checks (before the font replacement)

- 554 Python tests, 16 browser regressions and the source Electron scientific
  workflow passed (16.4 seconds for the workflow).
- Six Node release/runtime tests and 12 Python release-tool tests passed.
- The optional Vite production build passed into a temporary output directory,
  preserving the shipped static files.
- The standalone build passed with official Node 24.22.1, whose archive matched
  Node's published SHA-256. All 1,606 symlinks stayed within the rebuilt app.
- A copy under `/tmp/dave-packager20-relocatable-validation` passed the full
  independent Stingray workflow in 37.6 seconds with checkout and Homebrew reads
  denied. This validates the updated build tools; this smoke build is not the
  notarized release binary and is not uploaded as the release app.
- The notices ZIP extracted successfully. Its app retained code hash
  `7e97e30c7e9ffa19bd9af3efea8933da8eb2693a`, valid deep signatures, a valid stapled
  ticket and Notarized Developer ID Gatekeeper acceptance. All extracted notice
  checksums matched. The ZIP checksum changed because companion notices were added.
- The clean-Mac result remains `not-run`. Its diagnostics correctly report the
  development copy's missing browser quarantine; CSV negative checks reject altered
  values, missing rows and NaNs, and output inside the app is refused.

## Owner-authorized font replacement

Archangelsk was removed and replaced with unmodified Oxanium SemiBold 2.000 from
Severin Meyer's pinned upstream commit. The full OFL-1.1 license, copyright,
source URLs and hashes accompany the font inside the app. Splash and navbar
branding use the same dimensions, positions and colors; other controls are unchanged.
Source-browser regression tests passed (16 tests), and a visual check confirmed
that the font loads locally and the established plot/control layout is retained.

Fresh signing exposed that codesign treats app main-executable paths as bundles.
Those executables are now sealed with their app containers after the 999 other
independent native files. All 1,004 native signatures then passed verification.
The former signed candidate is retained separately; it is not modified in place.

The full workflow exposed an intermittent debugger-controlled shutdown stall.
The test helper now returns its debugger request, detaches the test inspector,
and calls the real app.quit(). It still requires the actual child-process close
event within 30 seconds. No app API is mocked and no forced exit substitutes for
successful shutdown. The complete source workflow, including both shutdowns and
fresh workspace recalculation, passed in 30.1 seconds after this change.

Apple submission 1456fc85-02e0-4e79-a6a0-dd989e9baeee is in progress. Final ticket,
archive and clean-Mac-kit identities will be updated only after acceptance and
extracted-app verification. The separate clean-Mac test remains not run.
