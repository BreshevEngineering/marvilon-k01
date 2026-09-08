# K01 MEDTAS repository overlay v1.9

Current priority: **data -> production definition -> drawing/BOM -> acceptance**, not additional structural solver work.

Key authorities:

- requirements: `control/requirements/requirements.json`
- part metadata: `control/product/parts.json`
- stable non-part identities: `control/identity/entities.json`
- interface/analysis parameters: `control/parameters/`
- material state: `control/materials/`
- drawing characteristic policy: `control/drawings/`
- characteristic/inspection policy: `control/inspection/`
- Engineering Build Graph: `control/medtas/v1/graph/K01_engineering_build_graph_v1_9.json`

Main commands:

- `03_RUN_MEDTAS_PIPELINE.cmd` — priority-driven pipeline
- `OPEN_K01_COMMAND_CENTER_V11.cmd` — secure local Center
- `22_BUILD_AI_HANDOFF.cmd` — one ZIP for AI review

Additional release commands:

- `00_AUDIT_IDENTITY.cmd`
- `01_BUILD_REQUIREMENTS_COVERAGE.cmd`
- `02_RUN_MEDTAS_ASSURANCE_TESTS.cmd`
- `23_BUILD_EBOM_MBOM.cmd`
- `24_SYNC_PARTS_REGISTRY_TO_CAD_PROPS.cmd`
- `25_BUILD_P007_EXEMPLAR_PLAN.cmd`
- `26_VERIFY_DRAWING_QA.cmd`
- `28_BUILD_P007_EXEMPLAR_SKELETON.cmd`
- `29_BUILD_INSPECTION_CHARACTERISTICS.cmd`
- `30_INGEST_INSPECTION_RESULTS.cmd <results.csv>`
- `31_BUILD_RELEASE_PROGRAM.cmd`

CalculiX/Gmsh commands are preserved but are not on the current critical path.
