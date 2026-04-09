# Public Demo Narrative (Kaggle)

## Core message
Demonstrate a complete portability loop: scan, manifest, validate, package, import, and verify from a public repo in one replayable flow.

## 0:00–0:20 Setup
- Open Kaggle notebook.
- State objective: reproducible portability, not model training.
- Run clone/install and create `/kaggle/working/artifacts`.

## 0:20–1:00 Scan + source of truth
- Run:
  `python3 -m agentforge.cli scan examples/openclaw-sample --output /kaggle/working/artifacts/scan.json`
- Explain that deterministic scan output and signature are the starting contract.

## 1:00–1:45 Manifest generation
- Run:
  `python3 -m agentforge.cli generate-manifest --scan /kaggle/working/artifacts/scan.json --output /kaggle/working/artifacts/manifest.json`
- Optional note: mention `--prefer-gemma` is available, but deterministic manifest is the default path.

## 1:45–2:20 Validate and preview
- Run:
  `python3 -m agentforge.cli validate-manifest --manifest /kaggle/working/artifacts/manifest.json`
  `python3 -m agentforge.cli preview --manifest /kaggle/working/artifacts/manifest.json --output /kaggle/working/artifacts/preview.json`
- Define the split: validation is machine guarantees, preview is human readability.

## 2:20–3:00 Package artifact
- Run:
  `python3 -m agentforge.cli package --manifest /kaggle/working/artifacts/manifest.json --workspace examples/openclaw-sample --output /kaggle/working/artifacts/agentforge-package.zip`
- Confirm non-zero zip and mention embedded manifest integrity payload.

## 3:00–3:40 Restore and verify
- Run:
  `python3 -m agentforge.cli import --artifact /kaggle/working/artifacts/agentforge-package.zip --output /kaggle/working/imported-workspace`
- Confirm restored file structure and import integrity.

## 3:40–4:10 Close
- Reiterate: we produced reproducible portability from public inputs with deterministic checks.
- Tie out to captured evidence list: `scan.json`, `manifest.json`, `preview.json`, package zip, import result.
