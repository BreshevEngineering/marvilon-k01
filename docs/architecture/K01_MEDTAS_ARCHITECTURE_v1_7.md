# K01 MEDTAS architecture v1.7

## 1. Authority boundaries

- Requirements/controlled parameters/material specifications define intent.
- SOLIDWORKS native CAD owns geometry and configuration semantics.
- MBD/DimXpert is the target machine-readable authority for released tolerances/datums/PMI.
- The canonical engineering snapshot is the normalized interface between native authoring tools and derived calculations.
- Drawings and BOM exports are derived artifacts, not independent truth stores.
- Solver reports are evidence artifacts; they never override the solver-neutral engineering model.

## 2. Build graph and stale propagation

Each node records its contract, current semantic `STATE_HASH`, output `ARTIFACT_HASH`, build provenance and verification result. Downstream nodes consume upstream state, artifact, or both as explicitly declared by graph edges.

Changing an upstream semantic state changes the downstream expected state hash. A node becomes STALE without recursively writing manual status flags.

## 3. CAD semantic qualification

Native SOLIDWORKS binaries are excluded from semantic hashing. The canonical snapshot removes timestamps, machine/user names, absolute paths and other non-semantic noise and normalizes numeric representation.

Qualification rule: repeated export, including repeated save with no engineering change, must preserve the canonical payload hash and node `STATE_HASH`.

## 4. Persistent face identity

Solver boundary conditions cannot depend on runtime face indices. MEDTAS creates geometric face descriptors/signatures from part/body identity, primitive type/parameters, area, bounding box, normal and edge count. Any zero-match or multi-match condition is fail-closed.

The current SOLIDWORKS Simulation study is queried directly for fixture/load entities. A no-op rebuild qualification requires the same role-to-signature mapping after rebuild.

## 5. MBD / drawings

MBD authoring is controlled characteristic-by-characteristic. Nominal numerical equality alone is not sufficient ownership evidence. Geometry or native-dimension candidates may be proposed read-only, then explicitly reviewed.

Drawing generation imports model annotations and intentionally does not use AutoDimension. Released drawing verification additionally requires visual QA bound to the current drawing artifact-set hash.

## 6. Independent structural verification

SOLIDWORKS Simulation and CalculiX branch from one solver-neutral structural model. The CalculiX branch is gated on exact boundary-role mapping, neutral geometry, quadratic mesh and explicit equivalence of contact/bolt/preload representation. Cross-solver reconciliation therefore compares solvers rather than different physics.

## 7. Command Center

The Center is a materialized engineering view, not an authority file. Browser polling reads cached/materialized state only. All side effects require controlled server-side action/file IDs and same-origin POST authorization.
