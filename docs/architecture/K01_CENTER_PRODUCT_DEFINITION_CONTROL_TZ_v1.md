# K01 Center — Product Definition control requirements v1

This is an implementation specification for the separate Center branch. The Center remains a derived UI, never engineering authority.

## 1. Core navigation

Keep the main navigation simple and stable:

`Assembly → Node → Interface → Artifact → Evidence`

Product Characteristics are shown inside the relevant Node/Interface view rather than becoming another top-level navigation layer.

## 2. Home page — low visual noise

The first screen must show only:

1. current checkpoint;
2. active engineering node/change;
3. current stage/readiness gate;
4. top release/drawing blockers;
5. exact next action.

Do not place large raw JSON dumps, long debug tables or full evidence lists on the first screen.

All timestamps are rendered in `Europe/Kyiv`. Suggested display: `12.09.2026 09:37 Kyiv`.

## 3. Node / Product Definition panel

For every part, show one matrix with these columns:

- Characteristic ID;
- function;
- nominal/requirement;
- tolerance / fit / GD&T;
- definition state;
- source authority;
- CAD binding;
- PMI/MBD state;
- analysis/tolerance evidence;
- drawing projection state;
- inspection state;
- release blocker.

No value may be hard-coded in HTML/JS. Values come from generated Product Definition/authority feeds.

## 4. Required readiness cards

Show three separate gates, never one generic PASS:

- `DRAWING_CANDIDATE_READY`;
- `PMI_AUTHORING_READY`;
- `DRAWING_RELEASE_READY`.

For each HOLD, provide `Why?` with exact characteristic IDs and missing predecessor evidence.

## 5. Traceability navigation

Clicking a characteristic must expose the complete chain:

`Requirement → Decision/Calculation → Characteristic → CAD binding → PMI → Drawing callout → Inspection → Evidence`

The user must be able to move backward and forward without searching directories.

## 6. Drift/conflict presentation

Center must prominently detect:

- legacy candidate spec conflicts with current decision;
- CAD nominal mismatch;
- tolerance/fit mismatch between compiled Product Definition and PMI;
- drawing callout mismatch;
- inspection criterion mismatch;
- stale evidence or source fingerprint drift;
- OPEN value replaced by a numeric/default value.

Conflict state is `HOLD/DRIFT`; never silently choose one value.

## 7. Method history / anti-loop control

Show execution method status from `K01_EXECUTION_METHOD_REGISTRY_CURRENT.json`:

- ACTIVE;
- PROVEN;
- REJECTED;
- SUPERSEDED.

Rejected paths must remain visible with reason. The UI must warn before rerunning a rejected method.

## 8. Actions

Buttons are gate-driven:

- `Run Product Definition Guard` — always read-only with respect to CAD;
- `Author PMI candidate` — enabled only when PMI_AUTHORING_READY for selected characteristics;
- `Build/Refine Drawing Candidate` — enabled only when DRAWING_CANDIDATE_READY;
- `Promote Drawing` — enabled only when DRAWING_RELEASE_READY + semantic QA + visual QA;
- `Open Artifact` / `Open Evidence` — via registered IDs/paths.

Center delegates to canonical project runners. It must not contain a second implementation of engineering logic.

## 9. “Why is this value here?”

Every numeric/control value shown in Center must have a one-click explanation containing:

- authority type;
- source file/requirement/EDR/evidence ID;
- source fingerprint/date;
- current decision state;
- downstream consumers;
- whether changing it will stale CAD/analysis/drawing/inspection nodes.

## 10. Change impact before write

Before any mutation action, Center must show an impact preview:

- characteristics changed;
- downstream nodes that become STALE;
- CAD files that may be written;
- analyses requiring rerun;
- drawings/inspection plans requiring regeneration;
- rollback snapshot target.

The action is disabled if the active gate does not authorize mutation.

## 11. Center acceptance tests

Center implementation is not complete until automated fixtures prove:

- OPEN stays OPEN;
- a conflicting legacy candidate tolerance is shown as DRIFT/HOLD;
- a changed characteristic stales drawing/inspection projections;
- rejected execution method cannot be launched without explicit override decision;
- drawing release button remains disabled with any release-blocking OPEN characteristic;
- timestamps render in Europe/Kyiv;
- first page contains no raw engineering debug dump.
