# MARVILON K01 — MEDTAS v8 update

## Install location

Extract the ZIP **directly into**:

`D:\BreshevEngineering\marvilon-k01\`

Do not create a nested `K01_MEDTAS_v8...` directory.

This package is a controlled **update layer**. It does not replace native CAD and it does not promote stable P003/P006/P007.

## First run

1. Run the read-only preflight:

`00_MEDTAS_V8_PREFLIGHT.cmd`

2. If infrastructure preflight is PASS, start the Center:

`control\command_center\OPEN_K01_COMMAND_CENTER_V8.cmd`

3. Normal work should be performed from the Center. Use `Evidence / Files` to open current CAD/evidence/work packages rather than searching paths manually.

## v8 architecture

MEDTAS v8 separates authority by artifact class:

- native SOLIDWORKS — nominal geometry/topology/configurations;
- Drawing Intent + SLDDRW/PDF — released allowable variation, datums/GD&T, material/process/inspection requirements;
- EDR / work packages — engineering rationale and alternatives;
- solver/API/test reports — verification evidence for exact inputs;
- BOM reconciliation — identity/metadata/quantity consistency;
- state reducer — current task/gate state derived from evidence;
- event ledger — append-only state transitions;
- Git/GitHub — text/code/control history; ordinary Git is not the native-CAD vault.

No single file is the absolute source of truth for the whole project.

## Current C2R1 status

J2 geometry remains frozen unless new contrary evidence appears:

- flange OD33;
- 3×M2.5×0.45 on PCD26.5;
- P003/P007 AISI 316L / EN 1.4404;
- Ø14.10 H7/g6 locating pilot;
- P007 flange t3 within L35;
- P003 J2 zone5;
- 16×1.5 static O-ring architecture;
- C2R1 build/assembly/interference evidence already passed in the existing repository.

**Production release is still HOLD.**

## Release workflow

MEDTAS v8 drives the following evidence chain:

T03 — pilot tolerance chain + native P006 two-pin service-drive candidate  
T04 — J2 local temperature/media envelope + exact elastomer compound + compression/leak qualification  
T05 — M2.5 preload/threads + local flange/contact + torque–clamp calibration  
T06 — thermal preload + anti-galling process + repeated-service qualification  
T07 — final P007 +0.20 bar Static and -0.20 bar Buckling refresh  
T08 — controlled BOM property projection + automatic BOM/reconciliation rerun  
T09 — Drawing Assurance: intent → native V3 draft → release-semantic lint → visual PDF approval  
T10 — P015/B001 production inputs → final FEMM → bench acceptance  
T11 — atomic P003/P007 promotion only after release evidence is complete.

## Drawing Assurance

`AutoDimension` is prohibited for release drawings.

The drawing process is:

functional requirement → datum scheme → worst-case tolerance stack → Drawing Intent characteristics → native SOLIDWORKS SLDDRW/PDF → semantic lint → visual review → release.

The two project references used as primary drawing/tolerance methodology are registered in MEDTAS:

- Simmons / Maguire / Phelps, *Manual of Engineering Drawing*;
- Fischer, *Mechanical Tolerance Stackup and Analysis*.

Run from the Center or directly:

`control\drawings\RUN_K01_DRAWING_INTENT_LINT.cmd`

`cad_api\gates\gate04d_c2r1\06_GATE04D_C2R1_DRAWINGS_V3.cmd`

`control\drawings\RUN_K01_DRAWING_VISUAL_APPROVAL.cmd`

A successfully generated PDF is **not** automatically a released drawing.

## Seal strategy correction

Do not freeze a universal FFKM solution before the real J2 environment is bounded.

Current controlled strategy:

- preferred current-BOF production candidate: post-cured low-outgassing FKM, nominal 75 Shore A;
- FFKM 75A: controlled fallback when the bounded process/temperature envelope cannot be approved for FKM;
- exact compound remains OPEN until local J2 temperature, process/cleaning media, supplier compatibility/CoC, compression force and leak evidence are available.

## BOM

Run a dry run first. When the dry run produces `PASS_DRY_RUN`, MEDTAS changes the next T08 action to controlled APPLY.

The APPLY launcher:
- requires explicit `APPLY_METADATA`;
- backs up files;
- changes controlled text properties only;
- does not assign an OPEN material as native material;
- automatically reruns the C2R1 BOM pipeline after a successful projection.

## Git

Do not use `git add -A` while the current tree is unclassified.

Use:

`control\git\RUN_K01_GIT_CLASSIFY_V2.cmd`

The v2 classifier is read-only and produces a checkpoint plan. Commit only after source/control/current structured evidence have been separated from generated/local/timestamp/binary artifacts.

## Multi-user / SW2026 path

v8 remains local-first. This is deliberate while the engineering process is stabilizing.

Git/GitHub is the collaboration layer for text/code/control artifacts. Native CAD should later move to a CAD-aware PDM/vault when the stable design is migrated to SOLIDWORKS 2026 and more participants need concurrent access.
