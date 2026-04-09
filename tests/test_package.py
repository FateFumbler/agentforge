from __future__ import annotations

import hashlib
import shutil
import zipfile
import tempfile
import unittest
from pathlib import Path

from agentforge import package as package_bridge
from agentforge.package_io import PackageValidationError, build_package_manifest
from agentforge.scanner import scan_workspace


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class PackageBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="agentforge-bridge-src-"))
        self.out = Path(tempfile.mkdtemp(prefix="agentforge-bridge-out-"))
        (self.workspace / "README.md").write_text("agentforge package bridge\n", encoding="utf-8")
        (self.workspace / "agent").mkdir()
        (self.workspace / "agent" / "manifest.json").write_text('{"name":"agent"}\n', encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)
        shutil.rmtree(self.out, ignore_errors=True)

    def test_package_bridge_returns_artifact_checksum(self) -> None:
        scan = scan_workspace(self.workspace)
        manifest = build_package_manifest(scan, workspace_name="bridge-checksum")
        package_file = self.out / "agentforge-package.zip"

        summary = package_bridge.export_package(manifest, str(self.workspace), str(package_file))

        self.assertTrue(Path(summary["artifact"]).exists())
        self.assertEqual(summary["artifactChecksum"], _sha256_file(Path(summary["artifact"])))
        self.assertEqual(summary["workspaceFiles"], len(manifest["files"]))

    def test_strict_import_blocks_extra_archive_members(self) -> None:
        scan = scan_workspace(self.workspace)
        manifest = build_package_manifest(scan, workspace_name="bridge-strict")
        package_file = self.out / "agentforge-package.zip"
        package_bridge.export_package(manifest, str(self.workspace), str(package_file))

        with zipfile.ZipFile(package_file, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("unexpected.txt", "this should be rejected")

        with self.assertRaises(PackageValidationError):
            package_bridge.import_package(str(package_file), str(self.out / "strict"), strict=True)
