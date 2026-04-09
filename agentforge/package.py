"""Legacy compatibility shim for AgentForge package API."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .manifest import read_manifest
from .package_io import export_package as _export_package, import_package as _import_package


def _artifact_checksum(path: str | Path) -> str:
    digest = sha256()
    artifact_path = Path(path)
    with artifact_path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def export_package(
    manifest: str | dict[str, Any],
    workspace_path: str | None,
    output_path: str,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    if isinstance(manifest, (str, Path)):
        manifest_path = str(manifest)
        manifest_payload = read_manifest(manifest_path)
    else:
        manifest_payload = manifest
        manifest_path = "memory-manifest"

    if workspace_path:
        workspace = Path(workspace_path)
    else:
        workspace = Path(
            manifest_payload.get("project", {}).get("sourceRoot")
            or manifest_payload.get("source", {}).get("rootPath")
            or ""
        ).resolve()
    if not workspace.exists():
        raise FileNotFoundError(f"workspace root not resolvable from manifest: {manifest_path}")
    summary = _export_package(manifest_payload, workspace, output_path, overwrite=overwrite)
    artifact_checksum = _artifact_checksum(summary.package_path)
    return {
        "artifact": summary.package_path,
        "manifestPath": manifest_path,
        "workspaceFiles": summary.file_count,
        "artifactChecksum": artifact_checksum,
    }


def import_package(
    package_path: str,
    output_path: str,
    *,
    strict: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    summary = _import_package(package_path, output_path, strict=strict, overwrite=overwrite)
    return {
        "outputPath": summary.output_path,
        "workspaceFiles": summary.file_count,
    }
