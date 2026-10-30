"""Prepare a self-contained acceptance kit; no Python is required on the test Mac."""

import argparse
import csv
import hashlib
import json
import runpy
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output.exists():
        parser.error("Use a new output directory to preserve acceptance evidence")
    args.output.mkdir(parents=True)
    generator = runpy.run_path(
        str(root / "tests/electron/resources/generate_workflow_reference.py")
    )
    reference = generator["generate_reference"](args.output / "fixture")
    for filename, section, keys in (
        ("expected-lightcurve.csv", "lightcurve", ("time", "countrate", "countrate_err")),
        ("expected-pds.csv", "pds", ("freq", "power", "power_err")),
    ):
        with (args.output / "fixture" / filename).open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerows(zip(*(reference[section][key] for key in keys), strict=True))
    for filename in ("verify-clean-mac.sh", "compare-clean-mac-csv.sh"):
        shutil.copyfile(root / "scripts" / filename, args.output / filename)
    shutil.copyfile(root / "docs/CLEAN_MAC_INSTALL_TEST.md", args.output / "README.md")
    template = {
        "status": "not-run",
        "tester": "",
        "machine": "",
        "macOS": "",
        "architecture": "",
        "separateCleanMachine": None,
        "noDevelopmentEnvironment": None,
        "browserDownloadQuarantine": None,
        "archiveChecksumPassed": None,
        "offlineFinderFirstLaunchPassed": None,
        "publisherDisplayed": "",
        "normalOpenConfirmationOnly": None,
        "diagnosticResult": None,
        "lightcurveCsvPassed": None,
        "pdsCsvPassed": None,
        "eightSegmentsAndInjectedPeak": None,
        "workspaceFreshReopenPassed": None,
        "reopenedCsvComparisonsPassed": None,
        "existingUiPreserved": None,
        "onlineRelaunchPassed": None,
        "evidencePaths": [],
        "notes": "",
    }
    (args.output / "RESULTS.json").write_text(json.dumps(template, indent=2) + "\n")
    files = sorted(
        file for file in args.output.rglob("*") if file.is_file() and file.name != "RESULTS.json"
    )
    (args.output / "KIT_SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.relative_to(args.output)}\n"
            for file in files
        )
    )
    print(f"Prepared kit: {args.output}; result remains not-run until a human completes the test")


if __name__ == "__main__":
    main()
