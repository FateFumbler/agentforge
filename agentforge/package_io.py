"""Package manifest, export, and import helpers for AgentForge."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCAN_FILE_SECTIONS = ("markerFiles", "skillFiles", "configFiles", "docFiles", "testFiles", "otherFiles")
MANIFEST_SCHEMA_VERSION = "2.1.0"
ZIP_MANIFEST_NAME = "agentforge-manifest.json"
LEGACY_SCHEMA_VERSION = "1.0.0"
KNOWN_MANIFEST_MARKERS = ("SOUL.md", "USER.md", "TOOLS.md", "MEMORY.md", "AGENTS.md")


class PackageValidationError(ValueError):
    """Raised when a package or manifest fails validation."""


@dataclass(frozen=True)
class PackageSummary:
    file_count: int
    bytes_written: int
    package_path: str
    manifest_path: str
    source_signature: str
    output_path: str


def _sha256_bytes(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _scan_file_data(node: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise PackageValidationError("scan file entry must be an object.")
    required = {"path", "size_bytes", "sha256"}
    missing = required.difference(node)
    if missing:
        raise PackageValidationError(f"scan file entry missing keys: {', '.join(sorted(missing))}")
    path = str(node.get("path", "")).strip()
    if not path:
        raise PackageValidationError("scan file entry has empty path.")
    if path.startswith("/") or ".." in Path(path).parts:
        raise PackageValidationError(f"invalid scan file path: {path}")
    size = node.get("size_bytes")
    if not isinstance(size, int) or size < 0:
        raise PackageValidationError(f"invalid file size in scan entry: {path}")
    sha256 = str(node.get("sha256", ""))
    if len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256.lower()):
        raise PackageValidationError(f"invalid sha256 in scan entry: {path}")
    return {"path": path, "size_bytes": size, "sha256": sha256.lower()}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PackageValidationError(f"{path} did not contain a JSON object.")
    return payload


def load_scan(path: str | Path) -> dict[str, Any]:
    scan_path = Path(path).expanduser().resolve()
    if not scan_path.exists():
        raise FileNotFoundError(f"scan file not found: {scan_path}")
    if not scan_path.is_file():
        raise FileNotFoundError(f"scan path is not a file: {scan_path}")
    return _load_json(scan_path)


def _normalize_scan_sections(scan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(scan, dict):
        raise PackageValidationError("scan payload must be a JSON object.")

    files = scan.get("files")
    if not isinstance(files, dict):
        raise PackageValidationError("scan payload missing required `files` object.")

    normalized: dict[str, list[dict[str, Any]]] = {}
    for section in SCAN_FILE_SECTIONS:
        entries = files.get(section)
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            raise PackageValidationError(f"scan.files.{section} must be a list.")
        normalized[section] = []
        for entry in entries:
            normalized[section].append(_scan_file_data(entry))
    return normalized


def _validate_scan(scan: dict[str, Any]) -> dict[str, Any]:
    required = {
        "rootPath",
        "signature",
        "schemaVersion",
        "scannedAt",
        "files",
        "summary",
    }
    missing = required.difference(scan)
    if missing:
        raise PackageValidationError(f"scan payload missing keys: {', '.join(sorted(missing))}")

    signature = str(scan["signature"])
    if not signature:
        raise PackageValidationError("scan signature is empty.")
    root_path = str(scan["rootPath"]).strip()
    if not root_path:
        raise PackageValidationError("scan rootPath is empty.")

    _normalize_scan_sections(scan)
    return scan


def _iter_scan_files(scan: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    file_sections = _normalize_scan_sections(scan)
    for section in SCAN_FILE_SECTIONS:
        for entry in file_sections[section]:
            yield section, entry


def build_package_manifest(scan: dict[str, Any], *, workspace_name: str | None = None) -> dict[str, Any]:
    """Build a normalized package manifest from a scanner payload."""
    validated_scan = _validate_scan(scan)
    root_path = Path(str(validated_scan["rootPath"])).as_posix()

    files = []
    seen: set[str] = set()
    for section, entry in _iter_scan_files(validated_scan):
        path = entry["path"]
        if path in seen:
            continue
        seen.add(path)
        files.append(
            {
                "path": path,
                "size_bytes": int(entry["size_bytes"]),
                "sha256": entry["sha256"],
                "section": section,
            }
        )

    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "packageId": workspace_name or f"agentforge:{Path(root_path).name}:{validated_scan['signature'][:12]}",
        "scanner": {
            "schemaVersion": str(validated_scan["schemaVersion"]),
            "signature": str(validated_scan["signature"]),
            "scannedAt": str(validated_scan["scannedAt"]),
        },
        "source": {
            "rootPath": root_path,
            "totalFiles": int(validated_scan["summary"].get("totalFiles", len(files))),
            "markerFilesDetected": dict(validated_scan["summary"].get("markerFilesDetected", {})),
            "counts": {
                "markerFileCount": int(
                    sum(
                        1 for value in validated_scan["summary"].get("markerFilesDetected", {}).values() if value
                    )
                ),
                "skillFileCount": int(validated_scan["summary"].get("skillFileCount", 0)),
                "configFileCount": int(validated_scan["summary"].get("configFileCount", 0)),
                "docFileCount": int(validated_scan["summary"].get("docFileCount", 0)),
                "testFileCount": int(validated_scan["summary"].get("testFileCount", 0)),
                "otherFileCount": int(validated_scan["summary"].get("otherFileCount", 0)),
            },
        },
        "files": files,
    }


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise PackageValidationError("manifest payload must be a JSON object.")
    if manifest.get("schemaVersion") == LEGACY_SCHEMA_VERSION:
        return _coerce_legacy_manifest(manifest)
    if manifest.get("schemaVersion") != MANIFEST_SCHEMA_VERSION:
        raise PackageValidationError("manifest schemaVersion is unsupported.")

    if not isinstance(manifest, dict):
        raise PackageValidationError("manifest payload must be a JSON object.")
    required = {"schemaVersion", "generatedAt", "packageId", "scanner", "source", "files"}
    missing = required.difference(manifest)
    if missing:
        raise PackageValidationError(f"manifest missing keys: {', '.join(sorted(missing))}")

    files = manifest["files"]
    if not isinstance(files, list):
        raise PackageValidationError("manifest.files must be a list.")
    if not files:
        raise PackageValidationError("manifest.files is empty.")
    return manifest


def _coerce_legacy_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    project = manifest.get("project")
    if not isinstance(project, dict):
        raise PackageValidationError("legacy manifest missing project object.")

    project_name = str(project.get("name", "")).strip()
    if not project_name:
        raise PackageValidationError("legacy manifest missing project.name.")

    source_root = str(project.get("sourceRoot", "")).strip()
    if not source_root:
        raise PackageValidationError("legacy manifest missing project.sourceRoot.")

    signature = str(project.get("signature", "")).strip()
    if not signature:
        raise PackageValidationError("legacy manifest missing project.signature.")

    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raise PackageValidationError("legacy manifest `files` must be a list.")
    file_entries: list[dict[str, Any]] = []
    for raw_file in raw_files:
        if not isinstance(raw_file, dict):
            raise PackageValidationError("legacy manifest files must contain objects.")

        path = str(raw_file.get("path", "")).strip()
        if not path:
            raise PackageValidationError("legacy manifest file entry missing path.")
        if path.startswith("/") or ".." in Path(path).parts:
            raise PackageValidationError(f"legacy manifest file path invalid: {path}")

        size = raw_file.get("sizeBytes")
        try:
            size_bytes = int(size)
        except (TypeError, ValueError):
            raise PackageValidationError(f"legacy manifest file has invalid sizeBytes: {path}")

        sha = str(raw_file.get("sha256", "")).strip().lower()
        if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
            raise PackageValidationError(f"legacy manifest file has invalid sha256: {path}")

        file_entries.append(
            {
                "path": path,
                "size_bytes": size_bytes,
                "sha256": sha,
                "section": "other",
            }
        )

    detected_markers = {marker: False for marker in KNOWN_MANIFEST_MARKERS}
    for marker in project.get("markerFiles", []) if isinstance(project.get("markerFiles"), list) else []:
        marker_name = str(marker).strip()
        if marker_name in detected_markers:
            detected_markers[marker_name] = True

    file_summary = manifest.get("fileSummary", {})
    total_files = len(file_entries)
    if isinstance(file_summary, dict):
        total_files = int(file_summary.get("totalFiles", total_files))

    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "generatedAt": str(manifest.get("generatedAt", "")) or datetime.now(timezone.utc).isoformat(),
        "packageId": f"agentforge:{project_name}:{signature[:12]}",
        "scanner": {
            "schemaVersion": str(manifest.get("schemaVersion")),
            "signature": signature,
            "scannedAt": str(manifest.get("generatedAt", "")) or datetime.now(timezone.utc).isoformat(),
        },
        "source": {
            "rootPath": source_root,
            "totalFiles": int(total_files),
            "markerFilesDetected": detected_markers,
            "counts": {
                "markerFileCount": sum(1 for present in detected_markers.values() if present),
                "skillFileCount": int(file_summary.get("skillFileCount", 0)),
                "configFileCount": int(file_summary.get("configFileCount", 0)),
                "docFileCount": int(file_summary.get("docFileCount", 0)),
                "testFileCount": int(file_summary.get("testFileCount", 0)),
                "otherFileCount": int(file_summary.get("otherFileCount", 0)),
            },
        },
        "files": file_entries,
    }


def _validate_manifest_members(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    file_entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in manifest["files"]:
        normalized = _scan_file_data(entry)
        path = normalized["path"]
        if path in seen:
            raise PackageValidationError(f"duplicate file in manifest: {path}")
        seen.add(path)
        if not isinstance(entry.get("section"), str) or not str(entry.get("section")).strip():
            raise PackageValidationError(f"manifest entry missing section for: {path}")
        section = str(entry["section"]).strip()
        file_entries.append(
            {
                "path": path,
                "size_bytes": normalized["size_bytes"],
                "sha256": normalized["sha256"],
                "section": section,
            }
        )
    return file_entries


def export_package(
    manifest: dict[str, Any],
    workspace_root: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> PackageSummary:
    validated_manifest = _validate_manifest(manifest)
    entries = _validate_manifest_members(validated_manifest)
    root = Path(workspace_root).expanduser().resolve()
    if not root.exists():
        raise PackageValidationError(f"workspace root does not exist: {root}")
    if not root.is_dir():
        raise PackageValidationError(f"workspace root is not a directory: {root}")

    package_path = Path(output_path).expanduser()
    if package_path.suffix.lower() != ".zip":
        package_path = package_path.with_suffix(".zip")
    if package_path.exists() and not overwrite:
        raise PackageValidationError(f"artifact exists: {package_path}")
    if package_path.exists() and overwrite:
        package_path.unlink()

    package_root = package_path.parent
    package_root.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(ZIP_MANIFEST_NAME, json.dumps(validated_manifest, indent=2, sort_keys=True) + "\n")
        for entry in entries:
            source_file = root / entry["path"]
            if not source_file.exists():
                raise PackageValidationError(f"missing packaged file: {entry['path']}")
            if not source_file.is_file():
                raise PackageValidationError(f"packaged path is not a regular file: {entry['path']}")
            size_bytes = source_file.stat().st_size
            if size_bytes != entry["size_bytes"]:
                raise PackageValidationError(
                    f"size mismatch during export for: {entry['path']} (expected {entry['size_bytes']}, got {size_bytes})"
                )
            digest = _sha256_bytes(source_file)
            if digest != entry["sha256"]:
                raise PackageValidationError(f"checksum mismatch during export for: {entry['path']}")
            zf.write(source_file, arcname=entry["path"])
            bytes_written += size_bytes

    return PackageSummary(
        file_count=len(entries),
        bytes_written=bytes_written,
        package_path=str(package_path),
        manifest_path=ZIP_MANIFEST_NAME,
        source_signature=validated_manifest["scanner"]["signature"],
        output_path=str(root),
    )


def _validate_zip_member_path(member: str) -> None:
    parts = tuple(Path(member).parts)
    if member.startswith("/") or member.startswith("\\") or member.startswith("../"):
        raise PackageValidationError(f"invalid archive member path: {member}")
    if ".." in parts:
        raise PackageValidationError(f"invalid archive member path: {member}")
    if ":" in member.split("/", 1)[0]:
        raise PackageValidationError(f"invalid archive drive style path: {member}")


def import_package(
    package_path: str | Path,
    output_dir: str | Path,
    *,
    strict: bool = True,
    overwrite: bool = False,
) -> PackageSummary:
    package_file = Path(package_path).expanduser().resolve()
    if not package_file.exists():
        raise FileNotFoundError(f"package file not found: {package_file}")
    if not package_file.is_file():
        raise PackageValidationError(f"package path is not a file: {package_file}")

    target = Path(output_dir).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        if not overwrite:
            raise PackageValidationError(f"target directory is not empty: {target}")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(package_file, "r") as zf:
        all_members = [m for m in zf.namelist() if not m.endswith("/")]
        if ZIP_MANIFEST_NAME not in all_members:
            raise PackageValidationError(f"archive is missing required manifest: {ZIP_MANIFEST_NAME}")
        for member in all_members:
            _validate_zip_member_path(member)

        # ZIP API does not parse JSON at path; read manifest from bytes explicitly.
        raw_manifest = json.loads(zf.read(ZIP_MANIFEST_NAME).decode("utf-8"))
        _validate_manifest(raw_manifest)
        entries = _validate_manifest_members(raw_manifest)
        expected_names = {e["path"] for e in entries}
        included_members = set(all_members)
        if strict:
            extras = sorted(included_members - expected_names - {ZIP_MANIFEST_NAME})
            if extras:
                raise PackageValidationError(f"archive contains unexpected files: {', '.join(extras)}")
        missing = sorted(expected_names - included_members)
        if missing:
            raise PackageValidationError(f"archive missing expected file(s): {', '.join(missing)}")

        for entry in entries:
            target_file = target / entry["path"]
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(entry["path"], "r") as source, target_file.open("wb") as dest:
                shutil.copyfileobj(source, dest)
            if target_file.stat().st_size != entry["size_bytes"]:
                raise PackageValidationError(f"size mismatch after import for: {entry['path']}")
            if _sha256_bytes(target_file) != entry["sha256"]:
                raise PackageValidationError(f"checksum mismatch after import for: {entry['path']}")

    return PackageSummary(
        file_count=len(entries),
        bytes_written=sum(int(file["size_bytes"]) for file in entries),
        package_path=str(package_file),
        manifest_path=ZIP_MANIFEST_NAME,
        source_signature=raw_manifest["scanner"]["signature"],
        output_path=str(target),
    )
