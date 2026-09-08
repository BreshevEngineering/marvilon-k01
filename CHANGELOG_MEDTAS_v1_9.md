# MEDTAS v1.9 changelog

- Fixed common JSON loader regression (`load(path, default)`).
- Added authoritative `control/requirements/requirements.json`.
- Added requirement-to-evidence coverage report; gate coverage and evidence coverage are distinct.
- Added stable identity policy/registry and non-destructive identity audit.
- Added reducer fixture tests for MISSING/BLOCKED, STALE propagation, DRIFT, and verification freshness.
- Added `parts.json`-driven one-way CAD property projection.
- Split computed specification into EBOM and MBOM; explicit non-modeled items, suppressed occurrence audit, welding/manufacturing transformations.
- Added P007/K01-D-006 first-exemplar plan, MBD checklist, manufacturer-review template and draft skeleton generator.
- Drawing generator remains skeleton-only: no AutoDimension, no blanket PMI dump, no independent duplicate tolerance authoring.
- Added fail-closed drawing QA policy and immutable revision policy.
- Added release characteristic registry and inspection result data contract.
- Added stage 0-7 release-program materialized view without adding another Command Center tab.
- Command Center Overview now exposes the stage program; Requirements view uses authoritative registry + coverage.
- AI Handoff includes requirements, identity, parts/EBOM/MBOM, P007 exemplar, inspection data, architecture, and assurance fixtures.
- CalculiX remains deferred assurance while production-definition stages are open.
