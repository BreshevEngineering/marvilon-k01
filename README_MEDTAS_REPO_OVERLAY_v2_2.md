# K01 MEDTAS v2.2

Purpose: transition verified Gate04E geometry into a stable-name final assembly and build release data around it.

## Authority hierarchy
See `control/project/K01_AUTHORITY_MAP_v2_2.json`.

## Important safety boundary
`31B_APPLY_FINAL_ASSEMBLY_PROMOTION.cmd` performs CAD writes through SolidWorks Pack and Go. Run preflight first and keep SolidWorks open. Do not manually rename files in Explorer.

## Current project priority
Final stable CAD → technical-filter coverage → P007 PMI/drawing → computed EBOM/MBOM → release requirements → inspection → R01.
CalculiX remains deferred assurance.

## GitHub
Local Git audit is included. The ChatGPT GitHub connector exposed no repositories during this audit, so remote GitHub state could not be verified from ChatGPT. The local audit records actual configured remotes/branch/dirty state.
