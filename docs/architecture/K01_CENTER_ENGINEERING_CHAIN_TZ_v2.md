# K01 Center — Engineering Chain Control TZ v2

## Objective

The Center must make the lifecycle and dependency state visible without becoming a second engineering authority.

## Required top-level status

Show only:

- current checkpoint / configuration baseline;
- active engineering entity/change;
- current lifecycle stage/gates;
- top release blockers;
- exact next action;
- graph freshness summary.

## Requirement / allocation panel

For every requirement show:

- requirement ID/revision/status/source;
- allocation ID(s);
- target system/subsystem/interface/part/Cxx;
- allocation type and share/budget/complementary responsibility;
- unallocated/open responsibility warning;
- affected downstream nodes.

Equal numeric values must never be grouped as one requirement without shared identity.

## Derived-input panel

Show separately from requirements:

- derived-input ID;
- quantity kind;
- value/unit;
- derivation/source chain;
- requirement/assumption links;
- status (`CONTROLLED`, `SCREENING_ONLY`, `ORIGIN_OPEN`, etc.);
- consumers;
- release-authority flag.

The two current 300 N values must render as separate rows with different quantity kinds.

## Product Characteristic panel

For each Cxx show:

- characteristic ID + revision/effectivity;
- function;
- requirement allocations;
- derived inputs;
- nominal/requirement;
- tolerance/fit/GD&T;
- datum/reference system;
- measurement condition (temperature/state/fixture/force as applicable);
- material/surface/process;
- manufacturing route/capability;
- inspection strategy/capability;
- CAD binding;
- binding-invariance level/status;
- PMI/MBD state;
- drawing projection state;
- release blocker.

## Datum/reference-system view

Provide a dedicated interface datum view. Show J1 A/B/C authority from EDR-023 and J2 current A/B system with tertiary/DRF OPEN where not closed. Do not infer a datum from fastener geometry merely because CAD mates exist.

## Analysis split

Display two independent evidence families:

1. `PHYSICS / BEHAVIOR` — strength, thermal, magnetic, flow, contact, etc.;
2. `VARIATION / CAPABILITY` — tolerance stacks, process capability, measurement/inspectability.

Each family shows its own consumed fingerprint and why it became stale.

## Manufacturing/supplier view

For P007 show route alternatives, current selection state, supplier/process capability evidence, inspectability, cost/lead-time evidence if available, and which characteristics are blocked by route uncertainty.

## Configuration/effectivity view

For requirement/allocation/characteristic/CAD/process/drawing/inspection artifacts show revision/effectivity and predecessor/successor relation. As-built/as-inspected records must pin the released definition fingerprint used.

## Feedback loop view

EFR records are first-class Center objects. For each show:

- source stage/artifact;
- affected entities/Cxx;
- finding/severity;
- required upstream stage to reopen;
- linked EDR/change record;
- impact plan;
- status.

The Center must never offer a direct "fix characteristic" action from a downstream finding.

## Freshness / impact

Use authoritative MEDTAS graph v2.2 and domain slices. `Why stale?` must display the shortest causal path, for example:

`P007 measurement condition changed -> variation slice changed -> tolerance analysis stale -> release HOLD`

or

`P007 drawing layout changed -> visual QA stale only`.

## Prohibited behavior

- no duplicated requirement or characteristic database;
- no manual PASS override of graph freshness;
- no implicit OPEN -> value conversion;
- no automatic counterpart-part mutation;
- no grouping by equal numeric value;
- no release based only on drawing/PDF presence.


## Domain projection / minimum invalidation diagnostics

Center must show the context subdomain that actually changed (`DATUM`, `MEASUREMENT`, `INSPECTION`, `MANUFACTURING`, `BINDING`, `CONFIGURATION`) and the resulting Product Definition slice(s). It must not explain every change as "Product Definition changed".

For each stale node show both:

- changed source projection/hash;
- shortest graph path to the stale consumer.

Example expected behavior: an `inspection_strategy` change may stale inspection and variation/capability nodes while leaving `K01.DRAWING.D006.PROJECTION` and physics nodes fresh.

## Drawing D1-D9 panel / release-native lane

Center must display the V10 design-review lane and the release-native D1-D9 lane separately. A green V10 semantic-projection state must never be rendered as release-native drawing readiness.

For `K01-D-006`, show a compact D1-D9 chain with dependency status and evidence links:

- **D1 Authoring Plan:** plan fingerprint, claim count, target annotation-view roles, binding anchors, D2 blockers.
- **D2 PMI Authoring:** mutation authorization, model candidate identity, engineer, actual SOLIDWORKS annotation-view identities/orientations, authoring evidence.
- **D3 Authoring Verify:** per-claim semantic match, datum/DRF match, annotation-view match, binding-invariance level/result.
- **D4 Native Definition:** release-native drawing semantic fingerprint and list of proven model carriers.
- **D5 Drawing Import:** template/seed hash, transport method/capability evidence, imported claim identities/counts.
- **D6 Layout:** pre/post semantic fingerprint; any semantic delta is HOLD/EFR.
- **D7 Semantic QA:** DQA-001...DQA-016 results with claim/provenance links.
- **D8 Visual QA:** preview/raster evidence, overlap/clipping diagnostics, human approval.
- **D9 Export/Baseline:** required delivery formats, recipient capability/acceptance, hashes/effectivity.

Center must render claim-level mapping, not only characteristic-level mapping. Example: `C05.FLANGE_OD -> AV_FLANGE_END` and `C05.FLANGE_THICKNESS -> AV_J2_LONGITUDINAL`.

`Why blocked?` for D2/D9 must distinguish stage ownership. An OPEN STEP AP242 recipient-acceptance field may block D9 delivery optimization while not falsely blocking safe D2 PMI work; an OPEN manufacturing route can block process-dependent D2/release semantics.

The Center must expose the current drawing-pipeline authority and drawing-delivery capability as read-only control sources. It must not infer that `InsertModelAnnotations3` is a proven DimXpert transport in SW2018; transport status comes from registered capability/exemplar evidence.

## V12 manual exemplar lane

Center must distinguish three states for K01-D-006:

1. **V10 DESIGN-REVIEW BASE** — compiled fallback semantics, editable SLDDRW, not native release PMI.
2. **V12 MANUAL EXEMPLAR** — dedicated linked part/drawing copies; claim-scoped D2 authoring, actual annotation-view/import/layout evidence, visual QA.
3. **D1–D9 RELEASE-NATIVE** — full D3/D4/D7/D8/D9 evidence required.

The Center must show `d2_authorizable_claim_ids` separately from release blockers. An OPEN manufacturing route must not blanket-block route-independent claims. For every claim show `manufacturing_route_dependency`, D2 eligibility, actual annotation-view identity when captured, and the reason for any HOLD.

The exemplar panel must expose direct links to the workspace part, workspace SLDDRW, PDF/BMP, D1 plan, workpack, capture report, and source-invariance hashes. It must label the exemplar `NOT RELEASED`.

## V13 Drawing Family / View Plan panel

For every part/drawing pair Center shall show the reusable presentation classification separately from Product Definition:

- Drawing family ID and classifier evidence;
- required/optional/omitted view roles;
- claim -> engineering role -> preferred drawing view mapping;
- D2 authoring order class/order;
- whether a view is present because of controlled semantics or only for form comprehension;
- family-plan fingerprint and freshness;
- learned exemplar rules / exceptions;
- explicit warning: family/view routing is not semantic authority and cannot create tolerances or GD&T.

For `K01-P-007 / K01-D-006` current family is `ROTATIONAL_FLANGED_HOLLOW`; primary view is axial full section, secondary is flange end, isometric is auxiliary, and the redundant external longitudinal view is omitted unless a later controlled claim requires it.

## V14 whole-project engineering-domain coverage matrix

The Center must render `control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json` and `reports/control/K01_ENGINEERING_SYSTEM_COVERAGE_CURRENT.json` as a first-class matrix. This prevents the UI from narrowing the project to the currently active drawing/CAD task.

Required rows include at minimum: Requirements/Allocation, Derived Inputs, Product Definition, CAD/MBD Binding, Drawing D1-D9, Tolerance/Variation, Structural FEA, CalculiX/CCX, FEMM, Flow/CFD, Thermal, Pressure/Vacuum/Containment, Materials/Joining/Manufacturing, EBOM, MBOM, Inspection/Metrology, Configuration/Release and Repo/Handoff/Toolchain.

For each row show:

- coverage state (`COVERED`, `DECLARED_OPEN_GAP`, `BLOCKED_COVERAGE`, etc.);
- authority/evidence path;
- graph node(s);
- current runtime solver/verification state where applicable;
- release relevance;
- declared gap/action;
- shortest stale/impact path.

Do not convert `PASS_ENGINEERING_SYSTEM_COVERAGE__DECLARED_GAPS` into a green release status. It means the architecture has accounted for the gap, not that the engineering work is closed.

CalculiX must be displayed as `CalculiX / CCX`; FEMM as `FEMM`. EBOM and MBOM must remain separate rows. Structural, magnetic, flow, thermal and pressure/vacuum evidence must remain separate physics families.

## V15 D3 / D7 exemplar assurance panel

Center must show D3 and D7 as separate derived verification nodes on the existing V12 exemplar. D3 shall display C01/C02/C09 claim identity, actual annotation-view identity, geometry-binding signature, L1/L2 status and explicit L3 `PENDING_RECIPE` release blocker. D7 shall display every DQA code, counts of authorized/unauthorized visible semantics, dangling/manual dimensions, display/unit overrides, fallback-note count and MMGS/ISO/FIRST_ANGLE/A3 environment state.

A green `PASS_D3_EXEMPLAR_L1_L2` or `PASS_D7_EXEMPLAR_SCOPE` must carry a visible `NOT RELEASED / BOUNDED EXEMPLAR SCOPE` badge. The Center must link directly to the exact V12 workspace part/drawing and D3/D7 evidence. If D7 is HOLD, show the machine defect list as the only permitted manual correction scope; if the correction needs semantic change, route to EFR rather than editing the drawing.
