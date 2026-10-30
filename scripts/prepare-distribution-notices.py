"""Assemble reviewed notices and corresponding-source material outside the signed app."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(file):
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notices", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("build/third-party-source-cache"))
    args = parser.parse_args()
    if args.sources.exists():
        parser.error("Use a new source directory; existing evidence is preserved")
    runtime = json.loads((args.notices / "runtime-components.json").read_text())
    electron = json.loads((args.notices / "electron-components.json").read_text())
    web = json.loads((args.notices / "web-components.json").read_text())
    resolutions = json.loads((args.notices / "source-resolutions.json").read_text())
    if runtime["errors"] or any(record["errors"] for record in web["upstreamNotices"]):
        parser.error("Collection errors must be resolved before assembly")
    if set(resolutions["unresolved"]) - {"libmagic"}:
        parser.error("Unresolved source notices")
    libmagic = next(
        record for record in web["upstreamNotices"] if record["component"] == "libmagic-5.47"
    )
    if not libmagic["files"]:
        parser.error("Missing version-specific libmagic COPYING")
    args.sources.mkdir(parents=True)
    packages = {record["name"]: record for record in runtime["condaPackages"]}
    sources = []
    for record in resolutions["resolutions"]:
        selected = [source for source in record.get("sources", []) if source["copyleftSource"]]
        if not selected:
            continue
        package = packages[record["name"]]
        identifier = "{name}-{version}-{build}".format(**package)
        recipe = args.notices / "conda" / identifier / "recipe"
        shutil.copytree(recipe, args.sources / "recipes" / identifier)
        for source in selected:
            archive = args.cache / source["archive"]
            if sha256(archive) != source["sha256"]:
                parser.error(f"Source SHA-256 mismatch: {archive.name}")
            for patch in source["patches"]:
                if not (recipe / patch).is_file() and not (recipe / "parent" / patch).is_file():
                    parser.error(f"Missing recipe patch: {identifier}/{patch}")
            destination = args.sources / "archives" / archive.name
            destination.parent.mkdir(exist_ok=True)
            if not destination.exists():
                shutil.copyfile(archive, destination)
            sources.append({"package": identifier, **source})
    (args.sources / "source-manifest.json").write_text(json.dumps(sources, indent=2) + "\n")
    (args.sources / "README.md").write_text("""# DAVE 2.0.0 bundled runtime sources

These hash-verified upstream archives and exact conda-forge build recipes/patches
correspond to the shipped readline, libiconv and GCC runtime packages. GCC build
sources also include zlib. See source-manifest.json for package builds, download
URLs, hashes and patches; recipes contain build scripts and rendered requirements.
The binaries are conda-forge builds, relocated for DAVE by the public packaging
scripts; DAVE source and pixi.lock are in the release source commit. No upstream
source changes beyond the supplied recipes/patches are claimed.

Readline is GPL-3.0; libiconv is LGPL-2.1; GCC runtimes include the GCC Runtime
Library Exception. Read their full notices in THIRD_PARTY_NOTICES. Shared runtime
libraries remain separate files; user-modified bundles require appropriate local
signing and may no longer satisfy Gatekeeper. Do not bypass Gatekeeper for the
clean-Mac acceptance test. This source collection has not been rebuilt independently
and is not a legal clearance. Review completeness and any LGPL relinking obligations
before publication. Keep this companion source asset available alongside each
binary release; do not rely on transient upstream links as the sole source offer.
""")
    review = {
        "status": "hold-before-publication",
        "publishable": False,
        "condaPackages": len(runtime["condaPackages"]),
        "pythonDistributions": len(runtime["pythonDistributions"]),
        "npmProductionPackages": len(electron["npmPackages"]),
        "electronVersion": electron["electronVersion"],
        "countNote": "Conda and Python distribution inventories overlap; do not add counts.",
        "externalLicenseResolutions": {"libmagic": libmagic["files"]},
        "pylruLicenseCorrection": "Installed pylru.py SPDX and LICENSE.txt are MIT; conda GPL-2.0 metadata is stale.",
        "freetypeLicenseSelection": "FTL",
        "unresolvedRedistributionRights": web["unresolvedRedistributionRights"],
        "sourceReview": "Archives and declared patches verified; independent source rebuild and final obligations review pending.",
    }
    (args.notices / "review.json").write_text(json.dumps(review, indent=2) + "\n")
    (args.notices / "README.md").write_text("""# DAVE 2.0.0 third-party notices — draft review

PUBLICATION HOLD: redistribution terms remain unconfirmed for Archangelsk.ttf,
Song Ho Ahn Logger.js and the stripped legacy Canvas2Image v0.1. Their actual
headers/font metadata are preserved. A different fork's MIT declaration does not
establish permission for the shipped version. Do not publish until these items
and the clean-Mac acceptance test are resolved. No existing UI asset was changed.

The inventories describe the actual notarized Apple Silicon app: 253 conda
packages, 138 Python distributions (overlapping conda packages), 48 production
npm packages and Electron 43.8.4. Package license texts, copyright notices,
Chromium notices, exact conda recipes and hashes are included. Collection does
not itself prove license compatibility or provide blanket legal clearance.

This software is based in part on the work of the FreeType Team.
FreeType is used under its FreeType License (FTL), one of its dual-license options.
Font Awesome by Dave Gandy: fonts OFL-1.1, code MIT; see upstream notices.

pylru 1.3.1 is MIT according to the actual installed module's SPDX header,
installed LICENSE.txt and PyPI metadata. The conda GPL-2.0 field is stale.
Do not treat the conda recipe's own BSD license as an upstream project license.
Missing native texts were recovered from hash-verified upstream source archives;
libmagic 5.47 COPYING was recovered from its exact upstream version tag.

agent-base 6.0.2 and https-proxy-agent 5.0.1 omit license files: primary upstream
proxy-agents license copies and provenance hashes accompany their MIT package
metadata. lazy-val 1.0.5 declares MIT and author Vladimir Krivosheev; the upstream
README and standard MIT terms accompany that declaration. The MIT terms also
apply to the preserved explicit MIT declarations in Stefan Petre's Colorpicker
and Start Bootstrap's SB Admin stylesheet; see their actual copyright headers.
No such inferred grant is applied to the three unresolved assets.

The companion DAVE-2.0.0-RUNTIME-SOURCES.tar.gz contains verified source archives
and exact build recipes/patches for readline, libiconv and GCC runtime components.
Read its README and source-manifest.json. Retain this asset alongside the binary;
review source completeness and applicable relinking requirements before publication.
DAVE source, relocation scripts and the dependency lock are in the release commit
at https://github.com/kartikmandar/dave (modernization-2025).

Electron/Chromium notices restored here were missing from the app's original
resource directory. This folder accompanies DAVE.app at the ZIP root; the signed
application and notarization ticket are unchanged. Keep the folder with any copy
of the distributed archive. review.json records remaining holds explicitly.
""")
    for directory in (args.notices, args.sources):
        files = sorted(
            file for file in directory.rglob("*") if file.is_file() and file.name != "SHA256SUMS"
        )
        (directory / "SHA256SUMS").write_text(
            "".join(f"{sha256(file)}  {file.relative_to(directory)}\n" for file in files)
        )
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    main()
