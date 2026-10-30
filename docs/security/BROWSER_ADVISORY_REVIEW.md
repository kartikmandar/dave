# Shipped browser advisory review — 30 October 2026

This review covers the files actually served by DAVE, independently of npm's
optional frontend build tree. scripts/browser-vendor-manifest.json pins the
complete vendor tree, exact package versions, upstream archive integrity and the
application's MathJax safety configuration. audit-browser-vendors.py rejects
changed hashes, added files, new advisories and stale exceptions. CI verifies the
inventory; use --live for a fresh GitHub Advisory Database query before a release.

| Component | Shipped disposition | Evidence |
| --- | --- | --- |
| jsPDF | 1.3.3 legacy file removed; official 4.2.1 UMD used by actual PDF action | 15 prior registry advisories; 4.2.1 fixes latest HTML-injection advisory; real JPEG/PDF content regression |
| Async | 2.5.0 removed; 2.6.4 retains the callback/waterfall API | GHSA-fwr7-v2mv-hh25; prototype-pollution negative regression and waterfall result |
| MathJax | 2.7.0 replaced with 2.7.9, matching TeX/SVG interfaces; local TeX/accessibility modules included | GHSA-3c48-6pcv-88rm fixed; Safe extension blocks executable/file URLs; real typesetting and no-missing-module regression |
| Plotly | Active 3.6.0 retained | No matching non-withdrawn registry advisories; unused 1.30.1, its backup and 2.35.2 removed |
| html2canvas | Unused legacy copy removed | Plot exports already use Plotly.toImage |
| jQuery 4.0.0, jQuery UI 1.14.1, Bootstrap 5.3.8 | Retained | No matching non-withdrawn registry advisories in the exact-version query |
| Colorpicker, waiting dialog | Existing attributed local vendor code retained and hash pinned | No inferred npm identity or claim that registry scanning covers arbitrary local code |

## One explicit MathJax exception

GHSA-v638-q856-grg8 / CVE-2023-39663 remains listed for MathJax <=2.7.9 and has no
patched 2.x release. Its maintainer disputes applicability: the implicated regular
expressions process MathJax's own localization/message templates. DAVE has no
application callers of MathJax.Message or MathJax.Localization and supplies no
user-controlled message templates or configuration. The reviewed exception is
therefore **not applicable to DAVE's current input path**, not fixed upstream.

The audit guards against introducing application calls into those APIs/config
paths, pins the local safety configuration and matches the exception to exactly
this advisory/package/version. Re-review if any of these conditions change or if
the advisory is withdrawn/updated. This is a bounded disposition of a known
report; it is not a claim of zero registry findings or absence of all defects.

Scientific TeX is still rendered through the existing SVG renderer. The Safe
extension rejects executable and file URLs in TeX without changing numeric plot
labels, layout, settings or export menus. PNG/PDF tests inspect real trace pixels.

Primary sources:
- https://github.com/parallax/jsPDF/releases/tag/v4.2.1
- https://github.com/parallax/jsPDF/security/advisories/GHSA-wfv2-pwc8-crg5
- https://github.com/advisories/GHSA-fwr7-v2mv-hh25
- https://github.com/advisories/GHSA-3c48-6pcv-88rm
- https://github.com/advisories/GHSA-v638-q856-grg8
- https://github.com/mathjax/MathJax/issues/3074#issuecomment-1658291365
