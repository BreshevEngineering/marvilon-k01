# MEDTAS stale-propagation specification v1

## 1. Core rule
MEDTAS is a state engine over an Engineering Build Graph (DAG). It does **not** store manual status as the source of truth. Status is derived from the current graph, two hashes, build records, artifact bytes, and verification records.

The Engineering Build Graph remains the causal model: it answers **what depends on what**. MEDTAS answers **what is fresh, stale, missing, drifted, verified, blocked, and what must be rebuilt**.

## 2. Two hashes

### STATE_HASH
Semantic/build-dependency identity. It is SHA-256 of a canonical object containing:
- node identity and kind;
- normalized semantic payload;
- upstream hashes according to each edge's `consume` mode;
- tool/script/config identities when the node policy says they affect results;
- hash-policy version.

It excludes host-specific noise such as absolute drive letters, usernames, timestamps, UI state, and temporary solver folders.

### ARTIFACT_HASH
Identity of the actual output bytes. For one file: SHA-256 of its bytes. For a set/directory: SHA-256 of a sorted manifest of `{relative path, size, sha256}`.

This separates engineering change from binary drift:
- STATE same + ARTIFACT same = same state and same evidence;
- STATE changed = rebuild required;
- STATE same + ARTIFACT changed = artifact/evidence drift, not automatically a design change.

## 3. Edge semantics
Each input edge declares `consume`:
- `state`: downstream depends on upstream engineering semantics only;
- `artifact`: downstream depends on exact upstream bytes;
- `both`: both are causal.

This is essential. Example: a drawing verification node should consume drawing semantic state **and** rendered/exported drawing artifact. A tolerance calculation normally consumes semantic state, not PDF bytes.

## 4. Derived-state precedence
Topological evaluation uses this precedence:
1. `SUPERSEDED` if lifecycle says a newer node replaces it.
2. `BLOCKED` if a required upstream node is `MISSING`, `BLOCKED`, or `HOLD`.
3. `PASS` for valid source-semantic nodes that require no built artifact.
4. `MISSING` if required outputs are absent/unbound or a derived node has no build record.
5. `STALE` if `build_record.built_from_state_hash != current STATE_HASH`.
6. `DRIFT` if state matches but current ARTIFACT_HASH differs from the recorded artifact hash.
7. `FRESH_UNVERIFIED` if current hashes are fresh but verification is absent or is tied to old hashes.
8. `PASS`, `PASS_WITH_LIMITATIONS`, or `HOLD` from a verification record tied to the current two hashes.

## 5. Propagation algorithm
There is no recursive 'set stale on children' mutation. Instead:
1. Evaluate nodes in topological order.
2. Compute each node's current STATE_HASH from current upstream hashes.
3. Any upstream semantic change changes the downstream current STATE_HASH.
4. If the downstream artifact was built from the old state hash, it becomes `STALE` automatically.
5. Continue to descendants.

For UI/action planning, MEDTAS may additionally compute an `impact_closure(changed_node)` list, but that list is explanatory only; it does not create authoritative status.

## 6. Important propagation cases

### Parameter change
`PARAM → CAD semantic → canonical snapshot → tolerance / structural / FEMM / drawing / BOM` all receive new state hashes. Existing outputs become stale if they were built from the prior state.

### Raw CAD binary re-save without semantic change
If the semantic extractor produces the same CAD semantic state, semantic consumers stay fresh. Only nodes that explicitly consume the raw CAD artifact bytes should see artifact drift.

### Drawing PDF regenerated with same drawing semantics
Drawing artifact hash changes. Drawing verification becomes stale/drifted because it consumes artifact; tolerance and structural FEM remain fresh because they do not consume drawing bytes.

### Material change
Material node state changes. CAD/canonical snapshot and all material-sensitive analyses become stale. BOM and drawings become stale because material is part of their semantics.

### Solver/script version change
If `identity_affects_state=true`, the solver-run node's STATE_HASH changes; its old result becomes stale. Unrelated branches do not.

## 7. Verification is a node, not a comment
Verification records must bind to both `verified_state_hash` and `verified_artifact_hash`. A PASS cannot silently survive a rebuilt model or modified evidence file.

Issues/limitations (for example `FEMM-FORCE-001`) are separate from state. `PASS_WITH_LIMITATIONS` is allowed only when a controlled verification policy classifies those issues as non-blocking for the current gate.

## 8. Release policy
Different gates may require different graph closures. For K01:
- Gate04E engineering screen may pass with the current SolidWorks structural screen and FEMM field/automation screen.
- Production Release additionally requires tolerance chain, independent structural cross-check/reconciliation (CalculiX unless formally waived), verified drawings, and verified BOM.

A baseline stores two roots:
- `BASELINE_STATE_HASH`: root of approved engineering semantics/dependencies;
- `BASELINE_ARTIFACT_HASH`: root of the released evidence/artifact manifest.

## 9. Canonicalization requirements
Before hashing:
- units must be normalized;
- object keys and unordered sets must be deterministically sorted;
- critical floats should be represented as normalized decimal strings at controlled precision;
- absolute paths must be converted to repository-relative logical paths if path identity is actually required;
- timestamps, machine names, usernames, UI state, and temporary paths are excluded from STATE_HASH.

## 10. Build selection ('what must run?')
A scheduler can select nodes whose derived state is `MISSING`, `STALE`, or `DRIFT` (when exact artifacts are required), then expand only the required upstream closure. `HOLD` and `BLOCKED` are not auto-rebuilt until their blocking cause is changed or cleared. `FRESH_UNVERIFIED` schedules verification, not the expensive solver/build itself.
