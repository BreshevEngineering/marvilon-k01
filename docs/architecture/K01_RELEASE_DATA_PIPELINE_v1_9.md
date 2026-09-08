# K01 release-data pipeline v1.9

The mechanical calculation branch is no longer the main critical path. MEDTAS v1.9 prioritizes identity, controlled registries, product definition, drawing/BOM release, acceptance data, and only then unattended rebuild infrastructure.

## Stage 0 — stable identity

Authority:
- `control/identity/K01_IDENTITY_POLICY_v1_9.json`
- `control/identity/entities.json`
- `control/product/parts.json`

State/lifecycle tokens are prohibited in the canonical native CAD identity. Existing `GATE*`, `CANDIDATE`, `VERIFY`, `REFERENCE`, etc. names are migration debt. Migration is deliberately not performed by archive extraction or file-system rename because SOLIDWORKS references must be updated safely.

Done when the identity audit is PASS and no new stateful canonical filenames are introduced.

## Stage 1 — two authoritative registries

- `control/requirements/requirements.json` owns requirement definition.
- `control/product/parts.json` owns product identity metadata.

Derived gate state, evidence freshness, quantities, and CAD geometry are not authored in those registries.

`K01_REQUIREMENTS_COVERAGE_CURRENT.json` reports explicit coverage. Gate coverage and registered evidence coverage are shown separately.

## Stage 2 — trustworthy reducer and Center

- one status model;
- unknown status -> MISSING;
- side-effect endpoints POST only;
- same-origin + CSRF;
- open/reveal by registered server-side ID only;
- DOM text inserted with `textContent`, not raw server-controlled HTML;
- no engineering dimensions hard-coded in HTML/JS/CSS;
- reducer fixtures verify MISSING/BLOCKED, STALE, DRIFT, and verification freshness.

## Stage 3 — specification is computed

CAD owns modeled occurrence/quantity. `parts.json` owns metadata. EBOM and MBOM are separate computed nodes.

The BOM model explicitly includes:
- non-modeled required items;
- suppressed-occurrence disposition;
- welding/manufacturing transformations.

CAD custom properties are a one-way projection from `parts.json`.

## Stage 4 — tolerances are model data

Native PMI/MBD is the target tolerance/datum authority. Tolerance analysis consumes extracted model data. Legacy seeds are screening fallback only and must not silently become released tolerances.

Worst-case is deterministic. Monte Carlo is allowed only when the production distribution is explicitly assigned; no normal distribution is guessed.

## Stage 5 — drawings

P007 / K01-D-006 is the first exemplar because it combines thin wall, welding/containment, locating GD&T and hermetic inspection.

The API creates the skeleton (template + standard views). It does not AutoDimension or independently author duplicate tolerances. Released drawing tolerance/GD&T must originate from model PMI/MBD. Drawing QA is fail-closed.

## Stage 6 — characteristics and acceptance

A stable characteristic key links:
- model PMI;
- drawing balloon;
- inspection plan;
- measured result;
- released acceptance criterion.

Candidate textual specs are not parsed into release acceptance. A measured result is automatically evaluated only against structured released bounds/criteria.

## Stage 7 — runners / nightly build

Deferred until stages 0-6 are materially stable. Cloud CI should run non-CAD assurance. A qualified Windows self-hosted runner later rebuilds stale SOLIDWORKS/FEMM nodes and publishes a morning delta.

No active scheduled workflow is shipped before the physical Windows runner is qualified.
