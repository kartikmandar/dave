"""Release safety regressions runnable without a certificate or Apple account."""

import importlib.util
import plistlib
import runpy
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "macos_release", Path(__file__).resolve().parents[2] / "scripts/macos-release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
prepare_runtime = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/prepare-macos-runtime.py")
)["prepare"]


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def test_data_and_object_files_are_not_executable_inventory(self):
        (self.directory / "data").write_bytes(b"a data file")
        (self.directory / "object").write_bytes(struct.pack("<4I", 0xFEEDFACF, 0, 0, 1))
        self.assertEqual(list(release.native_files(self.directory)), [])

    def test_native_inventory_ignores_symlink_aliases(self):
        native = self.directory / "python"
        native.write_bytes(struct.pack("<4I", 0xFEEDFACF, 0, 0, 2))
        (self.directory / "python3").symlink_to("python")
        self.assertEqual(list(release.native_files(self.directory)), [native])

    def test_universal_binary_checks_all_slices(self):
        native = self.directory / "universal"
        native.write_bytes(
            struct.pack(">2I", 0xCAFEBABE, 2)
            + struct.pack(">5I", 0, 0, 48, 16, 0)
            + struct.pack(">5I", 0, 0, 64, 16, 0)
            + struct.pack("<4I", 0xFEEDFACF, 0, 0, 2)
            + struct.pack(">4I", 0xFEEDFACE, 0, 0, 6)
        )
        self.assertEqual(release.macho_types(native), {2, 6})

    def test_legacy_mutable_runtime_is_rejected_before_tools_run(self):
        app = self.directory / "DAVE.app"
        resources = app / "Contents/Resources"
        resources.mkdir(parents=True)
        (resources / "runtime.json").write_text('{"sha256":"preview"}')
        (app / "Contents/Info.plist").write_bytes(
            plistlib.dumps(
                {
                    "CFBundleShortVersionString": "2.0.0",
                    "CFBundleVersion": "2.0.0",
                    "CFBundleIdentifier": "science.stingray.dave",
                }
            )
        )
        with self.assertRaisesRegex(ValueError, "immutable runtime"):
            release.preflight(app, "a-node-executable-that-must-not-run")

    def test_existing_archive_is_never_overwritten(self):
        archive = self.directory / "release.zip"
        archive.write_bytes(b"previous release")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            release.zip_app(self.directory / "DAVE.app", archive)
        self.assertEqual(archive.read_bytes(), b"previous release")

    def test_missing_keychain_profile_retains_diagnostic_and_reports_no_upload(self):
        process = subprocess.CompletedProcess(
            [], 69, "", "No Keychain password item found for profile: dave-notary"
        )
        with self.assertRaisesRegex(ValueError, "No successful upload is established"):
            release.parse_notary_result(process, self.directory)
        self.assertEqual((self.directory / "notary-submit.stderr.log").read_text(), process.stderr)
        self.assertFalse((self.directory / "notary-result.json").exists())

    def test_notary_response_without_submission_id_is_rejected(self):
        process = subprocess.CompletedProcess([], 0, '{"status":"Accepted"}', "")
        with self.assertRaisesRegex(ValueError, "no submission ID"):
            release.parse_notary_result(process, self.directory)

    def test_pending_submission_cannot_be_finalized_or_marked_rejected(self):
        with self.assertRaisesRegex(ValueError, "Do not upload this candidate again"):
            release.require_accepted({"id": "pending-request", "status": "In Progress"})

    def test_finalization_requires_accepted_status_and_submission_id(self):
        for status in ("Invalid", "Rejected", "unknown", None):
            with self.subTest(status=status), self.assertRaises(ValueError):
                release.require_accepted({"id": "request", "status": status})
        with self.assertRaisesRegex(ValueError, "no submission ID"):
            release.require_accepted({"status": "Accepted"})
        release.require_accepted({"id": "request", "status": "Accepted"})

    @unittest.skipUnless(sys.platform == "darwin", "Requires Apple's codesign tool")
    def test_code_directory_hash_is_available_from_actual_codesign_output(self):
        self.assertRegex(release.code_directory_hash(Path("/bin/ls")), r"^[a-f0-9]{40}$")

    def test_source_environment_symlinks_become_internal_relative_links(self):
        source = self.directory / "source"
        runtime = self.directory / "runtime"
        for folder in (source, runtime):
            (folder / "lib").mkdir(parents=True)
            (folder / "lib/debug.py").write_text("debug support")
        link = runtime / "debug.py"
        link.symlink_to(source / "lib/debug.py")
        prepare_runtime(runtime, source)
        self.assertEqual(link.readlink(), Path("lib/debug.py"))
        self.assertEqual(link.resolve(), (runtime / "lib/debug.py").resolve())

    def test_unexpected_external_symlinks_stop_preparation(self):
        runtime = self.directory / "runtime"
        runtime.mkdir()
        (runtime / "unexpected").symlink_to("/usr/bin/python3")
        with self.assertRaisesRegex(ValueError, "outside the source environment"):
            prepare_runtime(runtime, self.directory / "source")


if __name__ == "__main__":
    unittest.main()
