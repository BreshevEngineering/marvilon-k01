# MARVILON K01 — MEDTAS v7

## Install / update

Extract the archive directly into:

`D:\BreshevEngineering\marvilon-k01\`

Do **not** create a nested `K01_MEDTAS_v7` folder.

Launch:

`control\command_center\OPEN_K01_COMMAND_CENTER_V7.cmd`

The server is local-only at `127.0.0.1:8765` and requires no Python.

## Why v7

v7 changes the Control Center from a status viewer into an evidence-reduced engineering workflow:

- completed automated tasks are derived from actual PASS reports;
- state is recomputed from evidence every refresh;
- true state changes are appended to `control\state\K01_EVENT_LEDGER.jsonl`;
- EDS and RVM are derived current views, rather than stale copies of old spreadsheets;
- full J2 engineering rationale/calculations/history are rendered inside the Center;
- raw JSON/MD remains audit evidence, not the normal working interface;
- the supplied P003 PDF is explicitly classified as `HOLD_NOT_MANUFACTURING_DRAWING`;
- a new SOLIDWORKS Drawing V2 generator creates a quality-gated A3 manufacturing draft;
- Git changes can be classified read-only before any checkpoint;
- AI Handoff includes state, events, dossier and current evidence.

## Current carried evidence

Gate04D-C2R1:
- native build: PASS;
- assembly verify: PASS;
- active mate errors: 0;
- interference: PASS;
- new/unclassified interference pairs: 0.

BOM:
- raw metadata audit: HOLD, 26 issues;
- reconciled BOM: HOLD;
- 7 engineering release blockers;
- 13 CAD metadata projections required.

Drawing:
- current P003 PDF exists but is **not** accepted as a manufacturing drawing.

## Current engineering task

`T03 — Pilot tolerance chain + P006 service-tool envelope`

A study work package is included:
- pilot clearance proposal: P003 Ø12 H9 / P006 head Ø11.5 h9;
- radial clearance study: 0.250...0.293 mm;
- minimum pilot wall with the current Ø14.10 g6 envelope: about 1.020 mm;
- preferred service-tool architecture: hollow axial face-drive tool through the Ø12 pilot;
- final P006 face-drive feature and released service torque/assembly method remain OPEN.

## Drawings V2

Run from the Center, or directly:

`cad_api\gates\gate04d_c2r1\05_GATE04D_C2R1_DRAWINGS_V2.cmd`

The generator is written against SW2018 API signatures and has been statically audited here, but the user's local SW2018 interop/compiler is the final authority. If compilation reports an exact signature mismatch, return the compiler output; do not manually redraw the candidate.

## Git

Do not run `git add -A` on the current dirty tree.

Run the read-only classifier from the Center first:

`control\git\RUN_K01_GIT_CLASSIFY.cmd`

No Git commit, stable CAD promotion, or production release is performed by installing v7.
