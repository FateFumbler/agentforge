"""Manifest schema, generator, and validation for AgentForge."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from os import getenv
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MANIFEST_SCHEMA_VERSION = "1.0.0"
DEFAULT_GEMMA_MODEL = "google/gemma-2-9b-it:free"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

ENTRYPOINT_HINTS = {
    "main.py",
    "__main__.py",
    "cli.py",
    "app.py",
    "server.py",
    "index.py",
    "index.js",
    "main.js",
    "manage.py",
}

KNOWN_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".md": "markdown",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _normalize_file_entry(entry: dict[str, Any]) -> dict[str, Any]:
    path = str(entry.get("path", "")).strip()
    if not path:
        return {}

    size_bytes = entry.get("size_bytes")
    if size_bytes is None:
        size_bytes = entry.get("sizeBytes")
    try:
        size_bytes = int(size_bytes)
    except (TypeError, ValueError):
        return {}

    sha = str(entry.get("sha256", "")).strip().lower()
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        return {}

    return {
        "path": path,
        "size_bytes": size_bytes,
        "sizeBytes": size_bytes,
        "sha256": sha,
    }


def _extract_files_for_manifest(scan_data: dict[str, Any]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for category in ("markerFiles", "skillFiles", "configFiles", "docFiles", "testFiles", "otherFiles"):
        for raw_entry in _safe_list(scan_data.get("files", {}).get(category, [])):
            normalized = _normalize_file_entry(raw_entry)
            if normalized:
                files.append(normalized)
    return files


def _infer_languages(files: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for entry in files:
        path = entry.get("path", "")
        suffix = Path(path).suffix.lower()
        language = KNOWN_EXTENSIONS.get(suffix)
        if language:
            counter[language] += 1
    return [language for language, _ in counter.most_common()]


def _detect_entrypoints(files: list[dict[str, Any]]) -> list[str]:
    entrypoints: list[str] = []
    seen: set[str] = set()
    for entry in files:
        path = str(entry.get("path", ""))
        base = Path(path).name
        if base in ENTRYPOINT_HINTS and not path.startswith(".") and path not in seen:
            entrypoints.append(path)
            seen.add(path)
    return entrypoints


def _derive_markers(scan_data: dict[str, Any]) -> list[str]:
    marker_hits = scan_data.get("summary", {}).get("markerFilesDetected", {})
    return sorted(marker for marker, present in marker_hits.items() if present)


def _project_name_from_scan(scan_data: dict[str, Any], override: str | None = None) -> str:
    if override:
        return override.strip() or "workspace"
    root = scan_data.get("rootPath", "workspace")
    return Path(root).name or "workspace"


def _base_manifest_payload(scan_data: dict[str, Any], project_name: str | None, owner: str | None, tags: list[str] | None) -> dict[str, Any]:
    files = _extract_files_for_manifest(scan_data)
    markers = _derive_markers(scan_data)
    summary = scan_data.get("summary", {})
    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": _project_name_from_scan(scan_data, override=project_name),
            "owner": owner or "unknown",
            "sourceRoot": scan_data.get("rootPath", ""),
            "signature": str(scan_data.get("signature", "")),
            "markerFiles": markers,
        },
        "files": files,
        "runtimeHints": {
            "languages": _infer_languages(files),
            "entrypoints": _detect_entrypoints(files),
        },
        "fileSummary": {
            "totalFiles": int(summary.get("totalFiles", 0)),
            "markerFileCount": len(markers),
            "skillFileCount": int(summary.get("skillFileCount", 0)),
            "configFileCount": int(summary.get("configFileCount", 0)),
            "docFileCount": int(summary.get("docFileCount", 0)),
            "testFileCount": int(summary.get("testFileCount", 0)),
            "otherFileCount": int(summary.get("otherFileCount", 0)),
        },
        "tags": sorted({*(tags or []), "openclaw", "agentforge"}),
        "portablePolicy": {
            "minimizeSecrets": True,
            "allowedCategories": [
                "markerFiles",
                "skillFiles",
                "configFiles",
                "docFiles",
                "testFiles",
                "otherFiles",
            ],
        },
    }


def _strip_code_fence(payload_text: str) -> str:
    text = payload_text.strip()
    if text.startswith("```"):
        text = text.strip("`\n ")
        if text.startswith("json"):
            text = text[len("json") :].strip()
    return text.strip()


def _post_chat_prompt(prompt: str, *, model: str, api_key: str | None, timeout: float | None = None) -> str:
    key = api_key or getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not configured")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Return only a valid JSON object. No markdown."},
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        OPENROUTER_CHAT_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout or 30.0) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, ValueError) as err:
        raise RuntimeError(str(err))

    candidates = raw.get("choices")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("no model response choices")
    message = candidates[0].get("message", {})
    content = message.get("content", "")
    if not isinstance(content, str):
        raise RuntimeError("invalid model response content")
    return content.strip()


def _coerce_manifest_like_payload(payload: dict[str, Any], scan_data: dict[str, Any], project_name: str | None, owner: str | None, tags: list[str] | None) -> dict[str, Any]:
    base = _base_manifest_payload(scan_data, project_name=project_name, owner=owner, tags=tags)
    merged = {**base, **payload}

    if not isinstance(merged.get("project"), dict):
        merged["project"] = base["project"]
    else:
        merged["project"] = {**base["project"], **merged["project"]}

    if not isinstance(merged.get("runtimeHints"), dict):
        merged["runtimeHints"] = base["runtimeHints"]
    else:
        merged["runtimeHints"] = {**base["runtimeHints"], **merged["runtimeHints"]}

    if not isinstance(merged.get("fileSummary"), dict):
        merged["fileSummary"] = base["fileSummary"]
    else:
        merged["fileSummary"] = {**base["fileSummary"], **merged["fileSummary"]}

    merged["files"] = [
        normalized
        for normalized in (_normalize_file_entry(entry) for entry in _safe_list(merged.get("files")))
        if normalized
    ] or base["files"]

    merged["tags"] = merged.get("tags") if isinstance(merged.get("tags"), list) else []
    merged["tags"] = sorted({*(tags or []), *{tag for tag in merged["tags"] if isinstance(tag, str)}, "openclaw", "agentforge"})
    merged.setdefault("portablePolicy", base["portablePolicy"])
    merged["schemaVersion"] = MANIFEST_SCHEMA_VERSION

    merged["manifestId"] = sha256(json.dumps(merged, sort_keys=True).encode("utf-8")).hexdigest()
    return merged


def build_manifest_prompt(scan_data: dict[str, Any]) -> str:
    """Return a deterministic prompt for LLM manifest generation."""
    signature = str(scan_data.get("signature", "unknown"))
    root = str(scan_data.get("rootPath", "unknown"))
    summary = scan_data.get("summary", {})
    markers = [name for name, present in summary.get("markerFilesDetected", {}).items() if present]

    return "\n".join(
        [
            "Task: produce a minimal portable manifest for this workspace.",
            f"Workspace root: {root}",
            f"Workspace signature: {signature}",
            "",
            "Return ONLY JSON with this schema:",
            "{",
            '  "schemaVersion": "1.0.0",',
            '  "project": {',
            '    "name": "string",',
            '    "owner": "string",',
            '    "sourceRoot": "string",',
            '    "signature": "string",',
            '    "markerFiles": ["string"]',
            "  },",
            '  "files": [',
            "    {",
            '      "path": "string",',
            '      "sizeBytes": 0,',
            '      "sha256": "string"',
            "    }",
            "  ],",
            '  "runtimeHints": {"languages": ["string"], "entrypoints": ["string"]},',
            '  "fileSummary": {"totalFiles": 0},',
            '  "tags": ["openclaw", "agentforge"]',
            "}",
            "",
            f"Detected marker files: {', '.join(markers) or 'none'}",
            "Scan summary:",
            json.dumps(summary, sort_keys=True),
        ]
    )


def build_manifest_from_scan(
    scan_data: dict[str, Any],
    *,
    project_name: str | None = None,
    owner: str | None = None,
    tags: list[str] | None = None,
    use_llm: bool = False,
    llm_model: str = DEFAULT_GEMMA_MODEL,
    api_key: str | None = None,
    llm_timeout: float | None = None,
) -> dict[str, Any]:
    if not use_llm:
        manifest = _base_manifest_payload(scan_data, project_name=project_name, owner=owner, tags=tags)
        manifest["manifestId"] = sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()
        return manifest

    prompt = build_manifest_prompt(scan_data)
    response_text = _post_chat_prompt(prompt, model=llm_model, api_key=api_key, timeout=llm_timeout)
    raw_payload = _strip_code_fence(response_text)
    try:
        payload = json.loads(raw_payload)
        if not isinstance(payload, dict):
            raise TypeError("manifest payload is not an object")
        return _coerce_manifest_like_payload(payload, scan_data, project_name=project_name, owner=owner, tags=tags)
    except Exception:
        return _base_manifest_payload(scan_data, project_name=project_name, owner=owner, tags=tags)


def build_manifest_preview(manifest_data: dict[str, Any]) -> dict[str, Any]:
    errors = validate_manifest(manifest_data)
    project = manifest_data.get("project", {})
    hints = manifest_data.get("runtimeHints", {})
    summary = manifest_data.get("fileSummary", {})
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "project": project,
        "tags": manifest_data.get("tags", []),
        "summary": {
            "generatedAt": manifest_data.get("generatedAt"),
            "fileCount": summary.get("totalFiles", 0),
            "languages": hints.get("languages", []),
            "entrypoints": hints.get("entrypoints", []),
            "markerFiles": project.get("markerFiles", []),
        },
    }


def validate_manifest(manifest_data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not isinstance(manifest_data, dict):
        return ["manifest must be a JSON object"]

    if manifest_data.get("schemaVersion") != MANIFEST_SCHEMA_VERSION:
        errors.append(f'unsupported schemaVersion: {manifest_data.get("schemaVersion")}')

    project = manifest_data.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
    else:
        required_project_fields = {"name", "owner", "sourceRoot", "signature", "markerFiles"}
        missing = sorted(required_project_fields - set(project.keys()))
        if missing:
            errors.append(f"project missing fields: {', '.join(missing)}")

    files = manifest_data.get("files")
    if not isinstance(files, list):
        errors.append("files must be an array")
    else:
        for idx, file_entry in enumerate(files):
            if not isinstance(file_entry, dict):
                errors.append(f"files[{idx}] must be an object")
                continue
            if not file_entry.get("path"):
                errors.append(f"files[{idx}] missing path")
            if "sizeBytes" not in file_entry and "size_bytes" not in file_entry:
                errors.append(f"files[{idx}] missing size")
            if "sha256" not in file_entry:
                errors.append(f"files[{idx}] missing sha256")

    if not isinstance(manifest_data.get("runtimeHints"), dict):
        errors.append("runtimeHints must be an object")

    if not isinstance(manifest_data.get("fileSummary"), dict):
        errors.append("fileSummary must be an object")

    if not isinstance(manifest_data.get("tags"), list):
        errors.append("tags must be an array")

    return errors


def read_scan(path: str | Path) -> dict[str, Any]:
    return _read_json(path)


def read_manifest(path: str | Path) -> dict[str, Any]:
    return _read_json(path)
