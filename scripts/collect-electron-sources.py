"""Collect the exact Electron/Chromium copyleft source components, patches and build pins."""

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path


def fetch(url, file):
    file.parent.mkdir(parents=True, exist_ok=True)
    checksum = file.with_name(file.name + ".sha256")
    if file.exists() and checksum.exists():
        if digest(file) != checksum.read_text().strip():
            raise ValueError("Cached source checksum mismatch: " + str(file))
    else:
        temporary = file.with_suffix(file.suffix + ".partial")
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
                "--max-time",
                "300",
                "--proto",
                "=https",
                url,
                "-o",
                str(temporary),
            ],
            check=True,
        )
        temporary.replace(file)
        checksum.write_text(digest(file) + "\n")
    return file


def digest(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def collect(notices, sources, cache):
    runtime = json.loads((notices / "runtime-components.json").read_text())
    urls = [item["url"] for item in runtime["condaPackages"]]
    if not any("/osx-arm64/" in url for url in urls) or any("/osx-64/" in url for url in urls):
        raise ValueError("This source configuration review currently covers Apple Silicon only")
    version = json.loads((notices / "electron-components.json").read_text())["electronVersion"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Unexpected Electron version")
    output = sources / "electron-chromium"
    if output.exists():
        raise ValueError("Use a fresh source directory")
    output.mkdir(parents=True)
    records = []

    def archive(url, name):
        file = fetch(url, cache / name)
        with tarfile.open(file) as package:
            # Inspect only archive metadata here; no source secrets/keys are opened.
            if any(
                Path(member.name).is_absolute() or ".." in Path(member.name).parts
                for member in package
            ):
                raise ValueError("Unsafe upstream source archive paths")
        shutil.copyfile(file, output / name)
        records.append({"file": name, "url": url, "sha256": digest(file)})
        return file

    def gitiles(path, relative):
        url = (
            f"https://chromium.googlesource.com/chromium/src/+/{chromium_commit}/{path}?format=TEXT"
        )
        cached = fetch(url, cache / (relative.replace("/", "__") + ".base64"))
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(cached.read_bytes()))
        records.append({"file": relative, "url": url, "sha256": digest(target)})
        return target.read_text()

    reference = json.loads(
        subprocess.check_output(["gh", "api", f"repos/electron/electron/git/ref/tags/v{version}"])
    )["object"]
    if reference["type"] == "tag":
        reference = json.loads(
            subprocess.check_output(
                ["gh", "api", "repos/electron/electron/git/tags/" + reference["sha"]]
            )
        )["object"]
    if reference["type"] != "commit":
        raise ValueError("Electron source tag must resolve to a commit")
    electron_commit = reference["sha"]
    electron = archive(
        f"https://codeload.github.com/electron/electron/tar.gz/{electron_commit}",
        f"electron-{version}-{electron_commit}.tar.gz",
    )
    with tarfile.open(electron) as package:
        prefix = package.getmembers()[0].name.split("/")[0]
        deps = package.extractfile(prefix + "/DEPS").read().decode()
        patches = (
            package.extractfile(prefix + "/patches/ffmpeg/.patches").read().decode().splitlines()
        )
        if not patches or any(
            not (name.endswith(".patch") and "/" not in name) for name in patches
        ):
            raise ValueError("Unreviewed Electron FFmpeg patch list")
        for name in patches:
            (output / name).write_bytes(
                package.extractfile(prefix + "/patches/ffmpeg/" + name).read()
            )
    chromium_version = re.search(r"'chromium_version':\s*'([^']+)'", deps)[1]
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", chromium_version):
        raise ValueError("Unexpected Chromium version")
    tag = fetch(
        f"https://chromium.googlesource.com/chromium/src/+/{chromium_version}?format=JSON",
        cache / f"chromium-{chromium_version}.json",
    )
    chromium_commit = json.loads(tag.read_text()[5:])["commit"]
    deps = gitiles("DEPS", "chromium/DEPS")
    ffmpeg_commit = re.search(r"'ffmpeg_revision':\s*'([a-f0-9]{40})'", deps)[1]
    ffmpeg = archive(
        f"https://chromium.googlesource.com/chromium/third_party/ffmpeg/+archive/{ffmpeg_commit}.tar.gz",
        f"ffmpeg-{ffmpeg_commit}.tar.gz",
    )
    configurations = {}
    with tarfile.open(ffmpeg) as package:
        for branding in ("Chrome", "Chromium"):
            name = f"chromium/config/{branding}/mac/arm64/config.h"
            config = package.extractfile(name).read().decode()
            flags = {
                key: int(re.search(r"#define CONFIG_" + key + r"\s+(\d+)", config)[1])
                for key in ("GPL", "NONFREE", "VERSION3")
            }
            if any(flags.values()):
                raise ValueError("FFmpeg license/build flags require renewed review")
            configurations[name] = flags
        for name in ["COPYING.LGPLv2.1", "LICENSE.md"]:
            (output / ("ffmpeg-" + name)).write_bytes(package.extractfile(name).read())
    for directory in ["renderer", "public", "common", "tools"]:
        archive(
            f"https://chromium.googlesource.com/chromium/src/+archive/{chromium_commit}/third_party/blink/{directory}.tar.gz",
            f"blink-{directory}-{chromium_commit}.tar.gz",
        )
    archive(
        f"https://chromium.googlesource.com/chromium/src/+archive/{chromium_commit}/build.tar.gz",
        f"chromium-build-{chromium_commit}.tar.gz",
    )
    # Include Mozilla-derived URL/certificate source conservatively, even where BSD options apply.
    for directory in ["url", "net/cert"]:
        archive(
            f"https://chromium.googlesource.com/chromium/src/+archive/{chromium_commit}/{directory}.tar.gz",
            f"chromium-{directory.replace('/', '-')}-{chromium_commit}.tar.gz",
        )
    for path in [
        ".gn",
        "BUILD.gn",
        "LICENSE",
        "third_party/blink/DEPS",
        "third_party/blink/LICENSE_FOR_ABOUT_CREDITS",
        "third_party/blink/README.md",
    ]:
        gitiles(path, "chromium/" + path)
    shutil.copyfile(notices / "electron/LICENSES.chromium.html", output / "LICENSES.chromium.html")
    result = {
        "electronVersion": version,
        "electronCommit": electron_commit,
        "chromiumVersion": chromium_version,
        "chromiumCommit": chromium_commit,
        "ffmpegCommit": ffmpeg_commit,
        "electronFFmpegPatches": patches,
        "macArm64FFmpegFlags": configurations,
        "archivesAndBuildPins": records,
        "blinkScope": "Complete renderer/public/common/tools product sources; non-product manual/performance/web test trees omitted",
        "rebuild": "Electron archive supplies all Electron patches, DEPS, scripts and build args. Chromium DEPS pins all additional permissive build dependencies for a full engine rebuild. A full independent Chromium build is not claimed.",
    }
    (output / "source-manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notices", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--cache", type=Path, default=Path("build/electron-source-cache"))
    args = parser.parse_args()
    print(json.dumps(collect(args.notices, args.sources, args.cache), indent=2))


if __name__ == "__main__":
    main()
