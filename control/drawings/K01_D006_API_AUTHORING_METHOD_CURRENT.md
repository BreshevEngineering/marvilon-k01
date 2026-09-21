# K01-D-006 API AUTHORING METHOD — CURRENT
Revision: 2026-09-15
Status: controlled working method for the first K01-D-006.
Protocol: K01-TZ-AI-OPERATING v1.0

## Goal
Use SolidWorks API/Python only where they directly reduce time on the current deliverable.
The target is not zero-touch drawing generation.
The target is:
`API semantic authoring + API verification + fast manual visual finish`.

## Current proven result
`TWO_VIEW_V2` is the current best API baseline.

It demonstrated:
- two-view manufacturing concept;
- longitudinal section;
- J2 mating-side flange view;
- full controlled drawing coverage for the current P007 characteristics (9 production dimensions after EDR-032);
- native Datum A/B creation and five GTol carriers;
- controlled C04 TED boxing and ISO-5458 pattern semantics from EDR-033;
- native surface-finish creation on J2 mating/seal-contact face;
- positive authoring of controlled dimensions without bulk model-driving-dimension dump;
- PDF/BMP export;
- source-copy / candidate workflow;
- K01-TZ preflight in the runner.

The current result is a semantic-complete engineering-review authoring base. It is not manufacturing release until D7/D8/D9 and the remaining project release conditions pass.

## Architecture for P007
Drawing archetype:
`P007_FLANGED_THIN_WALL_CAN`

Required manufacturing views:
1. `SECTION` — full longitudinal section through the functional axis.
2. `J2_MATING_END` — flange view from the P003/J2 mating side.

No side/profile or isometric view is required for manufacturing definition unless a later ambiguity is proven.

## Authority chain
`Product Definition -> characteristic manifest -> native model/drawing semantic -> SLDDRW/PDF -> inspection`

Engineering tolerances/GPS are never independent hard-coded authority in C#.
The executor consumes current controlled Product Definition / EDR data.

CAD equations own nominal geometry.
Product Definition owns tolerances/GPS/material/process/inspection semantics.
Drawing automation owns projection/presentation only.

## Stable identity
Primary identity:
`characteristic_id`

Preferred names:
- C01_DATUM_A
- C01_FLATNESS_CZ
- C02_LOCATOR_DIA
- C02_LOCATOR_DEPTH
- C03_LOCATOR_PERP_A
- C04_CLAMP_HOLE_PATTERN
- C04_CLAMP_PATTERN_POS
- C05_FLANGE_OD
- C05_FLANGE_THK
- C06_OAL
- C07_CAN_OD
- C08_CAN_ID
- C08_WALL_REF
- C11_CAN_OD_RUNOUT
- C11_CAN_ID_RUNOUT
- BLIND_END_THK

Binding safety:
`characteristic_id + readable name + semantic/geometric signature`

Do not rely on:
- creation order;
- `Diameter2` / `Diameter4`;
- transient SolidWorks object IDs;
- nominal value alone.

## Proven SW2018/API26 patterns
Use these before inventing new methods:
- `CreateDrawViewFromModelView3`
- proven section-view creation path (`CreateSectionViewAt5` where applicable)
- `InsertModelAnnotations3`
- `swInsertDimensionsMarkedForDrawing`
- `swInsertDimensionsNotMarkedForDrawing`
- `swInsertDatums`
- `swInsertGTols`
- `IInsertDatumTag2`
- `IInsertGtol`
- `InsertSurfaceFinishSymbol2`
- `DimensionTolerance.SetFitValues`
- silent `SaveAs` / PDF export
- SHA/source-invariance verification

Selection rule:
- do not call `Face2.Select4` directly in SW2018 interop;
- use `Face2 -> Entity -> IEntity.Select4` or a proven corresponding-entity path.

## Non-destructive rule
Default = PRESERVE.

Never:
`import -> numeric guess -> delete everything else`.

`CORE_DIMS_V1` proved this failure mode:
25 annotations imported, 23 destructively filtered.

Correct approach:
`import / author -> classify positively -> hide only after positive classification`.

Do not use destructive DeleteSelection2 cleanup as a presentation strategy.

## Automation / manual split
API:
- create/position views initially;
- native Datum/GTol/surface-finish semantics;
- controlled fits/tolerances where model binding is proven;
- model-item import;
- notes/material/title metadata where safe;
- PDF/BMP export;
- read-only coverage/binding/dangling checks.

Python:
- compile characteristic manifest;
- enforce Goal Lock/preflight;
- freshness/fingerprint checks;
- compare expected vs extracted drawing semantics;
- evidence/coverage update;
- handoff/continuity state.

Manual:
- hide non-product model-driving dimensions;
- move annotations;
- remove visual overlaps;
- refine leader routing;
- final title-block visual cleanup;
- final human readability approval.

The user should not have to remember or invent engineering values manually.

## Current surface-texture decision
EDR-031 engineering-review candidate:
- functional surface: P007 J2 mating/seal-contact face;
- `Ra 0.8 µm max`;
- release is conditional on final seal compound/product, media/cleaning envelope and leak qualification;
- do not apply this as a global roughness requirement to all P007 surfaces.

## Current drawing-specific lessons
1. Part and drawing can live in different controlled folders. Never infer one path from the other.
2. `*Left` is the selected P007 J2 mating-side flange orientation for the current archetype.
3. The O-ring gland belongs to P003. K01-D-006 defines the P007 contact face, not P003 groove geometry.
4. Datum A = J2 functional mating plane/face set.
5. Datum B = derived axis of the Ø14.10 H7 locator feature.
6. A/B and GTol must be native semantics, not plain-text imitation.
7. Two views are sufficient for this part unless a real ambiguity is found.
8. Layout perfection is not an API release criterion for the first drawing; human visual cleanup is allowed.

## Current V2/R7 limitations / backlog
Semantic content is now closed for the current drawing-authoring scope, but presentation/release evidence remains:
- C02 depth is controlled by EDR-032 as `2.00 ±0.05`; first-article capability confirmation remains required and D003/P003 must later project the paired `1.50 ±0.05` pilot length;
- C04 is controlled by EDR-033 as `POSITION ⌀0.15 CZ Ⓜ | A | B`, with Datum B explicitly RFS;
- SOLIDWORKS 2018 has no proven native ISO-5458:2018 CZ object. The R7 executor attempts a controlled `CZ` literal in the tolerance-value compartment. If that rendering fails or becomes ambiguous, D006 remains HOLD for controlled manual ISO representation;
- C01 `CZ` has the same SW2018 compatibility limitation and requires final visual/semantic review;
- annotation placement/leader routing and collision removal remain D6 human layout;
- title block/template, first-angle projection symbol and final ISO-7200 fields remain D8/D9 work;
- sheet and both required views use the controlled ISO 5455 enlargement scale `5:1`;
- `ENGINEERING REVIEW — NOT FOR MANUFACTURE` remains until final release gates pass.

## Stop conditions
Do not continue automatic mutation if:
- Product Definition fingerprint is stale;
- active model/drawing identity is ambiguous;
- a native Datum/GTol would have to be replaced by a plain text note;
- a required characteristic is still OPEN;
- geometry signature changes unexpectedly;
- two automation iterations fail to reduce the remaining manual work.

## Reusable drawing algorithm
The reusable operational sequence is documented in `docs/architecture/K01_DRAWING_AUTHORING_ALGORITHM_ISO_GPS_v1.md`.
It is subordinate to, and operationalizes, `K01_DRAWING_PIPELINE_D1_D9_v2.md`; it is not a competing authority or a new lifecycle.

The key rule learned from D006 is: **close Product Definition first, author semantics second, arrange presentation third, verify semantics after manual layout, then baseline.**

## Post-D006 improvement path
Only after the first accepted D006:
1. retrospective;
2. capture annotation layout map;
3. migrate stable Cxx names;
4. test same-part rebuild/reapply layout;
5. benchmark SW2026 in a COPY/SANDBOX;
6. run the method on 2–3 more parts;
7. only then generalize archetypes / batch drawing generation.

This file is the continuity source for the drawing API method.
