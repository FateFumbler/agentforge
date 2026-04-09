# ADR-0001: Manifest and import/export contract

## Status
Accepted

## Context
AgentForge needs a deterministic and lightweight contract to move a workspace from scan output to a portable package and back, without forcing heavy dependencies.

## Decision
1. Use a single manifest JSON versioned by `schemaVersion` (`1.0.0`) as the interchange object.
2. Keep manifest generation deterministic from scan output by default, with an optional LLM prompt path for future upgrades.
3. Define three stable CLI stages:
   - scan -> generate-manifest -> package/import
4. Keep file inventory flattened in manifest for portability and deterministic hashing.
5. Store export metadata inside the package archive so importer can validate assumptions.

## Consequences
- Enables reproducible end-to-end flow for Kaggle and local demos.
- Validates and previews before package creation, avoiding invalid payloads in artifact steps.
- Keeps future LLM swap-in simple: prompt template is deterministic and explicit.
