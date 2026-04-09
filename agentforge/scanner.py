"""Deterministic workspace scanner for OpenClaw-style agent workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


MARKER_FILES = ("SOUL.md", "USER.md", "TOOLS.md", "MEMORY.md", "AGENTS.md")
SKILL_DIRS = {"skills", ".paperclip/skills", ".openclaw/skills"}
DOC_DIRS = {"docs", "doc"}
TEST_DIRS = {"tests", "test", "__tests__", "spec"}
CONFIG_FILENAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "tox.ini",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}
CONFIG_EXTENSIONS = {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".env"}
ROOT_DOC_FILES = {
    "README.md",
    "README.rst",
    "CHANGELOG.md",
    "LICENSE",
    "LICENSE.md",
    "SOUL.md",
    "USER.md",
    "TOOLS.md",
    "MEMORY.md",
    "AGENTS.md",
}
IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "vendor",
}


def _sha256_bytes(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ScanFile:
    path: str
    size_bytes: int
    sha256: str


def _is_ignored_dir(dir_name: str) -> bool:
    if dir_name in {".paperclip", ".openclaw"}:
        return False
    if dir_name.startswith(".") and dir_name in {".git", ".venv", ".idea", ".vscode", ".pytest_cache"}:
        return True
    return dir_name in IGNORED_DIRS


def _classify_path(rel_posix: str) -> str:
    parts = rel_posix.split("/")
    filename = rel_posix.split("/")[-1]
    if filename in MARKER_FILES:
        return "marker"
    if rel_posix.startswith(".paperclip/skills/") or rel_posix.startswith(".openclaw/skills/"):
        return "skills"
    if any(part == "skills" for part in parts):
        return "skills"
    if any(part in parts for part in SKILL_DIRS if "/" not in part):
        # root skill directory names and direct descendants.
        return "skills"
    if filename in ROOT_DOC_FILES or any(part in DOC_DIRS for part in parts):
        return "docs"
    if filename == ".env":
        return "configs"
    if filename in CONFIG_FILENAMES or any(part in {"config", ".paperclip", ".openclaw"} for part in parts) or Path(filename).suffix in CONFIG_EXTENSIONS:
        return "configs"
    if any(part in parts for part in TEST_DIRS):
        return "tests"
    return "other"


def _scan_tree(root: Path, include_hidden: bool = False) -> List[Path]:
    file_paths: List[Path] = []
    for dir_path, dir_names, file_names in _iter_directory_tree(root):
        for filename in sorted(file_names):
            candidate = Path(dir_path) / filename
            if candidate.is_file() and not candidate.is_symlink():
                if not include_hidden and filename.startswith(".") and filename not in (".env", *MARKER_FILES):
                    continue
                file_paths.append(candidate)
    return file_paths


def _iter_directory_tree(root: Path) -> Iterable[tuple[str, List[str], List[str]]]:
    root_str = str(root)
    from os import walk

    for dir_path, dir_names, file_names in walk(root_str, topdown=True):
        dir_names[:] = sorted([d for d in dir_names if not _is_ignored_dir(d)])
        yield dir_path, dir_names, file_names


def scan_workspace(
    workspace_root: str | Path,
    include_hidden: bool = False,
) -> dict:
    root = Path(workspace_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Workspace path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Workspace path is not a directory: {root}")

    file_paths = _scan_tree(root, include_hidden=include_hidden)
    marker_hits = {marker: None for marker in MARKER_FILES}
    categories: dict[str, list[ScanFile]] = {
        "markers": [],
        "skills": [],
        "configs": [],
        "docs": [],
        "tests": [],
        "other": [],
    }

    for file_path in file_paths:
        rel = file_path.relative_to(root).as_posix()
        category = _classify_path(rel)
        digest = _sha256_bytes(file_path)
        entry = ScanFile(
            path=rel,
            size_bytes=file_path.stat().st_size,
            sha256=digest,
        )

        if category == "marker":
            marker_hits[file_path.name] = entry
            continue
        if category in {"skills", "configs", "docs", "tests", "other"}:
            categories.setdefault(category, []).append(entry)

    for marker, entry in marker_hits.items():
        if entry is not None:
            categories["markers"].append(entry)

    for key in categories:
        categories[key] = sorted(categories[key], key=lambda item: item.path)

    scan_signature = "".join(f"{item.path}:{item.size_bytes}:{item.sha256};" for item in categories["other"])
    scan_signature += "".join(f"{item.path}:{item.size_bytes}:{item.sha256};" for item in categories["docs"])
    scan_signature += "".join(f"{item.path}:{item.size_bytes}:{item.sha256};" for item in categories["configs"])
    scan_signature += "".join(f"{item.path}:{item.size_bytes}:{item.sha256};" for item in categories["tests"])
    scan_signature += "".join(f"{item.path}:{item.size_bytes}:{item.sha256};" for item in categories["skills"])
    scan_signature += "".join(f"{item.path}:{item.size_bytes}:{item.sha256};" for item in categories["markers"])
    workspace_digest = hashlib.sha256(scan_signature.encode("utf-8")).hexdigest()

    result = {
        "schemaVersion": "1.0.0",
        "rootPath": str(root),
        "scannedAt": datetime.now(timezone.utc).isoformat(),
        "signature": workspace_digest,
        "files": {
            "markerFiles": [asdict(item) for item in categories["markers"]],
            "skillFiles": [asdict(item) for item in categories["skills"]],
            "configFiles": [asdict(item) for item in categories["configs"]],
            "docFiles": [asdict(item) for item in categories["docs"]],
            "testFiles": [asdict(item) for item in categories["tests"]],
            "tests": [asdict(item) for item in categories["tests"]],
            "otherFiles": [asdict(item) for item in categories["other"]],
            "other": [asdict(item) for item in categories["other"]],
        },
        "summary": {
            "totalFiles": len(file_paths),
            "markerFilesDetected": {
                marker: marker_hits[marker] is not None for marker in MARKER_FILES
            },
            "skillFileCount": len(categories["skills"]),
            "configFileCount": len(categories["configs"]),
            "docFileCount": len(categories["docs"]),
            "testFileCount": len(categories["tests"]),
            "otherFileCount": len(categories["other"]),
        },
    }
    return result


def scan_to_file(workspace_root: str | Path, output: str | Path, *, include_hidden: bool = False) -> dict:
    result = scan_workspace(workspace_root, include_hidden=include_hidden)
    output_path = Path(output).expanduser()
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan an OpenClaw-style workspace.")
    parser.add_argument("input", help="Path to workspace root")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional JSON output path. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include dotfiles (except for known ignored internals).",
    )
    return parser


def render_scan_json(workspace_root: str | Path, output: str | None = None, *, include_hidden: bool = False) -> str:
    result = scan_workspace(workspace_root, include_hidden=include_hidden)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output is None:
        return serialized

    output_path = Path(output).expanduser()
    output_path.write_text(serialized, encoding="utf-8")
    return serialized
