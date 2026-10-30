# DAVE 2.0.0 clean-Mac acceptance test

Status: prepared, not yet performed on a separate clean Mac. Local development-Mac
checks are supporting evidence only. The release must remain a draft until the
required manual evidence and publication checklist items are reviewed.

Use an Apple Silicon Mac without the DAVE checkout, Python, Node, Pixi or Homebrew.
A fresh macOS user on a development Mac is useful additional coverage but must be
reported as that, not as a separate clean machine. Record the exact macOS version;
the current candidate has only been validated on macOS 27.2.

## Download and first launch

1. In Safari or Chrome, sign in to GitHub and download the app ZIP, `SHA256SUMS`,
   and clean-Mac test kit from the draft in `kartikmandar/dave`. Use the browser,
   not curl, gh or AirDrop, so the download receives quarantine metadata.
2. In the download folder run `shasum -a 256 -c SHA256SUMS`. Save the successful
   output. A checksum failure stops the test.
3. Use Finder/Archive Utility to extract the ZIP, then drag `DAVE.app` to
   Applications. Keep any accompanying notices with the distribution.
4. Before the first launch, turn off external networking. Loopback networking
   remains available. This tests the stapled ticket and local bundled runtime.
5. Open the app through Finder. Record the exact Gatekeeper dialog and publisher
   (Kartik Mandar), and select the normal Open confirmation if offered. A damaged
   app/unidentified-developer warning fails this test. Do not remove quarantine,
   use Open Anyway, disable Gatekeeper, or install developer tools to bypass it.
6. Verify that the existing main UI appears and the local backend connects.
   No Python/runtime download or external dependency installation should occur.
7. After first launch, run the included read-only diagnostics:

   ```sh
   sh verify-clean-mac.sh /Applications/DAVE.app "$HOME/Desktop/DAVE-clean-mac-evidence"
   ```

The diagnostic script checks version, bundle ID, code identity, Developer ID team,
signatures, Gatekeeper and quarantine evidence. It requires no Xcode/notarytool,
Python, Node or package manager. It does not launch or modify the app. Passing it
does not substitute for the manual first-launch and workflow observations.

## Independent scientific workflow

The test kit contains a deterministic synthetic NuSTAR-style `source.evt`, with
two GTIs and an injected 0.25 Hz signal, plus direct-Stingray CSV references.
No real mission data or user observation files are included.

1. Import `fixture/source.evt` with the existing chooser. Set bin size to `0.5`
   seconds using the actual input and refresh the light curve.
2. Enable the PDS card through Analysis. Choose averaged PDS, Leahy normalization,
   a `16` second segment size and no frequency rebinning. Expect eight segments
   and the injected peak at 0.25 Hz. Compare displayed GTIs with `reference.json`.
3. Export light curve and PDS using Save as CSV. Compare both exported files:

   ```sh
   sh compare-clean-mac-csv.sh fixture/expected-lightcurve.csv /path/to/lightcurve.csv
   sh compare-clean-mac-csv.sh fixture/expected-pds.csv /path/to/pds.csv
   ```

4. Save the workspace to a path containing spaces. Quit the entire app, open it
   again through Finder, and reopen that workspace. Recalculation must succeed
   without a stale backend URL or missing cached dataset. Export and compare both
   CSVs again. Confirm the bin size, PDS settings and eight segments are retained.
5. Open and close the LOG panel, check that messages retain their level colors,
   then export a plot through Save as PNG and Save as PDF. Open both files in
   Preview and compare their contents with the displayed plot. Verify the
   established controls, plot layout, file chooser and exports remain
   usable. Record screenshots of initial and reopened plots.
6. Re-enable networking, relaunch once, and repeat the basic import. No unexpected
   updater/download dialog should appear; updates are currently manual.

## Evidence and decision

Fill in the test kit result template. Include checksum output, diagnostic output,
Gatekeeper observations, both pairs of exported CSVs, workspace and screenshots.
Do not include credentials or private scientific data. Keep evidence local until
reviewed. Any bypass, missing quarantine evidence, failed comparison or incomplete
manual step prevents marking this acceptance test passed. No automatic script
can certify that a machine is clean.
