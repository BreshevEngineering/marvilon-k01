# K01 Gate04E FEM / FEMM Verification Report v1

**Project:** K01 Calibration Module  
**Date:** 2026-09-06  
**Scope:** P006 service structural screening and current-position FEMM magnetic screening.  
**Evidence root SHA-256:** `c0b78d820237f75b173c6c67ca61a273fdfd45297be325dad19658b06d7e6e03`

## Executive decision
- **Structural FEM (SolidWorks Simulation): PASS** for the defined linear-static service load case.
- **FEMM solver/automation and qualitative field screening: PASS_WITH_LIMITATIONS.** Both 1 A-turn cases completed and produced field plots; absolute force extraction is **NOT VERIFIED** and must not be used as release evidence.
- **Gate04E engineering screen:** PASS TO CONTINUE.
- **Production release:** not yet closed; tolerance chain, CalculiX independent check/reconciliation, drawings, and BOM remain downstream controlled nodes.

## 1. Structural FEM
Latest report assigns both analyzed bodies to **1.4404 (X2CrNiMo17-12-2)**: yield 400 MPa, tensile 600 MPa, E=200 GPa, ν=0.28, density 8000 kg/m³.

Loads: fixed geometry on one face; 300 N normal force; 0.02 MPa pressure on five faces; three M2.5 bolt connectors, 300 N preload each; no-penetration surface-to-surface global contact.

Mesh: 102,923 nodes; 63,800 elements; 1.12755 mm nominal element size; max aspect ratio 13.093; 92.3% of elements AR<3; 0.00313% AR>10; 0 distorted Jacobian elements.

Results: σ_vm,max = **40.66 MPa**; u_res,max = **0.002171 mm = 2.171 µm**; ε_eq,max = **1.207e-4**; resultant support reaction = **302.262 N**. Bolt axial forces are approximately 307.4–307.9 N, with ~2.06–2.07 N resultant shear.

Yield utilization = 40.66/400 = **10.17%**; simple yield factor of safety = **9.84**.

**Decision:** PASS. The analyzed geometry is structurally adequate for this defined static service case with a large margin. This verdict does not claim thermal-cycle, nonlinear, fatigue, frictional-contact, or mesh-convergence release verification.

## 2. FEMM
Evidence includes Coil A and Coil B 1 A-turn runs. Both DONE markers contain `PASS_SCRIPT_COMPLETED` and `Fz_N=0`. The CSV records Br=1.00 T and μ316=1.005. Coil A has a completed row with FluxB=2.624496529278694e-006; the Coil B row terminates at `FluxA=` and is incomplete.

Both field-density plots were generated. The images demonstrate that FEMM solved and rendered a magnetic field distribution for both excitation cases. No reliable numerical Bmax extraction is present in the evidence set, so the color scale is not used as a quantitative acceptance value.

Open evidence defects:
- `FEMM-GEO-001`: FEMM reported orphaned DXF endpoints after import. Solve completed, therefore this is non-blocking for the current screening but must be eliminated for a clean production workflow.
- `FEMM-OUT-001`: Coil B CSV row is incomplete.
- `FEMM-FORCE-001`: `Fz_N=0` has not been validated as a physical force result; until the force integral/group selection is independently verified, it is treated as an extraction defect/unknown, not as proof of zero force.

**Decision:** PASS_WITH_LIMITATIONS for solver/automation + qualitative field screening. Absolute force quantification remains NOT VERIFIED.

## 3. Next controlled nodes
1. Bind the canonical CAD semantic snapshot and begin automatic tolerance-chain derivation.
2. Build a solver-neutral structural model and run CalculiX as the independent structural branch.
3. Generate and verify production drawings from canonical semantics; drawings must carry material, datums, fits, tolerances, surface/manufacturing notes, and revision linkage.
4. Generate BOM from canonical assembly semantics and verify quantity/revision/material/make-buy parity.
5. Use MEDTAS two-hash state engine to derive freshness and schedule only stale/missing nodes.
