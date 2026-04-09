# Overnight tasks

## P0
1. Manifest schema and validation contract [done]
2. Deterministic workspace scanner [done]
3. Gemma prompt builder and manifest generator [done]
4. Export package builder [done]
5. Import package flow [done]
6. Kaggle notebook runner [done]

## P1
7. Preview card or preview JSON [done]
8. Demo sample workspace [done]
9. Submission writeup outline [done]
10. Video script outline [done]

## Done criteria by morning
- repo has runnable scaffold
- scanner works on a real sample workspace
- manifest generation produces valid JSON
- export produces portable artifact
- import restores structure cleanly
- Kaggle instructions are documented
- hourly progress check-ins summarize done vs remaining

## Progress (CTO update)
- 2026-04-08: Implemented deterministic manifest schema module, scan→manifest preview, package export/import, CLI for full pipeline phases (scan, generate, validate, preview, package, import), package manifest validation hardening, and sample workspace fixture at `examples/openclaw-sample`.
- 2026-04-09: Hardened package shim checksum: `artifactChecksum` now hashes the exported artifact bytes, with regression coverage in `tests/test_package.py`.
