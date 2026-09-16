# Marvilon Drawing System v1

Status: CONTROLLED ENGINEERING WORKFLOW / D003 generic semantic authoring PASS / candidate lifecycle PASS / placement capture+replay round-trip PASS / generic-engine hardening in progress.

## Goal

Build professional ISO/GPS drawings without turning each drawing into a new software project. Product definition stays upstream; the drawing system projects controlled semantics into SolidWorks, verifies them, then leaves only the visual last mile to a human.

## Authority chain

`requirement / EDR -> product characteristic -> CAD geometry -> drawing spec -> geometry binding -> native drawing annotation -> semantic QA -> human visual QA -> release`

The drawing is never the primary source of a value that already exists upstream.

## Mandatory preflight

Before any drawing mutation:
1. Goal Lock / active drawing / WIP=1.
2. Canonical model identity and material.
3. Product-characteristic state: CONTROLLED / CANDIDATE / OPEN.
4. Global datum namespace: one datum identifier = one physical datum feature within a part drawing.
5. View minimum set.
6. Manufacturing and inspection meaning for every controlled callout.
7. OPEN items remain visible as blockers; review mode may proceed, release mode may not.
8. Source model hash captured; drawing work must not mutate source CAD.


## View-selection policy

The drawing system does not use a fixed recipe such as “front + top + side”. It selects the minimum set of orthographic representations that makes manufacture and inspection clear and unambiguous.

Rules:
1. Prefer a longitudinal section as the primary representation when internal axial geometry, steps, bores, wall thicknesses or interface engagement cannot be defined cleanly by an external profile without hidden-line dependence.
2. Add a dedicated end/interface view for every functionally non-equivalent end that carries unique non-axisymmetric information: hole/thread pattern, clocking feature, gland, datum feature or interface geometry.
3. An end view may be omitted only when equivalence/symmetry is explicitly proven and no unique Product Characteristic would be lost.
4. A view is justified by information content, not by convention or screen convenience. Redundant views are forbidden.

For K01-D-003 the accepted functional minimum is therefore: `LONGITUDINAL_SECTION + J1_END + J2_END`. The `*Front` orientation exists only as the parent orientation from which the section is created; it is not the delivered primary external view. J1 and J2 both remain visible because they are different interfaces and are not rotationally/functionally symmetric.

## Generic authoring primitives

The API layer owns deterministic operations:
- A3/A4 sheet + preferred ISO scale;
- first-angle sheet property;
- longitudinal/orthographic/end/detail view creation;
- geometry binding by controlled selector/signature (diameter, region, adjacency, count; feature identity may be added when a stable named feature is available), never by face index alone;
- size dimensions, fits and unilateral/symmetric tolerances;
- datum tags;
- feature-control frames;
- TED boxes;
- controlled thread/hole notes;
- controlled material/status notes and document custom properties;
- PDF/BMP export;
- source-hash invariance;
- machine-readable coverage report.

Fail closed when a geometric selector is ambiguous.

## Human last mile

Manual work is intentionally limited to:
- leader routing;
- collision removal;
- small annotation moves;
- hatch/readability review;
- final title-block appearance when the template cannot express a field natively in SW2018.

No manual re-entry of engineering values.

## Capture loop

Candidate lifecycle is controlled by `MARVILON_DRAWING_CANDIDATE_LIFECYCLE_V1.md`. The generated semantic candidate is preserved, visual work is performed only in `manual_finish`, and stable semantic annotation names are captured into `control/drawings/placement/<drawing_id>_PLACEMENT_CURRENT.json`. Subsequent rebuilds consume that profile automatically. This converts manual layout from recurring work into a one-time calibration rather than writing coordinates back into engineering values.

## D006 lessons frozen into v1

- Product > Evidence > Automation.
- Semantic coverage before beauty.
- Construction/model dimensions are not manufacturing characteristics.
- ISO 5458 pattern semantics (`CZ/CZR/SIM`) are an engineering decision, not decoration.
- SW2018 representation limitations never change upstream GPS meaning.
- One local PASS does not imply drawing/product release.

## Second-part validation: K01-D-003

D003 is deliberately harder than D006: two functional interfaces, five global datum identifiers, fits, a threaded clamp pattern, an O-ring gland and a kinematic Datum-C feature. It is the system-validation drawing.

P003 has two local interface datum systems in historical project documents. `EDR-034` resolves the whole-part drawing namespace:
- J1: A / B / C;
- J2: D / E.

This is only a datum-letter mapping; physical references and numerical tolerances remain those of the controlling EDRs.

## Validation criterion for Drawing System v1

The system is considered generalized only when:
1. D006 rebuild remains semantically complete from controlled data;
2. D003 review candidate is built from its drawing spec without manual retyping;
3. the engine reports OPEN/CANDIDATE items as HOLD instead of inventing values;
4. source CAD hashes remain unchanged;
5. only visual layout remains manual.

## Binding rule for approximate CAD boxes

`IFace2.GetBox` may be used only as a coarse discriminator (for example NEGATIVE/POSITIVE axial region or approximate trimmed end). It is not an acceptance measurement and shall never justify micrometre-level tolerances. Final binding must also match exact analytic surface type/diameter/count and, for adjacent planes, resolve the nearest analytic plane with an explicit selection rule. Ambiguity is a HOLD.

## Canonical discovery and new-chat continuity

The canonical machine-readable pointer is:

`control/drawings/K01_DRAWING_SYSTEM_CURRENT.json`

The implementation is not discovered by searching the newest D006 patch. Read the pointer first. It names the generic engine, lifecycle tool, placement-capture implementation, drawing-spec root, runners and current validation state.

For a new chat/session:
1. run `run.cmd handoff`;
2. upload the generated `K01_AI_HANDOFF_CURRENT.zip`;
3. read `K01_START_HERE`;
4. read `control/drawings/K01_DRAWING_SYSTEM_CURRENT.json`;
5. only then open the generic engine/spec files named by the pointer.

Quick workstation check:

`RUN_K01_DRAWING_SYSTEM_STATUS_V1.cmd`

This command is discovery/status only; it does not mutate CAD.

## Capability boundary as of 2026-09-15

**Proven:** spec-driven views, dimensions/fits/tolerances, datum tags, supported GTols, TED boxes, controlled notes, semantic annotation names, source-hash invariance, PDF/BMP export, fail-closed binding ambiguity, candidate folder lifecycle, and preservation of OPEN items.

**Runtime-proven:** capture of view/annotation positions and replay of those positions on the next build. The workstation round trip was completed on K01-D-003 on 2026-09-16 with the placement profile applied on rebuild and the semantic build remaining PASS.

**Not yet generic/implemented:** leader-route capture/replay, collision detection/automatic layout optimization, graphical first-angle projection symbol, release-grade ISO 7200 title-block template binding, generic surface-finish authoring, generic modern ISO pattern modifiers beyond proven representations, and D8 automatic visual QA.

The API should own progressively more of presentation where deterministic behavior is proven. Human work is not defined as “everything visual”; the irreducible human responsibility is final D8 readability approval.

## Generic semantic core validation — 2026-09-16

The same `K01DrawingSystemV1.cs` engine has now passed workstation semantic builds for two deliberately different parts:

- K01-D-003 / P003: 3 views, 5 datums, 6 controlled dimensions, 2 controlled GTols, 4 TED boxes; OPEN product-definition items preserved.
- K01-D-006 / P007: 2 views, 2 datums, 9 controlled dimensions, 5 controlled GTols, 2 TED boxes, 1 surface finish; source CAD invariance PASS.

This closes the generic-semantic-core gate. Historical D006 part-specific scripts remain evidence/reference implementations, not the forward authoring path.

The next layer is `MARVILON_DRAWING_PRESENTATION_ENGINE_V1.md`. Presentation automation must be developed only after semantic PASS and must never silently alter controlled engineering meaning.


## K01 balance decision — 2026-09-16

The semantic core is validated on D003 and D006 and the placement roundtrip is runtime-proven. For K01, this is the automation baseline. Presentation automation beyond captured positions is experimental and non-blocking. The default production workflow is now:

`controlled Product Definition -> generic semantic build -> placement profile replay -> manual visual finish -> D8 human approval`.

Do not expand leader routing, collision optimization or automatic D8 checks merely to remove small manual layout work. Reopen that work only when repeated use shows that manual finishing is a material schedule/cost problem. Product closure has priority over presentation-tool polish.


## Stable control plane / file order

Routine navigation is no longer through timestamp candidate folders. The canonical control chain is:

1. `control/drawings/K01_DRAWING_SYSTEM_CURRENT.json`
2. `control/drawings/K01_DRAWING_REGISTRY_CURRENT.json`
3. `reports/control/K01_DRAWING_CONTROL_CURRENT.json`
4. `D:\Marvilon\K01\cad\drawings\current\<drawing_id>\` for the current working SLDDRW/PDF
5. `D:\Marvilon\K01\cad\drawings\candidates\<drawing_id>\...` for immutable evidence history only.

`RUN_K01_DRAWING_CONTROL_REFRESH_V1.cmd` rebuilds this projection without changing engineering authority. Center and new AI handoffs consume the same control projection. No candidate is deleted automatically.
