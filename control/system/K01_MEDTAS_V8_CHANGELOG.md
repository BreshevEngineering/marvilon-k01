# MEDTAS v8 — K01 controlled update

## Main changes

- Control Center v8 is evidence-driven, not a passive status page.
- Added `Evidence / Files` registry with direct Open / Folder actions for current CAD, reports, work packages, BOM, drawing evidence, Git classification and AI handoff.
- Fixed Control Center PowerShell API invocation (`State`, `GitState`, `FilesState`, `Handoff`) so API endpoints return JSON rather than bare command text.
- C2R1 geometry stays frozen; production-release tasks T03–T10 are separated from geometry rework.
- Added T03 P006 two-pin hollow service-drive native candidate builder.
- Added T04 local-media/temperature qualification layer. FKM 75A is the preferred bounded-BOF candidate; FFKM remains a controlled fallback.
- Added T05 preload/thread/local-flange screen and T06 thermal/galling/service work packages.
- Added T07 final P007 static/buckling release definitions.
- Added T08 controlled BOM metadata projection. APPLY automatically reruns BOM reconciliation.
- Added MEDTAS TPD / Drawing Assurance workflow based on project drawing/tolerance references.
- `AutoDimension` is prohibited for release drawings.
- Drawing linter v2 is fail-closed: native PDF generation cannot become drawing release while OPEN/STUDY/CANDIDATE or unbounded critical characteristics remain.
- Added explicit visual-approval record tied to PDF SHA-256.
- Added technical-filter links to registered literature/evidence.
- Added Git classifier v2 / checkpoint plan; no automatic staging or commit.
- Added read-only installation preflight.
- Mutable evidence, event ledger and native CAD are intentionally not overwritten by this update package.

## Current deliberate drawing holds

The current Drawing Intent definitions are **not RELEASE_READY**. That is intentional.

Known holds include:
- P003 Ø12 H9 is still a release candidate until T03 native/service evidence closes;
- P006 Ø6 through bore lacks a released production tolerance;
- P007 thin-can OD10 / ID9.4 lack explicitly released production tolerances and await T07/manufacturing closure;
- all three drawing-intent files remain `RELEASE_CANDIDATE_NOT_APPROVED`.

Therefore Drawing V3 may generate a useful native draft, but T09 must stay HOLD until these are closed.
