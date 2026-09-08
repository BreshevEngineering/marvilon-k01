# MEDTAS v8.2 changelog

- fixed `/api/files` null-array crash caused by registry entries that use `patterns` without `candidates`;
- added defensive file-registry resolver and per-entry error isolation;
- added file-registry semantic check to preflight;
- redesigned Technical Filter for engineering readability;
- added BOM / Configuration tab;
- added Assembly / FEMM maturity tab;
- added FEMM 4.2 installation check and K01 screening/final-release plan;
- added explicit A001 assembly maturity definition;
- advanced Digital Thread architecture to v2 with BOM, solver, GitHub/PDM and feedback contracts;
- added read-only GitHub remote-health check;
- tightened T03 semantics so `CAD_PASS / SERVICE_PROCESS_OPEN` does not falsely satisfy a full release dependency;
- retained fail-closed release logic and no automatic Git/CAD promotion.
