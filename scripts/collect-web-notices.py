"""Collect shipped web-asset notices from upstream; keep uncertain grants explicit."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

SOURCES = [
    (
        "oxanium-2.000",
        "OFL-1.1",
        [
            "https://raw.githubusercontent.com/sevmeyer/oxanium/a8f39e0c71186190027a093e9001459410192d1e/OFL.txt"
        ],
    ),
    ("jquery-4.0.0", "MIT", ["https://raw.githubusercontent.com/jquery/jquery/4.0.0/LICENSE.txt"]),
    (
        "jquery-ui-1.14.1",
        "MIT",
        ["https://raw.githubusercontent.com/jquery/jquery-ui/1.14.1/LICENSE.txt"],
    ),
    ("bootstrap-5.3.8", "MIT", ["https://raw.githubusercontent.com/twbs/bootstrap/v5.3.8/LICENSE"]),
    ("async-2.5.0", "MIT", ["https://raw.githubusercontent.com/caolan/async/v2.5.0/LICENSE"]),
    ("plotly-3.6.0", "MIT", ["https://raw.githubusercontent.com/plotly/plotly.js/v3.6.0/LICENSE"]),
    (
        "plotly-2.35.2",
        "MIT",
        ["https://raw.githubusercontent.com/plotly/plotly.js/v2.35.2/LICENSE"],
    ),
    (
        "plotly-1.30.1",
        "MIT",
        ["https://raw.githubusercontent.com/plotly/plotly.js/v1.30.1/LICENSE"],
    ),
    (
        "mathjax-2.7.0",
        "Apache-2.0",
        ["https://raw.githubusercontent.com/mathjax/MathJax/2.7.0/LICENSE"],
    ),
    (
        "html2canvas-0.5.0-beta3",
        "MIT",
        ["https://raw.githubusercontent.com/niklasvh/html2canvas/v0.5.0-beta3/LICENSE"],
    ),
    (
        "jspdf-1.3.3",
        "MIT",
        ["https://raw.githubusercontent.com/parallax/jsPDF/v1.3.3/MIT-LICENSE.txt"],
    ),
    (
        "waiting-dialog",
        "MIT",
        ["https://raw.githubusercontent.com/ehpc/bootstrap-waitingfor/master/LICENSE"],
    ),
    (
        "font-awesome-4.7.0",
        "OFL-1.1 fonts; MIT code; CC-BY-3.0 docs",
        [
            "https://fontawesome.com/v4/license/",
            "https://openfontlicense.org/open-font-license-official-text/",
        ],
    ),
    (
        "agent-base-6.0.2",
        "MIT",
        [
            "https://raw.githubusercontent.com/TooTallNate/proxy-agents/main/packages/agent-base/LICENSE"
        ],
    ),
    (
        "https-proxy-agent-5.0.1",
        "MIT",
        [
            "https://raw.githubusercontent.com/TooTallNate/proxy-agents/main/packages/https-proxy-agent/LICENSE"
        ],
    ),
    (
        "lazy-val-1.0.5",
        "MIT declared in actual package metadata",
        ["https://raw.githubusercontent.com/develar/lazy-val/master/readme.md"],
    ),
    (
        "MIT-standard-terms",
        "MIT",
        ["https://raw.githubusercontent.com/spdx/license-list-data/main/text/MIT.txt"],
    ),
    (
        "libmagic-5.47",
        "BSD-2-Clause-Darwin",
        ["https://raw.githubusercontent.com/file/file/FILE5_47/COPYING"],
    ),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(args.app.resolve()):
        parser.error("Do not modify the signed app")
    for removed in ("logger.js.txt", "canvas2image.js.txt"):
        if (output / "bundled-web-headers" / removed).exists():
            parser.error("Use a fresh notice directory; removed vendor source headers are present")
    records = []
    for component, license_name, urls in SOURCES:
        files, errors = [], []
        for number, url in enumerate(urls):
            destination = output / "upstream" / component / f"notice-{number + 1}.txt"
            destination.parent.mkdir(parents=True, exist_ok=True)
            process = subprocess.run(
                [
                    "/usr/bin/curl",
                    "--disable",
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--proto",
                    "=https",
                    "--retry",
                    "2",
                    "--max-time",
                    "60",
                    "--output",
                    str(destination),
                    url,
                ],
                capture_output=True,
                text=True,
            )
            if process.returncode:
                errors.append({"url": url, "error": process.stderr.strip()})
            else:
                files.append(
                    {
                        "path": str(destination.relative_to(output)),
                        "url": url,
                        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                    }
                )
        records.append(
            {"component": component, "license": license_name, "files": files, "errors": errors}
        )
    static = args.app / "Contents/Resources/resources/static"
    inventory = []
    for directory in (
        static / "scripts/external",
        static / "styles/external",
        static / "font-awesome-4.7.0",
        static / "fonts",
    ):
        for file in sorted(directory.rglob("*")):
            if file.is_file() and not file.is_symlink():
                inventory.append(
                    {
                        "path": str(file.relative_to(static)),
                        "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                    }
                )
    # The former vendor files must be absent, rather than merely unreferenced.
    for removed in ("logger.js", "canvas2image.js"):
        if (static / "scripts/external" / removed).exists():
            raise ValueError(f"Legacy component still packaged: {removed}")
    first_party = []
    for filename in ("logPanel.js", "canvasExport.js"):
        file = static / "scripts" / filename
        source = file.read_text()
        if not source.startswith("/* SPDX-License-Identifier: Apache-2.0"):
            raise ValueError(f"Missing first-party license declaration: {filename}")
        inventory.append(
            {
                "path": str(file.relative_to(static)),
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            }
        )
        first_party.append(
            {
                "component": filename,
                "license": "Apache-2.0",
                "copyright": "2026 DAVE contributors",
                "implementation": "Original DAVE implementation using native browser APIs; compatibility API names retained",
            }
        )
    unresolved = []
    # Preserve the actual legacy declarations while awaiting full provenance review.
    headers = output / "bundled-web-headers"
    headers.mkdir(exist_ok=True)
    for filename in ("colorpicker.js", "waiting_dialog.js"):
        text = (static / "scripts/external" / filename).read_text(errors="replace")
        (headers / (filename + ".txt")).write_text(text[:4000])
    (headers / "sb-admin-theme.css.txt").write_text(
        (static / "styles/external/sb-admin-theme.css").read_text()[:4000]
    )
    from fontTools.ttLib import TTFont

    for filename in (
        static / "fonts/Oxanium-SemiBold.ttf",
        static / "font-awesome-4.7.0/fonts/FontAwesome.otf",
    ):
        font = TTFont(filename)
        names = [
            {"nameID": item.nameID, "text": item.toUnicode()}
            for item in font["name"].names
            if item.nameID in {0, 7, 8, 9, 11, 13, 14}
        ]
        (headers / (filename.name + ".json")).write_text(json.dumps(names, indent=2) + "\n")
    report = {
        "upstreamNotices": records,
        "firstPartyReplacements": first_party,
        "shippedWebAssetInventory": inventory,
        "unresolvedRedistributionRights": unresolved,
    }
    (output / "web-components.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "upstreams": len(records),
                "downloadErrors": [record["component"] for record in records if record["errors"]],
                "unresolvedRights": unresolved,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
