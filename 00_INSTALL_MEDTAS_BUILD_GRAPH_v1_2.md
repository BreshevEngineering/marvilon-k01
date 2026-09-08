# K01 MEDTAS repository overlay v1.2

## Install
Extract this archive **directly over the repository root**:

`D:\BreshevEngineering\marvilon-k01\`

Allow overwrite of the v1.1 MEDTAS files. Do not create an additional `K01_MEDTAS...` subfolder.

## Run
Keep SolidWorks running, then execute:

`03_RUN_MEDTAS_PIPELINE.cmd`

The window now **always pauses** on PASS or HOLD. Failures are persisted instead of disappearing with the console.

## Persistent diagnostics
- `reports\medtas\logs\current\K01_MEDTAS_PIPELINE.log`
- `reports\medtas\logs\current\K01_CAD_SEM_A001_EXPORT.log`
- `reports\control\K01_MEDTAS_LAST_FAILURE.json`
- `reports\control\K01_MEDTAS_CENTER_CURRENT.html`
- `reports\control\K01_MEDTAS_CENTER_FEED_CURRENT.json`

Even if SolidWorks API extraction fails, the state feed and failure JSON are regenerated.

## What v1.2 builds after CAD semantic PASS
1. `K01.CAD.SEM.A001` from the real SolidWorks assembly.
2. `K01.SNAPSHOT.A001` canonical engineering snapshot.
3. `K01.TOL.A001` controlled tolerance screen; missing tolerances remain explicit limitations.
4. `K01.STRUCT.MODEL.P006` solver-neutral structural model and face inventory candidates.
5. `K01.STRUCT.SWSIM.P006` binding to the existing verified SolidWorks Simulation source report.
6. `K01.FEMM.*` binding to current FEMM evidence and formal limitations.
7. `K01.DRAWING.MODEL.GATE04E` drawing-intent model.
8. `K01.BOM.MODEL.A001` canonical BOM projection from live CAD component identities/materials.
9. `K01.VERIFY.GATE04E` current engineering-screen decision.
10. CalculiX preflight; actual CCX run stays open until topology-stable face roles and neutral mesh are bound.

## Important
`STATE_HASH` and `ARTIFACT_HASH` are separate. Derived JSON/HTML files are materialized views, not manual sources of truth.
