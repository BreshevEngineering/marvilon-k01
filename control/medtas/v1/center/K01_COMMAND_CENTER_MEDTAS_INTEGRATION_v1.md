# K01 Command Center — MEDTAS integration contract v1

The Command Center must not discover engineering reports by filename. It consumes one generated feed:

`reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json`

The feed contains:
- Engineering Build Graph node state and both hashes;
- blockers/stale reasons;
- registered engineering evidence and report paths;
- current CAD semantic snapshot identity;
- release readiness summary.

The controlled evidence catalog is:

`control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1.json`

The formal Gate04E FEM/FEMM report therefore appears in the Center by evidence ID, not by manual file browsing.

## Required UI section

`Engineering Build Graph`

Each node card should display:
- node ID and title;
- derived state;
- STATE_HASH short form;
- ARTIFACT_HASH short form;
- stale/block reason;
- direct upstream/downstream links;
- evidence/report links where registered.

The Center is a view/controller over MEDTAS. `K01_CURRENT_STATE.json` remains a generated materialized view, not an authoritative source.
