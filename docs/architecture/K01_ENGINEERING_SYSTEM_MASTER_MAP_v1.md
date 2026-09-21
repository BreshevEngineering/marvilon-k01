# K01 Engineering System Master Map v1

## Purpose

This document is the readable projection of the executable engineering-domain registry. It prevents project work from collapsing into the currently active topic (CAD, drawing, FEM, BOM, etc.). The authoritative machine contract is `control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json`.

## Main definition spine

`S0 Requirement / Interface -> S0A Allocation -> S1 Decision / Technical Filter -> S1A Derived Inputs + S1B Manufacturing/Supply -> S2 Product Characteristics -> S3 CAD/MBD Binding -> S4A Physics + S4B Variation/Capability -> S4C Compiled Product Definition -> S5 Drawing -> S6 Inspection -> S7 Configuration/Release`.

This spine is a DAG, not a one-way checklist. Downstream failures return upstream only through EFR/change control; downstream tools never silently edit upstream Product Definition.

## Parallel release lanes

### 1. Definition lane
Requirements, allocation, derived inputs, decisions, Product Characteristics, datum/DRF, measurement condition, material/surface/process, inspection strategy and configuration/effectivity.

### 2. CAD/MBD lane
Native SolidWorks geometry, stable semantic binding, DimXpert/PMI and binding-invariance evidence. Runtime face IDs are not authority.

### 3. Physics evidence lanes
Independent evidence families with separate fingerprints and stale propagation:

- Structural: SolidWorks Simulation primary screen + CalculiX/CCX independent branch/reconciliation.
- Magnetic: FEMM.
- Flow/CFD: SolidWorks Flow Simulation or another controlled solver when applicable.
- Thermal: thermal/preload/galling/service evidence.
- Pressure/Vacuum/Containment: differential pressure, containment strength/process and leak acceptance/test evidence.

A PASS in one physics family never implies PASS in another.

### 4. Variation/capability lane
Tolerance chains, process capability, measurement capability and inspectability. This lane is independent of structural/thermal/magnetic behavior evidence.

### 5. Product-structure lane

- EBOM: computed engineering product structure from controlled CAD occurrence tree + product registry.
- MBOM: manufacturing transformation of EBOM consuming route/process definitions.

EBOM and MBOM are not interchangeable and must remain separately visible.

### 6. Documentation lane
D1-D9 drawing pipeline. Product Definition is semantic authority; drawing is a representation. Family/view planning routes controlled claims but cannot create engineering values.

### 7. Verification lane
Inspection/metrology/test plans and actual results. Measurement condition/capability belong upstream with Product Characteristics; S6 realizes and records inspection/test evidence.

### 8. Configuration/release lane
Revision/effectivity, immutable baseline, evidence hashes, as-built/as-inspected traceability, Git/handoff reproducibility.

## Current explicit gaps

The registry currently declares, rather than hides, these gaps:

- D3/D7/D8/D9 release-native drawing chain is incomplete for D006.
- Flow/CFD evidence is not yet normalized into authoritative MEDTAS nodes.
- Thermal workpack exists but no dedicated thermal evidence node is in the authoritative graph.
- Pressure/Vacuum/Containment has controlled envelope evidence but no dedicated containment/leak evidence family yet.
- CalculiX/CCX cross-check is graph-backed but runtime preflight may remain blocked by neutral mesh/toolchain availability.
- FEMM has solver/field evidence with limitations; absolute force extraction is not release evidence until independently validated.
- EBOM/MBOM verification can remain HOLD while non-modeled items, revisions, materials or manufacturing transformations are open.

A declared gap is not a failure of the system architecture; an undeclared gap is.

## Change propagation rule

When one part, characteristic, interface, requirement, process or solver input changes:

1. identify changed engineering entity and domain;
2. compute graph seeds;
3. propagate `STALE/BLOCKED/REVIEW_REQUIRED` only through consumers;
4. trigger counterpart review on shared interfaces without automatic counterpart mutation;
5. rebuild in topological order;
6. preserve unaffected domains/fingerprints;
7. keep release HOLD until every required release-path node is fresh and verified.

## Center requirement

Center must show a domain-coverage matrix, current runtime solver state, declared gaps, release effect and `Why stale?` causal paths. Center is a projection/orchestrator only and never stores a competing engineering truth.
