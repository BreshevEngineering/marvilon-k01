# K01 MEDTAS repository overlay v2.0

Install by extracting the archive directly over the repository root, for example:

`D:\BreshevEngineering\marvilon-k01\`

Allow replacement of versioned MEDTAS files. Runtime/current engineering evidence is not shipped as a replacement source of truth.

## Current priority

1. Keep the verified mechanical design frozen unless contrary evidence appears.
2. Complete one-time stable identity migration before immutable released drawings.
3. Complete P007 as the first manufacturing drawing exemplar.
4. Close `parts.json` / EBOM / MBOM production metadata and project it one-way into SolidWorks custom properties.
5. Author required P007 PMI/MBD; drawing remains a derived manufacturing presentation.
6. Close release-critical requirements and then inspection/acceptance characteristics.
7. Keep CalculiX as deferred independent assurance.

## Main commands

- `03_RUN_MEDTAS_PIPELINE.cmd` — priority 8-stage MEDTAS pipeline.
- `OPEN_K01_COMMAND_CENTER_V11.cmd` — secure standalone local Center, server build 2.0.
- `00_AUDIT_IDENTITY.cmd` — audit actual native SolidWorks filenames.
- `00B_BUILD_IDENTITY_MIGRATION_PLAN.cmd` — produce read-only reference-safe rename work order.
- `23_BUILD_EBOM_MBOM.cmd` — compute EBOM/MBOM from CAD occurrences + `parts.json`.
- `24_SYNC_PARTS_REGISTRY_TO_CAD_PROPS.cmd` — dry-run, then optional one-way registry -> SolidWorks property projection; active A001 is not required.
- `25_BUILD_P007_EXEMPLAR_PLAN.cmd` — extract live P007 geometry, detect draft drift, build exemplar plan.
- `22_BUILD_AI_HANDOFF.cmd` — CLI fallback for the same current AI handoff ZIP exposed by the Center button.
- `02_RUN_MEDTAS_ASSURANCE_TESTS.cmd` — canonical hash, reducer, registry, Center security/action/runtime tests.

## Important P007 finding

Current live CAD resolves the J2 locator as Ø14.10 with axial length 2.00 mm. The existing legacy draft candidate contains `Ø14.10 H7 × 1.70`. v2.0 treats this as drawing-draft drift, not as a reason to silently modify CAD. Review the functional basis; absent contrary evidence, retain the current verified 2.00-mm CAD and supersede the 1.70-mm draft value.

## AI handoff button

After installing v2.0, close any old Command Center console and restart `OPEN_K01_COMMAND_CENTER_V11.cmd`. The client/server build handshake will block action buttons if an old server is still serving the page. AI handoff build failures are logged in:

`reports\medtas\logs\current\K01_CENTER_HANDOFF.log`

The CLI fallback remains:

`22_BUILD_AI_HANDOFF.cmd`

## Build graph v2.0

The active DAG is `control/medtas/v1/graph/K01_engineering_build_graph_v2_0.json`. It adds first-class nodes for the identity migration work order, the controlled P007 exemplar specification, live P007 geometry/draft reconciliation, and the current AI handoff artifact.

## Qualification result

The packaged v2.0 overlay passed static/runtime integration tests against the latest K01 AI handoff available during packaging. The active graph contains 53 nodes and 119 causal dependencies with no cycles. The current design-data replay detects five one-time stateful filename migrations and one P007 legacy drawing drift item (C02 locator length). These are engineering HOLD items, not infrastructure failures.
