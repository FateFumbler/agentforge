# MAY-99 Golden Demo Evidence Report

## Commands Executed
- `python3 -m agentforge.cli scan examples/openclaw-sample --output artifacts/MAY-99/scan.json`
- `python3 -m agentforge.cli generate-manifest --scan artifacts/MAY-99/scan.json --output artifacts/MAY-99/manifest.json`
- `python3 -m agentforge.cli validate-manifest --manifest artifacts/MAY-99/manifest.json`
- `python3 -m agentforge.cli preview --manifest artifacts/MAY-99/manifest.json --output artifacts/MAY-99/preview.json`
- `python3 -m agentforge.cli package --manifest artifacts/MAY-99/manifest.json --workspace examples/openclaw-sample --output artifacts/MAY-99/agentforge-package.zip`
- `python3 -m agentforge.cli import --artifact artifacts/MAY-99/agentforge-package.zip --output artifacts/MAY-99/imported-workspace`

## Result Summary
- Status: PASS (single clean golden pass)
- Manifest ID: a59bdb6fd48e2a3577e6ca760517a5205381a35dfa151f70b36c0234469e65c0
- Package ID: None
- Scan signature: ccbadea954b101a236bc8d81d7bd32532f1a6c0dfc0e51d2c4aaf6a87378cb47

## Artifact Checksums
- `scan.json`: `3235338aa33f6ff79b02eca98fd7f18c494855e7023c5399f09bcb76b31ee811` (3071 bytes)
- `manifest.json`: `2b2f1a05bfcf9411b5e6c3d83ca2e0bc9a94f0030903553df7fd83cfe6070537` (3051 bytes)
- `preview.json`: `33b5269a6d8d120654c5c89de98f6ab3cc9bc1d7719a29bbbbbbcb86a6484031` (764 bytes)
- `agentforge-package.zip`: `e20ada0031c8d4bd0c7daf78259db81e8a891dc79befac5ac547525e442b2734` (3009 bytes)

## Import Validation
- Output workspace: `artifacts/MAY-99/imported-workspace`
- Imported file count: 11

## Reuse in Writeup/Video
- Drop-in assets are in `/home/Fate/.openclaw/workspace/projects/agentforge/artifacts/MAY-99`
- Use checksums + imported-tree counts in slides/narration to prove reproducibility and integrity.
