# MEDTAS v1.4 — 2026-09-06

## Fixed

- Corrected all compile errors reported by SOLIDWORKS 2026 early-bound interop:
  - `System.Environment` ambiguity;
  - material lookup moved to `IPartDoc.GetMaterialPropertyName2`;
  - explicit COM casts for Feature/DisplayDimension return values;
  - `IFace2.IGetSurface()` used for typed surface access;
  - typed `ISldWorks.IGetOpenDocumentByName2()` used for open-document lookup.
- Removed native `SLDPRT/SLDASM` SHA from semantic exporter payload.
- Fixed `OPEN_K01_COMMAND_CENTER_V9.cmd` trailing-backslash/quote root-path corruption by passing `%CD%`.
- Local server remains the primary Center UI; static HTML remains diagnostic only.

## Added

- Canonical hash core and synthetic self-test.
- Mandatory no-change save invariance test: `06_TEST_CAD_HASH_INVARIANCE.cmd`.
- STEP header-normalized artifact hash tool: `07_STEP_CANONICAL_HASH.cmd`.
- New graph node `K01.MBD.A001` for native MBD/DimXpert extraction.
- DimXpert C# exporter and orchestrator.
- Tolerance node v1.4 behavior: MBD-first source priority + explicit worst-case/Monte-Carlo framework with no guessed distributions.
- Command Center Build Graph display for MBD coverage and canonical-hash invariance.
- MBD/DimXpert and canonical-hash policies codified under `control/medtas/v1/spec`.

## Architecture correction

`ARTIFACT_HASH` is now explicitly prevented from leaking into canonical snapshot `STATE_HASH`: provenance hashes are written to a separate provenance file.
