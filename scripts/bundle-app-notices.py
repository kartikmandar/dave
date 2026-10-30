"""Copy verified license notices into an unsigned staging app before signing."""
import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path


def verify_notices(directory):
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        file = (directory / name).resolve()
        if not file.is_relative_to(directory.resolve()) or file.suffix.lower() in {".pem", ".key", ".p8", ".p12"}:
            raise ValueError("Unsafe notice path")
        if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError("Notice hash mismatch: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--notices", required=True, type=Path)
    args = parser.parse_args()
    resources = args.app / "Contents/Resources"
    if not resources.is_dir() or (resources / "THIRD_PARTY_NOTICES").exists():
        parser.error("Use a fresh staging app with no bundled notice folder")
    signature = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(args.app)], capture_output=True)
    details = subprocess.run(["codesign", "-dvv", str(args.app)], capture_output=True, text=True)
    if signature.returncode == 0 and "Authority=Developer ID Application:" in details.stderr:
        parser.error("Never change an already signed app; prepare a new staging copy first")
    verify_notices(args.notices)
    shutil.copytree(args.notices, resources / "THIRD_PARTY_NOTICES")
    for name in ["RUNTIME_SOURCE_OBLIGATIONS.md", "THIRD_PARTY_NOTICES.html"]:
        shutil.copyfile(Path(__file__).resolve().parents[1] / "docs" / name, resources / name)
    print("Bundled verified notices in unsigned staging app; sign this copy next")


if __name__ == "__main__":
    main()
