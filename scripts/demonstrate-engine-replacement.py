"""Build compatible local engine/media replacement shims and observe real startup.

This mechanism demonstration does not rebuild Chromium or modify the official app.
"""

import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--app", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
root = args.output.resolve()
if root.exists() or root.is_relative_to(args.app.resolve()):
    parser.error("Use a fresh output directory outside the original app")
if (
    args.app.suffix != ".app"
    or not (args.app / "Contents/Frameworks/Electron Framework.framework").is_dir()
):
    parser.error("Provide an existing Electron app")
root.mkdir(parents=True)
app = root / "DAVE.app"
subprocess.run(["ditto", str(args.app.resolve()), str(app)], check=True)
framework = app / "Contents/Frameworks/Electron Framework.framework"
version = framework / "Versions/A"
for target, original_name, label, install_name in [
    (
        version / "Libraries/libffmpeg.dylib",
        "libffmpeg-original.dylib",
        "ffmpeg",
        "@loader_path/libffmpeg.dylib",
    ),
    (
        version / "Electron Framework",
        "Electron Framework.original.dylib",
        "blink-framework",
        "@rpath/Electron Framework.framework/Versions/A/Electron Framework",
    ),
]:
    original = target.with_name(original_name)
    target.rename(original)
    subprocess.run(
        ["install_name_tool", "-id", "@loader_path/" + original_name, str(original)], check=True
    )
    source = root / (label + ".c")
    marker = root / (label + "-loaded.txt")
    source.write_text(
        "#include <stdio.h>\n__attribute__((constructor)) static void loaded(void) { FILE *f = fopen("
        + json.dumps(str(marker))
        + ', "w"); if (f) { fputs("recipient-built compatible '
        + label
        + ' replacement loaded", f); fclose(f); } }\n'
    )
    subprocess.run(
        [
            "clang",
            "-arch",
            "arm64",
            "-dynamiclib",
            str(source),
            "-Wl,-reexport_library," + str(original),
            "-Wl,-install_name," + install_name,
            "-o",
            str(target),
        ],
        check=True,
    )
    for file in [original, target]:
        subprocess.run(["codesign", "--force", "--sign", "-", str(file)], check=True)
for file in [framework, *(app / "Contents/Frameworks").glob("*.app"), app]:
    subprocess.run(
        ["codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(file)],
        check=True,
    )
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
print("Private recipient-built FFmpeg and Electron-framework replacement ready:", app)
