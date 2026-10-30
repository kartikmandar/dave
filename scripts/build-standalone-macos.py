"""Build an Apple Silicon/Intel app using the native locked Pixi environment.

Install conda-pack==0.9.2 in the build interpreter (or PYTHONPATH). Use the
supported Node 22 or 24 build runtime with Electron Packager 20.
"""

import argparse
import platform
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node")
    parser.add_argument("--reuse-runtime", action="store_true")
    parser.add_argument("--version", default="2.0.0", help="Numeric public release version")
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("Build on macOS for the target CPU architecture")
    root = Path(__file__).resolve().parents[1]
    archive = root / "build/standalone/python-runtime.tar.gz"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not args.reuse_runtime:
        import conda_pack

        conda_pack.pack(prefix=str(root / ".pixi/envs/default"), output=str(archive), force=True)
    if not archive.exists():
        parser.error("No runtime archive exists; omit --reuse-runtime")
    version = subprocess.check_output([args.node, "--version"], text=True)
    if int(version.lstrip("v").split(".")[0]) not in (22, 24):
        parser.error("Use --node with Node 22 or 24")
    subprocess.run(
        [args.node, str(root / "scripts/package-macos.cjs"), args.version], check=True, cwd=root
    )


if __name__ == "__main__":
    main()
