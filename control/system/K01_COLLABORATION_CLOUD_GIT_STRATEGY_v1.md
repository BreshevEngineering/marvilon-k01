# K01 Collaboration / Cloud / Git Strategy v1

## Phase 1 — now

Do not add a cloud CAD/PDM layer while geometry and control structure are still being normalized.

Use:
- local native CAD vault: `D:\Marvilon\K01\cad`;
- Git repository for text/control/scripts/reports/schemas/fingerprints;
- local K01 Command Center server reading both locations;
- immutable Pack-and-Go / STEP/PDF evidence at release checkpoints.

## Phase 2 — second laptop / SW2026

After K01 design freeze:
1. clone/sync Git control repository to the second laptop;
2. create a controlled CAD migration copy;
3. open/convert the frozen release in SW2026;
4. run post-migration geometry/mate/BOM fingerprints;
5. keep the SW2018 frozen release read-only for rollback.

Do not casually save SW2026-converted files over the only SW2018 baseline.

## Phase 3 — multi-user CAD

When several participants actively edit native CAD, introduce a CAD-aware managed vault/PDM rather than a generic sync folder. GitHub remains appropriate for code, schemas, EDRs, requirements/control text, generated reports and PR/review workflow.

## Git checkpoint policy

The connected GitHub installation currently does not expose a repository named `marvilon-k01`. Treat the current local `.git` repository as not yet confirmed against a connected remote.

Do not make one catch-all commit before:
- v2 structure is merged locally;
- J2 compact trade decision is recorded;
- obsolete one-off files are classified KEEP / ARCHIVE / DELETE;
- master repair plan is fixed.

Then make a clean checkpoint commit containing the decision system, Command Center v2, Gate04C PASS evidence and current system docs. Native CAD remains outside Git.
