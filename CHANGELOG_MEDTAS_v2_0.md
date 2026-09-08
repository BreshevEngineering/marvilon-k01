# K01 MEDTAS v2.0 — priority release/data-control stabilization

## Purpose
v2.0 stops expanding the assurance stack and focuses MEDTAS on the remaining release work: stable identity, authoritative registries, EBOM/MBOM, P007 product definition/drawing, inspection characteristics, and trustworthy Command Center actions. CalculiX remains deferred assurance.

## Changes

### Stable identity
- Native filename audit now reads `native_path` from the RAW SolidWorks semantic snapshot rather than the canonical semantic JSON, because filesystem paths are intentionally excluded from `STATE_HASH`.
- Only lifecycle/state tokens (`GATE`, `CANDIDATE`, `VERIFY`, `REFERENCE`, etc.) are release-blocking. Stable descriptive wording differences are notes, not automatic rename requests.
- Added read-only one-time migration work order. It never renames CAD itself.
- Current live handoff identifies five reference-safe rename operations before immutable drawing release: A001, P003, P006, P007, B001.

### Parts registry -> CAD properties
- `parts.json` remains the metadata authority.
- Property projection no longer requires A001 to be the active SolidWorks document.
- Native part paths are resolved from the current RAW CAD semantic snapshot; parts are opened silently as required.
- Dry-run remains mandatory before `--apply`.
- Geometry and native material assignment are never modified by the property projection.

### P007 first exemplar
- Added live P007 geometry authority extraction from the current canonical CAD face inventory.
- Live geometry is reconciled against controlled J2 parameters and legacy/draft drawing candidates before drawing data are used.
- Current live evidence resolves: flange OD 33.0 mm, flange thickness 3.0 mm, locator OD 14.1 mm, locator axial length 2.0 mm, 3 holes Ø2.9 on PCD 26.5, thin can OD 10.0 mm, ID 9.4 mm, OAL 35.0 mm.
- Detected controlled conflict: legacy draft C02 uses locator length 1.70 mm while current live CAD is 2.00 mm. v2.0 recommends protecting current frozen/verified CAD and superseding the 1.70-mm draft candidate unless contrary functional evidence is produced.

### Command Center reliability
- Server build 2.0 (`center_server_v12.py`) keeps the secure POST/Origin/CSRF/registered-ID model.
- Priority actions use direct Python argv instead of nested CMD launch where possible.
- AI Handoff ZIP is built in-process, protected by a lock, and logged to `reports/medtas/logs/current/K01_CENTER_HANDOFF.log`.
- Client/server build handshake prevents action use through a stale browser/server pair after an overlay update.
- Startup now runs security/static and controlled action-launch self-tests before serving the Center.

### Pipeline
- `03_RUN_MEDTAS_PIPELINE.cmd` runs `pipeline_v2_0.py`.
- P007 live-geometry/draft-drift check and parts-registry property dry-run are part of the normal priority pipeline.
- CalculiX remains in the DAG but is not a current production-release priority.

## Non-goals
- No automatic mass rename of SolidWorks files.
- No reopening of frozen mechanical geometry solely to match stale drawing text.
- No automatic MBD tolerance invention.
- No new Command Center tab.
- No CalculiX work on the current critical path.

### Build graph v2.0
- Added active `K01_engineering_build_graph_v2_0.json`.
- Added first-class nodes for the identity migration work order, controlled P007 exemplar specification, live P007 geometry/draft reconciliation, and AI handoff artifact.
- P007 exemplar planning now causally depends on live CAD geometry reconciliation, not only on static candidate text.
- Registry-to-CAD property projection node records that active A001 is not required.

### Final integration QA
- Python compileall: PASS.
- Controlled JSON parse: PASS.
- DAG validation: 53 nodes, 119 dependencies, 53/53 topological, 0 cycles.
- Status model / reducer / registry tests: PASS.
- Command Center security/static, direct action launch, runtime ETag/CSRF/registered-ID tests: PASS.
- Current AI handoff replay: 5 stateful identity migrations detected, P007 live geometry extracted, exactly one legacy-draft conflict retained (C02 locator length 1.70 vs live CAD 2.00).
