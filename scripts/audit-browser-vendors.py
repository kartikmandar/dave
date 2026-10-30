"""Verify the shipped browser tree and query advisories for its exact versions."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]


def audit(manifest, directory, live=False):
    errors = []
    actual = {str(file.relative_to(directory)): file for file in directory.rglob("*") if file.is_file()}
    if set(actual) != set(manifest["files"]):
        errors.append("Vendored tree inventory changed; review additions and removals")
    for name, expected in manifest["files"].items():
        if name not in actual or hashlib.sha256(actual[name].read_bytes()).hexdigest() != expected:
            errors.append("Vendored hash mismatch: " + name)
    # The one disputed exception is valid only while no application code feeds
    # user strings/configuration into the implicated message/localization APIs.
    owned = directory.parent if directory.name == "external" else ROOT / "src/main/resources/static/scripts"
    for name, expected in manifest.get("policyFiles", {}).items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            errors.append("Browser policy file changed; renewed security review required: " + name)
    for file in owned.rglob("*.js"):
        if "external" not in file.relative_to(owned).parts and re.search(r"MathJax\s*\.\s*(Message|Localization)|MathJax\s*\.\s*Hub\s*\.\s*Config", file.read_text()):
            errors.append("MathJax message/config path requires renewed advisory review: " + str(file.relative_to(ROOT)))
    advisories = []
    if live:
        allowed = {(item["id"], item["package"], item["version"]) for item in manifest["advisoryExceptions"]}
        seen = set()
        for component in manifest["components"]:
            query = urlencode({"ecosystem": "npm", "affects": component["package"] + "@" + component["version"], "per_page": 100})
            result = json.loads(subprocess.check_output(["gh", "api", "advisories?" + query]))
            if len(result) >= 100:
                errors.append("Advisory pagination requires review")
            for item in result:
                if item["withdrawn_at"]:
                    continue
                key = (item["ghsa_id"], component["package"], component["version"])
                seen.add(key)
                advisories.append({"id": key[0], "package": key[1], "version": key[2], "url": item["html_url"], "severity": item["severity"], "disposition": "reviewed-exception" if key in allowed else "unresolved"})
                if key not in allowed:
                    errors.append("Unreviewed advisory: " + str(key))
        if allowed - seen:
            errors.append("Advisory exception is stale or no longer matches; review it")
    return {"reviewedOn": manifest["reviewedOn"], "filesVerified": len(actual), "liveAdvisoryQuery": live, "advisories": advisories, "exceptions": manifest["advisoryExceptions"], "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, help="Inspect the packaged app instead of source")
    parser.add_argument("--live", action="store_true", help="Query GitHub Advisory Database; requires gh access")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "scripts/browser-vendor-manifest.json").read_text())
    directory = args.app / "Contents/Resources/resources/static/scripts/external" if args.app else ROOT / manifest["root"]
    report = audit(manifest, directory, args.live)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
