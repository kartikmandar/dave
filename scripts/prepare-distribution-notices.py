"""Assemble reviewed notices and corresponding-source material outside the signed app."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
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
    parser.add_argument(
        "--source-commit", required=True, help="Full Git commit matching the packaged DAVE source"
    )
    parser.add_argument("--replacement-evidence", required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        parser.error("Use a full source commit")
    replacement = json.loads(args.replacement_evidence.read_text())
    if (
        not replacement.get("modifiedLibraryLoaded")
        or not replacement.get("workflowPassed")
        or not replacement.get("engineReplacementValidated")
    ):
        parser.error(
            "Real runtime and engine shared-library replacements and full workflows must pass first"
        )
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
        selected = [
            source
            for source in record.get("sources", [])
            if source["copyleftSource"] or source.get("runtimeSourceDependency")
        ]
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
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("collect-electron-sources.py")),
            "--notices",
            str(args.notices),
            "--sources",
            str(args.sources),
        ],
        check=True,
    )
    source_files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", args.source_commit], text=True
    ).splitlines()
    omitted = [
        name
        for name in source_files
        if re.search(r"(^|/)(\.env($|\.)|credentials($|\.))|\.(pem|key|p8|p12)$", name)
    ]
    included = [name for name in source_files if name not in omitted]
    snapshot = args.sources / "DAVE-source.tar.gz"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            "--prefix=DAVE-source/",
            "--output=" + str(snapshot.resolve()),
            args.source_commit,
            "--",
            *included,
        ],
        check=True,
    )
    (args.sources / "source-snapshot-omissions.json").write_text(
        json.dumps(
            {
                "reason": "Excluded credential/environment filenames without reading their contents",
                "paths": omitted,
            },
            indent=2,
        )
        + "\n"
    )
    (args.sources / "DAVE-source-commit.txt").write_text(args.source_commit + "\n")
    for name in (
        "RUNTIME_SOURCE_OBLIGATIONS.md",
        "LGPL_REBUILD_EXAMPLE.md",
        "ELECTRON_SOURCE_REBUILD.md",
    ):
        shutil.copyfile(Path(__file__).resolve().parents[1] / "docs" / name, args.sources / name)
    shutil.copyfile(args.replacement_evidence, args.sources / "replacement-validation.json")
    shutil.copyfile(
        args.notices / "runtime-components.json", args.sources / "runtime-components.json"
    )
    (args.sources / "source-manifest.json").write_text(json.dumps(sources, indent=2) + "\n")
    (args.sources / "README.md").write_text("""# DAVE 2.0.0 bundled runtime sources

These hash-verified upstream archives and exact conda-forge build recipes/patches
correspond to the shipped readline, libiconv, Python, ncurses and GCC runtime packages. The
electron-chromium directory adds FFmpeg, Blink product sources, the full Electron
source archive and patches, Chromium build files and all dependency pins. GCC build
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
byte-for-byte across every scientific dependency. The supplied replacement evidence
records an independently compiled modified libiconv, loaded in a private locally
signed copy that passes the full scientific/workspace workflow. Modification
rights and the LGPL section 6(b) shared-library mechanism are documented in
RUNTIME_SOURCE_OBLIGATIONS.md. DAVE-source.tar.gz supplies the exact source commit,
including relocation, replacement, packaging scripts and dependency lock. Keep this companion source asset available alongside each
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
        "firstPartyReplacements": web.get("firstPartyReplacements", []),
        "sourceReview": "Engineering obligations review complete: exact runtime and Electron/Chromium copyleft sources/recipes/patches, Python/Readline dependencies, source snapshot, modification rights and tested runtime/engine/media shared-library replacement supplied. Byte-for-byte rebuild of all scientific packages is not claimed.",
        "sourceCommit": args.source_commit,
        "replacementValidation": replacement,
        "electronSourceManifest": "electron-chromium/source-manifest.json",
        "publicationHolds": ["separate clean-Mac acceptance test"],
    }
    (args.notices / "review.json").write_text(json.dumps(review, indent=2) + "\n")
    (args.notices / "README.md").write_text("""# DAVE 2.0.0 third-party notices — draft review

PUBLICATION HOLD: the separate clean-Mac test remains open. Runtime-source
engineering obligations and legacy browser advisory dispositions are documented
in the release review; the remaining MathJax advisory has a narrow, explicit
maintainer-disputed exception, not a claim of zero registry findings. The former Song Ho Ahn Logger.js and legacy Canvas2Image files are
removed. Their compatibility APIs are provided by new DAVE-owned logPanel.js and
canvasExport.js implementations under the project's Apache-2.0 license. The full
project license accompanies this folder; firstPartyReplacements records their
provenance. Existing log-panel styles, controls and export menu are retained.

Oxanium SemiBold by Severin Meyer replaces the former font with unconfirmed redistribution terms with owner
authorization. It is bundled unmodified under OFL-1.1, with its copyright, license
and pinned upstream source recorded inside the app and in these notices.

The inventories describe the reviewed Apple Silicon app: 253 conda
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
No license grant is inferred for the removed vendor implementations.

The companion DAVE-2.0.0-RUNTIME-SOURCES.tar.gz contains verified source archives
and exact build recipes/patches for readline, libiconv, Python, ncurses and GCC
runtime components, plus the exact DAVE source snapshot and modification rights.
Read its README and source-manifest.json. Retain this asset alongside the binary;
the documented LGPL shared-library mechanism has been tested with a recipient-built
modified libiconv. The evidence does not certify a byte-for-byte rebuild of every dependency.
DAVE source, relocation scripts and the dependency lock are in the release commit
at https://github.com/kartikmandar/dave (modernization-2025).

The electron-chromium source directory includes exact FFmpeg/Blink product sources,
Electron patches/build configuration and pinned dependencies. Compatible FFmpeg
and Electron Framework replacement has been executed without the publisher key.
The corresponding runtime/engine copyleft component sources accompany the binary; the source
manifest records scope and does not claim a full independent Chromium rebuild.

Electron/Chromium notices restored here were missing from the app's original
resource directory. These notices are bundled inside the app before signing and also accompany
DAVE.app at the ZIP root. No signed app files are changed after notarization. Keep the folder with any copy
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
