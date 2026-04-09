from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agentforge.scanner import scan_workspace


class WorkspaceScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="agentforge-scan-"))
        self._write(self.workspace / "SOUL.md", "identity")
        self._write(self.workspace / "USER.md", "user")
        self._write(self.workspace / "TOOLS.md", "tools")
        self._write(self.workspace / "MEMORY.md", "memory")
        self._write(self.workspace / "AGENTS.md", "agent rules")
        self._write(self.workspace / "README.md", "# workspace")

        self._write(self.workspace / "requirements.txt", "pytest\n")
        self._write(self.workspace / "pyproject.toml", "[build-system]")
        self._write(self.workspace / ".env", "SECRET=demo\n")

        self._write(self.workspace / ".paperclip" / "skills" / "demo.py", "print('skill')\n")
        self._write(self.workspace / "skills" / "helper.ts", "export const x = 1;\n")
        self._write(self.workspace / "docs" / "notes.md", "# notes")
        self._write(self.workspace / "tests" / "test_scanner.py", "def test_dummy():\n    pass\n")
        self._write(self.workspace / "other" / "notes.txt", "ignore for this test")

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_scans_core_files_and_categories(self) -> None:
        result = scan_workspace(self.workspace)
        markers = result["summary"]["markerFilesDetected"]
        self.assertTrue(all(markers[name] for name in ("SOUL.md", "USER.md", "TOOLS.md", "MEMORY.md", "AGENTS.md")))

        files = result["files"]
        self.assertTrue(any(item["path"] == "README.md" for item in files["docFiles"]))
        self.assertTrue(any(item["path"] == ".paperclip/skills/demo.py" for item in files["skillFiles"]))
        self.assertTrue(any(item["path"] == "skills/helper.ts" for item in files["skillFiles"]))
        self.assertTrue(any(item["path"] == "requirements.txt" for item in files["configFiles"]))
        self.assertTrue(any(item["path"] == "pyproject.toml" for item in files["configFiles"]))
        self.assertTrue(any(item["path"] == ".env" for item in files["configFiles"]))
        self.assertTrue(any(item["path"] == "tests/test_scanner.py" for item in files["tests"]))
        self.assertTrue(any(item["path"] == "docs/notes.md" for item in files["docFiles"]))

        total = result["summary"]["totalFiles"]
        self.assertEqual(
            total,
            len(result["files"]["markerFiles"])
            + len(files["skillFiles"])
            + len(files["configFiles"])
            + len(files["docFiles"])
            + len(files["tests"])
            + len(files["other"]),
        )

    def test_scan_signature_is_deterministic(self) -> None:
        first = scan_workspace(self.workspace)
        second = scan_workspace(self.workspace)
        self.assertEqual(first["signature"], second["signature"])


if __name__ == "__main__":
    unittest.main()
