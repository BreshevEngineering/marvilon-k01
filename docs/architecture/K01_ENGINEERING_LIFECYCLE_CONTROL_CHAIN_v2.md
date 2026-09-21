# K01 Engineering Lifecycle Control Chain v2

## 1. Purpose

This is the controlling lifecycle logic for K01. It closes gaps found during P007/K01-D-006 work: requirement allocation, derived-load identity, datum/measurement semantics, feedback loops, binding invariance, separate physics vs variation evidence, inspection sequencing, manufacturing feasibility and configuration/effectivity.

The chain is not a one-way document workflow. It is a governed dependency graph with explicit backward engineering feedback.

## 2. Controlling chain

```text
S0  REQUIREMENT / INTERFACE ENVELOPE
        |
S0A REQUIREMENT ALLOCATION
        |   requirement -> system/subsystem/interface/part/Cxx responsibility
        |   share/budget/complementary responsibility explicit
        v
S1  ENGINEERING DECISION + TECHNICAL FILTER
        |
        +--> S1A DERIVED ENGINEERING INPUTS
        |       load / preload / calculated limit / screening value
        |       stable ID + derivation + status + consumers
        |
        +--> S1B MANUFACTURING / SUPPLY STRATEGY
                route alternatives + process/supplier capability + inspectability
        |
        v
S2  PRODUCT CHARACTERISTIC Cxx
        nominal / requirement
        tolerance / fit / GD&T
        datum/reference system
        measurement condition
        material / surface / process
        inspection strategy
        configuration / effectivity
        CONTROLLED / PARTIAL / OPEN
        |
        v
S3  DETERMINISTIC CAD BINDING + MBD/PMI
        semantic readback
        save/reopen persistence
        L2/L3 binding invariance qualification
        |
        +-------------------+
        |                   |
        v                   v
S4A PHYSICS / BEHAVIOR    S4B VARIATION / CAPABILITY
strength/thermal/...      tolerance stack/process capability/inspectability
        |                   |
        +---------+---------+
                  v
S4C COMPILED PRODUCT DEFINITION
        full fingerprint + domain slices
        drawing / variation / inspection / physics / manufacturing / configuration
                  |
                  v
S5  DRAWING PROJECTION + SEMANTIC QA + VISUAL QA
                  |
                  v
S6  INSPECTION REALIZATION
        released plan/procedure + actual results
                  |
                  v
S7  CONFIGURATION RELEASE / EFFECTIVITY
```

## 3. Backward feedback is mandatory

Any failure at S2/S3/S4A/S4B/S5/S6 creates an Engineering Feedback Record (EFR). If design intent changes, EFR opens or references an EDR/change record and pre-change impact is run before mutation.

Examples:

- tolerance not manufacturable -> S4B -> EFR -> S1 decision reopen;
- selected inspection cannot verify thin-wall ID without deformation -> S6/S4B -> EFR -> S1/S2 reopen;
- PMI binds to wrong face after rebuild -> S3 -> EFR -> binding/design decision review;
- drawing reveals ambiguous requirement -> S5 -> EFR -> S2/S1, never a handwritten drawing fix.

## 4. Requirement allocation

A requirement is not automatically a part characteristic. Allocation is a separate controlled object.

`REQ-K01-J2-LOC-001` is shared/complementary: P007 owns the H7 female locator characteristic while P003 owns the complementary g6 side. Neither part alone is the system-level requirement.

`REQ-K01-ACT-FORCE-001` is currently allocated at actuator-subsystem level; its numeric acceptance/budget remains OPEN.

## 5. Derived engineering inputs

Derived loads are not requirements.

Current known example:

- `DER-K01-P006-SERVICE-NORMAL-FORCE-001` = 300 N service normal-force screening input;
- `DER-K01-J2-BOLT-PRELOAD-SCREEN-001` = 300 N/screw candidate clamp preload.

The equal number `300` creates no relationship. Quantity kind + derivation ID define identity.

## 6. Product Characteristic contract

Each release-relevant characteristic carries:

- stable ID;
- revision/effectivity;
- allocated requirement IDs;
- derived-input IDs if directly consumed;
- nominal/requirement;
- variation semantics;
- datum/reference-system semantics;
- measurement condition;
- material/surface/process;
- manufacturing feasibility context;
- inspection strategy/capability;
- CAD binding + binding-invariance level;
- MBD carrier;
- drawing projection rule;
- CONTROLLED/PARTIAL/OPEN and release blocker state.

## 7. Measurement condition

No global measurement condition is silently assumed. Temperature, free/fixture state, support and measurement force are controlled where functionally significant.

For thin-wall P007 C07/C08/C11/blind-end this is release-critical because fixturing and probe force can alter the measured geometry.

## 8. Binding invariance

- L1: save-close-reopen persistence;
- L2: no-op `ForceRebuild3(false)` and semantic-geometry identity before/after;
- L3: approved perturb-and-restore on a disposable candidate.

Runtime face index is never sufficient. Zero or multiple semantic matches = HOLD.

## 9. Analysis split

S4A physics/behavior and S4B variation/capability are separate nodes/domains. A load/material/geometric change can stale a physics case while a tolerance-only change stales variation evidence. Domain slices prevent unnecessary rebuilds while preserving fail-closed propagation.

## 10. Inspection sequencing

Inspection **strategy/method/capability** is part of S2 Product Definition. S6 contains the released procedure, sampling/measurement execution and actual results. If a characteristic cannot be inspected with the required uncertainty/capability, the definition returns upstream before release.

## 11. Manufacturing/supply feasibility

P007 route is currently OPEN between monolithic deep-bore construction and welded applicability review. Process-dependent tolerance, roughness, joining symbols and MBOM route cannot be released before route/capability closure.

## 12. Configuration/effectivity

Every released characteristic and artifact must state revision/effectivity. Design-review data may be baseline-scoped; production release requires explicit part/configuration revision/effectivity. Released history is immutable.

## 13. Change propagation

Changes propagate **state**, not automatic design mutations.

A P007 interface change can make J2, P003 counterpart review, assembly semantics, affected analysis, variation, drawing, inspection and release stale. The system may automatically calculate impact/rebuild pure derived nodes, but it never silently edits P003 or changes a characteristic.

Domain-specific Product Definition slices are used so a visual drawing edit does not stale FEM, and an inspection-method update does not force drawing regeneration unless drawing semantics actually depend on it.


## 14. Minimum necessary invalidation

The full compiled Product Definition is an aggregate traceability/readiness object; it is **not** used as the universal freshness input for every downstream consumer. Domain consumers bind to the narrowest sufficient slice.

The single characteristic-context authority remains `K01_CHARACTERISTIC_CONTEXT_CURRENT.json`, but MEDTAS creates hash-only JSON projections for datum, measurement, inspection, manufacturing-route, binding and configuration/effectivity fields. These projections are not second authorities; they let the graph distinguish, for example, an inspection-method change from a physics-input change.

Examples:

- measurement-condition change -> drawing/variation/inspection/manufacturing consumers as declared; physics is not invalidated unless a physics case explicitly consumes that condition;
- inspection-strategy change -> inspection + variation/capability consumers; D006 projection and physics are not invalidated merely because the same context file changed;
- drawing visual change -> visual/drawing verification only; Product Definition and analysis remain fresh;
- interface geometry change -> CAD/interface/shared-counterpart and every declared downstream consumer become stale/review-required.

This is fail-closed but avoids rebuilding unrelated work.
