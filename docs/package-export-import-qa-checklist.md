# Export / Import QA Checklist

Use this checklist before release and before demo runs.

## Pre-export checks

1. Verify scan output is deterministic:
   - run scan twice on the same workspace
   - ensure signatures match
   - compare first/last 5 file entries are identical
2. Validate manifest integrity:
   - every manifest file entry has `path`, `size_bytes`, `sha256`, `section`
   - no duplicate paths
   - `scanner.signature` equals the scan signature
3. Validate export preconditions:
   - workspace root exists and is readable
   - every manifest file exists on disk
   - every file size/hash matches scan metadata
4. Export package:
   - confirm `.zip` exists and is non-empty
   - confirm manifest is embedded as `agentforge-manifest.json`

## Import checks

1. Validate archive shape before extraction:
   - manifest file is present
   - no path traversal entries (relative `..`)
   - expected files exactly match manifest entries when strict mode is enabled
2. Validate extracted files:
   - each expected file exists
   - each file size and SHA256 match manifest
3. Fail-fast behavior:
   - if any file is missing/mismatched, import aborts with a clear error
   - if output directory is non-empty and `--overwrite` is not set, import aborts

## Repro check

```bash
python3 -m agentforge.cli scan . --output artifacts/scan.json
python3 -m agentforge.cli generate-manifest --scan artifacts/scan.json --output artifacts/manifest.json
python3 -m agentforge.cli package --manifest artifacts/manifest.json --workspace . --output artifacts/agentforge.zip
python3 -m agentforge.cli import --artifact artifacts/agentforge.zip --output artifacts/imported
python3 -m agentforge.cli import --artifact artifacts/agentforge.zip --allow-extra --overwrite --output artifacts/imported-with-extra
python3 -m unittest discover tests
```
