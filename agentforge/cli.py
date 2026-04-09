"""CLI entrypoint for AgentForge utilities."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .manifest import (
    build_manifest_from_scan,
    build_manifest_prompt,
    build_manifest_preview,
    read_manifest,
    read_scan,
    validate_manifest,
)
from . import package as package_bridge
from .scanner import render_scan_json


def build_parser() -> "Any":
    import argparse

    parser = argparse.ArgumentParser(description="AgentForge CLI.")
    parser.add_argument("--version", action="store_true", help="Print tool version and exit.")

    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan a workspace and emit scan JSON.")
    scan_parser.add_argument("input", help="Path to workspace root")
    scan_parser.add_argument("--output", default=None, help="Optional JSON output path.")
    scan_parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include dotfiles (except known ignored internals).",
    )

    generate_parser = subparsers.add_parser(
        "generate-manifest",
        help="Generate a deterministic manifest from a scan JSON.",
    )
    generate_parser.add_argument("--scan", required=True, help="Path to scan JSON.")
    generate_parser.add_argument(
        "--output",
        required=True,
        help="Output manifest JSON path.",
    )
    generate_parser.add_argument("--project-name", default=None, help="Optional manifest name override.")
    generate_parser.add_argument("--owner", default=None, help="Optional owner string.")
    generate_parser.add_argument("--tag", action="append", default=[], help="Optional tags.")
    generate_parser.add_argument(
        "--prefer-gemma",
        action="store_true",
        help="Attempt Gemma-backed manifest generation before deterministic fallback.",
    )
    generate_parser.add_argument(
        "--gemma-model",
        default=None,
        help="Override Gemma model name (default: built-in Gemma model).",
    )
    generate_parser.add_argument(
        "--gemma-timeout",
        type=float,
        default=8.0,
        help="Gemma request timeout in seconds.",
    )
    generate_parser.add_argument(
        "--gemma-api-key",
        default=None,
        help="API key override for OpenRouter calls.",
    )
    generate_parser.add_argument(
        "--emit-prompt",
        action="store_true",
        help="Emit the LLM prompt instead of writing manifest.",
    )

    validate_parser = subparsers.add_parser("validate-manifest", help="Validate a manifest JSON file.")
    validate_parser.add_argument("--manifest", required=True, help="Path to manifest JSON.")

    preview_parser = subparsers.add_parser("preview", help="Render a manifest preview.")
    preview_parser.add_argument("--manifest", required=True, help="Path to manifest JSON.")
    preview_parser.add_argument("--output", default=None, help="Optional output JSON path.")

    package_parser = subparsers.add_parser("package", help="Export a manifest+files package.")
    package_parser.add_argument("--manifest", required=True, help="Path to manifest JSON.")
    package_parser.add_argument(
        "--workspace",
        "--input",
        default=None,
        help="Optional workspace root override; defaults to manifest project.sourceRoot.",
    )
    package_parser.add_argument("--output", required=True, help="Output artifact path.")
    package_parser.add_argument("--overwrite", action="store_true", help="Overwrite output artifact.")

    import_parser = subparsers.add_parser("import", help="Import a package artifact into workspace.")
    import_parser.add_argument("--artifact", required=True, help="Path to package artifact.")
    import_parser.add_argument("--output", required=True, help="Directory to restore the workspace.")
    import_parser.add_argument("--overwrite", action="store_true", help="Overwrite output path.")
    import_parser.add_argument(
        "--allow-extra",
        action="store_false",
        dest="strict",
        help="Allow extra files in package archive (default: reject extras).",
    )

    return parser


def _run_legacy_scan(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="AgentForge legacy scan mode.")
    parser.add_argument("input", help="Path to workspace root.")
    parser.add_argument("--output", default=None, help="Optional JSON output path.")
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include dotfiles (except known ignored internals).",
    )
    args = parser.parse_args(argv)
    payload = render_scan_json(args.input, args.output, include_hidden=args.include_hidden)
    if args.output is None:
        print(payload, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Backward-compatible mode: if no explicit command is provided, assume legacy scan.
    if argv and argv[0] not in {"scan", "generate-manifest", "validate-manifest", "preview", "package", "import", "--version", "-h", "--help"}:
        try:
            return _run_legacy_scan(argv)
        except Exception as err:  # pragma: no cover - CLI boundary
            print(f"scan failed: {err}", file=sys.stderr)
            return 1

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.version:
            print("agentforge-cli/0.1.0")
            return 0

        if args.command == "scan":
            output = render_scan_json(
                args.input,
                args.output,
                include_hidden=args.include_hidden,
            )
            if args.output is None:
                print(output, end="")
            return 0

        if args.command == "generate-manifest":
            scan_data = read_scan(args.scan)
            if args.emit_prompt:
                print(build_manifest_prompt(scan_data))
            else:
                manifest = build_manifest_from_scan(
                    scan_data,
                    project_name=args.project_name,
                    owner=args.owner,
                    tags=args.tag,
                    use_llm=args.prefer_gemma,
                    llm_model=args.gemma_model or "google/gemma-2-9b-it:free",
                    api_key=args.gemma_api_key,
                    llm_timeout=args.gemma_timeout,
                )
                Path(args.output).write_text(
                    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                print(f"wrote manifest to {args.output}")
            return 0

        if args.command == "validate-manifest":
            manifest = read_manifest(args.manifest)
            errors = validate_manifest(manifest)
            if errors:
                for error in errors:
                    print(error)
                return 1
            print("manifest valid")
            return 0

        if args.command == "preview":
            manifest = read_manifest(args.manifest)
            preview = build_manifest_preview(manifest)
            payload = json.dumps(preview, indent=2, sort_keys=True) + "\n"
            if args.output is None:
                print(payload, end="")
            else:
                Path(args.output).write_text(payload, encoding="utf-8")
                print(f"wrote preview to {args.output}")
            return 0 if preview.get("ok", False) else 1

        if args.command == "package":
            manifest = read_manifest(args.manifest)
            result = package_bridge.export_package(
                manifest,
                args.workspace,
                args.output,
                overwrite=args.overwrite,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "import":
            result = package_bridge.import_package(
                args.artifact,
                args.output,
                strict=args.strict,
                overwrite=args.overwrite,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        parser.print_help()
        return 0
    except Exception as err:  # pragma: no cover - CLI boundary
        print(f"agentforge-cli failed: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
