# K01 J2 Compactness Review — 2026-09-04

## Finding

The current verified **full circular OD36 flange is not a packaging optimum**.

It was a conservative feasibility geometry and is the minimum full circular
diameter under the current assumptions:

- M3 clearance hole = Ø3.40
- PCD = 28
- seal groove worst OD = 20.60
- project robustness ligament target = 2.00 mm

Result:
- inner ligament = `(28-3.4-20.6)/2 = 2.00 mm`
- minimum full circular OD = `28+3.4+2×2 = 35.4 mm`
- OD36 gives outer ligament = 2.30 mm

So **OD36 is internally consistent, but only because PCD28/M3/2-mm-ligament were
held fixed**. It should not be described as globally optimal.

## Recommended production optimization study

Keep functional architecture:
- removable static-sealed J2;
- P003/P007 metal-face axial location;
- Ø14.10 H7/g6 pilot/locator;
- 16×1.5 O-ring unless the seal study changes it;
- three-point symmetric clamp.

Study two compact variants:

### C1 — M3 three-lobed flange
Keep 3×M3 / PCD28 / current seal.
Replace the complete Ø36 disk by a central circular sealing land with three local
bolt ears blended by large fillets.

Advantages:
- same proven seal/bolt geometry;
- much lower visual and mass bulk;
- no need to reduce ligament.

Disadvantage:
- maximum local radial envelope remains close to current screw-boss envelope;
- adds milling/profile operation after turning.

### C2 — preferred compact study: 3×M2.5
Candidate arithmetic only, not release data:
- normal-clearance assumption Ø2.9;
- PCD candidate 26.5;
- ligament study target 1.5;
- with gland OD20.6: inner ligament ≈1.50 mm;
- full circular mathematical OD minimum ≈32.4 mm → use ~OD33 for study.

A three-lobed M2.5 version can reduce actual flange mass and visual envelope
further, but exact fastener standard, head envelope, edge distance, tightening
torque, seal compression and FEA must be frozen before release.

## Recommendation

Do **not** promote the OD36 Gate04C candidate yet.

Use it as the verified functional reference and run one compact-production
optimization pass before atomic P003/P007 promotion.

M2 is not recommended as the first production choice because it unnecessarily
reduces service robustness for very little system benefit over M2.5.
