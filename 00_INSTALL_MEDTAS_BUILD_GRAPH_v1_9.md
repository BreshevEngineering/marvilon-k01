# Install K01 MEDTAS v1.9

Extract the overlay directly into the repository root, e.g.:

`D:\BreshevEngineering\marvilon-k01\`

Overwrite versioned source/control files when prompted.

## Important mutable bindings

The v1.9 package does **not** overwrite runtime-selected local bindings such as the chosen SOLIDWORKS drawing template or local analysis-tool paths. If a mutable binding is absent, `03_RUN_MEDTAS_PIPELINE.cmd` creates it from a `.default.json` template.

## First run

1. Keep SOLIDWORKS running with current K01 A001 available.
2. Run `03_RUN_MEDTAS_PIPELINE.cmd`.
3. Open `OPEN_K01_COMMAND_CENTER_V11.cmd`.
4. Use the release program stages on Overview; do not run deferred CalculiX work while product-definition stages are open.

## Recommended immediate sequence

- `00_AUDIT_IDENTITY.cmd`
- `01_BUILD_REQUIREMENTS_COVERAGE.cmd`
- `02_RUN_MEDTAS_ASSURANCE_TESTS.cmd`
- `23_BUILD_EBOM_MBOM.cmd`
- `24_SYNC_PARTS_REGISTRY_TO_CAD_PROPS.cmd` (dry run first)
- `25_BUILD_P007_EXEMPLAR_PLAN.cmd`
- `28_BUILD_P007_EXEMPLAR_SKELETON.cmd` only when the P007 plan/template state permits it
- `29_BUILD_INSPECTION_CHARACTERISTICS.cmd`
- `22_BUILD_AI_HANDOFF.cmd`

No bulk CAD rename is performed by installation.
