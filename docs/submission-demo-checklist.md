# AgentForge Kaggle Submission Checklist

## Pre-Demo Setup
- Confirm `examples/openclaw-sample` is present.
- Use `/kaggle/working/artifacts` as the output root.
- Keep GPU usage focused on optional Gemma cells only.

## Reproducible Pipeline Cells
1. `!git clone https://github.com/FateFumbler/agentforge.git`
2. `!cd agentforge && !python3 -m pip install -U pip && !pip install -r requirements.txt`
3. `!mkdir -p /kaggle/working/artifacts`
4. `!python3 -m agentforge.cli scan examples/openclaw-sample --output /kaggle/working/artifacts/scan.json`
5. `!python3 -m agentforge.cli generate-manifest --scan /kaggle/working/artifacts/scan.json --output /kaggle/working/artifacts/manifest.json`
6. `!python3 -m agentforge.cli validate-manifest --manifest /kaggle/working/artifacts/manifest.json`
7. `!python3 -m agentforge.cli preview --manifest /kaggle/working/artifacts/manifest.json --output /kaggle/working/artifacts/preview.json`
8. `!python3 -m agentforge.cli package --manifest /kaggle/working/artifacts/manifest.json --workspace examples/openclaw-sample --output /kaggle/working/artifacts/agentforge-package.zip`
9. `!python3 -m agentforge.cli import --artifact /kaggle/working/artifacts/agentforge-package.zip --output /kaggle/working/imported-workspace`

## Acceptance Criteria
- All JSON outputs exist and parse.
- `manifest` validates.
- Package zip writes and restores successfully.
- Import pass is visible in logs with integrity results.
- Runtime remains within Kaggle notebook constraints.

## Risk and Controls
- Avoid secrets in logs or artifacts.
- Keep sample workspace under `/kaggle/working`.
- Keep non-deterministic steps explicit and bounded.
