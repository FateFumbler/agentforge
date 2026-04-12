"""Static file server for the AgentForge frontend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, Response
from starlette.types import Receive, Scope, Send


def _resolve_frontend_dir() -> Path:
    """Resolve the frontend/dist directory relative to this package."""
    package_dir = Path(__file__).resolve().parent
    frontend_dir = package_dir.parent / "frontend" / "dist"
    if not frontend_dir.is_dir():
        frontend_dir = package_dir / "frontend" / "dist"
    return frontend_dir


def _guess_content_type(path: Path) -> str:
    """Return a Content-Type based on file extension."""
    ext = path.suffix.lower()
    content_types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".webp": "image/webp",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".txt": "text/plain; charset=utf-8",
        ".xml": "application/xml",
    }
    return content_types.get(ext, "application/octet-stream")


def serve_static_files(
    scope: Scope,
    receive: Receive,
    send: Send,
    *,
    frontend_dir: Path | None = None,
) -> None:
    """ASGI app that serves files from the frontend/dist directory.

    Falls back to index.html for unknown paths (SPA-style routing).
    """
    base = frontend_dir or _resolve_frontend_dir()

    if not base.is_dir():
        response = HTMLResponse(
            content="<h1>AgentForge</h1><p>Frontend not built. Run the frontend build first.</p>",
            status_code=503,
        )
        return response(scope, receive, send)

    path = scope["path"]
    if path.startswith("/"):
        path = path[1:]

    # Prevent directory traversal
    if ".." in path or path.startswith("/"):
        response = HTMLResponse(content="Not found", status_code=404)
        return response(scope, receive, send)

    file_path = base / path if path else None

    if file_path and file_path.is_file():
        response = FileResponse(str(file_path), headers={"Content-Type": _guess_content_type(file_path)})
        return response(scope, receive, send)

    # SPA fallback: serve index.html
    index = base / "index.html"
    if index.is_file():
        response = FileResponse(str(index), headers={"Content-Type": "text/html; charset=utf-8"})
        return response(scope, receive, send)

    response = HTMLResponse(content="Not found", status_code=404)
    return response(scope, receive, send)


def create_static_app(frontend_dir: Path | None = None) -> Callable:
    """Return an ASGI callable for serving frontend static files."""
    return lambda scope, receive, send: serve_static_files(
        scope, receive, send, frontend_dir=frontend_dir
    )
