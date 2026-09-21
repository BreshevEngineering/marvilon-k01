# K01 Drawing / Product-Definition Workflow v1

Status: CONTROLLED ARCHITECTURE
Scope: K01 and reusable Marvilon drawing workflow
Method: hybrid MBD + 2D derivative drawing

## 1. Authority model

The 2D drawing is not a second independent source of dimensions.

Authority chain:

`requirement / engineering decision -> product characteristic Cxx -> 3D geometry -> native PMI/DimXpert or controlled model annotation -> annotation view -> 2D drawing presentation -> inspection characteristic -> verification result`

Roles:
- Native 3D CAD owns nominal geometry.
- Product-characteristic registry owns intent, state and release/OPEN status.
- Native DimXpert/PMI owns released dimensional/GD&T semantics associated with geometry.
- The 2D drawing is a human-readable derivative/presentation of controlled product definition.
- Drawing-only notes are allowed only when explicitly controlled as supplemental product definition.
- Inspection characteristics are derived from the same Cxx/PMI source, never reconstructed from OCR or manually retyped drawing values.

## 2. Proven-current rule

P007 C02/C05 native PMI is already PROVEN on current canonical geometry:
- C02: Ø14.10; native DimXpert semantic PASS.
- C05: Ø33.00; native DimXpert semantic PASS.
- save/close/reopen PASS.
- persistent states 0/0.
- solid geometry invariant.
- proven core SHA-256: `2d6546a84b32261c3e99bbe7f8754d205ecf7b8f741069722b822a71bdf8c636`.

Do not rebuild these annotations from typed drawing text.

## 3. SOLIDWORKS 2018 transfer path

For SW2018, DimXpert data must be transferred using drawing/annotation-view import, not by manually retyping values.

Supported UI workflow:
1. Open the part containing DimXpert annotations.
2. Create/open the drawing.
3. Insert/select the relevant drawing or annotation view.
4. Enable `Import annotations` + `DimXpert annotations`.
5. For section views, select the appropriate source annotation view and enable the same DimXpert import option.
6. Move/reflow imported annotations in the drawing. Do not replace their numerical content with typed dimensions.

Important: direct `IView.ImportAnnotations` automation with a DimXpert-import flag is not part of the SW2018 API surface used by this project, and `InsertModelAnnotations3` / Model Items is not accepted as the DimXpert transfer mechanism.

K01 therefore uses an **automation-first compatibility bridge** for this narrow SW2018 gap: the existing linked SLDDRW is copied to a timestamped candidate; SOLIDWORKS API controls the drawing/view state; Windows UI Automation is allowed only to toggle the native Drawing View PropertyManager controls `Import annotations = ON`, `DimXpert annotations = ON`, `Design annotations = OFF`; SOLIDWORKS/DimXpert API then verifies the exact Cxx semantic bindings before the candidate can PASS. Source CAD and source drawing must remain invariant.

If the compatibility bridge returns HOLD because the local SW2018 UI controls cannot be resolved, the tool must emit diagnostics. Manual UI import is a controlled fallback, not the default workflow. The drawing is not rebuilt from zero.

## 4. Required drawing stages

### D0 — Product definition readiness
For every Cxx:
- geometry identity is controlled;
- value/tolerance is CONTROLLED or OPEN;
- datum relationships are known where applicable;
- material is explicit;
- no invented release values.

### D1 — 3D PMI / annotation-view readiness
Released dimensional/GD&T characteristics are authored in the model.
Create/organize annotation views by manufacturing/readability purpose, not by arbitrary CAD orientation.

Recommended P007 annotation views:
- `AV_J2_LONGITUDINAL`
- `AV_FLANGE_END`
- `AV_CAN_SECTION`
- optional `AV_GENERAL`

### D2 — Automated drawing seed
Automation may create:
- sheet from controlled template;
- standard orthographic/section/detail/isometric views;
- center marks / center lines;
- linked custom properties;
- candidate filename / revision metadata;
- PDF/BMP preview.

Automation must NOT claim professional release based only on file creation.

### D3 — Native DimXpert import
Default path: run the controlled SW2018 native DimXpert compatibility bridge on a timestamped copy of the existing linked drawing. The bridge uses the native Drawing View import controls, with Design annotations disabled, and must machine-verify the exact Cxx/DimXpert bindings after import.

Manual UI import is permitted only as an explicitly controlled fallback after a diagnostic bridge HOLD. The drawing is not rebuilt from zero.

No typed duplicate of a native PMI dimension is allowed. `DIMXPERT_COUNT = 0` is always HOLD.

### D4 — Human drawing layout / detailing
This is the final **10–20% visual last mile** after semantic PMI transfer PASS. Structural drawing refinement remains automated. Human controls presentation:
- choose the minimum necessary views;
- choose sheet size and scale;
- position views;
- reposition annotation text/leaders;
- avoid crossings and overlaps;
- set section/detail view positions;
- check hatching;
- check centre lines/marks;
- manage line weights/fonts;
- keep the title block readable;
- add only controlled drawing-only notes.

This is the intended last-mile step. Manual **layout** is allowed. Manual **re-entry of semantic values** is not.

### D5 — Automated semantic QA
Required checks:
- drawing references the approved source part/configuration;
- source model hash is unchanged by drawing work;
- each released Cxx shown on the drawing maps to a controlled PMI/model annotation or approved supplemental note;
- no duplicate/conflicting controlled values;
- no dangling annotations;
- required datums/GD&T present;
- imported C02/C05 numerical values match model PMI;
- title-block properties match controlled metadata;
- no released dimension exists only as free text;
- OPEN characteristics remain OPEN.

### D6 — Human visual QA
Check:
- readable at print/PDF scale;
- no collisions;
- visual hierarchy is clear;
- correct view choice;
- section/detail view communicates geometry;
- annotations are adjacent to the relevant feature;
- title block is not overwritten;
- no giant filename/property text;
- no engineering-status table obscures geometry;
- no unnecessary empty sheet area.

### D7 — Inspection linkage
Generate inspection/FAI characteristic list from Cxx/PMI authority:
`Cxx -> PMI/drawing callout -> inspection method -> acceptance -> result`.

The characteristic table belongs in inspection/workpack evidence unless the drawing standard explicitly requires it on the sheet.

### D8 — Release
Only after semantic QA + visual QA + technical filter + release blockers are closed:
- drawing candidate may be promoted;
- PDF is generated from the promoted SLDDRW;
- release state is explicit.

## 5. Current K01-D-006 layout target

The current auto-generated sheet is an **automation seed**, not a professional drawing.

Preferred P007 sheet concept:
- A3 landscape initially. Project scale profile is controlled: SECTION A-A 5:1; FLANGE END 5:1; PARENT/SIDE 2:1; ISOMETRIC 2:1; DETAIL B 10:1 when required.
- Primary view: longitudinal full/half section through the can axis.
- Secondary view: flange/end view for Ø33 and 3-hole pattern.
- Detail B: J2 locator/flange interface if C02/H7/depth becomes crowded.
- Small isometric view for orientation only; no manufacturing dimensions.
- Delete redundant identical side views.

Primary longitudinal section should carry, when controlled:
- OAL 35;
- flange thickness 3;
- locator Ø14.10 H7 and depth 2.00;
- can OD Ø10;
- can ID Ø9.40 / wall 0.30;
- blind-end nominal 1.00;
- relevant datums/GD&T.

End view should carry, when controlled:
- flange Ø33;
- 3×Ø2.90 THRU;
- PCD Ø26.50;
- angular/basic pattern definition;
- datum/pattern controls.

## 6. What must NOT be on the final manufacturing drawing

Do not use the drawing sheet as a project dashboard.

Move these to separate controlled reports/workpacks:
- `semantic_pass=True`;
- persistent-ref states;
- large OPEN-item characteristic table;
- implementation/debug messages;
- long filenames;
- API status;
- workflow notes.

For an incomplete design-review drawing, use a short status:
`DESIGN REVIEW - NOT FOR MANUFACTURE`
and reference the controlled open-item/workpack externally.

## 7. Title block and template

Use one title block only.

Target controlled template pair:
- K01 `.drwdot` document template: ISO drafting/document properties, fonts, line weights, arrows, units.
- K01 `.slddrt` sheet format: frame + title block + projection symbol + controlled property links.

Title block fields should come from controlled properties:
- drawing number;
- part number;
- title;
- revision;
- document status;
- material;
- scale;
- sheet;
- drawn/check/approved;
- date.

Do not use the full file name as the visible drawing number/title.

## 8. Standards profile

K01 should freeze an ISO/GPS project profile rather than depend on SOLIDWORKS defaults.

Reference stack:
- ISO 8015 — GPS fundamental principles.
- ISO 129-1 — presentation of dimensions/tolerances.
- ISO 1101 — geometrical tolerancing.
- ISO 5459 — datums and datum systems.
- ISO 14405-1 — linear sizes.
- ISO 5457 — sheet size/layout.
- ISO 7200 — title-block/document-header data.
- ISO 16792 — digital product-definition data practices.

Because SOLIDWORKS 2018 predates some current editions, use only notation that has been explicitly verified in SW2018; newer GPS constructs require manual standards verification before release.

## 9. Classification of current generated K01-D-006

The current generated artifact proves:
- native SLDDRW/PDF creation;
- source model reference;
- section command execution;
- source hash invariance;
- export pipeline.

It does NOT prove professional drawing quality.

Correct status:
- `PASS_LINKED_DRAWING_SEED`
- `HOLD_PROFESSIONAL_PRESENTATION_AND_PMI_TRANSFER`

The label `PASS_K01_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE` is therefore too strong as a visual-quality claim and must not be interpreted as release evidence.
