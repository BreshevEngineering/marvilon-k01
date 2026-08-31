# K01 Calibration Module Engineering Control

Private engineering repository for the K01 calibration mechanism.

## Purpose
This repository stores engineering logic, requirements, parameters, verification code and audit outputs.
Native SolidWorks CAD (`SLDPRT`, `SLDASM`, `SLDDRW`) is not the primary Git payload; it belongs in SolidWorks PDM when PDM is introduced.

## Authority model
1. `master/K01_master.json` — requirements, materials, lifecycle, gates.
2. `params/k01_params.py` — single editable source for controlled numeric geometry.
3. `cad_api/` — SolidWorks API automation and CAD snapshot tools.
4. `calc/` — engineering calculations.
5. `tests/` — automated consistency checks.
6. `reports/CAD_SNAPSHOT.json` — machine-readable snapshot exported from native SolidWorks.

## Branching
- `main` — controlled baseline.
- `feature/<short-name>` — design changes.
- `fix/<short-name>` — corrections.
- `release/Rxx` — release preparation only when needed.

Do not commit secrets, corporate credentials or GitHub tokens.
