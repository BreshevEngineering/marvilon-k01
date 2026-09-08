# K01 MEDTAS v1.7 changelog

## Engineering Build Graph
- Expanded graph to 35 first-class nodes.
- Added controlled J2 interface-parameter state.
- Added project-structure state/audit node.
- Added MBD authoring-plan node.
- Added face-map qualification node.
- Added drawing release-plan node.
- Preserved two-hash model: semantic `STATE_HASH` and physical `ARTIFACT_HASH`.

## Canonical CAD state
- SLDPRT/SLDASM bytes remain provenance only, never semantic state.
- Canonical hash qualification separates adapter/export failures from true semantic drift.
- STEP header normalization retained as artifact-stability fingerprint only.

## MBD / tolerance / drawings
- Native DimXpert readback remains the target product-definition authority.
- Added read-only dimension/geometry candidate discovery and controlled authoring plan.
- Drawing release is gated by MBD/product definition rather than hand-entered drawing literals.
- Added native drawing-pack generator using model views + model annotations; AutoDimension is not used.
- Added explicit artifact-hash-bound visual QA approval.

## Structural / CalculiX
- Added SOLIDWORKS Simulation selection exporter for exact study loads/fixtures.
- Face identities use semantic geometric signatures, not runtime face numbers.
- Added fail-closed ambiguity handling and no-op rebuild qualification.
- Contact remains global no-penetration body-pair semantics when that is what the SOLIDWORKS study uses.
- Added controlled neutral STEP export, quadratic C3D10-compatible Gmsh mesh path, bolt-equivalence gate, CalculiX input gate, toolchain discovery, solver runner and reconciliation path.
- CalculiX deck is not emitted until boundary-role identity, mesh and bolt/preload equivalence gates are satisfied.

## BOM
- Canonical BOM model remains separate from CSV artifact.
- Semantic parity verification remains independent from open product-data/material/supplier limitations.

## Command Center v11
- Replaced v8/v9/v10 dependency chain with one local server process.
- Removed arbitrary-path open/reveal API; registered IDs only.
- Side effects are POST-only with exact same-origin Origin + CSRF checks.
- Generic evidence opener blocks executable/script extensions.
- Removed `innerHTML` and inline `onclick` from v11 UI.
- Unified status mapping into one controlled status-model JSON; unknown status maps to MISSING.
- Removed hard-coded interface engineering values from HTML/JS.
- Dashboard uses one 15 s materialized read and ETag/304; GET does not recompute the graph.
- Added Project Structure, MBD/Tolerance, Drawings, BOM, Structural/CalculiX and Evidence views.

## Project structure
- Added canonical logical zones for control/docs/drawings/BOM/analysis/reports/tools/tests.
- Existing files are never moved automatically. Migration output is review-only until explicitly approved.
