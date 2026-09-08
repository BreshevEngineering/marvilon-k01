# MARVILON K01 — MEDTAS v8.3 update

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

Do not create a nested v8.3 project directory.

## First run

1. Run:

`00_MEDTAS_V8_PREFLIGHT.cmd`

2. If the result is `PASS_INFRASTRUCTURE`, start:

`control\command_center\OPEN_K01_COMMAND_CENTER_V8.cmd`

## v8.3 corrections

### Technical Filter

The entire Control Center UI is English-only.

The Technical Filter is now:
- blockers-first;
- grouped by 8 engineering domains;
- filterable by HOLD / Conditional / PASS / STALE;
- rendered as compact engineering cards;
- accompanied by lightweight J2 vector schematics.

The schematics are navigation context only. They are not design authority and do not replace native CAD or released drawings.

Controlled filter:

`control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json`

### P006 Gate04E

The previous builder called `GetPartBox` on `ModelDoc2`, which is not a SW2018 `IModelDoc2` method.

v8.3 removes `GetPartBox` completely. The builder now identifies the positive-X planar end face directly from `PartDoc` solid bodies and `Surface.PlaneParams`.

The Gate04E launcher now performs two controlled CAD stages:

1. build candidate:
`D:\Marvilon\K01\cad\candidates\gate04e_p006_service\K01-P-006_Retaining_Plug_GATE04E_SERVICE_CANDIDATE.SLDPRT`

2. create a full C2R1 + P006 verification assembly:
`D:\Marvilon\K01\cad\candidates\gate04e_p006_service\verification\K01-A-001_GATE04E_P006_SERVICE_VERIFY.SLDASM`

Stable P006 and production A001 are not direct write targets.

### Assembly maturity

A full C2R1 geometric candidate already exists and is valid for current engineering geometry review.

Gate04E adds the P006 service candidate into a copied full assembly.

A full assembly file is not equivalent to a final released production assembly. Final release additionally requires material, BOM, process, drawing, structural, FEMM and bench evidence.

### Digital Thread

The Digital Thread page is now an operational K01 lifecycle map:

Requirements → Decisions → Native CAD → Verification → BOM/TPD → FEMM/Test → Release

It also shows:
- the current engineering object;
- the next evidence;
- live tool mesh;
- SOLIDWORKS state;
- FEMM install state;
- BOM state;
- drawing state;
- GitHub remote state;
- examples of reverse change-impact propagation.

The four-layer MEDTAS platform architecture remains available as a secondary expandable section.

### BOM

BOM / Configuration remains a first-class release layer.

Authority split:
- CAD → occurrence / quantity / configuration;
- controlled product data → PartNo / Description / Material state / Make-Buy / Supplier / Lifecycle;
- MEDTAS → reconciliation and controlled projection.

### GitHub

The workstation Git remote has been verified reachable by the user's read-only check.

The ChatGPT GitHub connector is a separate authorization context and currently does not expose the private repository to this chat. This does not block local MEDTAS/Git operation.

### FEMM

Keep the v8.2 baseline:
- FEMM 4.2 64-bit stable distribution;
- native Lua command-line automation first;
- pyFEMM optional later.

FEMM screening can start from frozen C2R1 geometry after Gate04E P006 readback and current P015/B001 screening inputs are fingerprinted.

Final FEMM still requires production P015 and actual B001 supplier data.

## Current immediate action

Run from the Center:

`T03 → Build P006 service candidate`

The updated launcher now builds P006 and then creates the full Gate04E verification assembly.

Return the complete console output if either compile or runtime fails.
