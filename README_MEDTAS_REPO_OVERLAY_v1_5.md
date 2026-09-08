# K01 MEDTAS repository overlay v1.5

Extract this archive **over the repository root**:

`D:\BreshevEngineering\marvilon-k01\`

Allow file replacement. Do not unpack it into a new nested `K01_MEDTAS...` folder.

## Normal operation

1. Start SOLIDWORKS 2026. The Gate04E verification assembly may be open; the pipeline also attempts controlled opening.
2. Run `03_RUN_MEDTAS_PIPELINE.cmd`.
3. Run `OPEN_K01_COMMAND_CENTER_V10.cmd` and work through the local server. Legacy v8 server is not required.
4. After the CAD semantic stage first passes, run `06_TEST_CAD_HASH_INVARIANCE.cmd` once as architecture qualification.

## Reliability rules

- C# interop DLLs are bundled locally at compile time beside the exporter executable.
- CAD semantic extraction has two adapters: early-bound C# then pywin32 fallback.
- The pipeline writes an 8-stage run report even when an upstream engineering stage is blocked.
- The Center is available independently of CAD/solver stage success.
- No native CAD binary hash participates in `STATE_HASH`.

## Current engineering frontiers after CAD pass

- MBD/DimXpert coverage migration for critical tolerance characteristics.
- Exact SolidWorks study face-role binding for CalculiX.
- Native drawing artifact generated from MBD-backed drawing semantics.
- CalculiX neutral mesh / `.inp` / reconciliation.
