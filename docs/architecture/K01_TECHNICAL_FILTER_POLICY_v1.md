# K01 technical decision filter policy

## Role

The technical filter is mandatory for every engineering change, analysis, candidate, drawing and promotion. It prevents a local numerical PASS from being mistaken for an engineering release decision.

The existing numeric category mapping remains owned by:
- `tools/medtas/technical_filter_map_v2_2.py`
- `reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json`

This document intentionally does **not** create a second numbering scheme.

## Mandatory engineering domains

Each active decision shall consider, where applicable:
requirements/acceptance; function/performance; interfaces/datums/kinematics; strength; stiffness; stability/buckling; fatigue/service life; thermal behavior; pressure/vacuum/leak/containment; magnetic/electromagnetic loads; dynamics/inertia/vibration; friction/tribology/wear/galling; tolerances/GD&T/stack-up; materials/environment; manufacturability; process capability/joining/fastening; assembly/accessibility; operation/service/maintenance; inspection/metrology/testability; reliability/fail-safe/misassembly; independent verification/cross-check; supply/availability/obsolescence; cost/value/complexity; concept preservation/change impact/documentation/traceability.

## Status rule

Every applicable domain is `PASS`, `PASS_WITH_LIMIT`, `OPEN`, `HOLD` or `N/A + rationale`.

- `N/A` without rationale = HOLD.
- Screening PASS authorizes only a screening claim.
- Engineering-baseline promotion may preserve explicitly recorded release-only HOLDs.
- R01 requires zero unresolved applicable release blockers.
- Materials are always explicit; unknown = OPEN.
- Rejected alternatives and reasons remain in the decision/change history.

## Step rule

No CAD write, BOM promotion, drawing release or R01 transition bypasses:
`checkpoint → authority → dependency/freshness → technical filter → evidence/rollback`.
