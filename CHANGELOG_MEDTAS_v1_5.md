# K01 MEDTAS v1.5

## Stabilization boundary

v1.5 removes two infrastructure failure modes that blocked engineering progress:

1. **SolidWorks interop runtime binding** — the exact `SolidWorks.Interop.*.dll` set is copied beside the compiled C# exporters. If the early-bound adapter still fails on a machine-specific COM path, the CAD semantic export automatically falls back to **pywin32**, using the same canonical semantic model.
2. **Command Center dependency on legacy v8 upstream** — v10 is a single-process standalone local server. `/api/state`, `/api/git`, `/api/files`, `/api/medtas`, evidence navigation and handoff no longer return 503 because a second server failed to start.

## 8-stage pipeline

1. Canonical hash self-test.
2. SolidWorks adapter preparation and local runtime interop bundle.
3. Real `K01.CAD.SEM.A001` extraction + canonical `STATE_HASH`.
4. Native MBD / DimXpert extraction.
5. Canonical snapshot; tolerance; structural/FEMM; drawing/BOM semantic models. Substeps build BOM CSV + parity verification and Drawing-as-MBD release workpack.
6. Persistent structural face-map candidate.
7. CalculiX case scaffold + preflight.
8. Derived-state / stale propagation + Center feed.

## Hashing

- Native `.SLDPRT/.SLDASM` bytes are **never** semantic freshness inputs.
- Canonical JSON is the semantic hash input.
- `06_TEST_CAD_HASH_INVARIANCE.cmd` now distinguishes `BLOCKED_EXPORT` from actual semantic drift.
- STEP header normalization remains artifact-stability assurance only, not geometric-equivalence proof.

## MBD / drawing

`K01.MBD.A001` remains the preferred source of machine-readable tolerances/datums. Drawing generation is defined as a derived presentation of native CAD + MBD/DimXpert; missing PMI remains OPEN and is never invented.

## BOM

`K01.BOM.MODEL.A001` can now produce `reports/bom/current/K01_BOM_A001_CURRENT.csv` with semantic parity verification. The CSV is a derived artifact, not a second BOM truth.

## CalculiX

A solver-neutral case scaffold is now generated before preflight. `.inp` generation remains fail-closed until exact SolidWorks study face roles are bound to persistent geometric face signatures and a controlled neutral mesh exists.
