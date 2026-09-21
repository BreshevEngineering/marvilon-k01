# ТЗ для Engineering Center — dependency / change impact control

Center remains a projection/orchestration layer. It must not become another engineering authority.

## Required navigation

```text
Assembly → Node → Interface → Artifact → Evidence
```

Product Characteristics appear inside Node/Interface, not as another top-level navigation tree.

## Required top-level information

Keep the first screen low-noise. Show only:

- current checkpoint;
- active change / active node;
- current stage and gate;
- top release blockers;
- exact next action;
- stale/drift count caused by the active change.

Time must be displayed in `Europe/Kyiv` without verbose ISO timestamp noise.

## Change impact panel

For the active change Center must render:

- changed entity and change domain;
- direct graph seeds;
- shared interfaces;
- counterpart parts requiring review;
- transitive affected nodes;
- reason/path for every affected node (`A → B → C`);
- current state (`PASS / STALE / DRIFT / BLOCKED / HOLD / FRESH_UNVERIFIED`);
- required action (`REBUILD / REVERIFY / REVIEW_SOURCE / COUNTERPART_REVIEW`);
- topological rebuild order;
- release impact.

Center must provide **Why stale?** for each node and show the exact upstream fingerprint transition/evidence when available.

## Product Definition trace

For any Cxx:

```text
Requirement / Interface
→ Engineering decision / Technical Filter
→ calculation / standard / test evidence
→ Cxx definition
→ CAD binding
→ PMI / semantic verification
→ compiled Product Definition fingerprint
→ drawing projection
→ inspection characteristic
→ release state
```

## Drift rules

Center must visually separate:

- `STALE`: source/input fingerprint changed; rebuild required;
- `DRIFT`: artifact bytes changed without a matching controlled build record; stop/reconcile;
- `OPEN`: engineering requirement not decided;
- `HOLD`: gate cannot proceed;
- `PARTIAL`: some characteristic semantics are controlled, release is not.

Never collapse these to one generic red/green status.

## Cross-part behavior

If a shared interface changes, Center must show every participant as `COUNTERPART_REVIEW_REQUIRED`. It must never imply the counterpart CAD should be automatically edited.

## Inputs

Center should consume:

- `reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json`;
- `reports/control/K01_CHANGE_IMPACT_CURRENT.json`;
- `reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json` (and equivalent per-part reports later);
- authoritative graph/relationship registries via Authority Map.

Do not use `control/project/K01_DEPENDENCY_STATE.json` or `control/system/K01_DEPENDENCY_GRAPH_v2.json` as new engineering authorities; keep only for legacy compatibility until the other Center branch migrates.
