from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
import unittest
from pathlib import Path

from agentforge.package_io import (
    ZIP_MANIFEST_NAME,
    build_package_manifest,
    export_package,
    import_package,
    PackageValidationError,
)
from agentforge.scanner import scan_workspace


class PackageExportImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="agentforge-source-"))
        self.out = Path(tempfile.mkdtemp(prefix="agentforge-out-"))

        (self.workspace / "README.md").write_text("AgentForge fixture\n", encoding="utf-8")
        (self.workspace / "agent").mkdir()
        (self.workspace / "agent" / "agent.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
        (self.workspace / "tests").mkdir()
        (self.workspace / "tests" / "test_agent.py").write_text("assert True\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)
        shutil.rmtree(self.out, ignore_errors=True)

    def test_roundtrip_export_import(self) -> None:
        scan = scan_workspace(self.workspace)
        manifest = build_package_manifest(scan, workspace_name="qa-roundtrip")
        package_file = self.out / "agentforge-package.zip"

        summary = export_package(manifest, self.workspace, package_file)
        self.assertTrue(Path(summary.package_path).exists())
        self.assertEqual(summary.file_count, len(manifest["files"]))

        imported = self.out / "imported"
        import_summary = import_package(package_file, imported)
        self.assertEqual(import_summary.file_count, summary.file_count)
        self.assertTrue((imported / "README.md").exists())
        self.assertTrue((imported / "agent" / "agent.json").exists())

    def test_strict_import_blocks_extra_artifacts(self) -> None:
        scan = scan_workspace(self.workspace)
        manifest = build_package_manifest(scan)
        package_file = self.out / "agentforge-package.zip"
        export_package(manifest, self.workspace, package_file)

        with zipfile.ZipFile(package_file, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("notes.md", "added after export\n")

        with self.assertRaises(PackageValidationError):
            import_package(package_file, self.out / "strict", strict=True)

    def test_rejects_path_traversal_members(self) -> None:
        bad_package = self.out / "bad.zip"
        bad_manifest = {
            "schemaVersion": "2.1.0",
            "generatedAt": "2026-01-01T00:00:00Z",
            "packageId": "bad-path",
            "scanner": {"schemaVersion": "1.0.0", "signature": "bad", "scannedAt": "2026-01-01T00:00:00Z"},
            "source": {"rootPath": str(self.workspace), "totalFiles": 1, "markerFilesDetected": {}},
            "files": [
                {"path": "../outside.txt", "size_bytes": 4, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "section": "other"},
            ],
        }

        with zipfile.ZipFile(bad_package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(ZIP_MANIFEST_NAME, json.dumps(bad_manifest))
            zf.writestr("../outside.txt", "evil")

        with self.assertRaises(PackageValidationError):
            import_package(bad_package, self.out / "malicious", strict=True)


if __name__ == "__main__":
    unittest.main()
