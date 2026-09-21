# K01 engineering lifecycle and P0-P6 control architecture

## Purpose

K01 is developed as a controlled engineering system, not as a sequence of disconnected files. This document preserves the reusable project logic for K01 and future Marvilon nodes/products.

## Separation of control mechanisms

- **P0-P6 maturity gates** answer: how far the product is from release.
- **MEDTAS dependency graph** answers: what depends on what and what is FRESH/STALE/BLOCKED/MISSING.
- **Change control** answers: why a change exists, what it impacts, how it is verified and promoted.
- **Technical filter** answers: which engineering domains are applicable and whether their evidence is sufficient.
- **Checkpoint/evidence chain** answers: exactly what proves the current transition.
- **Baseline/promotion** answers: which verified candidate becomes canonical authority.
- **Product definition/BOM/TPD** answers: what is manufactured, inspected and released.
- **Git/AI handoff** preserve history and resume context; neither is product-definition authority.

## Lifecycle

```text
REQUIREMENTS
    ↓
ARCHITECTURE / FUNCTIONAL INTERFACES
    ↓
ENGINEERING ANALYSES
    ↓
JOINTS / SEALS / TOLERANCES / MANUFACTURING PROCESSES
    ↓
PART CANDIDATES
    ↓
CAD PRODUCER INVARIANT VERIFICATION
    ↓
CANDIDATE ASSEMBLY INTEGRATION
    ├─ identity/reference safety
    ├─ datum / DOF logic
    ├─ mates / constraints
    ├─ signed position/orientation
    ├─ motion-state envelope
    ├─ interference
    └─ product-structure delta
    ↓
CONTROLLED CANONICAL PROMOTION
    ↓
NEW CANONICAL SNAPSHOT
    ↓
DEPENDENCY / STALE REDUCTION
    ├─ analyses
    ├─ EBOM / MBOM
    ├─ DimXpert / drawings
    └─ qualification evidence
    ↓
CANDIDATE TECHNICAL PRODUCT DEFINITION
    ├─ native CAD + DimXpert/PMI
    ├─ drawings
    ├─ inspection characteristics
    └─ EBOM / MBOM
    ↓
VERIFICATION AGAINST REQUIREMENTS
    ↓
PHYSICAL QUALIFICATION WHERE REQUIRED
    ↓
RELEASE REVIEW
    ↓
R01
```

## Reusable node contracts

### CAD_PRODUCER
Must prove the functional geometry it owns, not only that a feature exists:
- controlled source identity;
- coordinate-frame contract;
- feature ownership;
- actual dimensions/location/end condition;
- material status;
- output candidate identity/evidence.

### INTEGRATION_QA
A local part PASS never replaces assembly proof:
- canonical hash guard;
- exact candidate set;
- reference-safe replacement;
- DOF/mates/constraints;
- signed side/orientation/depth;
- motion envelope;
- unexpected interference;
- product-structure/BOM delta;
- verification artifact hash.

### PROMOTION
Candidate verification and authority change are separate:
- frozen PASS evidence;
- exact candidate hashes;
- pre-write archive/rollback;
- stable-identity/reference-safe apply;
- reopen + semantic/assembly verification;
- new canonical snapshot;
- dependency/stale reduction;
- product-data refresh.

### STALE_PROPAGATOR
Staleness is computed from declared dependencies/hashes. Unrelated branches remain fresh.

## Checkpoint classes

- **CP-E** engineering decision.
- **CP-C** candidate integration.
- **CP-P** canonical promotion.
- **CP-G** Git checkpoint.
- **CP-H** AI handoff checkpoint.
- **CP-R** product/R01 release.

Current checkpoint:
`K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED` = CP-C.

## Mandatory step rule

Before every mutating engineering step:
1. read current checkpoint/authority;
2. read P0-P6 gate;
3. resolve dependency/freshness inputs;
4. apply technical filter;
5. state material for each affected part or mark OPEN;
6. evaluate tolerance/DimXpert/drawing/BOM/inspection impact;
7. define evidence and rollback;
8. execute one controlled line only;
9. write machine-readable evidence;
10. change authority only through promotion.

## Baseline-02C lesson captured for reuse

Datum C proved why these contracts are necessary. Part-level checks initially missed a physical P003/P017 clash. Assembly QA exposed it. The producer was strengthened instead of whitelisting the clash. The final solution required explicit model-to-sketch coordinate mapping, Through-All proof, fresh COM topology after rebuilds and signed positional readback. Final candidate integration proved 14 components, zero active mate errors, correct P017 depth/protrusion, moving-group propagation and zero unexpected IN/MID/OUT interference.

The process pattern is reusable. The hard-coded K01 dimensions are not.

## Control namespace discipline

Critical control families have exactly one declared authority in `K01_AUTHORITY_MAP_CURRENT.json::control_families`. Existing versioned siblings are migration history. `control_namespace_guard.py` freezes existing version-family membership so history may shrink but silent `vNext` proliferation is blocked. Stable unversioned names are the migration target.

`CURRENT` is a pointer/materialized-view convention, not a version selector. Multi-format projections (for example JSON+CSV of the same logical current artifact) are allowed; same-format `_CURRENT_vN`/`_Vn_CURRENT` ambiguity is migration debt and new instances are blocked.

## Canonical step gate

Before an engineering write, the active step contract must name the checkpoint and declare impacts on requirements, materials, BOM, DimXpert/drawings, inspection, dependencies, rollback and evidence. `tools/assurance/engineering_step_gate.py` verifies those declarations and referenced control/evidence states. Passing a step gate authorizes only the declared intent; it never upgrades release evidence.

## Requirements-to-evidence semantics

Requirement maturity and evidence linkage are independent. A linked FEM/CFD/FEMM/method report is supporting evidence unless it directly evaluates the released acceptance criterion on the applicable baseline and envelope. OPEN/PARTIAL/CANDIDATE release blockers remain blockers even when supporting evidence is linked. The migration target is explicit `supporting_evidence_ids` versus `qualifying_evidence_ids`; current `evidence_ids` is treated as linkage only.

## Semantic/BOM baseline rule

`K01.CAD.SEM.A001` resolves its assembly from the explicit engineering-baseline authority. It must not select a Gate04E/candidate file by filename fallback. EBOM/MBOM are rebuilt only after that baseline is promoted, reopened and semantically exported.

## Canonical control commands before an engineering write

```text
run.cmd root-cleanup          # dry-run only
run.cmd root-cleanup-apply    # moves only validated local/transport root artefacts; no native CAD
run.cmd prewrite-check        # namespace -> technical filter -> requirements coverage -> active step gate -> final handoff
```

The active step gate remains intent-specific authority. `prewrite-check` cannot convert OPEN release evidence into PASS and cannot authorize native CAD mutation unless the current step contract explicitly permits it.
