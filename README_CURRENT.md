# K01 Stage3 Control V5 — current order

1. Ignore old cleanup/repo APPLY scripts.
2. Extract this package over `D:\BreshevEngineering\marvilon-k01`.
3. Run `control\01_CANDIDATES_SWEEP_DRYRUN.cmd`.
4. If only intended leftovers are classified, close SOLIDWORKS and run
   `control\02_CANDIDATES_SWEEP_APPLY.cmd`.
5. Reopen stable K01-A-001 and run `control\03_DATUM_C_GATE04B_V3.cmd`.
6. Send console + `K01_GATE04B_DATUM_C_BUILD.json`.
7. Run `control\04_BOM_FROM_SOLIDWORKS.cmd`.
8. Run root audit; do not APPLY root cleanup until Datum C result is safe.
9. Next engineering gate after Datum C is native CAD for the removable
   P003↔P007 service joint.
