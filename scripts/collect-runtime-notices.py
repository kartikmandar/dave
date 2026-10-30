"""Collect exact conda package licenses and recipes without modifying the app.

Missing package archives are downloaded only from conda-forge and SHA-256 checked.
This inventories notices; unresolved rights and source obligations remain explicit.
"""

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath


def digest(file):
    result = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def allowed_member(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(part.startswith((".env", "credentials")) for part in path.parts):
        return False
    if path.suffix.lower() in {".pem", ".key", ".p8", ".p12"}:
        return False
    return name.startswith(("info/licenses/", "info/recipe/")) or name in {
        "info/license.txt",
        "info/about.json",
        "info/index.json",
        "info/files",
    }


def archive_members(archive):
    if archive.name.endswith(".conda"):
        with zipfile.ZipFile(archive) as package:
            entries = [
                name
                for name in package.namelist()
                if name.startswith("info-") and name.endswith(".tar.zst")
            ]
            if len(entries) != 1:
                raise ValueError(f"Expected one conda info component: {archive}")
            compressed = package.read(entries[0])
        try:
            from compression import zstd
        except ImportError:
            from backports import zstd
        stream = io.BytesIO(zstd.decompress(compressed))
        source = tarfile.open(fileobj=stream, mode="r:")
    else:
        source = tarfile.open(archive, mode="r:*")
    with source:
        for entry in source:
            if entry.isfile() and allowed_member(entry.name):
                if entry.size > 20 * 1024 * 1024:
                    raise ValueError(f"Unexpectedly large notice/recipe: {entry.name}")
                yield entry.name, source.extractfile(entry).read()


def collect_package(record, output, cache, archives):
    identifier = "{name}-{version}-{build}".format(**record)
    target = output / "conda" / identifier
    source = cache / identifier
    provenance = {
        key: record.get(key) for key in ("name", "version", "build", "license", "url", "sha256")
    }
    files = []
    if (source / "info/index.json").exists():
        index = json.loads((source / "info/index.json").read_text())
        if any(str(index[key]) != str(record[key]) for key in ("name", "version", "build")):
            raise ValueError(f"Package-cache identity mismatch: {identifier}")
        members = (
            (str(file.relative_to(source)), file.read_bytes())
            for file in (source / "info").rglob("*")
            if file.is_file()
            and not file.is_symlink()
            and allowed_member(str(file.relative_to(source)))
        )
        provenance["noticeSource"] = "exact-build-package-cache"
    else:
        url = urllib.parse.urlparse(record["url"])
        if (
            url.scheme != "https"
            or url.hostname != "conda.anaconda.org"
            or url.username
            or url.query
        ):
            raise ValueError(f"Unexpected package download origin: {identifier}")
        archives.mkdir(parents=True, exist_ok=True)
        archive = archives / Path(url.path).name
        if not archive.exists() or digest(archive) != record["sha256"]:
            temporary = archive.with_suffix(archive.suffix + ".partial")
            # Use macOS's verified system trust store; never disable TLS checks.
            subprocess.run(
                [
                    "/usr/bin/curl",
                    "--disable",
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--retry",
                    "2",
                    "--proto",
                    "=https",
                    "--max-time",
                    "180",
                    "--output",
                    str(temporary),
                    record["url"],
                ],
                check=True,
            )
            if digest(temporary) != record["sha256"]:
                raise ValueError(f"Package SHA-256 mismatch: {identifier}")
            temporary.replace(archive)
        members = archive_members(archive)
        provenance["noticeSource"] = "sha256-verified-package-archive"
    for name, data in members:
        destination = target / PurePosixPath(name).relative_to("info")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        if name.startswith("info/licenses/") or name == "info/license.txt":
            files.append(str(destination.relative_to(output)))
    provenance["licenseFiles"] = files
    payload = (target / "files").read_text().splitlines() if (target / "files").exists() else []
    provenance["payloadFiles"] = len(payload)
    provenance["noticeStatus"] = (
        "collected" if files else ("metadata-only" if not payload else "missing-license-text")
    )
    return provenance


def collect_python(runtime, output):
    records = []
    for directory in sorted(runtime.glob("lib/python*/site-packages/*.dist-info")):
        from email.parser import Parser

        metadata = Parser().parsestr((directory / "METADATA").read_text(errors="replace"))
        name, version = metadata["Name"], metadata["Version"]
        target = output / "python" / directory.name
        licenses = []
        for file in directory.rglob("*"):
            relative = file.relative_to(directory)
            if (
                file.is_file()
                and not file.is_symlink()
                and (
                    relative.parts[0] == "licenses"
                    or any(word in file.name.lower() for word in ("license", "copying", "notice"))
                )
            ):
                if not allowed_member("info/licenses/" + str(relative)):
                    continue
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file, destination)
                licenses.append(str(destination.relative_to(output)))
        records.append(
            {
                "name": name,
                "version": version,
                "license": metadata.get("License-Expression") or metadata.get("License"),
                "licenseFiles": licenses,
                "noticeSource": "actual-bundled-dist-info",
            }
        )
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cache", type=Path, default=Path.home() / "Library/Caches/rattler/cache/pkgs"
    )
    parser.add_argument("--archives", type=Path, default=Path("build/third-party-package-cache"))
    args = parser.parse_args()
    app, output = args.app.resolve(), args.output.resolve()
    if output.is_relative_to(app):
        parser.error("Notices must be staged outside the signed app")
    runtime = app / "Contents/Resources/python-runtime"
    packages = [
        json.loads(file.read_text()) for file in sorted((runtime / "conda-meta").glob("*.json"))
    ]
    if not packages:
        parser.error("No bundled conda metadata found")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    errors = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(collect_package, item, output, args.cache, args.archives): item
            for item in packages
        }
        for future in as_completed(futures):
            try:
                records.append(future.result())
            except Exception as error:
                errors.append({"name": futures[future]["name"], "error": str(error)})
            if (len(records) + len(errors)) % 25 == 0:
                print(
                    f"Collected {len(records)} of {len(packages)} package notices; errors: {len(errors)}",
                    flush=True,
                )
    report = {
        "condaPackages": sorted(records, key=lambda record: record["name"]),
        "pythonDistributions": collect_python(runtime, output),
        "errors": errors,
    }
    (output / "runtime-components.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "packages": len(records),
                "errors": errors,
                "missingLicenseText": [
                    record["name"]
                    for record in records
                    if record["noticeStatus"] == "missing-license-text"
                ],
            },
            indent=2,
        )
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
