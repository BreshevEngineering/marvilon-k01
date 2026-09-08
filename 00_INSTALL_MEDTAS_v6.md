# INSTALL / UPDATE TO K01 MEDTAS v6

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

Do not create a nested v6 project directory.

Launch:

`control\command_center\OPEN_K01_COMMAND_CENTER_V6.cmd`

## Why v6 exists

v5 could fail during `/api/files` because pattern-only artifacts that did not yet
exist resolved to an empty string, and the PowerShell server passed that empty
value into `Test-Path`. The browser then received a plain-text PowerShell error
(`Cannot bind argument ...`) while expecting JSON.

v6 fixes this structurally:
- null/empty artifact paths are legal MISSING states;
- `Safe-Info` never calls `Test-Path` on an empty value;
- every `/api/*` exception returns JSON;
- frontend parses API text defensively and shows the exact endpoint/error instead
  of collapsing the whole center;
- state/files/git are loaded independently.

## Engineering change carried into v6

Gate04D-C2 is REJECTED as-built.

The stable-vs-C2 delta report proved a new P003↔P006 interference of
15.396683664956 mm³. Controlled prior geometry states:
- P006 head OD = 11.5 mm;
- P006 head axial span from P003 rear = 0...2 mm;
- C2 pilot ID = 10.917 mm;
- C2 pilot length = 1.50 mm.

Analytical overlap:
`pi/4 * (11.5^2 - 10.917^2) * 1.50 = 15.396683664956 mm³`

This equals the CAD interference to numerical precision. Therefore it is a real
pilot/head collision, not a thread false-positive.

New active candidate: Gate04D-C2R1
- flange OD33;
- 3×M2.5;
- PCD26.5;
- pilot OD14.10 g6 × 1.50;
- pilot ID revised to 12.00 mm STUDY value;
- nominal radial P006-head clearance 0.25 mm;
- pilot radial wall 1.05 mm;
- P006 remains unchanged.

## First action

Open v6 Control Center and run:

`T02 — C2R1 build + verify + interference`

or directly:

`cad_api\gates\gate04d_c2r1\00_GATE04D_C2R1_ALL.cmd`

Do not promote stable CAD even if this passes. T03...T11 remain release gates.
