# K01 AI Engineering Working Protocol v1

This document is a human-readable companion to `control/project/K01_AI_SESSION_RULES_CURRENT.json`.

## Resume, do not restart

Every AI session resumes from the current checkpoint, `K01_ACTIVE_STEP_GATE`, `K01_NEXT_ACTIONS_CURRENT`, and current evidence. Earlier PASS gates are not rerun unless the dependency/staleness engine shows that their inputs changed.

## Proven-first implementation

Before any SOLIDWORKS/API implementation, search the proven capability registry and inspect the exact source/evidence. A capability that is already PROVEN must be reused or adapted. A parallel executor is prohibited unless a concrete capability gap is documented first.

A freeze is complete only if it includes all transitive executable dependencies and SHA-256 hashes. For adapted reuse, preserve the proven core byte-for-byte where practical and adapt only current authority/hash/input bindings.

## Binding contract

Product characteristics may bind to composite entity sets. API routines may require one primitive. The adapter must declare and verify a deterministic selector. Example: P007 C05 is a composite flange binding, while the proven DimXpert writer receives the unique Ø33 cylindrical face.

## SOLIDWORKS write path

`preflight/compile -> timestamped candidate -> native write -> save -> close -> reopen -> semantic readback -> geometry/assembly QA -> explicit promotion`

Canonical native CAD is never the first write target.

## Acceptance

API return values are diagnostics. Proven semantic evidence is authoritative where a return-code anomaly is known. PMI-only authoring requires semantic readback, persistent-reference reopen resolution, invariant solid geometry, and unchanged canonical source.

## Center

Center is a materialized view of engineering authorities. It must not own a second dependency graph, BOM truth, release status, CAD executor or command map.

## New chat

Normal flow:

```bat
cd /d D:\BreshevEngineering\marvilon-k01
run.cmd handoff
```

Upload:

`D:\BreshevEngineering\marvilon-k01\reports\control\K01_AI_HANDOFF_CURRENT.zip`

Nothing else is normally needed.

Upload the specific current `.SLDPRT`, `.SLDASM` or `.SLDDRW` separately only if the next task requires direct native-CAD inspection/modification because native SOLIDWORKS binaries are intentionally excluded from the handoff ZIP.

`RUN_FREEZE_PROVEN_API.cmd` is not a per-chat command. Run it after a capability becomes newly PROVEN or its proven source/dependency set changes, then rebuild the handoff.
