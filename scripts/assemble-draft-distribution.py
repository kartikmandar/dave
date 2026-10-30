"""Package companion notices with an already notarized app, without changing its seal."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def identity(app):
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    subprocess.run(["xcrun", "stapler", "validate", str(app)], check=True)
    subprocess.run(["spctl", "--assess", "--type", "execute", str(app)], check=True)
    result = subprocess.run(
        ["codesign", "-d", "--verbose=4", str(app)], check=True, capture_output=True, text=True
    )
    return next(line for line in result.stderr.splitlines() if line.startswith("CDHash="))


def sha256(file):
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--notices", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--test-kit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-cdhash", required=True)
    parser.add_argument(
        "--draft", action="store_true", help="Required: these materials have publication holds"
    )
    args = parser.parse_args()
    if not args.draft or args.output.exists():
        parser.error("Use --draft and a new output directory; never overwrite release evidence")
    if args.output.resolve().is_relative_to(args.app.resolve()):
        parser.error("Distribution output must be outside the signed app")
    original = identity(args.app)
    if original != "CDHash=" + args.expected_cdhash:
        parser.error("App is not the reviewed notarized 2.0.0 candidate")
    review = json.loads((args.notices / "review.json").read_text())
    args.output.mkdir(parents=True)
    stage = args.output / "archive-root"
    stage.mkdir()
    subprocess.run(["/usr/bin/ditto", str(args.app), str(stage / "DAVE.app")], check=True)
    shutil.copytree(args.notices, stage / "THIRD_PARTY_NOTICES")
    archive = args.output / "DAVE-2.0.0-macOS-arm64.zip"
    subprocess.run(
        ["/usr/bin/ditto", "-c", "-k", "--sequesterRsrc", str(stage), str(archive)], check=True
    )
    assert identity(stage / "DAVE.app") == original
    extracted = args.output / "verified-extraction"
    subprocess.run(["/usr/bin/ditto", "-x", "-k", str(archive), str(extracted)], check=True)
    assert identity(extracted / "DAVE.app") == original
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS"],
        cwd=extracted / "THIRD_PARTY_NOTICES",
        check=True,
        stdout=subprocess.DEVNULL,
    )
    source_archive = args.output / "DAVE-2.0.0-RUNTIME-SOURCES.tar.gz"
    subprocess.run(
        [
            "/usr/bin/tar",
            "-czf",
            str(source_archive),
            "-C",
            str(args.sources.parent),
            args.sources.name,
        ],
        check=True,
    )
    kit_archive = args.output / "DAVE-2.0.0-CLEAN-MAC-TEST.zip"
    subprocess.run(
        ["/usr/bin/ditto", "-c", "-k", "--keepParent", str(args.test_kit), str(kit_archive)],
        check=True,
    )
    assets = [archive, source_archive, kit_archive]
    (args.output / "ASSET_SHA256SUMS").write_text(
        "".join(f"{sha256(file)}  {file.name}\n" for file in assets)
    )
    (args.output / "SHA256SUMS").write_text(f"{sha256(archive)}  {archive.name}\n")
    report = {
        "draft": True,
        "publishable": False,
        "appCodeIdentity": original,
        "noticesReview": review,
        "assets": [
            {"name": file.name, "bytes": file.stat().st_size, "sha256": sha256(file)}
            for file in assets
        ],
    }
    (args.output / "distribution-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
