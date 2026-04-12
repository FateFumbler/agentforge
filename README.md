# AgentForge

Build the project for the Gemma hackathon on Kaggle: a Paperclip-powered portable agent marketplace with Gemma-based manifest generation, marketplace skeleton, and upload/download flow for OpenClaw-style agents.

## Company
Maya AI in Paperclip

## Repo
https://github.com/FateFumbler/agentforge

## Core idea
AgentForge turns an existing OpenClaw, Hermes, or Paperclip-style workspace into a portable package:
1. scan workspace
2. extract deterministic facts
3. use Gemma 4 to generate a manifest
4. preview marketplace metadata
5. export package
6. import package into another compatible environment

## Kaggle-first constraints
We should assume Kaggle Notebooks as the main public demo and reproducibility surface.

At time of planning, Kaggle docs indicate:
- 2 x NVIDIA Tesla T4 GPUs available in a T4 x2 notebook session
- 4 CPU cores
- 29 GB RAM on T4 x2 sessions
- 20 GB auto-saved working disk in `/kaggle/working`
- up to 12 hours per CPU/GPU notebook session
- weekly GPU quota is 30 hours, sometimes higher depending on demand/resources

This means the build should optimize for:
- inference and packaging, not heavy fine-tuning
- reproducible notebooks
- short demo runs
- minimal setup from a public repo
- model use that fits in Kaggle notebook sessions

## MVP
- portable manifest schema
- deterministic workspace scanner
- Gemma 4 manifest generation
- preview metadata card or JSON summary
- export package flow
- import package flow
- Kaggle notebook demo path

## Non-goals
- full public marketplace backend
- ratings, auth, payments
- large-scale multi-tenant cloud execution
- long training jobs

## Target tracks
Primary fit:
- Main Track
- Future of Education, if positioned as portable multi-tool educational agents
- Digital Equity & Inclusivity, if positioned as no-config portable agents on accessible hardware
- Safety & Trust, if positioned around transparent manifests and explainable agent packaging

## Overnight build order
1. define manifest schema
2. build scanner
3. build Gemma manifest generator
4. build package export
5. build import flow
6. build Kaggle demo notebook and instructions

## Local setup note

For local (non-Kaggle) verification, run in a virtual environment to avoid
`PEP 668` system-Python restrictions.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

Use the same `python3 -m pip` invocations as the Kaggle pipeline so behavior stays reproducible.

## Public demo deliverables
- `docs/submission-demo-checklist.md`: reproducible Kaggle setup + demo acceptance checklist.
- `docs/kaggle-demo-notebook-path.md`: concrete notebook flow for the Kaggle execution path.

## Workspace scanner (MVP)

Run a deterministic scan over an OpenClaw-style workspace:

```bash
python3 -m agentforge.cli scan /home/Fate/.openclaw/workspace/projects/agentforge --output artifacts/scan.json
```

Optional:

```bash
python3 -m agentforge.cli scan /home/Fate/.openclaw/workspace/projects/agentforge --include-hidden --output artifacts/scan.json
```

Scan output fields:

- `signature`: stable workspace hash built from sorted file paths, sizes, and checksums
- `files`: categorized paths for marker files, skills, configs, docs, tests, and other files
- `summary`: boolean marker presence for `SOUL.md`, `USER.md`, `TOOLS.md`, `MEMORY.md`, `AGENTS.md` plus counts

Package and import flow:

```bash
python3 -m agentforge.cli package --manifest artifacts/manifest.json --workspace /home/Fate/.openclaw/workspace/projects/agentforge --output artifacts/agentforge-package.zip
python3 -m agentforge.cli import artifacts/agentforge-package.zip artifacts/imported-workspace
```

`package` validates file integrity before writing, and `import` validates checksums/signatures before accepting an artifact.

## Demo story
Take a real agent workspace, scan it, let Gemma understand it, generate a portable manifest, show the preview, export it, and import it somewhere else with near-zero manual setup.

## Current CLI contract

```bash
python3 -m agentforge.cli scan /path/to/workspace --output artifacts/scan.json
python3 -m agentforge.cli generate-manifest --scan artifacts/scan.json --output artifacts/manifest.json
python3 -m agentforge.cli validate-manifest --manifest artifacts/manifest.json
python3 -m agentforge.cli preview --manifest artifacts/manifest.json --output artifacts/preview.json
python3 -m agentforge.cli package --manifest artifacts/manifest.json --output artifacts/agentforge-package.zip
python3 -m agentforge.cli import --artifact artifacts/agentforge-package.zip --output /tmp/imported-workspace
```

Backward-compatible legacy scan shorthand remains available:

```bash
python3 -m agentforge.cli /path/to/workspace --output artifacts/scan.json
```

## Manifest output fields

- `project`: sourceRoot, name, owner, signature, detected marker files
- `runtimeHints`: detected language list and likely entrypoints
- `files`: flattened file inventory with size and sha256 per file
- `fileSummary`: per-category file counts and total
- `tags`: manifest tags
- `portablePolicy`: export policy metadata

## Gemma-backed manifest generation (optional)

`generate-manifest` defaults to deterministic extraction.
When you want LLM enrichment, set `OPENROUTER_API_KEY` and pass `--prefer-gemma`:

```bash
export OPENROUTER_API_KEY=...
python3 -m agentforge.cli generate-manifest --scan artifacts/scan.json --output artifacts/manifest.json --prefer-gemma
```

Useful flags:
- `--gemma-model` override model
- `--gemma-timeout` request timeout seconds
- `--gemma-api-key` explicit key override
