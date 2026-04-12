# AgentForge Kaggle Submission Checklist

## Pre-Demo Setup
- Confirm `examples/openclaw-sample` is present.
- Use `/kaggle/working/artifacts` as the output root.
- Keep GPU usage focused on optional Gemma cells only.

## Reproducible Pipeline Cells
1. `!git clone https://github.com/FateFumbler/agentforge.git`
2. `!cd agentforge`
3. `!python3 -m pip install -U pip`
4. `!python3 -m pip install -r requirements.txt`
5. `!mkdir -p /kaggle/working/artifacts /kaggle/working/sample`
6. `!cp -R examples/openclaw-sample /kaggle/working/sample`
7. `!python3 -m agentforge.cli scan /kaggle/working/sample --output /kaggle/working/artifacts/scan.json`
8. `!python3 -m agentforge.cli generate-manifest --scan /kaggle/working/artifacts/scan.json --output /kaggle/working/artifacts/manifest.json`
9. `!python3 -m agentforge.cli validate-manifest --manifest /kaggle/working/artifacts/manifest.json`
10. `!python3 -m agentforge.cli preview --manifest /kaggle/working/artifacts/manifest.json --output /kaggle/working/artifacts/preview.json`
11. `!python3 -m agentforge.cli package --manifest /kaggle/working/artifacts/manifest.json --workspace /kaggle/working/sample --output /kaggle/working/artifacts/agentforge-package.zip`
12. `!python3 -m agentforge.cli import --artifact /kaggle/working/artifacts/agentforge-package.zip --output /kaggle/working/imported-workspace --overwrite`

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
