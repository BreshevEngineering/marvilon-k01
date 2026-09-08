# MARVILON K01 — Engineering Decision Standard EDS-001 v1

## Purpose

Every non-trivial engineering decision in K01 shall be captured as an Engineering Decision Record (EDR). A decision is not considered released merely because CAD can be built or because one calculation passes.

The goal is to prevent local optimization from damaging system-level quality: serviceability, manufacturability, compactness, thermal behavior, reliability, cost, supply, assembly or the project's core architecture.

## Two-layer decision filter

### Layer A — hard gates

A weighted score can NEVER compensate for failure of a hard gate. Each applicable criterion shall be PASS, HOLD, FAIL, or N/A with an explicit reason.

1. Functional requirement — problem, measurable acceptance criterion.
2. System architecture / concept integrity — preserve the hermetic calibration-module concept and avoid hidden subsystem coupling.
3. Interfaces and datum strategy — pilot/shoulder/datum functions, overconstraint, interchangeability, backwards compatibility.
4. Load cases — normal, worst credible, assembly, service, transport and misuse; pressure/vacuum, axial, radial, torsion, shear, contact.
5. Static strength / local stress / contact — yield, bearing pressure, thread stripping, bolt tensile/shear, flange bending, contact pressure.
6. Stability / buckling — thin shells, rods, springs, can walls.
7. Torsion and rotational integrity — anti-rotation, torque reaction, loosening.
8. Fatigue / cyclic life — stroke, service, thermal and vibration cycles.
9. Thermal — temperatures, gradients, expansion mismatch, distortion, preload change, property reduction.
10. Dynamics / vibration — natural frequencies, resonance, impacts, dynamic clearance.
11. Pressure / vacuum / sealing — leak path, seal compression, extrusion, pressure direction, outgassing/permeation where relevant.
12. Fluid / CFD — pressure loss, flow forces, heat transfer, contamination transport where relevant.
13. Magnetic / electromagnetic — force, saturation, demagnetization margin, temperature, force constant, magnetic gap.
14. Materials and environment — corrosion, process gas, cleanliness, wear, creep, compatibility. OPEN material stays OPEN.
15. Tolerance / GD&T / dimensional-chain robustness — worst-case stack, fit, thermal stack, datum transfer and process capability.
16. Manufacturability / process capability — stock, setups, tools, wall thickness, deep boring, threads, finishing, joining, heat treatment, passivation.
17. Assembly — tool access, sequence, mistake-proofing, seal/thin-wall damage risk.
18. Serviceability / maintainability — non-destructive disassembly, replacement access, service tools, restored alignment, service cycles.
19. Inspection / metrology / testability — measurable critical characteristics and defined test method.
20. Reliability / FMEA — failure modes/effects/detectability, single-point failures, degradation.
21. Safety / regulatory / containment — stored energy, hot surfaces, containment, machinery/electrical/pressure requirements where applicable.
22. Supply chain / availability / obsolescence — standards, materials, seals, magnets, wire, lead time, supplier alternatives, lot variability.
23. Change impact — CAD, drawings, BOM, solver models, technology, tests and interfaces that become stale.
24. Documentation / traceability — requirement, CAD, calculation, drawing, BOM, technology, inspection and rationale.

### Layer B — optimization criteria

Only alternatives that pass all mandatory hard gates may be ranked. Typical optimization criteria:
- manufacturing simplicity;
- number of setups / special processes;
- part count;
- assembly time;
- service time;
- material and purchased-part cost;
- total lifecycle cost;
- mass;
- radial/axial package envelope;
- tolerance sensitivity;
- robustness to operator variation;
- repeatability / scalability;
- standard-component availability;
- supplier independence;
- energy/flow/electrical efficiency;
- cleaning burden;
- architectural coherence;
- upgrade/modularity path.

Weights are declared before final scoring. Uncertainty and sensitivity are recorded. A score never overrides a failed hard gate.

## Decision classes

- Class A — system/architecture: full EDR + alternatives + cross-disciplinary review.
- Class B — critical part/interface: full EDR with quantitative trade study.
- Class C — local/detail: short EDR, still linked to requirement, material, manufacturing and release impact.

## Minimum EDR content

Unique ID; title/subsystem; class; requirement/problem; baseline; alternatives; assumptions; hard-gate dispositions; optimization matrix; evidence; uncertainty/sensitivity; selected alternative; rejected alternatives and reasons; affected artifacts; OPEN items; release decision/date.

## Release rule

An EDR may be RELEASED only when every applicable mandatory gate is PASS, no critical material/process item is OPEN, required evidence exists, dimensional chains are reconciled, affected calculations are current, CAD/BOM/technology/drawing projections agree, and change-control/Git checkpoint is complete.

VERIFIED CANDIDATE is not RELEASED.
