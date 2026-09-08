# K01 MEDTAS Core Hotfix 01 + Next Engineering Step

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

This hotfix corrects two concrete defects in the first stable-core refactor:

1. `core.ps1` contained a missing closing parenthesis in `EntryValues`.
2. `PREFLIGHT.ps1` used `$checks +=` inside helper-function local scopes, so the parent check array remained empty and could incorrectly print `PASS_INFRASTRUCTURE`.

The hotfix rewrites both pieces in simple multiline PowerShell and rewrites `run_core_tests.ps1`.

## Recommended path

Run:

`01_RUN_K01_NEXT_ENGINEERING.cmd`

It deliberately bypasses the browser as a dependency and executes only the next useful engineering chain:

1. stable-core preflight;
2. Gate04E P006 candidate + full C2R1/P006 verification assembly;
3. FEMM solver fingerprint.

If Gate04E passes, the immediate design work moves to:
- release differential-pressure requirement;
- T04 seal/media;
- T05 clamp/contact;
- T06 thermal/galling/service;
- T07 final P007 structural refresh;
- FEMM screening in parallel.

## FEMM

The user has stated that FEMM is already installed. `CHECK_FEMM_INSTALL.cmd` records the installed executable path, SHA-256 and file version so future magnetic evidence can be bound to the exact solver binary.

## Reliability rule

Do not spend engineering time on Command Center appearance until Gate04E and T04/T05 have materially advanced. The UI is optional; the direct engineering launchers and controlled evidence remain authoritative.
