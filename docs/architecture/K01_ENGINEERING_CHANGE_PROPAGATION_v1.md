# K01 engineering change propagation — authoritative execution model

## 1. Canonical chain

Every release-relevant item follows one chain. A downstream stage is a projection/consumer of the previous stage, never a second engineering authority.

```text
TЗ / Requirement / Interface envelope
                ↓
Engineering decision
Technical Filter
calculation / tolerance stack / standard / test
                ↓
PRODUCT CHARACTERISTIC Cxx
                ↓
nominal
variation: tolerance / fit / GD&T
material
surface requirement
process
inspection
CONTROLLED / PARTIAL / OPEN
                ↓
deterministic CAD binding
                ↓
DimXpert / PMI / controlled native annotation
                ↓
semantic verification
                ↓
COMPILED PRODUCT DEFINITION
+ definition fingerprint
+ MEDTAS consumed-state fingerprint
                ↓
DRAWING PROJECTION
                ↓
SLDDRW
                ↓
semantic QA + visual QA
                ↓
inspection characteristic
                ↓
release
```

## 2. Fingerprint rule

Each derived node is built from the state hashes of its declared inputs. The build record stores the consumed state hash and the artifact hash.

If any upstream state changes:

```text
upstream STATE_HASH changes
        ↓
consumer current STATE_HASH changes
        ↓
build record no longer matches
        ↓
consumer = STALE
        ↓
all transitive consumers become STALE / BLOCKED / FRESH_UNVERIFIED as applicable
```

No manual status edit can restore freshness. Rebuild/reverification against the new fingerprints is required.

## 3. Change to one part

A part change has two distinct effects.

### 3.1 Internal change

Example: a non-interface P007 feature changes.

- P007/A001 CAD semantic state changes.
- P007 CAD binding/PMI semantic verification is re-run.
- compiled Product Definition binding context is re-run.
- D006 projection becomes stale.
- affected analysis, BOM or inspection nodes become stale only when they actually consume the changed state/domain.

The system must not invalidate unrelated product authorities merely because the filename contains `P007`.

### 3.2 Shared-interface change

Example: P007 J2 pilot, flange, clamp pattern or interface material/process changes.

- J2 interface conformance becomes stale.
- P003 and P007 are both `COUNTERPART_REVIEW_REQUIRED` because they share J2.
- A001 integration/assembly verification becomes stale.
- downstream tolerance, analysis, drawing and inspection consumers are invalidated through the build graph.
- the system does **not** silently modify P003 to match P007. The counterpart requires an engineering decision/change.

This is the key difference between **automatic propagation** and **automatic design mutation**.

## 4. Change domains

Every change declares a domain: `requirement`, `interface_requirement`, `geometry`, `interface_geometry`, `material`, `product_definition`, `pmi`, `analysis_input`, `manufacturing_process`, `metadata`, or `drawing_visual`.

The domain controls the seed nodes. Transitive impact is then calculated only from the authoritative MEDTAS graph.

A `drawing_visual` change must not make CAD geometry/Product Definition/BOM stale. An `interface_geometry` change must not be treated as a drawing-only change.

## 5. Rebuild order

The impact engine produces a topological plan:

1. changed source authority / engineering review,
2. native CAD semantic extraction,
3. Product Definition / MBD semantic verification,
4. analysis/tolerance consumers,
5. drawing/inspection/BOM projections that consume the changed state,
6. QA/reverification,
7. release gate.

A consumer cannot rebuild while a required impacted predecessor is `STALE`, `DRIFT`, `BLOCKED` or `HOLD`.

## 6. Release rule

Any stale/drifted node on the active release path keeps release `HOLD`. PDF text, drawing notes or Center UI cannot override this.

## 7. System authorities

- topology: `control/medtas/v1/graph/K01_engineering_build_graph_v2_1.json`
- domain authority map: `control/project/K01_AUTHORITY_MAP_CURRENT.json`
- product-definition semantics: `control/product_definition/K01_PRODUCT_DEFINITION_POLICY_v2_0.json`
- relationship/cross-part registry: `control/project/K01_ENGINEERING_RELATIONSHIP_REGISTRY_v1.json`
- change propagation policy: `control/project/K01_CHANGE_IMPACT_POLICY_v1.json`
- runtime freshness: `reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json`
- current change impact/rebuild plan: `reports/control/K01_CHANGE_IMPACT_CURRENT.json`

Legacy manual dependency lists are compatibility/history only and must not drive new impact decisions.

## 8. Current granularity limitation (V9)

The current canonical CAD semantic extractor is assembly-level (`K01.CAD.SEM.A001`). Therefore a declared P007 geometry change conservatively seeds the A001 CAD semantic node and can invalidate more downstream analysis nodes than strictly necessary.

This is deliberate **safe over-invalidation**, not hidden precision. V9 must never under-invalidate a consumer just to shorten the rebuild list.

Planned optimization after the D006 projection path is stable: add part-level semantic slice nodes (for example P007/P003) with deterministic filtered fingerprints, then replace broad A001 seeds where evidence proves the narrower dependency. The optimization must preserve the same interface/counterpart rules.
