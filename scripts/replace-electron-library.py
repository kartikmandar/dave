"""Create a private locally signed app copy with a compatible engine/media library."""

import argparse
import shutil
import subprocess
from pathlib import Path


def replace_library(app, library, output):
    app, library, output = app.resolve(), library.resolve(), output.resolve()
    if library.name not in {"libffmpeg.dylib", "Electron Framework"}:
        raise ValueError("Use an interface-compatible libffmpeg.dylib or Electron Framework")
    if output.exists() or output.is_relative_to(app) or not output.name.endswith(".app"):
        raise ValueError("Choose a new .app destination outside the original app")
    framework_relative = Path("Contents/Frameworks/Electron Framework.framework")
    if not (app / framework_relative).is_dir() or not library.is_file():
        raise ValueError("App framework or replacement library is missing")
    subprocess.run(["/usr/bin/lipo", "-verify_arch", "arm64", str(library)], check=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/usr/bin/ditto", str(app), str(output)], check=True)
    framework = output / framework_relative
    target = (
        framework
        / "Versions/A"
        / (
            "Libraries/libffmpeg.dylib"
            if library.name == "libffmpeg.dylib"
            else "Electron Framework"
        )
    )
    target.unlink()
    shutil.copyfile(library, target)
    # Every Electron loading process needs a local signature, including helpers;
    # otherwise Developer ID library validation rejects a recipient's own code.
    for file in [target, framework, *(output / "Contents/Frameworks").glob("*.app"), output]:
        subprocess.run(
            [
                "/usr/bin/codesign",
                "--force",
                "--sign",
                "-",
                "--preserve-metadata=entitlements",
                str(file),
            ],
            check=True,
        )
    subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(output)], check=True)
    print(
        f"Private modified copy: {output}; local signature, not the official notarized distribution"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    replace_library(args.app, args.library, args.output)


if __name__ == "__main__":
    main()
