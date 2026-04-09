# Kaggle Demo Notebook Path (Execution Blueprint)

Use this path for the public submission demo and overnight handoff.

## Recommended repo layout

- `agentforge/` (core package)
- `docs/` (checklists and operational notes)
- `artifacts/` (run outputs in Kaggle, not checked into git)
- `outputs/` (optional local scratch; keep small)

## One-cell notebook flow

Create a Kaggle notebook that runs the full pipeline with explicit checkpoints. Use the committed notebook:

- `docs/agentforge-kaggle-mvp.ipynb`

Core one-cell flow:

1. **Clone & enter repo**
   ```bash
   !git clone https://github.com/FateFumbler/agentforge.git
   %cd agentforge
   ```
2. **Install runtime**
   ```bash
   !python3 -m pip install -U pip
   !pip install -r requirements.txt
   ```
3. **Create output workspace**
   ```bash
   !mkdir -p /kaggle/working/artifacts
   ```
4. **Prepare sample input**
  - Use a lightweight sample workspace (repo-provided at `examples/openclaw-sample`).
  - Keep the working tree under `/kaggle/working/sample`.
5. **Run pipeline**
  ```bash
  !python3 -m agentforge.cli scan --input /kaggle/working/sample --output /kaggle/working/artifacts/scan.json
   !python3 -m agentforge.cli generate-manifest --scan /kaggle/working/artifacts/scan.json --output /kaggle/working/artifacts/manifest.json
   !python3 -m agentforge.cli preview --manifest /kaggle/working/artifacts/manifest.json --output /kaggle/working/artifacts/preview.json
   !python3 -m agentforge.cli package --manifest /kaggle/working/artifacts/manifest.json --workspace /kaggle/working/sample --output /kaggle/working/agentforge-package.zip
   ```
6. **Optional restore check**
   ```bash
   !mkdir -p /kaggle/working/imported
   !python3 -m agentforge.cli import --artifact /kaggle/working/agentforge-package.zip --output /kaggle/working/imported
   ```
7. **Capture outputs**
   - Download `agentforge-package.zip`
   - Save output JSONs and a screenshot of successful runs for writeup/video

## Resource controls

- Prefer CPU for scan + packaging.
- Keep Gemma/LLM steps constrained to GPU cells.
- Stop execution if runtime exceeds expected budget and restart at the cleanest checkpoint.
- Track total session time under 12 hours and avoid unnecessary warm starts.
- Keep generated data under `/kaggle/working` to stay within Kaggle persistence limits.

## Hard acceptance checks

- `scan.json` exists and is stable with deterministic signature.
- `manifest.json` is parseable and schema-compliant.
- `preview.json` contains non-empty summary fields for the sample workspace.
- `agentforge-package.zip` writes successfully under `/kaggle/working`.
- `import` path reconstructs expected files and outputs no fatal errors.

### Example sample ingestion

```bash
!cp -R examples/openclaw-sample /kaggle/working/sample
```
