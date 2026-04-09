# AgentForge Launch Copy Bundle

## Board One-Pager

### Headline
AgentForge: Deterministic Portability for AI Agent Workspaces

### Summary
AgentForge turns a messy agent workspace into a reproducible, verifiable artifact. It scans source files, produces a validated manifest, packages the workspace into a portable zip, and restores it with integrity checks.

### Problem
- Teams cannot reliably share agent workspaces with full setup state.
- Current handoff patterns are manual, hard to audit, and fragile.
- Public demos need end-to-end reproducibility without hidden setup.

### Solution
- Deterministic scan and scan signature for source-of-truth capture.
- Schema-validated manifest generation (deterministic by default).
- Human-readable preview and machine validation gates.
- Signed archive packaging and strict import verification.

### Evidence and acceptance
- `scan.json` with stable signature.
- `manifest.json` passes validation.
- `preview.json` is present and readable.
- `agentforge-package.zip` generated successfully in `/kaggle/working`.
- Import restores expected workspace and passes integrity checks.

### Why now
A practical portability layer with explicit checks enables faster agent handoff, safer sharing, and easier demo reproducibility in Kaggle-centric workflows.

## Public Demo Narrative (4-minute version)

1. Setup
- Open Kaggle notebook, install dependencies, create `/kaggle/working/artifacts`.

2. Scan
- Run: `python3 -m agentforge.cli scan examples/openclaw-sample --output /kaggle/working/artifacts/scan.json`.
- Explain deterministic signature as audit anchor.

3. Manifest
- Run: `python3 -m agentforge.cli generate-manifest --scan /kaggle/working/artifacts/scan.json --output /kaggle/working/artifacts/manifest.json`.
- Note: Gemma enrichment is optional; deterministic path is the default.

4. Verify
- Run: `python3 -m agentforge.cli validate-manifest --manifest /kaggle/working/artifacts/manifest.json`.
- Run: `python3 -m agentforge.cli preview --manifest /kaggle/working/artifacts/manifest.json --output /kaggle/working/artifacts/preview.json`.

5. Package
- Run: `python3 -m agentforge.cli package --manifest /kaggle/working/artifacts/manifest.json --workspace examples/openclaw-sample --output /kaggle/working/artifacts/agentforge-package.zip`.

6. Restore
- Run: `python3 -m agentforge.cli import --artifact /kaggle/working/artifacts/agentforge-package.zip --output /kaggle/working/imported-workspace`.

7. Close
- Confirm portability loop completed with evidence files and integrity pass.

## Launch Documentation (Audience-facing)

### Short post
AgentForge makes AI agent workspaces shareable and reproducible. Scan a workspace, validate a manifest, package it, then restore it elsewhere with integrity checks.

### Medium post
AgentForge is a lightweight portability layer for agent teams. We generate a deterministic manifest from workspace scan data, offer human-readable previews, and create integrity-checked artifacts that can be re-imported with strict validation. The result is a faster, safer way to move agents between environments.

### Long post
Our team built AgentForge to solve a simple operational issue: agent workspaces are hard to move without drift, lost context, or hidden setup assumptions. AgentForge captures workspace facts in a scan signature, converts them into a validated manifest, and packages files into a portable artifact. Every step is reproducible from public code and designed to be demonstrated end-to-end in Kaggle with clear checkpoints. This is not a black-box model workflow; it is a transparency-first portability system for practical deployment and collaboration.

## Risk statement
- No secrets or credentials in outputs.
- Deterministic fallback remains available when model-assisted paths are unavailable.
- Import is strict by default, with explicit relax mode only when needed.

## CTO alignment note
Flow and command names are aligned to the implemented CLI contract.
