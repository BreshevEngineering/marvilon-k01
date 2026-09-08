# MEDTAS v2.2 — final-release integration overlay

Extract directly over the K01 repository root. This overlay does **not** delete legacy files and does not automatically rename native CAD.

Primary new execution path:
1. `31_COMPILE_FINAL_ASSEMBLY_PROMOTION.cmd`
2. `31A_PREFLIGHT_FINAL_ASSEMBLY_PROMOTION.cmd`
3. review preflight
4. `31B_APPLY_FINAL_ASSEMBLY_PROMOTION.cmd` only after approval
5. `31C_VERIFY_FINAL_ASSEMBLY_PROMOTION.cmd`
6. run live CAD semantic extraction against the promoted assembly
7. `31D_VERIFY_FINAL_ASSEMBLY_SEMANTICS.cmd`
8. compare component/mate identity and critical P007 baseline
7. `36_BUILD_TECHNICAL_FILTER_MAP.cmd`
8. `39_BUILD_FINAL_BOM_V2_2.cmd`
9. drawings / PMI / QA
10. `38_BUILD_CALCULATION_EVIDENCE_INDEX.cmd`
11. `35_GIT_AUDIT.cmd`
12. `37_AUDIT_PROJECT_STRUCTURE.cmd`
13. `40_BUILD_R01_RELEASE_CANDIDATE.cmd` — fail-closed until release gates pass.
