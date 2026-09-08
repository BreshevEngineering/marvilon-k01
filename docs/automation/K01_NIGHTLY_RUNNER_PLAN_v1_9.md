# K01 MEDTAS nightly runner plan v1.9

This is a deployment plan, not an active CI workflow.

## Cloud CI — safe now

Run only tasks that do not require native SOLIDWORKS/FEMM sessions:

- JSON/schema validation;
- canonical/hash unit tests;
- state-reducer fixtures;
- status-model tests;
- Command Center static/security tests;
- project-structure audit;
- requirements coverage from committed evidence manifests;
- EBOM/MBOM joins when a canonical CAD semantic snapshot is present;
- drawing/BOM semantic lint over committed structured evidence.

## Windows self-hosted runner — activate later

Required labels: `self-hosted`, `windows`, `k01-cad`.

Installed/controlled tools:

- SOLIDWORKS version fixed by toolchain binding;
- FEMM executable + SHA-256;
- optional CalculiX/Gmsh when independent assurance is reactivated.

Nightly sequence:

1. pull controlled repository state;
2. evaluate Engineering Build Graph;
3. rebuild only `MISSING`/`STALE` nodes whose producer is allowed on this runner;
4. verify artifacts and write evidence records;
5. rebuild derived state and AI handoff;
6. publish a concise morning delta report.

Do not enable a scheduled GitHub workflow until the physical runner is installed and a manual qualification run passes. This avoids queued or misleading nightly jobs.
