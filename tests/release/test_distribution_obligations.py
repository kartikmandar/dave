"""Safety regressions for vendor inventories, source notices and private copies."""
import hashlib
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
audit = runpy.run_path(str(ROOT / "scripts/audit-browser-vendors.py"))["audit"]
verify = runpy.run_path(str(ROOT / "scripts/bundle-app-notices.py"))["verify_notices"]
replace = runpy.run_path(str(ROOT / "scripts/replace-runtime-library.py"))["replace_library"]


def test_vendor_inventory_rejects_tampering_and_untracked_code(tmp_path):
    file = tmp_path / "vendor.js"
    file.write_text("original")
    manifest = {"files": {"vendor.js": hashlib.sha256(file.read_bytes()).hexdigest()}, "reviewedOn": "2026-10-30", "advisoryExceptions": []}
    assert audit(manifest, tmp_path)["errors"] == []
    file.write_text("modified")
    assert "Vendored hash mismatch" in str(audit(manifest, tmp_path)["errors"])
    (tmp_path / "unreviewed.js").write_text("extra")
    assert "inventory changed" in str(audit(manifest, tmp_path)["errors"])


def test_notice_paths_cannot_escape_the_companion(tmp_path):
    (tmp_path / "SHA256SUMS").write_text("0" * 64 + "  ../outside\n")
    with pytest.raises(ValueError, match="Unsafe notice path"):
        verify(tmp_path)


def test_modified_notice_cannot_be_bundled(tmp_path):
    (tmp_path / "license.txt").write_text("modified")
    (tmp_path / "SHA256SUMS").write_text("0" * 64 + "  license.txt\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(tmp_path)


def test_private_replacement_rejects_existing_destination_before_external_tools(tmp_path):
    with pytest.raises(ValueError, match="new .app"):
        replace(tmp_path, tmp_path / "libiconv.2.dylib", tmp_path)


def test_private_replacement_rejects_unrelated_library(tmp_path):
    with pytest.raises(ValueError, match="interface-compatible"):
        replace(tmp_path, tmp_path / "unrelated.dylib", tmp_path / "copy.app")
