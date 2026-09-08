# MEDTAS v1.6 — K01 engineering execution pass

## Why this release exists
v1.5 proved the first real K01 CAD semantic extraction from SOLIDWORKS: 13 components, 13 native documents, 30 mates, zero API warnings, and a real canonical `STATE_HASH`. v1.6 stops treating the remaining work as infrastructure and expands the engineering DAG itself.

## Fixed from the 2026-09-06 v1.5 run
- Fixed `IDimXpertDimensionTolerance.GetUpperAndLowerLimit` to use `ref` arguments required by the installed SOLIDWORKS 2026 interop.
- Fixed MBD raw-snapshot lookup: raw CAD evidence lives under `reports/cad/current`, while the canonical semantic state lives under `reports/medtas/cad/current`.
- Fixed the canonical hash qualification test so it resolves the raw snapshot from the controlled binding instead of a hard-coded wrong directory.
- Hash qualification now has two tests: deterministic repeated export, then no-change native saves. It never calls an export failure "semantic drift".

## New graph nodes
- `K01.CAD.HASH.QUAL.A001` — canonical save-invariance qualification.
- `K01.STRUCT.BOLT_EQUIV.P006` — explicit cross-solver M2.5/preload equivalence frontier.
- `K01.STRUCT.NEUTRAL.GEOMETRY.P006` — P003/P007 STEP artifacts + canonical STEP fingerprints + assembly transforms.
- `K01.STRUCT.MESH.P006` — controlled second-order tetra mesh with persistent boundary groups.
- `K01.STRUCT.CCX.INPUT.P006` — deterministic CalculiX input deck gate.

## New execution tools
- `10_BIND_STRUCTURAL_FACE_ROLES.cmd` — one-time human-confirmed binding of actual SOLIDWORKS study faces to persistent geometric signatures. No CAD geometry write.
- `11_EXPORT_STRUCTURAL_NEUTRAL_GEOMETRY.cmd` — exports P003/P007 STEP from native SOLIDWORKS and stores canonical STEP fingerprints and assembly transforms.
- `12_BUILD_STRUCTURAL_MESH.cmd` — Gmsh OpenCASCADE import, local CAD-signature-to-STEP-surface matching, assembly placement, named physical groups, and quadratic tetra mesh generation.
- `12_BUILD_BOLT_EQUIV_SCAFFOLD.cmd` — makes the three M2.5 / 300 N preload connector equivalence an explicit fail-closed engineering node.
- `13_BUILD_CALCULIX_INPUT.cmd` — controlled input-deck gate; it refuses to emit a fake equivalent model while bolt/contact/load-path equivalence is open.
- `09_BUILD_MBD_AUTHORING_CANDIDATES.cmd` — maps controlled MBD characteristic IDs to unique native SOLIDWORKS driving-dimension candidates without writing CAD.
- `09_BUILD_DRAWING_MBD_WORKPACK.cmd` — drawing definition workpack driven by MBD/DimXpert, not AutoDimension.

## Persistence rule improved
Re-running the pipeline no longer erases a verified face-role map. Confirmed face signatures survive rebuilds while every required signature still exists. If a CAD change removes a signature, the face-map verification automatically reopens.

## Hash policy remains strict
Native `SLDPRT` / `SLDASM` binary hashes are diagnostics only. Engineering freshness is controlled by canonical semantic JSON. STEP normalized hashes remove volatile header metadata but are not treated as geometric-equivalence proofs.

## CalculiX policy
The mesh target is second-order tetrahedral, C3D10-compatible. The CalculiX run remains blocked until:
1. face roles are PASS,
2. quadratic mesh is PASS,
3. M2.5 bolt/preload equivalence is PASS,
4. controlled `.inp` is generated,
5. a CalculiX executable is bound/discovered.

The intended reconciliation metrics remain maximum von Mises stress, maximum displacement and reaction/load balance. Similar-looking stress plots are not accepted as equivalence by themselves.
