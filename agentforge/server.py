"""FastAPI server powering the AgentForge marketplace webapp."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

from .manifest import (
    build_manifest_from_scan,
    validate_manifest,
)
from .package_io import (
    PackageValidationError,
    export_package,
    import_package,
)
from .scanner import scan_workspace
from .static_files import create_static_app

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts"
_FRONTEND_DIR = _PROJECT_ROOT / "frontend" / "dist"

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    """Body for POST /api/scan."""

    workspace_path: str = Field(..., description="Absolute or relative path to workspace root.")
    include_hidden: bool = Field(default=False, description="Include dotfiles.")


class ManifestGenerateRequest(BaseModel):
    """Body for POST /api/manifest/generate."""

    scan_data: dict[str, Any] = Field(..., description="Scan result JSON.")
    project_name: str | None = Field(default=None, description="Override project name.")
    owner: str | None = Field(default=None, description="Owner string.")
    tags: list[str] | None = Field(default=None, description="Optional tags.")


class ExportRequest(BaseModel):
    """Body for POST /api/package/export."""

    manifest: dict[str, Any] = Field(..., description="Manifest JSON (v1 or v2).")
    workspace_path: str | None = Field(default=None, description="Workspace root override.")
    output_filename: str = Field(default="agentforge-package.zip", description="Output zip filename.")
    overwrite: bool = Field(default=False, description="Overwrite existing package.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(frontend_dir: Path | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="AgentForge",
        version="0.1.0",
        description="AgentForge marketplace API server.",
    )

    static_dir = frontend_dir or _FRONTEND_DIR

    # ----- Health -----

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    # ----- Agent listing -----

    @app.get("/api/agents")
    async def list_agents() -> list[dict[str, Any]]:
        """List all agents by scanning the artifacts directory for manifests."""
        if not _ARTIFACTS_DIR.is_dir():
            return []

        agents: list[dict[str, Any]] = []
        for subdir in sorted(_ARTIFACTS_DIR.iterdir()):
            if not subdir.is_dir():
                continue
            manifest_path = subdir / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            agents.append({
                "name": subdir.name,
                "manifest": manifest,
            })
        return agents

    @app.get("/api/agents/{name}")
    async def get_agent(name: str) -> dict[str, Any]:
        """Return the manifest for a specific agent by name."""
        agent_dir = _ARTIFACTS_DIR / name
        if not agent_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
        manifest_path = agent_dir / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(status_code=404, detail=f"No manifest for agent: {name}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"Corrupt manifest: {exc}") from exc
        return {"name": name, "manifest": manifest}

    # ----- Scan -----

    @app.post("/api/scan")
    async def scan_workspace_api(body: ScanRequest) -> dict[str, Any]:
        """Scan a workspace directory and return the scan JSON."""
        try:
            result = scan_workspace(body.workspace_path, include_hidden=body.include_hidden)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except NotADirectoryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return result

    # ----- Manifest generation -----

    @app.post("/api/manifest/generate")
    async def generate_manifest(body: ManifestGenerateRequest) -> dict[str, Any]:
        """Generate a manifest from scan data."""
        try:
            manifest = build_manifest_from_scan(
                body.scan_data,
                project_name=body.project_name,
                owner=body.owner,
                tags=body.tags,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Manifest generation failed: {exc}") from exc
        return manifest

    # ----- Manifest validation -----

    @app.get("/api/manifest/validate/{name}")
    async def validate_manifest_api(name: str) -> dict[str, Any]:
        """Validate the manifest stored under artifacts/{name}/manifest.json."""
        agent_dir = _ARTIFACTS_DIR / name
        if not agent_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
        manifest_path = agent_dir / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(status_code=404, detail=f"No manifest for agent: {name}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"Corrupt manifest: {exc}") from exc
        errors = validate_manifest(manifest)
        return {"name": name, "valid": len(errors) == 0, "errors": errors}

    # ----- Package export -----

    @app.post("/api/package/export")
    async def export_package_api(body: ExportRequest) -> FileResponse:
        """Export a package zip from a manifest and workspace."""
        tmpdir = Path(tempfile.mkdtemp(prefix="agentforge-export-"))
        output_path = tmpdir / body.output_filename
        try:
            manifest = body.manifest
            workspace = body.workspace_path
            summary = export_package(
                manifest,
                workspace or str(Path.cwd()),
                str(output_path),
                overwrite=body.overwrite,
            )
        except PackageValidationError as exc:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        response = FileResponse(
            path=str(output_path),
            filename=body.output_filename,
            media_type="application/zip",
            background=BackgroundTask(lambda: shutil.rmtree(tmpdir, ignore_errors=True)),
        )
        return response

    # ----- Package import -----

    @app.post("/api/package/import")
    async def import_package_api(
        file: UploadFile = File(..., description="AgentForge package zip file."),
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Import a package zip file and restore workspace files."""
        tmpdir = Path(tempfile.mkdtemp(prefix="agentforge-import-"))
        try:
            upload_path = tmpdir / (file.filename or "package.zip")
            content = await file.read()
            upload_path.write_bytes(content)

            output_dir = tmpdir / "workspace"
            try:
                summary = import_package(
                    str(upload_path),
                    str(output_dir),
                    strict=True,
                    overwrite=overwrite,
                )
            except PackageValidationError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

            return {
                "status": "imported",
                "output_path": summary.output_path,
                "workspace_files": summary.file_count,
                "bytes_written": summary.bytes_written,
            }
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # ----- Static frontend (catch-all) -----

    app.mount("/", create_static_app(frontend_dir=static_dir))

    return app


# Default app instance for uvicorn / python3 -m agentforge.server
app = create_app()

# ---------------------------------------------------------------------------
# Dev server entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agentforge.server:app", host="0.0.0.0", port=8000, reload=True)
