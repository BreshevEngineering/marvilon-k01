# K01 drawing pipeline D1-D9 — controlled architecture v2

Status: **CURRENT CONTROLLED ARCHITECTURE / IMPLEMENT INCREMENTALLY**
Scope: K01 release-native drawings. The existing V10 `PROJECTION_FALLBACK` drawing remains a **design-review semantic base**, not release-native proof.

## 1. Core split

The model/Product Definition owns **what is specified**. The drawing owns **how that specification is presented to manufacturing and inspection**. A released drawing may not become a second source of dimensional/tolerance/GD&T semantics.

Two lanes are explicit:

1. **Design-review lane (V10):** compiled Product Definition -> linked SLDDRW -> controlled Cxx fallback callouts -> visual review. Useful now; never satisfies release-native PMI provenance.
2. **Release-native lane (D1-D9):** controlled claim -> deterministic CAD binding -> model PMI/native annotation -> verified annotation view -> drawing import -> D7 provenance QA -> D8 visual QA -> D9 baseline.

The lanes may use the same linked SLDDRW structure, but their release meaning is different.

## 2. Why claim-level authoring is mandatory

A characteristic is not always one graphical annotation. C05 contains at least flange OD and flange thickness; these belong naturally to different annotation/drawing views. Therefore `drawing_authoring.targets[]` is claim-level. `annotation_view` as one field on C05 is insufficient.

Each target has at least:

- `claim_id`;
- `claim_paths` into controlled Product Definition;
- `carrier`;
- normalized `annotation_view_role` when applicable;
- `drawing_view_role`;
- `authoring_class`;
- `action`;
- optional existing PMI identity / semantic binding anchor;
- release eligibility.

A concrete SOLIDWORKS annotation-view name/orientation is evidence created/verified in D2/D3, not guessed from a string such as `Front`.

## 3. Variation semantics

`CONTROLLED` does **not** imply every claim has a plus/minus tolerance. Valid controlled variation semantics include fit, geometric tolerance, basic/reference dimensions and an explicitly controlled general-tolerance policy. Conversely, an OPEN tolerance cannot be replaced by a template default.

For current P007 this means, for example:

- C02 diameter/fit may be a controlled claim (`Ø14.10 H7`);
- C02 bore depth remains controlled nominal with OPEN variation and is not release-native until its variation semantics close;
- C05 flange OD nominal may exist while its release tolerance remains OPEN;
- no `±0.25` or legacy `±0.05` becomes authority.

## 4. D1-D9

### D1 — Authoring plan
Automatic. Consumes the drawing Product Definition slice, claim-level drawing-authoring context, parts registry and drawing-pipeline policy. Produces exact engineer tasks. It does not mutate CAD.

D1 fails structurally on duplicate claim IDs, unresolved claim paths, impossible target-view mapping, nonexistent part/requirement identity or inconsistent carrier class. It may still produce a valid plan while holding D2 release-native mutation because manufacturing route, binding signature, measurement condition or other release prerequisites remain OPEN.

### D2 — PMI authoring
Manual native CAD mutation, explicitly authorized. The engineer creates/repairs DimXpert/PMI/native annotations **from D1**, including annotation-view assignment. API is used for readback and verification, not as an assumption that every DimXpert construct can be authored robustly.

### D3 — Authoring verification and binding invariance
Automatic. Verifies characteristic/claim identity, values, variation semantics, datums/DRF, annotation-view assignment and unique geometry binding. Runtime face IDs are not authority.

Binding qualification:

- L1 save-close-reopen;
- L2 no-op `ForceRebuild3(false)` plus re-resolve by semantic/geometric signature;
- L3 benign perturb -> rebuild -> verify -> restore -> rebuild -> verify on a disposable candidate.

0 or >1 semantic matches => HOLD.

### D4 — Release-native drawing definition compile
This is narrower than S4C engineering Product Definition. D4 consumes S4C plus D3 evidence and produces the exact set of **proven model carriers** that a released drawing may project. Its fingerprint is the release-native drawing semantic fingerprint.

### D5 — Drawing generation/import
Automatic **only through a capability-qualified method**. For K01/SW2018, native drawing/model-view import options are the intended DimXpert transport when annotation-view orientation matches. The prior K01 Model Items/`InsertModelAnnotations3` experiment produced zero DimXpert annotations, so that API is not accepted as a proven DimXpert transport.

D5 may either:

- create a new drawing from an approved template; or
- preferably for K01/SW2018, copy/relink/refine an approved linked SLDDRW seed whose view/section structure is already proven.

D5 creates/retains deterministic views and sections, maps annotation-view roles to drawing views, imports proven model semantics, fills controlled properties and saves. It does not solve leader placement or readability.

### D6 — Human layout only
The engineer places leaders/annotations, resolves visual collisions and adjusts view placement. **Semantic content may not change.** D6 records semantic fingerprint before and after. A semantic delta stops the pipeline and opens EFR/change control.

### D7 — Semantic QA
Automatic and identity/provenance based. This is the principal release assurance step.

It verifies claim identity and provenance, not merely equality of printed numbers. A manually typed `±0.05` is not valid merely because another model tolerance also equals `0.05`.

Mandatory BLOCK checks include:

- all required release-native claims present exactly once (subject to controlled composite representation);
- no unregistered release-semantic annotations;
- no dangling annotations;
- no duplicate/contradictory claim representations;
- every released dimension has model variation semantics or an explicit controlled general-tolerance-policy reference;
- datum/DRF consistency;
- revision/effectivity consistency;
- title-block/material/part identity consistency;
- characteristic/inspection tags distinct from BOM balloon numbering;
- release tolerance/GD&T provenance is model-PMI/native-model based, not manually typed drawing text;
- annotation-view provenance matches D1/D3;
- D6 semantic fingerprint unchanged.

A missing general tolerance note or default surface finish is **not** automatically a warning: it is applicable only when such a policy is controlled upstream.

### D8 — Visual QA
Uses a **temporary preview export** from the post-D6 SLDDRW, so there is no D8<->D9 dependency cycle. Raster checks may detect clipping, obvious overlap and minimum text size; final readability approval is human.

### D9 — Export/baseline
Consumes D7 PASS + D8 PASS. PDF is normally required. DXF is conditional by part/delivery policy; it is not mandatory for every complex part. STEP AP242 with PMI is conditional on local capability/license and manufacturer/supplier acceptance. Final hashes/effectivity enter the baseline.

## 5. SOLIDWORKS 2018 constraint

For DimXpert drawings, annotation views are part of the design of the drawing pipeline. A drawing view imports the annotations associated with compatible annotation views/orientations. Section views can import from a selected annotation view. Therefore D1 must plan annotation-view role before D2.

K01 evidence also establishes a negative capability: generic Model Items / `InsertModelAnnotations3` is not accepted as the proven DimXpert transfer path after the zero-annotation V6 result. Do not retry that assumption without a bounded new capability proof.

## 6. Staleness

Freshness is graph-derived. At minimum:

- D1: drawing-slice state + authoring-context projection + parts registry + policy/tool identity;
- D3: D1 + native CAD/PMI state + D2 evidence + binding policy/tool identity;
- D4: S4C state + D3 verification + parts registry + compiler identity;
- D5: D4 + approved template/seed + parts registry + transport capability + generator identity;
- D7: D4 + post-D6 SLDDRW + QA rules/tool identity;
- D8: post-D6 SLDDRW/preview + visual-QA policy;
- D9: D7 + D8 + delivery profile/exporter identity.

Any input-state change stales only graph-declared consumers. No manual freshness override.

## 7. Current P007 implementation sequence

1. Keep V10 candidate as design-review base; do not rebuild it simply because D1-D9 is introduced.
2. Generate D1 from current Product Definition. It must expose exact release-native authoring tasks and blockers.
3. Resolve blocking manufacturing-route implications and capture missing deterministic binding signatures; do not invent them.
4. Build one release-native P007 exemplar manually **according to D1**, logging actual SOLIDWORKS annotation-view identities/orientations and import behavior.
5. Implement/run D7 and D3 against that exemplar before investing in generalized D5 automation.
6. Only after D3/D7 evidence, freeze the proven D5 method for SW2018 and automate it.
7. Add D8/D9 and then scale to other K01 parts.

The order deliberately puts semantic verification before further drawing-generation optimization.

## 8. Center requirements

Center must expose D1-D9 as a dependency chain, not a checklist. For every claim show: requirement allocation -> decision/derived inputs -> Product Definition claim -> datum/measurement/inspection context -> CAD binding -> PMI/annotation view -> D3 invariance -> D4 fingerprint -> D5 drawing carrier -> D7/D8 -> D9 baseline.

`Why stale?` must traverse graph edges and display the changed input fingerprint. A drawing must become stale automatically when its declared semantic/template/registry/method input changes.

## V13 drawing-family planning layer

A reusable drawing-family plan is now a controlled presentation layer consumed by D1. It is **not** a new product-definition authority.

For family `ROTATIONAL_FLANGED_HOLLOW` the default view algorithm is:

1. significant coaxial internal geometry -> primary `AXIAL_FULL_SECTION`;
2. flange / non-axisymmetric end features -> required `FLANGE_END`;
3. isometric -> optional form-comprehension view only;
4. redundant `AXIAL_EXTERNAL` is omitted unless an external-only controlled claim requires it.

Claim routing is deterministic but semantic-neutral: already-controlled Product Characteristics are routed to preferred drawing roles; geometry never invents a dimension, tolerance, datum, GD&T or surface requirement.

D2 authoring order is controlled as `DATUM/DRF -> SIZE/FIT -> LOCATION/PATTERN -> GD&T -> SURFACE -> MATERIAL/PROCESS` so dependent GD&T is not authored before its reference datum system exists.

Standards basis for representation/presentation is the controlled profile (`ISO 128-3:2022`, `ISO 129-1:2018`, `ISO 5456-2:1996`, `ISO 5455:1979`).

## V15 first-exemplar D3/D7 assurance

V15 activates machine verification on the existing V12 P007/D006 exemplar; it does not create a new drawing.

**D3 current bounded scope:** C01 Datum A, C02 Ø14.10 H7 and C09 material identity/readback; actual SOLIDWORKS annotation-view identity; semantic/geometric binding; L1 save-close-reopen; L2 `ForceRebuild3(false)`; source SHA invariance. L3 perturb/restore is intentionally HOLD for release until a real benign P007 parameter, allowed delta and restore acceptance are controlled. No guessed perturbation is permitted.

**D7 current bounded scope:** the saved exemplar must contain exactly the authorized visible C01/C02 release-native semantics for this scope; unauthorized C05/other release semantics, dangling annotations, non-DimXpert/manual drawing dimensions, display/unit overrides, stale V10 fallback notes, non-MMGS units, non-ISO drafting standard, non-first-angle projection or non-A3 sheet block exemplar QA. C09 material is read from the model; title-block presentation remains a D8/manual or controlled property-link concern until normalized.

A V15 exemplar PASS is explicitly **not manufacturing release**. Full release still requires D3 L3, configuration/effectivity, all Product Definition release claims, D6 pre/post semantic-fingerprint control, D8 visual approval and D9 baseline. D7 findings are corrected on the same exemplar if presentation-only; semantic changes return upstream through EFR/change control.

## V16 operational drawing algorithm

The reusable engineer-facing execution algorithm is frozen in `docs/architecture/K01_DRAWING_AUTHORING_ALGORITHM_ISO_GPS_v1.md`. It is an operationalization of D1-D9, not a separate authority or lifecycle.

D006 established the working boundary: close Product Definition first; automate deterministic semantic projection and verification; perform D6 visual layout manually; then run D7/D8 before D9. CAD-version compatibility representations (for example ISO 5458 `CZ` in SW2018) must be explicitly declared and may never silently change the upstream GPS meaning.
