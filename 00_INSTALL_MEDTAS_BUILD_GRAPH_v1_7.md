# K01 MEDTAS v1.7 — installation / upgrade

## Install location
Extract this overlay **directly into the repository root**:

`D:\BreshevEngineering\marvilon-k01\`

Allow replacement of existing MEDTAS files. The archive contains repository-relative paths and no wrapper directory.

MEDTAS v1.7 does **not** move, delete, rename, stage, commit, or promote existing engineering files during installation.

## Primary entry points

- `03_RUN_MEDTAS_PIPELINE.cmd` — full 8-stage engineering build pipeline.
- `OPEN_K01_COMMAND_CENTER_V11.cmd` — secure standalone local Command Center.
- `06_TEST_CAD_HASH_INVARIANCE.cmd` — semantic hash qualification.
- `09_BUILD_MBD_AUTHORING_CANDIDATES.cmd` — read-only MBD candidate discovery.
- `09B_BUILD_MBD_AUTHORING_PLAN.cmd` — controlled MBD authoring plan.
- `10_BIND_STRUCTURAL_FACE_ROLES.cmd` — automatic binding from the actual SOLIDWORKS Simulation study.
- `10B_QUALIFY_STRUCTURAL_FACE_MAP.cmd` — no-op rebuild qualification of persistent face identities.
- `11_EXPORT_STRUCTURAL_NEUTRAL_GEOMETRY.cmd` — controlled P003/P007 STEP export.
- `12_BUILD_STRUCTURAL_MESH.cmd` — quadratic tetra mesh with named engineering groups.
- `12_BUILD_BOLT_EQUIV_SCAFFOLD.cmd` — cross-solver bolt/preload equivalence gate.
- `13_BUILD_CALCULIX_INPUT.cmd` — CalculiX deck gate; emits no deck until the model is equivalent and approved.
- `17_DISCOVER_ANALYSIS_TOOLCHAIN.cmd` — discover/bind CalculiX and Gmsh/Python-gmsh.
- `18_RUN_CALCULIX_P006.cmd` — controlled CalculiX execution.
- `20_DISCOVER_DRAWING_TEMPLATE.cmd` — drawing-template discovery/binding.
- `15_BUILD_DRAWING_RELEASE_PLAN.cmd` — MBD-backed drawing release plan.
- `16_BUILD_NATIVE_DRAWING_PACK.cmd` — native SLDDRW/PDF generation after definition gates pass.
- `21_RECORD_DRAWING_VISUAL_APPROVAL.cmd` — explicit visual drawing approval bound to the artifact-set hash.
- `14_AUDIT_PROJECT_STRUCTURE.cmd` — project-layout audit; no automatic relocation.

## Required runtime assumptions

1. SOLIDWORKS must be running for native CAD/MBD/Simulation/drawing API stages.
2. The current K01 Gate04E verification assembly must remain resolvable by the controlled CAD binding.
3. CalculiX and the Python `gmsh` module are external toolchain dependencies for the independent solver branch.
4. Released drawing generation also requires a controlled `.drwdot` template and closed MBD/product-definition characteristics.

## State/hash rule

Raw SLDPRT/SLDASM binary SHA is **not** engineering state. Semantic `STATE_HASH` is calculated only from the canonicalized machine-readable engineering snapshot. Native binary hashes are diagnostic/provenance only.

## Command Center

Use `OPEN_K01_COMMAND_CENTER_V11.cmd`.

v11 is a single-process localhost server. It has no v8/v9 proxy dependency. Side-effect operations use same-origin POST + CSRF and registered IDs; the browser never supplies arbitrary filesystem paths.
