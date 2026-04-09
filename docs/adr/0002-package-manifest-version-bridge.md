# ADR-0002: Preserve CLI manifest compatibility across schema versions

## Status
Accepted

## Context
The repo has two manifest shapes in use: public generation output (`1.0.0`) and validated package artifact payload (`2.1.0`). CLI users and docs were still moving between both, creating a brittle path mismatch.

## Decision
1. Keep public `generate-manifest` output on schema `1.0.0`.
2. Keep package artifact schema at `2.1.0` for strict import/export integrity checks.
3. Make package IO layer accept `1.0.0` manifests and coerce them to package schema internally before validation.
4. Route CLI `package`/`import` through the validated package IO path (not the legacy shim).
5. Expose strictness controls via CLI (`--allow-extra`).

## Consequences
- Existing generated manifests remain usable by existing pipelines.
- Package artifacts remain hash-verified and strict by default.
- CLI behavior is aligned with documentation and avoids dual code paths.
