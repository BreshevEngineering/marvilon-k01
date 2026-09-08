# K01 MEDTAS repository overlay v1.6

Unpack **directly into the repository root** with overwrite:

`D:\BreshevEngineering\marvilon-k01\`

The archive has no wrapper directory.

## Normal use
1. Keep SOLIDWORKS running with the current K01 Gate04E verification assembly available.
2. Run `03_RUN_MEDTAS_PIPELINE.cmd`.
3. Open `OPEN_K01_COMMAND_CENTER_V10.cmd`.
4. After a successful CAD semantic stage, run `06_TEST_CAD_HASH_INVARIANCE.cmd` once as a qualification gate.
5. Run `10_BIND_STRUCTURAL_FACE_ROLES.cmd` once for the current structural study. The binding is preserved automatically across rebuilds until a required face signature disappears.
6. Run `11_EXPORT_STRUCTURAL_NEUTRAL_GEOMETRY.cmd` if neutral STEP needs rebuilding.
7. Configure Gmsh / CalculiX in `control\medtas\v1\bindings\K01_TOOLCHAIN_BINDING_v1_6.json` if they are not on PATH.
8. Run `12_BUILD_STRUCTURAL_MESH.cmd`.
9. Close `K01.STRUCT.BOLT_EQUIV.P006`; only then is `13_BUILD_CALCULIX_INPUT.cmd` allowed to progress to a real input deck.

## What is already proven before v1.6
The v1.5 live run produced:
- `K01.CAD.SEM.A001 = PASS`
- real CAD `STATE_HASH = 1d9382fe562aec43970844b31e4c5d840c870f968f519912cded65488ec1b438`
- 13 assembly component instances
- 13 unique native documents
- 30 mates
- zero CAD semantic API warnings
- `K01.SNAPSHOT.A001 = PASS`
- current SolidWorks structural evidence = PASS
- FEMM field/automation screening = PASS_WITH_LIMITATIONS
- BOM artifact parity verification = PASS
- standalone Command Center v10 API = operational

The save-invariance qualification is **not yet proven**; the v1.5 attempt was blocked by a wrong raw-snapshot locator, which v1.6 fixes.

## Product-definition direction
The target authority is native SOLIDWORKS CAD + MBD/DimXpert. The tolerance engine consumes machine-readable MBD. Drawings are derived release presentations and must not introduce new tolerances independently. AutoDimension remains prohibited.

`09_BUILD_MBD_AUTHORING_CANDIDATES.cmd` proposes exact native dimension bindings for controlled characteristic IDs; it performs no CAD write. A later controlled MBD-write transaction is allowed only after candidate ownership is verified.

## Important distinction
A pipeline `PASS_WITH_LIMITATIONS` means the orchestration ran and the Engineering Build Graph was updated. It does **not** mean Production Release PASS. Product release remains fail-closed on open engineering nodes.
