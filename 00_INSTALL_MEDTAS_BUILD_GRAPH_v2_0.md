# Install K01 MEDTAS v2.0

1. Close the old Command Center browser tab and its console/server window.
2. Extract the v2.0 overlay directly into the K01 repository root with replacement enabled.
3. Leave SolidWorks running when executing live CAD steps.
4. Run `03_RUN_MEDTAS_PIPELINE.cmd`.
5. Start `OPEN_K01_COMMAND_CENTER_V11.cmd`.
6. Run identity audit and create the migration work order. Do **not** rename files manually in Explorer.
7. Run `24_SYNC_PARTS_REGISTRY_TO_CAD_PROPS.cmd` as DRY RUN first. Review the projection before answering `Y` to apply.
8. Run `25_BUILD_P007_EXEMPLAR_PLAN.cmd`; review the live-CAD vs legacy-draft C02 conflict before authoring P007 PMI.
9. Use **Build AI Handoff ZIP** in the Center. If it fails, inspect `reports\medtas\logs\current\K01_CENTER_HANDOFF.log`; `22_BUILD_AI_HANDOFF.cmd` is the CLI fallback.

## Release priority

CalculiX/Gmsh/face-map work is deferred unless new structural evidence requires reopening it. Current critical path is stable identity -> parts/EBOM/MBOM -> P007 product definition/MBD -> P007 drawing/manufacturer review -> remaining drawing pack -> release requirements -> inspection/acceptance.

## Destructive operations

The v2.0 overlay does not automatically rename SolidWorks files, move existing engineering files, rewrite native material assignments, or invent drawing/MBD tolerances. These remain controlled engineering operations with explicit review.
