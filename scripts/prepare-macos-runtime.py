"""Relocate conda native load commands before any distribution signatures exist."""

import os
import re
import runpy
import subprocess
import sys
from pathlib import Path

helpers = runpy.run_path(str(Path(__file__).with_name("macos-release.py")))


def prepare(runtime, source=None):
    runtime = runtime.resolve()
    source = (source or Path(__file__).resolve().parents[1] / ".pixi/envs/default").resolve()
    links = 0
    stale_debug_links = 0
    for directory, folders, files in os.walk(runtime):
        for name in folders + files:
            link = Path(directory) / name
            if not link.is_symlink() or link.resolve().is_relative_to(runtime):
                continue
            target = link.resolve()
            if not link.exists() and link.is_relative_to(runtime / "share/gdb/auto-load"):
                # Old conda environments can retain debugger aliases to removed
                # package versions. They are not runtime code or user data.
                link.unlink()
                stale_debug_links += 1
                continue
            if not target.is_relative_to(source):
                raise ValueError(f"Runtime symlink points outside the source environment: {link}")
            bundled = runtime / target.relative_to(source)
            if not bundled.exists():
                raise ValueError(f"Runtime symlink target is missing: {link}: {bundled}")
            link.unlink()
            link.symlink_to(os.path.relpath(bundled, link.parent))
            links += 1
    edits = 0
    for file in helpers["native_files"](runtime):
        commands = helpers["run"]("/usr/bin/otool", "-l", file)
        arguments = []
        for command, value in re.findall(
            r"cmd (LC_\w+)\s+cmdsize \d+\s+(?:name|path) (.*?) \(offset", commands
        ):
            if not value.startswith("/") or value.startswith(("/usr/lib/", "/System/Library/")):
                continue
            if command == "LC_RPATH":
                # Build-host search directories are not needed: all load commands
                # are relative or refer to macOS system libraries after relocation.
                arguments += ["-delete_rpath", value]
            elif command == "LC_ID_DYLIB":
                arguments += ["-id", "@rpath/" + file.name]
            elif "DYLIB" in command:
                target = runtime / "lib" / Path(value).name
                if not target.is_file():
                    raise ValueError(f"Cannot map native dependency into runtime: {file}: {value}")
                relative = os.path.relpath(target, file.parent)
                arguments += ["-change", value, "@loader_path/" + relative]
        if arguments:
            subprocess.run(["/usr/bin/install_name_tool", *arguments, str(file)], check=True)
            edits += 1
    print(
        f"Relocated {edits} native runtime files and {links} symlinks; removed {stale_debug_links} stale debugger aliases before signing"
    )


if __name__ == "__main__":
    prepare(Path(sys.argv[1]).resolve())
