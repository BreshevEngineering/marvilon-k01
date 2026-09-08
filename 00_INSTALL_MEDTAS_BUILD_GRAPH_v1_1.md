# Install K01 MEDTAS Build Graph v1.1

This archive is a **repository overlay**. Extract its contents directly into:

`D:\BreshevEngineering\marvilon-k01\`

Do not create `K01_MEDTAS_v1` as a separate project folder. The overlay intentionally places controlled definitions, tools, CAD API source, generated-report locations and Command Center feed contract into the existing repository structure.

It does not overwrite the existing Gate04 CAD executables or production CAD files.

## First run

1. Start SOLIDWORKS 2026 and leave it available.
2. From repository root run:

`03_RUN_MEDTAS_CAD_SEM_A001.cmd`

The command:
- compiles the dedicated C# SolidWorks API semantic exporter if needed;
- selects the current Gate04E verification assembly from `reports/cad/current/K01_GATE04E_P006_SERVICE_VERIFY.json` (fallback: production A001 assembly);
- extracts real assembly/component/configuration/transform/mate/feature/dimension/material semantics;
- writes a raw API snapshot;
- canonicalizes it into `K01.CAD.SEM.A001`;
- computes the real MEDTAS STATE_HASH and exact ARTIFACT_HASH;
- creates the build record;
- regenerates the current derived-state file and Command Center feed.

## Expected outputs

- `reports/cad/current/K01_A001_SEMANTIC_RAW_API_v1.json`
- `reports/medtas/cad/current/K01_CAD_SEM_A001.json`
- `reports/medtas/records/current/K01.CAD.SEM.A001.build.json`
- `reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json`
- `reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json`

Upload the last three JSON files after the first run. They are enough to verify the first real state hash and move to `K01.SNAPSHOT.A001 -> K01.TOL.A001`.
