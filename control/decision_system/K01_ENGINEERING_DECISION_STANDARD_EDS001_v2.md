# K01 Engineering Decision Standard — EDS-001 v2

Every non-trivial engineering decision must have an EDR before it may become a
released product baseline.

## A. Mandatory hard gates

A weighted score cannot compensate for a failed hard gate.

For each applicable gate: PASS / HOLD / FAIL / N/A + reason.

1. Functional requirement and measurable acceptance criterion.
2. Preservation of system architecture / concept.
3. Interfaces, datum scheme, constraints and interchangeability.
4. Complete load cases: normal, worst credible, assembly, service, transport.
5. Static/local/contact/thread strength.
6. Stability/buckling.
7. Torsion / anti-rotation / torque reaction / loosening.
8. Fatigue and cyclic life.
9. Thermal state, gradients, expansion mismatch, preload drift.
10. Dynamics, vibration, resonance and dynamic clearance.
11. Pressure/vacuum/sealing/leak path.
12. Fluid/CFD effects where relevant.
13. Magnetic/electromagnetic effects where relevant.
14. Materials/environment/corrosion/process-gas compatibility/cleanliness.
15. Tolerance, GD&T and worst-case dimensional/thermal stack.
16. Manufacturability and real process capability.
17. Assembly access, tooling, sequence, mistake-proofing.
18. Serviceability/maintainability and restoration of alignment.
19. Inspection, metrology and testability.
20. Reliability/FMEA/single-point failures/degradation.
21. Safety/regulatory/containment.
22. Supply chain, availability, alternate suppliers, lot variation, obsolescence.
23. Change impact: CAD/drawing/BOM/calculation/technology/tests/interfaces.
24. Documentation and traceability.

## B. Evidence gate — mandatory for every decision

Each important claim used to approve a decision shall reference one or more ERRs.

An ERR must state:
- source ID;
- source type: standard / handbook / paper / supplier / calculation / test /
  CAD readback / field evidence;
- title and edition/version;
- author/publisher;
- exact section/page/figure/table where practical;
- URL or controlled project path;
- claim supported;
- applicability to K01;
- limitations / assumptions;
- date checked;
- evidence status CURRENT / SUPERSEDED / OPEN.

Literature search is part of alternative generation and evidence review, not a
decorative bibliography.

## C. Optimization layer

Only alternatives passing hard gates are ranked.

Typical optimization criteria:
- manufacturing simplicity;
- number of setups/special processes;
- part count;
- assembly/service time;
- material + purchased-part + lifecycle cost;
- mass and package envelope;
- tolerance sensitivity;
- robustness to operator variation;
- repeatability/scalability;
- standard component availability;
- supplier independence;
- energy/flow/electrical efficiency;
- cleaning/contamination burden;
- architectural coherence;
- upgrade/modularity path.

Weights must be declared before final scoring for major decisions. Sensitivity to
reasonable weight changes must be checked if rankings are close.

## D. Decision classes

A — system/architecture: full EDR + alternatives + cross-disciplinary review.  
B — critical part/interface: full EDR + quantitative evidence/trade study.  
C — local/detail: short EDR but still material/manufacturing/change-impact controlled.

## E. Release rule

RELEASED requires:
- all applicable mandatory gates PASS;
- critical materials/processes not OPEN;
- evidence files exist and are CURRENT;
- dimensional chains reconciled;
- affected simulations current;
- CAD/BOM/technology/drawing consistent;
- ECR/change record complete;
- Git/configuration checkpoint complete.

VERIFIED CANDIDATE is not RELEASED.
