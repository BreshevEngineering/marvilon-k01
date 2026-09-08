# K01 MEDTAS repository overlay v1.4

Extract **into the repository root** with replacement:

`D:\BreshevEngineering\marvilon-k01\`

Do not create a nested `K01_MEDTAS...` directory.

## Primary commands

1. `03_RUN_MEDTAS_PIPELINE.cmd` — complete current build graph pipeline.
2. `OPEN_K01_COMMAND_CENTER_V9.cmd` — local-server engineering Center at `http://127.0.0.1:8790/`.
3. `06_TEST_CAD_HASH_INVARIANCE.cmd` — mandatory semantic-hash stability test after the CAD semantic exporter passes.
4. `05_CALCULIX_PREFLIGHT.cmd` — solver/mesher readiness.
5. `07_STEP_CANONICAL_HASH.cmd` — normalized STEP artifact hash when needed.

## Expected pipeline order

Canonicalization self-test → compile early-bound SOLIDWORKS exporters → real A001 semantic extraction → MBD/DimXpert extraction → snapshot/tolerance/structural/FEMM/drawing/BOM → face-map candidate → CalculiX preflight → derived state / Center feed.

## Important

- Native CAD binary hashes are not semantic freshness keys.
- `STATE_HASH` and `ARTIFACT_HASH` remain separate.
- MBD/DimXpert is the target authority for tolerances/GD&T/datums.
- The current tolerance seed remains a controlled screening fallback only until model PMI is authored.
- CalculiX cannot be released until SolidWorks load/contact selections are mapped to stable geometry signatures.
