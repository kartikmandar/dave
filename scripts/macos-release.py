"""Prepare, sign and notarize a standalone DAVE app without publishing it.

Only Keychain identity/profile names are accepted; no credential files are read.
"""

import argparse
import hashlib
import json
import os
import plistlib
import re
import struct
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACH_MAGICS = {b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf"}
FAT_MAGICS = {b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"}


def run(*arguments):
    return subprocess.check_output([str(item) for item in arguments], text=True).strip()


def macho_types(file):
    """Read only Mach-O headers, including all slices of universal binaries."""
    with file.open("rb") as stream:
        header = stream.read(8)
        if header[:4] in FAT_MAGICS:
            count = struct.unpack(">I", header[4:8])[0]
            if not 1 <= count <= 64:
                return set()  # The same magic also occurs in Java class files.
            wide = header[:4] == b"\xca\xfe\xba\xbf"
            records = [stream.read(32 if wide else 20) for _ in range(count)]
            offsets = [
                struct.unpack(">Q" if wide else ">I", item[8 : 16 if wide else 12])[0]
                for item in records
            ]
        elif header[:4] in MACH_MAGICS:
            offsets = [0]
        else:
            return set()
        types = set()
        for offset in offsets:
            stream.seek(offset)
            header = stream.read(16)
            if len(header) < 16 or header[:4] not in MACH_MAGICS:
                return set()
            endian = "<" if header[:4] in (b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe") else ">"
            types.add(struct.unpack(endian + "I", header[12:16])[0])
        return types


def native_files(app):
    for directory, folders, files in os.walk(app):
        folders[:] = [item for item in folders if not (Path(directory) / item).is_symlink()]
        for name in files:
            file = Path(directory) / name
            if name.startswith((".env", "credentials")) or file.suffix in {
                ".pem",
                ".key",
                ".p8",
                ".p12",
            }:
                continue  # Never inspect credential/certificate payloads.
            if not file.is_symlink() and macho_types(file) & {2, 6, 7, 8}:
                yield file


@contextmanager
def otool_path(file):
    # Recent otool versions treat parentheses as archive-member syntax, including
    # the standard Electron "Helper (Renderer)" executable name. Inspect an alias.
    if "(" not in str(file):
        yield file
        return
    with tempfile.TemporaryDirectory(prefix="dave-native-") as directory:
        alias = Path(directory) / "native"
        alias.symlink_to(file.resolve())
        yield alias


def preflight(app, node):
    if app.suffix != ".app" or not app.is_dir():
        raise ValueError("Provide an existing standalone .app")
    with (app / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    version = info["CFBundleShortVersionString"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or info["CFBundleVersion"] != version:
        raise ValueError("Bundle release and build versions must match numeric major.minor.patch")
    if info["CFBundleIdentifier"] != "science.stingray.dave":
        raise ValueError("Unexpected bundle identifier")
    resources = app / "Contents/Resources"
    manifest = json.loads((resources / "runtime.json").read_text())
    if manifest.get("layout") != "immutable-v1" or (resources / "python-runtime.tar.gz").exists():
        raise ValueError("Rebuild with the immutable runtime layout before signing")
    metadata = json.loads(run(node, ROOT / "scripts/macos-sign.cjs", "inspect", app))
    if metadata.get("unexpectedFiles"):
        raise ValueError("Unexpected credential filenames in the packaged JavaScript application")
    if metadata["appVersion"] != version:
        raise ValueError("Embedded package.json version differs from the bundle version")
    # Refresh this policy from the official Electron release schedule before releases.
    if int(metadata["electronVersion"].split(".")[0]) not in {43, 44, 45}:
        raise ValueError(
            "Electron is outside the supported majors reviewed on 2026-10-29 (43, 44, 45)"
        )
    inventory = []
    for file in native_files(app):
        with otool_path(file) as alias:
            dependencies = run("/usr/bin/otool", "-L", alias)
            commands = run("/usr/bin/otool", "-l", alias)
        for line in dependencies.splitlines():
            dependency = line.strip().split(" (", 1)[0]
            if (
                dependency.startswith("/")
                and not line.endswith(":")
                and not dependency.startswith(("/usr/lib/", "/System/Library/"))
            ):
                raise ValueError(f"External native dependency: {file}: {dependency}")
        for rpath in re.findall(r"cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset", commands):
            if rpath.startswith("/") and not rpath.startswith(("/usr/lib/", "/System/Library/")):
                raise ValueError(f"Non-relocatable native search path: {file}: {rpath}")
        inventory.append(str(file.relative_to(app)))
    if not inventory:
        raise ValueError("App contains no executable code")
    for directory, folders, files in os.walk(app):
        for name in folders + files:
            file = Path(directory) / name
            if file.is_symlink() and not file.resolve().is_relative_to(app.resolve()):
                raise ValueError(f"Symlink escapes app: {file}")
    return {
        "version": version,
        "bundleId": info["CFBundleIdentifier"],
        **metadata,
        "policyReviewed": "2026-10-29",
        "checkedOn": date.today().isoformat(),
        "nativeFiles": inventory,
    }


def signature_details(file):
    return subprocess.run(
        ["/usr/bin/codesign", "-dvv", str(file)], capture_output=True, text=True, check=True
    ).stderr


def verify_signatures(app):
    run("/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", app)
    signature = signature_details(app)
    team = re.search(r"^TeamIdentifier=([A-Z0-9]{10})$", signature, re.MULTILINE)
    if (
        "Authority=Developer ID Application:" not in signature
        or "runtime" not in signature
        or not team
    ):
        raise ValueError("Requires a Developer ID signature, Team ID and hardened runtime")
    # Deep bundle verification alone does not validate every code file in Resources.
    for file in native_files(app):
        run("/usr/bin/codesign", "--verify", "--strict", file)
        details = signature_details(file)
        if (
            "Authority=Developer ID Application:" not in details
            or f"TeamIdentifier={team[1]}" not in details
        ):
            raise ValueError(
                f"Native code is not signed by the application's Developer ID team: {file}"
            )
        if 2 in macho_types(file) and "runtime" not in details:
            raise ValueError(f"Executable does not enable hardened runtime: {file}")


def verify(app):
    verify_signatures(app)
    run("/usr/bin/xcrun", "stapler", "validate", app)
    run("/usr/sbin/spctl", "--assess", "--type", "execute", "--verbose=2", app)


def zip_app(app, archive):
    if archive.exists():
        raise ValueError(f"Refusing to overwrite {archive}")
    run("/usr/bin/ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app, archive)


def parse_notary_result(process, output):
    (output / "notary-submit.stdout.json").write_text(process.stdout)
    (output / "notary-submit.stderr.log").write_text(process.stderr)
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Apple notarytool returned no submission result; see notary-submit.stderr.log. "
            "No successful upload is established."
        ) from error
    if not isinstance(result, dict) or not result.get("id"):
        raise ValueError(
            "Apple notarytool returned no submission ID; see notary-submit.stdout.json"
        )
    (output / "notary-result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def verify_submission_archive(app, archive):
    with tempfile.TemporaryDirectory(prefix="dave-submission-check-") as directory:
        run("/usr/bin/ditto", "-x", "-k", archive, directory)
        extracted = Path(directory) / app.name
        verify_signatures(extracted)
        if code_directory_hash(app) != code_directory_hash(extracted):
            raise ValueError("Existing submission ZIP does not match the signed app")


def code_directory_hash(file):
    details = subprocess.run(
        ["/usr/bin/codesign", "-d", "--verbose=4", str(file)],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    match = re.search(r"^CDHash=([a-f0-9]+)$", details, re.MULTILINE)
    if not match:
        raise ValueError(f"No code-directory hash reported for {file}")
    return match[1]


def verify_notary_access(credentials, output):
    process = subprocess.run(
        ["/usr/bin/xcrun", "notarytool", "history", *credentials, "--output-format", "json"],
        capture_output=True,
        text=True,
    )
    # Do not retain unrelated submission history. Only account-access errors are needed.
    (output / "notary-access.stderr.log").write_text(process.stderr)
    if process.returncode:
        raise ValueError(
            "Apple notarization account access check failed; see notary-access.stderr.log. "
            "No upload was attempted."
        )


def require_accepted(result):
    if not result.get("id"):
        raise ValueError("Apple returned no submission ID")
    if result.get("status") == "In Progress":
        raise ValueError(
            f"Apple is still processing submission {result['id']}; "
            "retry finalize with that ID later. Do not upload this candidate again."
        )
    if result.get("status") != "Accepted":
        raise ValueError("Apple did not accept this submission; inspect its notarization log")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("preflight", "sign", "notarize", "finalize", "verify-signature", "verify"),
    )
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--node", default="node")
    parser.add_argument("--output", type=Path, default=ROOT / "build/release")
    parser.add_argument(
        "--identity", help="Full Developer ID Application identity installed in Keychain"
    )
    parser.add_argument("--team-id", help="10-character Apple Developer Team ID")
    parser.add_argument("--keychain-profile", help="Existing notarytool Keychain profile name")
    parser.add_argument(
        "--submission-id", help="Existing Apple submission ID for finalize; never uploads again"
    )
    parser.add_argument(
        "--keychain", help="Optional explicit Keychain path used when storing the profile"
    )
    parser.add_argument(
        "--reuse-submission",
        action="store_true",
        help="Verify and reuse the existing submission ZIP after a failed attempt",
    )
    args = parser.parse_args()
    app = args.app.resolve()
    if args.command == "verify-signature":
        verify_signatures(app)
        print(
            "Developer ID, hardened runtime and all nested native signatures passed; notarization is separate"
        )
        return
    if args.command == "verify":
        verify(app)
        print("Signature, stapled ticket and Gatekeeper assessment passed")
        return
    credentials = ["--keychain-profile", args.keychain_profile]
    if args.keychain:
        credentials += ["--keychain", args.keychain]
    existing_result = None
    if args.command in ("notarize", "finalize"):
        if not args.keychain_profile:
            parser.error("--keychain-profile is required")
        output = args.output.resolve()
        if output.is_relative_to(app):
            parser.error("The output directory must be outside the input app")
        output.mkdir(parents=True, exist_ok=True)
        verify_notary_access(credentials, output)
        if args.command == "finalize":
            if not args.submission_id:
                parser.error("finalize requires --submission-id from Apple")
            existing_result = json.loads(
                run(
                    "/usr/bin/xcrun",
                    "notarytool",
                    "info",
                    args.submission_id,
                    *credentials,
                    "--output-format",
                    "json",
                )
            )
            (output / "notary-result.json").write_text(json.dumps(existing_result, indent=2) + "\n")
            require_accepted(existing_result)
    report = preflight(app, args.node)
    if args.command == "preflight":
        print(json.dumps(report, indent=2))
        return
    output = args.output.resolve()
    if output.is_relative_to(app):
        parser.error("The output directory must be outside the input app")
    output.mkdir(parents=True, exist_ok=True)
    if args.command == "sign":
        if not args.team_id or not re.fullmatch(r"[A-Z0-9]{10}", args.team_id):
            parser.error("--team-id must be your 10-character Team ID")
        if (
            not args.identity
            or not args.identity.startswith("Developer ID Application: ")
            or not args.identity.endswith(f"({args.team_id})")
        ):
            parser.error("--identity must be a Developer ID Application identity for --team-id")
        destination = output / "DAVE.app"
        if destination.exists() or destination == app:
            parser.error("Use a fresh output directory; the input app is never signed in place")
        run("/usr/bin/ditto", app, destination)
        plan = output / "signing-plan.json"
        plan.write_text(json.dumps(report, indent=2) + "\n")
        run(args.node, ROOT / "scripts/macos-sign.cjs", "sign", destination, args.identity, plan)
        verify_signatures(destination)
        report.update(
            {"state": "signed-not-notarized", "teamId": args.team_id, "app": str(destination)}
        )
        (output / "signing-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Signed staging copy: {destination}. Notarization is still required.")
        return
    if not args.keychain_profile:
        parser.error(
            "--keychain-profile is required; create it interactively with notarytool store-credentials"
        )
    # Refuse ad-hoc or unsigned inputs before any upload.
    verify_signatures(app)
    if existing_result is not None:
        result = existing_result
    else:
        submission = output / "notary-submission.zip"
        if args.reuse_submission:
            if not submission.is_file():
                parser.error("No existing submission ZIP to reuse")
            verify_submission_archive(app, submission)
        else:
            zip_app(app, submission)
        submission_process = subprocess.run(
            [
                str(item)
                for item in (
                    "/usr/bin/xcrun",
                    "notarytool",
                    "submit",
                    submission,
                    *credentials,
                    "--wait",
                    "--timeout",
                    "30m",
                    "--output-format",
                    "json",
                )
            ],
            capture_output=True,
            text=True,
        )
        result = parse_notary_result(submission_process, output)
    if result.get("status") == "In Progress":
        require_accepted(result)
    log = run(
        "/usr/bin/xcrun",
        "notarytool",
        "log",
        result["id"],
        *credentials,
    )
    (output / "notary-log.json").write_text(log + "\n")
    require_accepted(result)
    run("/usr/bin/xcrun", "stapler", "staple", app)
    verify(app)
    architecture = run("/usr/bin/lipo", "-archs", app / "Contents/MacOS/dave").replace(" ", "-")
    archive = output / f"DAVE-{report['version']}-macOS-{architecture}.zip"
    zip_app(app, archive)
    with tempfile.TemporaryDirectory(prefix="dave-release-check-") as directory:
        run("/usr/bin/ditto", "-x", "-k", archive, directory)
        verify(Path(directory) / app.name)
    checksum = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    digest = checksum.hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
    report.update(
        {
            "state": "notarized-and-stapled",
            "submissionId": result["id"],
            "sha256": digest,
            "archive": archive.name,
        }
    )
    (output / "release-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verified distribution archive: {archive}. No files were published.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Release stopped: {error}", file=sys.stderr)
        sys.exit(1)
