# Kaggle Submission Draft (Board-Ready)

## Title
**AgentForge: Deterministic portability for AI agent workspaces**

## One-Line Summary
AgentForge converts an AI agent workspace into a verifiable, re-importable package using a deterministic scan-to-manifest pipeline with optional Gemma enrichment.

## Problem We Solve
- Team-shared agent environments are difficult to reproduce because setup assumptions, runtime hints, and metadata are spread across files.
- Manual sharing workflows are difficult to audit and verify.
- Kaggle submissions require every step to be reproducible from public code.

## What Was Built
- Deterministic scan of workspace contents into a signed scan payload.
- Manifest generation with schema validation and optional Gemma enrichment path.
- Human + machine verification via `preview` and `validate-manifest`.
- Integrity-first packaging into `agentforge-package.zip`.
- Strict, auditable import with checksum and manifest alignment checks.

## Architecture (demo level)
`scan` → `generate-manifest` → `validate-manifest` → `preview` → `package` → `import`

## Evidence Script for Writeup
```bash
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
mkdir -p /kaggle/working/artifacts
python3 -m agentforge.cli scan examples/openclaw-sample --output /kaggle/working/artifacts/scan.json
python3 -m agentforge.cli generate-manifest --scan /kaggle/working/artifacts/scan.json --output /kaggle/working/artifacts/manifest.json
python3 -m agentforge.cli validate-manifest --manifest /kaggle/working/artifacts/manifest.json
python3 -m agentforge.cli preview --manifest /kaggle/working/artifacts/manifest.json --output /kaggle/working/artifacts/preview.json
python3 -m agentforge.cli package --manifest /kaggle/working/artifacts/manifest.json --workspace examples/openclaw-sample --output /kaggle/working/artifacts/agentforge-package.zip
python3 -m agentforge.cli import --artifact /kaggle/working/artifacts/agentforge-package.zip --output /kaggle/working/imported-workspace
```

## Success Evidence
- `scan.json` created with stable `signature`.
- `manifest.json` passes validation.
- `preview.json` is non-empty and readable.
- `/kaggle/working/artifacts/agentforge-package.zip` exists and is non-empty.
- Import report shows restored files and hash/signature checks passing.

## Resource Profile
- GPU: T4×2 where available.
- RAM: up to 29 GB on GPU sessions.
- Disk: `/kaggle/working` and Kaggle 20 GB auto-saved limit.
- Session target: keep notebook under 12h.
- Quota safety: keep Gemma inference to the minimum necessary cell.

## Risk Controls
- No secrets or session tokens in artifacts.
- Deterministic fallback path if Gemma fails.
- Strict mode import by default; explicit tolerance (`--allow-extra`) required to accept extra archive entries.

## Public-Value Statement
AgentForge is a reproducible portability layer for agent workspaces. It converts messy workspace state into inspectable structure: scan, describe, package, import, and verify.
