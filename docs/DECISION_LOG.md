# Decision log

Use one entry per meaningful engineering decision.

## Template
### DEC-YYYY-NNN — Title
- Date:
- Status: PROPOSED / ACCEPTED / SUPERSEDED / REJECTED
- Context:
- Options:
- Decision:
- Evidence:
- Consequences:
- Supersedes:
## EDR-023 — J1 Datum C kinematic implementation baseline
- Date: 2026-09-09
- Status: ACCEPTED / ASSEMBLY QA PASS / PENDING CANONICAL PROMOTION
- Context: A+B already establish axial/transverse location; C must constrain only rotation about B without redundant radial location.
- Decision: use the later Gate04B v7/serviceable-joint implementation — relieved/diamond P017 in P003 Ø3.02 round hole. The relieved pin preserves radial freedom while its major width controls tangential clocking.
- Evidence: `reports/cad/current/K01_GATE04B_DATUM_C_BUILD.json`, `spec/K01_SERVICEABLE_JOINT_ARCHITECTURE_v3.json`, `docs/K01_MANUFACTURING_ASSEMBLY_ROUTER_v1.md`.
- Consequence: earlier radial-slot implementation text is superseded; A/B/C hierarchy and clamp-only-fastener rule remain. Canonical promotion is blocked until candidate A001 assembly QA passes.

## K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED
- Date: 2026-09-10
- Type: CP-C candidate-integration checkpoint.
- Result: Gate04B producer PASS + candidate A001 Assembly-QA PASS.
- Evidence: 14 modeled occurrences; P003/P016/P017 fully constrained; 0 active mate errors; P017 signed depth/protrusion 4/2 mm; moving group PASS; 0 unexpected IN/MID/OUT interference; verification SHA-256 `48763f29e18a7a699aab203ee695b9adc29760203c1e39aa33a313a5e23c7a12`.
- Authority: verified candidate, not canonical.
- Next: controlled canonical promotion -> canonical snapshot -> dependency/stale reduction -> EBOM/MBOM refresh.

## CHG-K01-BASELINE-02C-PROMOTION-001
- Date: 2026-09-10
- Status: PREPARED / PREFLIGHT REQUIRED / NO CAD WRITE YET.
- Toolchain review: supplied `tools/sw_gate04b_close_datum_c.py` is the obsolete radial-slot candidate builder and is prohibited for current EDR-023. `final_assembly_promotion_v2_2.py` is the separate final-candidate/R01 Pack-and-Go route. Review the existing atomic stable-promotion precedent `scripts/K01_PROMOTE_P003_P007.py` before adapting/reusing it.
- Release: this promotion updates engineering baseline authority only; it does not release R01 or close P1-P5 product-release blockers.

## CHG-K01-D006-AUTOMATION-FIRST-DIMXPERT-BRIDGE-001
- Date: 2026-09-11
- Status: ACCEPTED / EXECUTION AUTHORIZED / RELEASE NOT GRANTED.
- Context: The existing linked K01-D-006 refinement path successfully created a timestamped structural candidate with four views and exports, but the native DimXpert verifier returned `DIMXPERT_COUNT=0`, `C02=False`, `C05=False`. Rebuilding the drawing manually would break the intended digital-thread workflow and duplicate prior work.
- Decision: preserve the existing linked SLDDRW and keep the workflow automation-first. API owns candidate copying, view/section/scale/position refinement, cleanup, export, invariance and semantic verification. For the SW2018-only native DimXpert import gap, a narrow Windows UI Automation compatibility bridge is authorized to toggle only the native Drawing View import controls on a timestamped copy. Human work is limited to the final 10–20% visual last mile or an explicitly authorized fallback after bridge diagnostics.
- Safety/authority boundary: no overwrite of canonical P007 or source drawing; Design annotations OFF; no typed C02/C05 duplicates; exact C02=`Cylinder1/Diameter2` and C05=`Cylinder2/Diameter4` verification required; `DIMXPERT_COUNT=0` is HOLD; OPEN tolerances remain OPEN.
- Evidence: `reports/control/K01_D006_REFINED_EXISTING_CURRENT.json`; `reports/control/K01_D006_IMPORTED_PMI_VERIFY_CURRENT.json`; `reports/control/K01_P007_PMI_PROVEN_CURRENT.json`; `control/drawings/K01_DRAWING_ARCHITECTURE_CURRENT.json`.
- Consequence: the older `MANUAL_NATIVE_DIMXPERT_TRANSFER_AND_PROFESSIONAL_LAYOUT` stage wording is superseded as the default execution path. Manual full drawing rebuild is prohibited while the linked drawing seed remains valid.

## CHG-K01-D006-DIRECT-ASSOCIATIVE-DRAWING-PROJECTION-002
- Date: 2026-09-12
- Status: ACCEPTED / DEADLINE FALLBACK / RELEASE NOT GRANTED.
- Context: SW2018 native DimXpert authoring and persistence are proven, and C02/C05 semantics can be authored automatically, but repeated attempts to automate the Drawing View PropertyManager import surface did not expose usable controls to UI Automation. The failure is in the transfer UI surface, not in product geometry or PMI authoring.
- Decision: stop spending iterations on SW2018 UI automation. Keep native model PMI as semantic authority, but derive the 2D base drawing through native associative drawing reference dimensions created directly from the same controlled model entities/persistent bindings. Use `IView.SelectEntity` / corresponding model geometry plus native drawing dimension APIs. No general tolerance is invented: C02 is H7; C05/C06/C07/C08/blind-end remain nominal-only with release tolerance OPEN; C04 position tolerance remains OPEN.
- Engineering boundary: this is a compatibility projection for a usable drawing base, not a semantic downgrade and not release authority. Exact characteristic values are machine-checked against the controlled authoring profile; source drawing and part stay hash-invariant. Human work is limited to the final visual arrangement and any dimensions that the API cannot associate in one pass.
- Evidence basis: SOLIDWORKS 2018 API supports selecting model entities in drawing views and adding associative/reference dimensions; the existing K01 pipeline already proves persistent-reference recovery, linked drawing copies, reference-safe migration, section/views, PDF/BMP export and source-hash invariance.
- Supersedes for execution: repeated UI-Automation attempts for the SW2018 DimXpert-import PropertyManager. The native DimXpert model pipeline itself is retained.

## 2026-09-12 — Freeze Product Definition before further K01-D-006 drawing mechanics

**Decision:** stop iterating drawing-transfer mechanics after two bounded dead ends: SW2018 Drawing View PropertyManager UI Automation did not expose the required DimXpert controls, and direct drawing-entity dimensioning V7 produced 0/8 controlled dimensions. Preserve the proven linked-drawing structural refinement capability, but move the active gate upstream to Product Definition.

**Reason:** the drawing must not become a second design authority. P007 already contains controlled nominals, partial fit/PMI evidence and explicit OPEN release items, while legacy `candidate_spec` strings still contain stale numeric tolerances/GD&T (`±0.05`, flatness/perpendicularity/position candidates). Continuing drawing automation without a compiled authority contract risks reintroducing stale/default values.

**New mandatory chain:** requirement/interface → engineering decision/calculation/technical filter → stable Cxx characteristic → compiled Product Definition fingerprint → CAD binding/native PMI → drawing projection → inspection → release.

**Controls added:** `K01_PRODUCT_DEFINITION_POLICY_v2_0.json`, `K01_P007_DEFINITION_DECISIONS_CURRENT.json`, `K01_ENGINEERING_EXECUTION_CONTRACT_v1.json`, `K01_EXECUTION_METHOD_REGISTRY_CURRENT.json`, `RUN_K01_PRODUCT_DEFINITION_GUARD_V8.cmd` and Center Product Definition TZ.

**Execution rule:** a method pivot must update strategy/next-action/decision/method registry and acceptance gate in the same patch. Two failures of the same mechanism trigger architecture review; rejected mechanisms are not retried under new names without new evidence.

## 2026-09-12 — V9 authoritative change propagation / no manual stale-state authority

**Decision:** freeze one engineering execution chain and make the MEDTAS hash-DAG the sole transitive freshness/rebuild topology. Product Definition V8 is integrated as `K01.PD.P007.COMPILED`; D006 projection is represented as downstream node `K01.DRAWING.D006.PROJECTION`.

**Reason:** V6/V7 showed that correct local engineering work can drift sideways when stage boundaries and downstream invalidation are advisory rather than executable. A part/interface change must automatically invalidate every declared consumer while avoiding unsafe automatic redesign of counterpart parts.

**Rules:**
- Class A/B work runs pre-change impact analysis before write.
- Shared-interface changes mark all participants `COUNTERPART_REVIEW_REQUIRED`; counterpart CAD is never silently edited.
- A derived node becomes STALE when its consumed state fingerprint changes; manual status edits cannot restore PASS.
- Rebuild/reverification follows topological order.
- `K01_DEPENDENCY_STATE.json` and `control/system/K01_DEPENDENCY_GRAPH_v2.json` remain legacy compatibility views only; new decisions use Authority Map → MEDTAS engineering build graph.
- Drawing/inspection consume compiled Product Definition; visual drawing edits cannot create product semantics.

**Center requirement:** render changed entity/domain, counterpart review, reason path, stale/drift state, topological rebuild order and `Why stale?` without becoming an authority. See `docs/architecture/K01_CENTER_CHANGE_IMPACT_TZ_v1.md`.

## 2026-09-12 — D006 V10 compiled-definition projection compiler

**Decision:** After V9 dependency propagation PASS, K01-D-006 drawing work proceeds through `K01.DRAWING.D006.PROJECTION` using the compiled P007 Product Definition fingerprint as the only dimensional/semantic source. Existing linked SLDDRW is reused. The rejected SW2018 DimXpert PropertyManager UI-Automation path and V7 drawing-entity auto-dimension path are not retried.

**Design-review carrier policy:** If an already-proven native drawing carrier is unavailable in the bounded SW2018 path, a `PROJECTION_FALLBACK` callout generated from the compiled Product Definition is permitted in the editable base drawing. Every fallback is tied to Cxx and the compiled-definition fingerprint. It cannot be treated as released dimensional/GD&T authority.

**Acceptance:** all `safe_projection_ids` must read back in the V10 candidate; source drawing seed remains hash-invariant; SLDDRW/PDF/BMP are produced; semantic projection is PASS; human visual QA remains PENDING; `DRAWING_RELEASE_READY=HOLD` remains authoritative until Product Definition blockers close.

**Reason:** the deadline needs a usable, editable engineering base drawing without reintroducing ungoverned manual semantics or repeating failed SW2018 transfer mechanisms. This separates semantic completeness from final visual polish while preserving the full Requirement → Decision → Characteristic → Product Definition → Drawing → Inspection chain.


## 2026-09-12 — V11 executable engineering lifecycle: allocation, derived inputs, feedback and domain-slice invalidation

**Decision:** supersede the simplified one-way Requirement → Decision → Characteristic → Drawing chain with an executable lifecycle that explicitly represents requirement allocation, derived engineering inputs, datum/reference systems, measurement conditions, manufacturing/supplier feasibility, configuration/effectivity, binding invariance and controlled downstream-to-upstream feedback.

**Reason:** the previous chain could not distinguish system requirements from part responsibility, could confuse equal-valued but physically different quantities (notably the independent 300 N service normal-force and 300 N/screw preload screening inputs), and did not encode how manufacturability/inspectability/analysis failures reopen engineering decisions. It also treated save/reopen PMI persistence as too close to binding correctness and combined physics with variation/capability evidence.

**Current lifecycle:** S0 requirement/interface → S0A allocation → S1 decision/technical filter → S1A derived inputs + S1B manufacturing/supply strategy → S2 Product Characteristic with datum/measurement/inspection/configuration context → S3 deterministic CAD/PMI binding + invariance qualification → S4A physics and S4B variation/capability → S4C compiled Product Definition with domain fingerprints → S5 drawing projection/semantic+visual QA → S6 inspection realization → S7 released configuration/effectivity. Downstream defects return through EFR/change control; they never silently mutate upstream Product Definition.

**Invalidation rule:** consumers bind to the narrowest sufficient Product Definition slice (drawing, variation, inspection, physics, manufacturing, configuration). A change in one domain invalidates only declared consumers plus graph-connected shared-interface counterparts; automatic stale propagation is allowed, automatic counterpart redesign is prohibited.

**Drawing consequence:** V10 semantic base remains valid only against the V11 drawing-slice fingerprint. Changes that do not alter the drawing slice do not force drawing regeneration merely because another domain (for example supplier capability) changed.

**Center consequence:** Center must render allocation, derived-input identity/derivation, datum/measurement/inspection context, manufacturing route, configuration/effectivity, feedback records, domain fingerprints and `Why stale?`, while remaining a non-authority projection of control records. See `docs/architecture/K01_CENTER_ENGINEERING_CHAIN_TZ_v2.md`.

## 2026-09-12 — D1-D9 drawing pipeline separated from V10 design-review projection

- Adopt claim-level D1-D9 release-native drawing pipeline. Model/Product Definition owns semantic content; drawing owns presentation.
- Preserve V10 9/9 fallback projection as design-review base only; it cannot satisfy release-native PMI provenance.
- D2 PMI authoring is manual from D1; D3 verifies semantic identity, annotation-view mapping and binding invariance.
- D5 automation is deferred until one P007 release-native exemplar proves the SW2018 transport. `InsertModelAnnotations3` is not treated as proven DimXpert transport after prior zero-annotation evidence.
- D6 is layout-only with semantic pre/post fingerprint invariance. D7 is provenance-based and rejects manually typed release tolerance/GD&T.
- General tolerances/default roughness, DXF and STEP AP242 PMI are conditional controlled policies/capabilities, not defaults.
- Engineering graph authority advances to v2_2 with first-class drawing-pipeline policy, delivery capability and D1 plan node.


## 2026-09-12 — V12 claim-scoped D2 authorization and manual P007/D006 exemplar lane

**Decision:** replace the coarse D1 rule “P007 manufacturing route OPEN blocks all D2 PMI mutation” with claim-scoped authorization. Route-independent `CONTROLLED_CLAIM` items with deterministic binding may be authored/verified on a dedicated exemplar candidate while route/process/capability-dependent claims and all release gates remain HOLD.

**Current authorized exemplar scope:** `C01.DATUM_A`, `C02.DIAMETER_FIT`, `C09.MATERIAL`. C05 and all route/process-dependent claims are not authorized for new semantic authoring; pre-existing C05 `tolerance NONE` may be observed as diagnostic design-review support only.

**Exemplar lane:** preserve the successful V10 linked design-review base, create timestamped P007/D006 working copies, reference-safe relink the drawing to the copied P007, perform only the D1-authorized manual PMI/annotation-view work and human layout, then capture model/drawing semantic evidence and refreshed PDF/BMP. Canonical/proven sources are SHA-guarded and never overwritten.

**Reason:** the uploaded D1–D9 pipeline specification correctly makes manual PMI authorship and annotation-view planning precede automated release-native generation. However, its release prerequisite on manufacturing route must not be misapplied as a blanket blocker to a non-release exemplar or to route-independent controlled claims. The exemplar is explicitly not D3/D7/release PASS; it is empirical SW2018 evidence used to implement D3/D7 and later D5 without another speculative API loop.

**Control consequence:** Center/session/handoff must distinguish V10 design-review base, V12 manual exemplar and D1–D9 release-native lane. D2 eligibility is displayed per claim with its manufacturing-route dependency and reason.

## 2026-09-13 — V15 D3/D7 assurance on the first P007/D006 exemplar

**Decision:** stop drawing-generator iteration after V12 native transport and V13 family-plan proof. The existing V12 exemplar is the single controlled subject for D3 model-PMI/binding verification and D7 drawing semantic/provenance QA. No new D006 is created for this stage.

**D3 bounded implementation:** verify C01 Datum A, C02 Ø14.10 H7, C09 material, actual annotation-view identity, semantic/geometric face binding, L1 save/reopen, L2 `ForceRebuild3(false)` and source-file SHA invariance. L3 perturb/restore is deliberately not guessed; manufacturing-release D3 remains HOLD until a controlled benign P007 parameter, delta and restore acceptance are defined and pass.

**D7 bounded implementation:** verify the saved exemplar contains the authorized visible C01/C02 semantics exactly once, rejects visible unauthorized C05/other release semantics, dangling/manual/overridden dimensions and stale V10 fallback notes, and enforces MMGS / ISO / FIRST_ANGLE / A3 environment. C09 is verified from model material. Configuration/effectivity and D6 pre/post semantic fingerprint remain explicit release-only OPEN items for this legacy first exemplar.

**Correction rule:** D7 presentation defects are corrected on the same V12 SLDDRW. Any correction requiring a Product Definition semantic change returns upstream through EFR/change control. A V15 exemplar PASS is not manufacturing release and cannot close the 18 upstream Product Definition blockers, D3 L3, D8 or D9.

**System consequence:** graph authority advances to v2_5 with first-class D3 and D7 nodes; whole-project V14 domain coverage remains active so FEMM, CalculiX/CCX, Flow, Thermal, Containment, EBOM/MBOM and inspection cannot disappear while drawing assurance is the active task.
