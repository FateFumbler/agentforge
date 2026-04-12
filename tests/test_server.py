"""Tests for the AgentForge FastAPI server."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure httpx is available for TestClient
import httpx  # noqa: F401

from fastapi.testclient import TestClient

from agentforge.server import create_app
from agentforge.scanner import scan_workspace
from agentforge.manifest import build_manifest_from_scan
from agentforge.package_io import build_package_manifest, export_package


class _ServerTestBase(unittest.TestCase):
    """Base class that provides a test client and temp directories."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentforge-server-test-"))
        self.workspace = self.tmpdir / "workspace"
        self.workspace.mkdir()
        self.artifacts_dir = self.tmpdir / "artifacts"
        self.artifacts_dir.mkdir()
        self.export_dir = self.tmpdir / "exports"
        self.export_dir.mkdir()

        # Seed a minimal workspace
        (self.workspace / "SOUL.md").write_text("identity", encoding="utf-8")
        (self.workspace / "README.md").write_text("# test\n", encoding="utf-8")
        (self.workspace / "main.py").write_text("print('hello')\n", encoding="utf-8")

        self.app = create_app()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class HealthCheckTests(_ServerTestBase):
    def test_health_returns_ok(self) -> None:
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)


class ListAgentsTests(_ServerTestBase):
    def test_empty_artifacts_returns_empty_list(self) -> None:
        with patch("agentforge.server._ARTIFACTS_DIR", self.artifacts_dir):
            resp = self.client.get("/api/agents")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_lists_agents_with_manifests(self) -> None:
        agent_dir = self.artifacts_dir / "test-agent"
        agent_dir.mkdir()
        manifest = {
            "schemaVersion": "1.0.0",
            "project": {"name": "test-agent", "owner": "test"},
            "files": [],
            "tags": ["agentforge"],
        }
        (agent_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        with patch("agentforge.server._ARTIFACTS_DIR", self.artifacts_dir):
            resp = self.client.get("/api/agents")
        self.assertEqual(resp.status_code, 200)
        agents = resp.json()
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["name"], "test-agent")


class GetAgentTests(_ServerTestBase):
    def test_returns_agent_manifest(self) -> None:
        agent_dir = self.artifacts_dir / "my-agent"
        agent_dir.mkdir()
        manifest = {
            "schemaVersion": "1.0.0",
            "project": {"name": "my-agent", "owner": "test"},
            "files": [],
            "tags": [],
        }
        (agent_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        with patch("agentforge.server._ARTIFACTS_DIR", self.artifacts_dir):
            resp = self.client.get("/api/agents/my-agent")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "my-agent")
        self.assertIn("manifest", data)

    def test_unknown_agent_returns_404(self) -> None:
        with patch("agentforge.server._ARTIFACTS_DIR", self.artifacts_dir):
            resp = self.client.get("/api/agents/nonexistent")
        self.assertEqual(resp.status_code, 404)


class ScanWorkspaceTests(_ServerTestBase):
    def test_scan_returns_valid_json(self) -> None:
        resp = self.client.post(
            "/api/scan",
            json={"workspace_path": str(self.workspace)},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("schemaVersion", data)
        self.assertIn("files", data)
        self.assertIn("summary", data)

    def test_scan_nonexistent_path_returns_404(self) -> None:
        resp = self.client.post(
            "/api/scan",
            json={"workspace_path": "/nonexistent/path/that/does/not/exist"},
        )
        self.assertEqual(resp.status_code, 404)


class ManifestGenerateTests(_ServerTestBase):
    def test_generate_manifest_from_scan(self) -> None:
        scan = scan_workspace(self.workspace)
        resp = self.client.post(
            "/api/manifest/generate",
            json={
                "scan_data": scan,
                "project_name": "test-project",
                "owner": "tester",
                "tags": ["demo"],
            },
        )
        self.assertEqual(resp.status_code, 200)
        manifest = resp.json()
        self.assertEqual(manifest["project"]["name"], "test-project")
        self.assertEqual(manifest["project"]["owner"], "tester")
        self.assertIn("demo", manifest["tags"])

    def test_generate_manifest_handles_incomplete_scan_gracefully(self) -> None:
        """Incomplete scan data should still produce a manifest with defaults."""
        resp = self.client.post(
            "/api/manifest/generate",
            json={"scan_data": {"incomplete": True}},
        )
        # build_manifest_from_scan is lenient with missing keys, returns 200
        self.assertEqual(resp.status_code, 200)
        manifest = resp.json()
        self.assertIn("schemaVersion", manifest)


class ManifestValidateTests(_ServerTestBase):
    def test_validate_valid_manifest(self) -> None:
        agent_dir = self.artifacts_dir / "valid-agent"
        agent_dir.mkdir()
        scan = scan_workspace(self.workspace)
        manifest = build_manifest_from_scan(scan, project_name="valid-agent")
        (agent_dir / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True), encoding="utf-8"
        )

        with patch("agentforge.server._ARTIFACTS_DIR", self.artifacts_dir):
            resp = self.client.get("/api/manifest/validate/valid-agent")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["errors"], [])

    def test_validate_nonexistent_agent_returns_404(self) -> None:
        with patch("agentforge.server._ARTIFACTS_DIR", self.artifacts_dir):
            resp = self.client.get("/api/manifest/validate/nope")
        self.assertEqual(resp.status_code, 404)


class PackageExportTests(_ServerTestBase):
    def test_export_package_returns_zip(self) -> None:
        scan = scan_workspace(self.workspace)
        manifest = build_package_manifest(scan, workspace_name="export-test")
        output_path = str(self.export_dir / "test-package.zip")

        # Export via package_io directly to create the zip
        summary = export_package(manifest, str(self.workspace), output_path)

        # Now test via API: the API re-exports using the manifest
        resp = self.client.post(
            "/api/package/export",
            json={
                "manifest": manifest,
                "workspace_path": str(self.workspace),
                "output_filename": "api-test.zip",
                "overwrite": True,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/zip", resp.headers.get("content-type", ""))


class PackageImportTests(_ServerTestBase):
    def test_import_package_from_upload(self) -> None:
        scan = scan_workspace(self.workspace)
        manifest = build_package_manifest(scan, workspace_name="import-test")
        package_path = self.export_dir / "import-test.zip"
        export_package(manifest, str(self.workspace), str(package_path))

        with open(package_path, "rb") as f:
            resp = self.client.post(
                "/api/package/import",
                files={"file": ("import-test.zip", f, "application/zip")},
                data={"overwrite": "true"},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "imported")
        self.assertGreater(data["workspace_files"], 0)


class StaticFileTests(unittest.TestCase):
    """Test that static file serving works when frontend dir exists."""

    def test_root_returns_index_when_frontend_exists(self) -> None:
        tmpdir = Path(tempfile.mkdtemp(prefix="agentforge-static-"))
        frontend = tmpdir / "frontend"
        frontend.mkdir()
        (frontend / "index.html").write_text("<html><body>AgentForge</body></html>\n")
        try:
            app = create_app(frontend_dir=frontend)
            client = TestClient(app)
            resp = client.get("/")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("AgentForge", resp.text)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_unknown_path_falls_back_to_index(self) -> None:
        tmpdir = Path(tempfile.mkdtemp(prefix="agentforge-spa-"))
        frontend = tmpdir / "frontend"
        frontend.mkdir()
        (frontend / "index.html").write_text("<html><body>Fallback</body></html>\n")
        try:
            app = create_app(frontend_dir=frontend)
            client = TestClient(app)
            resp = client.get("/some/random/path")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Fallback", resp.text)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_subdirectory_file_served(self) -> None:
        tmpdir = Path(tempfile.mkdtemp(prefix="agentforge-subdir-"))
        frontend = tmpdir / "frontend"
        frontend.mkdir()
        pages = frontend / "pages"
        pages.mkdir()
        (pages / "about.html").write_text("<html><body>About</body></html>\n")
        (frontend / "index.html").write_text("<html><body>Index</body></html>\n")
        try:
            app = create_app(frontend_dir=frontend)
            client = TestClient(app)
            resp = client.get("/pages/about.html")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("About", resp.text)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class CLIStillWorksTests(unittest.TestCase):
    """Verify the CLI was not broken by adding server code."""

    def test_cli_import_works(self) -> None:
        from agentforge.cli import main
        self.assertTrue(callable(main))

    def test_scanner_import_works(self) -> None:
        from agentforge.scanner import scan_workspace
        self.assertTrue(callable(scan_workspace))

    def test_manifest_import_works(self) -> None:
        from agentforge.manifest import validate_manifest, build_manifest_from_scan
        self.assertTrue(callable(validate_manifest))
        self.assertTrue(callable(build_manifest_from_scan))


if __name__ == "__main__":
    unittest.main()
