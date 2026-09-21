# K01 Center — Assurance Coherence / Anti-Regression TZ v3

## 1. Purpose

Center is not only a viewer of engineering status. It must act as a **read-only coherence supervisor** over the digital thread so that a local PASS cannot coexist silently with a broken authority/provenance/dependency chain.

Center remains **NOT an engineering authority**. Engineering acceptance stays in controlled requirements, Product Definition, CAD/MBD, analysis and D1-D9 gates. Center verifies that those layers agree about identity, fingerprints, scope and sequencing.

The failure mode this specification eliminates is: each local check is technically correct, while the system as a whole is inconsistent.

## 2. Mandatory model

Every controlled engineering action is represented by five linked layers:

`AUTHORITY -> EXECUTOR -> EVIDENCE -> DEPENDENCY STATE -> PRESENTATION/ACTION`

A stage action is enabled only if all five layers are coherent for the exact revision/effectivity/fingerprint being acted on.

For every layer Center displays:
- object/node ID;
- schema/revision;
- source path;
- SHA/fingerprint;
- generated time;
- predecessor fingerprints;
- scope (`SCREENING`, `EXEMPLAR`, `RELEASE`);
- freshness;
- evidence links.

## 3. New global gate: ASSURANCE COHERENCE

The home screen shall show a permanent card:

`ASSURANCE COHERENCE: PASS | HOLD`

It is independent from Product Definition, D3, D7, FEMM, structural, BOM, etc. It does not replace those gates.

If coherence is HOLD:
- all mutation buttons are disabled;
- all stage-transition buttons are disabled;
- read-only inspection, artifact opening and diagnostics remain enabled;
- Center displays the exact failing ACI checks and shortest repair path.

Initial machine checks:

- `ACI-001 D1_WORKSPACE_PROVENANCE_PIN` — current artifact/exemplar is interpreted against the exact plan fingerprint pinned when it was created, or an explicit requalification record exists.
- `ACI-002 AUTHORITY_EXECUTOR_BINDING_CONTRACT` — verifier/executor implements the controlled binding semantics; no positional heuristic may silently replace persistent/composite identity.
- `ACI-003 ANNOTATION_VIEW_ROLE_CONTRACT` — normalized Product Definition/D1 view role is mapped to and verified against real SOLIDWORKS orientation identity; non-empty view name is insufficient.
- `ACI-004 GRAPH_DERIVED_STATE_PARITY` — every node of the current graph authority is materialized in current derived state or explicitly declared not materializable.
- `ACI-005 LEGACY_DEPENDENCY_STATE_QUARANTINE` — old dependency snapshots cannot be mixed with current MEDTAS state without an explicit legacy/quarantine flag.
- `ACI-006 STAGE_TRANSITION_CONTRACT` — UI next action and command enablement use the full gate predicate, never a subset such as L1/L2 when D3 PASS is required.
- `ACI-007 HANDOFF_RUNTIME_EVIDENCE_CLOSURE` — evidence referenced by a current report is either packed in handoff or hash-indexed in omitted evidence.

## 4. Fingerprint pinning — mandatory

No artifact may be evaluated only against `*_CURRENT` inputs.

At creation time every candidate/exemplar/release artifact receives a manifest with:
- input authority fingerprints;
- plan fingerprint;
- Product Definition fingerprint;
- CAD source SHA;
- configuration/effectivity;
- executor version/SHA;
- capability-registry version;
- graph version.

Later verification must first compare current inputs with the pinned manifest.

If they differ, Center shall show:

`HOLD_INPUT_DRIFT — REQUALIFICATION REQUIRED`

The user may then choose a controlled requalification workflow. Center must never silently reinterpret an old artifact through a new `CURRENT` plan.

## 5. Contract compilation instead of duplicated rules

Where practical, verifiers must consume or be generated from machine-readable authority contracts.

Examples:
- C01 binding type/entity set comes from Product Definition contract;
- annotation-view role comes from D1 contract;
- accepted material aliases come from material authority;
- expected units/standard/projection/sheet come from drawing environment contract.

Hard-coded engineering semantics inside C#/Python verifiers are prohibited unless the hard-coded value is itself a versioned capability/implementation invariant and is tested against authority fixtures.

Every verifier shall publish `consumed_authority[]` with path + SHA + object IDs.

## 6. Scope-safe PASS model

Center shall not render a generic green PASS.

Every PASS has a scope badge:
- `METHOD PASS`;
- `SCREENING PASS`;
- `EXEMPLAR PASS`;
- `RELEASE PASS`.

Examples:
- `PASS_D3_EXEMPLAR_L1_L2 / RELEASE HOLD: L3` is never shown as drawing release ready.
- `PASS_ENGINEERING_SYSTEM_COVERAGE__DECLARED_GAPS` means architecture coverage only.

A parent gate may become PASS only from an explicit aggregation contract; text matching on strings containing `PASS` is prohibited.

## 7. Cross-layer contradiction detector

Center shall continuously detect contradictions such as:
- Product Definition says composite face set; verifier expects one face;
- workspace pins D1 SHA A; current verifier consumes D1 SHA B;
- graph v2.5 has 95 nodes; derived state has 84;
- dependency snapshot predates current graph and omits active nodes;
- control report says D7 may run after L1/L2 while executable D7 requires D3 PASS;
- report references evidence missing from handoff;
- material shown as controlled while actual alias only partially matches the controlled grade;
- `OPEN` in authority appears as a numeric value downstream;
- same ID resolves to different effective definitions.

Contradiction state is always `HOLD_COHERENCE`; Center does not select a winner.

## 8. Preflight before every write

Every mutation command exposed by Center must execute this sequence:

1. refresh current authority fingerprints;
2. run Assurance Coherence;
3. run dependency/freshness evaluation;
4. run technical filter;
5. show change impact;
6. verify rollback snapshot target;
7. verify exact command/executor SHA;
8. only then enable mutation.

Any mismatch after the preview invalidates authorization and requires a new preflight.

## 9. Post-run transaction closure

A command is not considered complete when its process exits 0.

Center waits for a transaction closure record proving:
- expected output artifacts exist;
- output hashes recorded;
- graph/derived state refreshed;
- all affected downstream nodes are FRESH/STALE as expected;
- handoff required sources/evidence updated;
- source/CAD write boundary respected;
- no undeclared side effects occurred.

Only then does Center expose the next stage action.

## 10. D1-D9 lane requirements

For each D1-D9 stage show:
- gate predicate;
- consumed authority fingerprints;
- produced evidence fingerprints;
- stage owner;
- scope;
- predecessor status;
- downstream invalidation path;
- exact runnable command;
- whether command is currently enabled and why.

D7 cannot become runnable from `L1=True && L2=True`; it is runnable only when the D3 gate contract reports the accepted D3 PASS state.

## 11. Graph and derived-state rules

The graph definition and materialized state are separate objects and must be shown separately.

Center must display:
- graph authority version + node count;
- derived-state graph version + node count;
- missing/extra nodes;
- last refresh time;
- state reducer SHA.

If parity is not proven, graph-driven actions are disabled.

Legacy `K01_DEPENDENCY_STATE.json` may remain for history but must be marked `LEGACY/QUARANTINED` if it is not regenerated by the current graph engine.

## 12. Handoff closure

A handoff is complete only when it contains:
- all authority/executor sources required to reproduce current checks;
- current gate reports;
- runtime evidence referenced by those reports;
- graph definition and materialized state;
- omitted evidence manifest containing path, SHA, size and reason for every intentionally excluded file;
- a machine-readable resume manifest with exact next allowed action.

`PASS_COMPLETE_FOR_RESUME_AND_SOURCE_REVIEW` must therefore include runtime evidence closure, not only source coverage.

## 13. Center UI — minimum screens

### Home
- checkpoint;
- active change/node;
- Assurance Coherence card;
- release readiness;
- top blockers;
- exact next allowed action;
- graph freshness/parity.

### Coherence
Table columns:
`ACI | State | Authority | Consumer | Expected FP | Observed FP | Why | Impacted actions | Repair action | Evidence`

### Trace
Interactive chain:
`Requirement -> Decision -> Characteristic -> CAD binding -> PMI -> Drawing -> Inspection -> Evidence`
with pinned fingerprints at each edge.

### Transactions
For every run:
- command ID/SHA;
- preflight manifest;
- inputs;
- outputs;
- side effects;
- post-run refresh;
- closure status.

### Drift
Dedicated list of all fingerprint/schema/effectivity/identity contradictions. No hidden warnings in logs.

## 14. Acceptance tests

Center update is not accepted until fixtures prove at least:

1. old exemplar + changed D1 => ACI-001 HOLD and D7 disabled;
2. composite C01 authority + single-face positional verifier => ACI-002 HOLD;
3. non-empty `*Right` without role mapping => ACI-003 HOLD;
4. graph has D3/D7 but derived state does not => ACI-004 HOLD;
5. legacy dependency state cannot satisfy freshness => ACI-005 HOLD;
6. report says "run D7 after L1/L2" => ACI-006 HOLD;
7. referenced raw report absent from ZIP and omitted manifest => ACI-007 HOLD;
8. all seven repaired => Assurance Coherence PASS;
9. coherence HOLD disables all mutations but permits diagnostics;
10. a command exit code 0 without transaction closure does not unlock next stage;
11. PASS scope badges cannot be promoted by string matching;
12. changing an authority fingerprint invalidates exactly the affected downstream transaction manifests.

## 15. Architectural rule

The Center is the **control tower**, not a second source of engineering truth.

It must answer four questions before every action:

1. **What exact authority am I acting on?**
2. **Is the executor implementing that exact authority?**
3. **Is the evidence for the same fingerprints/configuration/effectivity?**
4. **Has the dependency/handoff state been refreshed after the last mutation?**

If any answer is not machine-provable, the action is HOLD.
