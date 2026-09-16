# MARVILON Drawing Control Plane v1

## Purpose

Provide one stable, controllable navigation layer over timestamped drawing candidates while preserving every build as evidence.

## Canonical hierarchy

1. `control/drawings/K01_DRAWING_SYSTEM_CURRENT.json` — drawing-system implementation/status pointer.
2. `control/drawings/K01_DRAWING_REGISTRY_CURRENT.json` — drawing identity, part identity, trace and runner registry.
3. `reports/control/K01_DRAWING_CONTROL_CURRENT.json` — generated runtime projection for Center/new-chat resume.
4. `D:\Marvilon\K01\cad\drawings\current\<drawing_id>\` — stable human/Center working projection.
5. `D:\Marvilon\K01\cad\drawings\candidates\<drawing_id>\drawing_system_v1_<timestamp>\` — immutable build/evidence history.

Routine work must not navigate timestamp folders to decide what is current.

## Trace rule

A drawing is a projection. It must link to native SLDPRT/SLDASM, drawing spec/intent, product registry/BOM, requirements/product definition, tolerance/interface evidence and the candidate manifest. The PDF is derivative only.

## Current publication

`RUN_K01_DRAWING_CONTROL_REFRESH_V1.cmd` scans the registry and candidate manifests, selects the latest controlled candidate, prefers a manual-finish artifact when present, and publishes stable copies plus `CURRENT.json` under `cad\drawings\current\<drawing_id>`.

No candidate is deleted automatically.

## Retention

`RUN_K01_DRAWING_CANDIDATES_AUDIT_V1.cmd` reports candidate counts without moving/deleting anything. Archive/delete requires explicit user approval and follows `K01_DRAWING_CANDIDATE_RETENTION_POLICY_CURRENT.json`.

## Center

Center consumes both the canonical Drawing System pointer and the generated Drawing Control projection. It must distinguish drawing semantic/build status from product/release status.
