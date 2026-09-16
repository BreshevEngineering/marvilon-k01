# K01 / MARVILON ISO GPS DRAWING AUTHORING ALGORITHM v1

Status: **CONTROLLED OPERATIONAL METHOD / SUBORDINATE TO D1-D9**
Date: 2026-09-15
Primary architecture: `docs/architecture/K01_DRAWING_PIPELINE_D1_D9_v2.md`
Current exemplar: `K01-D-006 / K01-P-007`

## 1. Purpose and boundary

This document is not a second drawing architecture. It turns D1-D9 into a repeatable working algorithm for K01/Marvilon drawings.

The objective is a manufacturing/inspection definition that is:
- function-derived;
- ISO GPS/TPD based;
- traceable to Product Characteristics and controlled decisions;
- unambiguous for manufacturing and inspection;
- resistant to CAD rebuild/identity drift;
- fast to update without re-authoring the drawing from zero.

Core order:

`FUNCTION -> PRODUCT CHARACTERISTIC -> VARIATION -> DATUM/DRS -> INSPECTION -> NATIVE/CONTROLLED CARRIER -> DRAWING VIEW -> HUMAN LAYOUT -> SEMANTIC QA -> VISUAL QA -> BASELINE`

A drawing is a projection of Product Definition. It is not an independent source of engineering values.

## 2. Mandatory preflight before drawing mutation

Before creating or changing a drawing:
1. Confirm Goal Lock / active deliverable / WIP limit.
2. Resolve canonical part, assembly and drawing identities.
3. Read current Product Characteristics and active EDRs.
4. Confirm material for the part; `OPEN` remains OPEN.
5. Confirm functional and dimensional chains affected by the drawing.
6. Confirm manufacturing route/capability state and inspection method.
7. Check dependencies/freshness and rollback path.
8. Confirm drawing-standard profile and applicable template.
9. Refuse to turn `OPEN/UNKNOWN/PARTIAL` into a released tolerance.

## 3. Product Definition closure gate (before D1/D2)

For every characteristic that will appear on the drawing, define all applicable elements:
- **size** / fit / dimensional limits;
- **location**;
- **orientation**;
- **form**;
- datum or datum system;
- material-condition modifier when functionally justified;
- surface texture/process requirement if functionally required;
- inspection/verification method;
- authority/evidence and stale triggers.

Do not start drawing semantics from raw CAD dimensions. Model-driving dimensions are not automatically Product Characteristics.

For patterns under ISO 5458, explicitly decide whether zones are independent or a pattern (`CZ/CZR/SIM`). Multiplicity such as `3×` alone is not an ISO tolerance-zone pattern.

For MMR/LMR, calculate the functional boundary and document why the modifier is used. Do not add a modifier for convenience.

## 4. D1 — drawing plan / view algorithm

Choose the minimum set of views that uniquely communicates the controlled characteristics.

Default for a rotational flanged hollow part:
1. `AXIAL_FULL_SECTION` for internal/axial features;
2. `FLANGE_END` for bolt pattern, locator and flange features;
3. optional auxiliary/isometric view only when it removes a real ambiguity.

Route each Product Characteristic to one preferred view. A characteristic should normally be specified once. Avoid duplicate dimensions and tolerance chains that only reconstruct a functional dimension indirectly.

Use only scales allowed by `K01_DRAWING_STANDARD_PROFILE_CURRENT.json`.

## 5. D2 — semantic authoring

Author in dependency order:
1. Datum / datum system.
2. Size and fits.
3. TED / location / patterns.
4. GD&T / GPS.
5. Surface texture.
6. Material/process/controlled notes.
7. Title-block controlled properties.

Preferred carrier order:
`native model PMI/DimXpert -> proven native drawing semantic -> controlled compatibility representation`

If the installed CAD version cannot natively represent a newer ISO construct, record the compatibility limitation and use a controlled representation only when its meaning is unambiguous and upstream authority is explicit. Never silently substitute a different GPS meaning.

Any geometry attachment must resolve by stable semantic/geometric signature. Zero matches or more than one match = HOLD. Never choose the nearest face to force PASS.

## 6. D3 — binding invariance

Verify that every release-critical annotation remains attached to the intended feature after:
- save / close / reopen;
- no-op rebuild;
- controlled benign perturb/restore when an approved L3 test exists.

Persistent/transient face IDs alone are not authority.

## 7. D4/D5 — release-native compile and projection

Compile the expected drawing semantic manifest from current Product Definition, then generate/refine the drawing through a capability-qualified method.

Automation may create views, sections, datums, fits, controlled dimensions, FCF/GTol carriers, surface symbols, notes, property links and initial placement.

Automation must not:
- bulk-dump construction dimensions into a release drawing;
- invent missing tolerances;
- infer a datum from manufacturing convenience;
- silently replace a failed feature binding;
- treat visual similarity as semantic proof.

## 8. D6 — human visual finish only

After semantic completeness, the engineer may:
- move annotations;
- reroute leaders;
- remove overlaps;
- improve grouping and white space;
- adjust view positions within the controlled layout.

The engineer may not change engineering values, datum order, tolerance modifiers, fit classes or controlled notes during D6.

Capture the pre-D6 semantic fingerprint and verify it is unchanged after D6. Where useful, capture final annotation coordinates for reuse as a layout seed.

## 9. D7 — semantic QA

Mandatory checks:
- every required Product Characteristic represented exactly once, except controlled composite representation;
- no missing required claim;
- no unregistered semantic annotation;
- no contradictory/duplicate dimension;
- no dangling annotation;
- correct feature binding;
- correct datum identities/order;
- correct fit/tolerance/GPS modifiers;
- TEDs used where theoretical location is required;
- pattern semantics explicit (`CZ/CZR/SIM`) when required;
- no uncontrolled general tolerance;
- material and part/drawing identity coherent;
- source/Product-Definition fingerprint current.

Printed numerical equality is not enough: provenance must also match.

## 10. D8 — visual/ISO presentation QA

Check the exported preview/PDF, not only API objects:
- first-angle projection symbol and consistent projection;
- ISO-approved scale;
- no annotation/geometry/title-block collisions;
- leaders point unambiguously to their controlled feature;
- FCFs sit close enough to the controlled feature to avoid misreading;
- no crossed leaders when avoidable;
- readable text/line hierarchy;
- adequate white space;
- section identification is complete or intentionally omitted when unambiguous;
- title block satisfies the controlled ISO 7200 field set;
- no debug/candidate filename in the drawing number/title;
- review/release status clearly visible.

A technically complete but hard-to-read drawing does not pass D8.

## 11. D9 — baseline / delivery

Only after D7 PASS + D8 PASS:
- export required PDF and other delivery formats;
- record source and output hashes;
- record revision/effectivity;
- link inspection/requirement evidence;
- promote through the project release gate.

Local drawing PASS never overrides product/release HOLD elsewhere in the project.

## 12. Automation boundary proven by D006

### Implementation maturity

The target automation boundary is broader than the currently proven implementation. Annotation/view positions are already machine-capturable and replayable by design; leader routing and collision optimization are technically automatable presentation tasks but are not yet implemented in Drawing System v1. Until proven, they remain D6 manual work. Final human D8 approval remains mandatory even after further layout automation.


**Automate:** view creation, semantic authoring from controlled manifest, datums, fits, FCF/GTol carriers, surface finish, controlled notes, title-block properties, positive hiding of known construction annotations, source-copy safety, semantic coverage, binding ambiguity checks, PDF export, coordinate capture.

**Keep human-controlled:** final leader routing, collision resolution, fine visual composition, last title-block visual check, and any CAD-version compatibility representation that cannot be proved native and stable.

The target is not zero-touch CAD. The target is deterministic semantics plus fast human presentation finish.

## 13. D006 exemplar-specific frozen lessons

1. Two views are sufficient for P007: axial section + J2 mating-side end view.
2. Datum A comes from the functional J2 mating/seal plane set; Datum B from the Ø14.10 H7 locator axis.
3. C02 is a coupled non-bottoming stack; after EDR-032 the drawing requirement is `2.00 ±0.05`, paired with P003 `1.50 ±0.05`.
4. C04 is an ISO 5458 pattern after EDR-033: `3× Ø2.90 H10 THRU; TED Ø26.50; TED 120°; POSITION ⌀0.15 CZ Ⓜ | A | B`; datum B remains RFS.
5. `WALL 0.30 REF` remains derived/reference; it is not silently promoted to a minimum-wall acceptance criterion.
6. C11 remains `TOTAL RUNOUT 0.02 | B` unless a new EDR changes the metrology/function basis.
7. SW2018 compatibility limitations do not change Product Definition. If native CZ support is unavailable, the representation must be explicitly controlled and verified.
8. D006 current reviewed sheet scale is `2:1`; future drawings shall select a preferred ISO 5455 scale from the controlled drawing spec. Multiple view scales are used only when functionally necessary and explicitly identified.

## 14. Stop / anti-loop rules

Stop and review the path if:
- two consecutive automation changes do not reduce a current drawing DoD gap;
- an API workaround requires guessing a face or semantic meaning;
- a visual fix starts changing Product Definition;
- a new tool duplicates an existing pipeline function;
- the current blocker is supplier/inspection evidence rather than CAD automation.

At that point the next action belongs upstream (engineering decision/evidence) or downstream (human D6/D8), not in another drawing-generation framework.


## View selection algorithm (controlled)

Before authoring annotations, derive views from Product Characteristics:

1. List each characteristic and the geometry it must expose for manufacture/inspection.
2. Choose the primary representation that exposes the greatest amount of controlled geometry with the least ambiguity. Use a longitudinal section instead of an external frontal/profile view when internal axial geometry is essential.
3. Partition remaining characteristics by functional interface/end.
4. Add one end/interface view for each non-equivalent asymmetric interface that carries unique information (patterns, clocking, datums, glands, threads, sealing geometry).
5. Remove a candidate view only if every characteristic on it is already unambiguously represented elsewhere and symmetry/equivalence is proven.
6. Record the rationale in the drawing spec `view_strategy`; the API must fail preflight if a required interface view is missing.

K01-D-003 reference plan: `LONGITUDINAL_SECTION + J1_END + J2_END`.
