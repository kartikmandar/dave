"""Fill missing license texts from exact, hash-verified upstream source archives."""

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import yaml

LOCKS = {}
LOCKS_GUARD = threading.Lock()


def sha256(file):
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(source, cache):
    expected = source.get("sha256", "")
    urls = source.get("url", [])
    if isinstance(urls, str):
        urls = [urls]
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("Source recipe has no SHA-256")
    with LOCKS_GUARD:
        lock = LOCKS.setdefault(expected, threading.Lock())
    with lock:
        errors = []
        for original in urls:
            url = original.replace("http://", "https://", 1)
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.username or parsed.query:
                continue
            filename = expected[:12] + "-" + Path(parsed.path).name
            file = cache / filename
            if file.exists() and sha256(file) == expected:
                return file, url
            temporary = file.with_suffix(file.suffix + ".partial")
            result = subprocess.run(
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
                    "240",
                    "--output",
                    str(temporary),
                    url,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and sha256(temporary) == expected:
                temporary.replace(file)
                return file, url
            errors.append(f"{url}: download or SHA-256 verification failed")
        raise ValueError("; ".join(errors) or "No verified source archive URL")


def source_notices(record, root, cache):
    identifier = "{name}-{version}-{build}".format(**record)
    folder = root / "conda" / identifier
    recipe = folder / "recipe/meta.yaml"
    if not recipe.exists():
        return {"name": record["name"], "error": "No rendered source recipe"}
    data = yaml.safe_load(recipe.read_text())
    sources = data.get("source", [])
    if isinstance(sources, dict):
        sources = [sources]
    result = {"name": record["name"], "sources": [], "licenseFiles": []}
    copyleft = "GPL" in record["license"] and record["name"] not in {
        "pylru",
        "freetype",
        "libfreetype",
        "libfreetype6",
    }
    for source in sources:
        try:
            archive, url = download(source, cache)
            result["sources"].append(
                {
                    "url": url,
                    "sha256": source["sha256"],
                    "archive": archive.name,
                    "patches": source.get("patches", []),
                    "copyleftSource": copyleft,
                    "runtimeSourceDependency": record["name"] in {"python", "ncurses"},
                }
            )
            with tarfile.open(archive, "r:*") as package:
                for member in package:
                    name = Path(member.name).name
                    if (
                        not member.isfile()
                        or member.size > 2 * 1024 * 1024
                        or not re.match(
                            r"^(licen[cs]e|copying|notice|copyright|ftl)(\.|$)", name, re.I
                        )
                    ):
                        continue
                    if (
                        Path(name).suffix.lower() in {".pem", ".key", ".p8", ".p12"}
                        or Path(member.name).is_absolute()
                        or ".." in Path(member.name).parts
                    ):
                        continue
                    destination = folder / "upstream-licenses" / archive.name / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(package.extractfile(member).read())
                    result["licenseFiles"].append(str(destination.relative_to(root)))
        except Exception as error:
            result.setdefault("errors", []).append(str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notices", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("build/third-party-source-cache"))
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    report = json.loads((args.notices / "runtime-components.json").read_text())

    def normalize(name):
        return re.sub(r"[-_.]+", "-", name.lower())

    python = {
        normalize(record["name"]): record
        for record in report["pythonDistributions"]
        if record["name"]
    }
    aliases = {
        "astropy-base": "astropy",
        "brotli-python": "brotli",
        "matplotlib-base": "matplotlib",
        "pyarrow-core": "pyarrow",
    }
    resolutions, pending = [], []
    for record in report["condaPackages"]:
        candidate = python.get(normalize(aliases.get(record["name"], record["name"])))
        if (
            record["noticeStatus"] == "missing-license-text"
            and candidate
            and candidate["licenseFiles"]
        ):
            resolutions.append(
                {
                    "name": record["name"],
                    "licenseFiles": candidate["licenseFiles"],
                    "evidence": "actual bundled Python distribution",
                    "distributionVersion": candidate["version"],
                }
            )
        elif record["name"] in {"python", "ncurses"} or record["noticeStatus"] == "missing-license-text" or (
            "GPL" in record["license"] and " OR " not in record["license"]
        ):
            pending.append(record)
    with ThreadPoolExecutor(max_workers=3) as executor:
        for result in executor.map(
            lambda record: source_notices(record, args.notices, args.cache), pending
        ):
            resolutions.append(result)
            print(
                f"Source notices: {result['name']} ({len(result.get('licenseFiles', []))} texts)",
                flush=True,
            )
    result = {
        "resolutions": resolutions,
        "unresolved": [record["name"] for record in resolutions if not record.get("licenseFiles")],
        "note": "Source and recipe collection is evidence for review, not a blanket legal clearance.",
    }
    (args.notices / "source-resolutions.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"unresolved": result["unresolved"]}))


if __name__ == "__main__":
    main()
