# K01 MEDTAS repository overlay v1.3

Primary commands:

- `OPEN_K01_COMMAND_CENTER_V9.cmd` — persistent local Center.
- `03_RUN_MEDTAS_PIPELINE.cmd` — CAD semantic extraction and downstream graph build.
- `04_REBUILD_MEDTAS_CENTER.cmd` — recompute derived graph/materialized evidence without changing CAD.
- `05_CALCULIX_PREFLIGHT.cmd` — check independent solver prerequisites.

The existing v8 Command Center remains the product/release-control frontend and API backend. v9 extends it rather than replacing its state, requirements, BOM, Git, file navigation, or action model. MEDTAS Build Graph is an additional computed layer.
