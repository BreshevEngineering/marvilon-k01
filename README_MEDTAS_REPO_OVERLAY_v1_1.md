# K01 MEDTAS repository overlay v1.1

Purpose: integrate Engineering Build Graph + evidence registry + real SolidWorks semantic hashing into the existing K01 Command Center architecture.

Main entry point after extraction into repository root:

`03_RUN_MEDTAS_CAD_SEM_A001.cmd`

The first successful run creates the first real `K01.CAD.SEM.A001` STATE_HASH from the selected real SolidWorks assembly and the exact ARTIFACT_HASH of the canonical semantic snapshot.

The Gate04E FEM/FEMM report is copied under `reports/engineering/current/` and registered in `control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1.json`, so the Center can surface it by evidence ID rather than relying on filename discovery.
