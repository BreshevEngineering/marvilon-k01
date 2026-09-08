# MARVILON K01 — MEDTAS v8.2 update

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

Do not create a nested v8.2 project directory.

## First run

1. Run:

`00_MEDTAS_V8_PREFLIGHT.cmd`

The preflight now checks:
- required files;
- JSON validity;
- PowerShell parser syntax for the state engine/server/preflight;
- file-registry semantics;
- SOLIDWORKS interop/compiler availability.

2. If preflight is `PASS_INFRASTRUCTURE`, start:

`control\command_center\OPEN_K01_COMMAND_CENTER_V8.cmd`

## v8.2 fixes

- `/api/files` no longer indexes a missing `candidates` array for pattern-only registry entries.
- missing future artifacts remain normal `MISSING` states rather than causing HTTP 500.
- one bad file-registry entry is isolated and reported instead of crashing the whole Files API.
- HTTP 500 responses now use `Internal Server Error`, not `500 (OK)`.

## Technical Filter

The Technical Filter page is now blockers-first:
- release blockers;
- 8 engineering domains;
- status filters;
- compact gate cards with Question / Basis / Verification / Evidence / Sources / Next action.

Controlled file:

`control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json`

## Assembly status

A **full C2R1 verification assembly already exists**:

`D:\Marvilon\K01\cad\candidates\gate04d_c2r1\verification\K01-A-001_GATE04D_C2R1_VERIFY.SLDASM`

It is a full geometric candidate assembly, not the final released production assembly.

The stable production assembly remains:

`D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM`

Final A001 remains blocked until T03–T10 release evidence closes.

## FEMM

v8.2 adds:

`control\femm\CHECK_K01_FEMM_INSTALL.cmd`

Recommended K01 baseline:
- FEMM 4.2;
- 64-bit Stable Distribution 21Apr2019;
- native Lua command-line automation;
- pyFEMM is optional, not required for the first MEDTAS FEMM adapter.

Official download:
https://www.femm.info/doku/doku.php?id=Download

FEMM screening may begin from the frozen C2R1 geometry after P006 service-candidate readback/current magnetic-input fingerprinting. Final FEMM release still requires production P015 and actual B001 supplier data.

## BOM / Configuration

The Center now has a dedicated BOM / Configuration view.

Rule:
- CAD owns occurrence / quantity / configuration;
- controlled product data owns identity, material release state, make/buy and supplier data;
- MEDTAS reconciles both;
- OPEN engineering fields stay OPEN.

## Git / GitHub

v8.2 adds a read-only remote check:

`control\git\CHECK_K01_GITHUB_REMOTE.cmd`

It uses `git ls-remote` only. It does not fetch, pull, push, stage or commit.

The ChatGPT GitHub connector could not resolve `BreshevEngineering/marvilon-k01` on 2026-09-05 (404), therefore connector access is not treated as verified. Local Git/origin remains the operational source until remote access is confirmed.

## Digital Thread

Architecture v2:

`control\digital_thread\K01_MEDTAS_DIGITAL_THREAD_ARCHITECTURE_v2.json`

MEDTAS now explicitly connects:
Requirements ↔ Decisions ↔ CAD ↔ Analysis ↔ BOM ↔ Manufacturing ↔ Inspection/Test ↔ Release ↔ Git/PDM

No single artifact is the absolute source of truth for the whole project.
