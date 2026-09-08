# MARVILON K01 — MEDTAS v8.1 hotfix + digital-thread update

## Install

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

and allow replacement of the v8 control files.

This update does **not** replace native CAD, current solver evidence, event history or Git index.

## Why v8.1

v8 contained a PowerShell parser error in `control\state\K01_STATE_ENGINE_v8.ps1`: a helper function call was placed directly after `-and`. v8.1 rewrites the state reducer so all evidence predicates are calculated explicitly before boolean expressions.

The preflight now parses the state reducer and Center server with the native PowerShell parser before the Center is allowed to run. This exact class of error therefore becomes a preflight HOLD rather than a browser/API failure.

## First run

1. Close the old Center window.
2. Extract v8.1 over the repository.
3. Run:

`00_MEDTAS_V8_PREFLIGHT.cmd`

4. Require `PASS_INFRASTRUCTURE`.
5. Start:

`control\command_center\OPEN_K01_COMMAND_CENTER_V8.cmd`

## Current engineering route

C2R1 geometry stays frozen.

- T03: build/read back native P006 two-pin service-drive candidate.
- T04: close J2 local temperature/media + exact FKM/FFKM compound + compression/leak evidence.
- T05: close released preload/torque + local flange/contact verification.
- T06: close thermal/galling/service-cycle evidence.
- T07: final P007 Static/Buckling refresh.
- T08: BOM property projection/reconciliation.
- T09: production Drawing V3 release chain.
- T10: P015/B001 freeze → final FEMM → bench.
- T11: atomic P003/P007 promotion only after release closure.

## Technical decision filter

Controlled location:

`control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json`

Schema/linter:

`control\technical_filter\K01_TECHNICAL_FILTER_SCHEMA_v1.json`

`control\technical_filter\RUN_K01_TECHNICAL_FILTER_LINT.cmd`

The Center's **Technical Filter** tab renders the current 24 gates and v8.1 also shows the controlled file path directly.

## Bidirectional SOLIDWORKS link

v8.1 adds a first low-risk read-only bridge:

`cad_api\bridge\START_K01_SOLIDWORKS_LIVE_BRIDGE.cmd`

With SOLIDWORKS running, it writes:

`reports\cad\live\K01_SOLIDWORKS_LIVE_STATE.json`

approximately every 2 seconds. The Center's **Digital Thread** tab reads that state and shows active document, path, type, configuration, dirty/save flag, feature count and top-level assembly component count.

MEDTAS already provides the opposite direction through explicit Center actions: candidate builders, drawing generation, BOM projection, verification/interference and direct Open/Folder navigation. No background CAD write is permitted.

The next phase after K01 freeze is event-based SOLIDWORKS/PDM integration; the current bridge intentionally starts read-only so it cannot destabilize production CAD.
