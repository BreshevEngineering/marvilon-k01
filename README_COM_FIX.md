# K01 CAD control — COM compatibility fix

The uploaded diagnostic files prove that the previous exporter was still
double-invoking late-bound COM values.

Observed:
- Assembly manifest: `GetPathName` was already a `str`, then code called it.
- P007: `GetEquationMgr` and `FirstFeature` were already returned COM objects,
  then code invoked their default dispatch and got `Member not found`.
- CustomPropertyManager `GetNames` was `None` and was called.

These are exporter defects, not CAD defects.

## Replacement

Overwrite:
- `tools/sw_review_export.py`
- `tools/k01_audit.py`
- `master/cad_contracts.json`
- `RUN_K01_FAST_AUDIT.cmd`

Add:
- `tools/sw_com.py`

## Important corrections

1. Zero-argument COM members now go through `member0()`:
   primitive -> use directly;
   returned COM object -> use directly;
   actual Python callable -> call once.

2. Subfeatures are traversed recursively using:
   `GetFirstSubFeature` then current-subfeature `GetNextSubFeature`.

3. P007 contract now compares against the actual current parameter names:
   `P007_THIN_OD_MM`
   `P007_THIN_ID_MM`

4. P007 remains 316L baseline. The uploaded draft `k01_audit.py` hard-coded
   `Inconel 625`; do not use that draft as project authority.

## First run

Open the fully resolved:
`K01-A-001_Calibration_Module.SLDASM`

Then:
`RUN_K01_FAST_AUDIT.cmd`

Expected qualitative change:
- assembly should produce many part snapshots, not zero;
- P007 should have FeatureManager entries, not zero;
- dimensions may still WARN until controlled dimensions are renamed;
- equation link may WARN until the external equation file is installed.

Do NOT enable the pre-commit hook until this run is clean enough to trust.
