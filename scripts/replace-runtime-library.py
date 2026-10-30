"""Create a private app copy with an interface-compatible LGPL runtime replacement.

Never modifies the official app. Re-signs modified code ad hoc for local testing;
this does not preserve Apple's distribution identity or notarization ticket.
"""
import argparse
import shutil
import subprocess
from pathlib import Path


def replace_library(app, library, output):
    app, library, output = app.resolve(), library.resolve(), output.resolve()
    if library.name not in {"libiconv.2.dylib", "libcharset.1.dylib"}:
        raise ValueError("Use an interface-compatible libiconv.2.dylib or libcharset.1.dylib")
    if output.exists() or output.is_relative_to(app) or not output.name.endswith(".app"):
        raise ValueError("Choose a new .app destination outside the original app")
    if not (app / "Contents/Resources/python-runtime").is_dir() or not library.is_file():
        raise ValueError("Standalone app or replacement library is missing")
    subprocess.run(["/usr/bin/lipo", "-verify_arch", "arm64", str(library)], check=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/usr/bin/ditto", str(app), str(output)], check=True)
    runtime = output / "Contents/Resources/python-runtime"
    target = (runtime / "lib" / library.name).resolve()
    if not target.is_relative_to(runtime):
        raise ValueError("Library symlink points outside the private runtime")
    target.unlink()
    shutil.copyfile(library, target)
    # An ad-hoc local Python signature removes distribution library validation,
    # allowing a recipient's own compatible library without the publisher's key.
    for file in (target, (runtime / "bin/python").resolve(), output):
        subprocess.run([
            "/usr/bin/codesign", "--force", "--sign", "-",
            "--preserve-metadata=entitlements", str(file),
        ], check=True)
    subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(output)], check=True)
    print(f"Private modified copy: {output}")
    print("This copy is locally signed; it is not the official notarized distribution.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    replace_library(args.app, args.library, args.output)


if __name__ == "__main__":
    main()
