# K01 FEMM — final magnetic calculation still required

The existing fixed-coil FEM evidence is a valid screening result:
`K_F,min ≈ 1.00 N/A at Br=1.00 T across the full ±5 mm stroke`.

It is not discarded.

However, after the serviceable P003↔P007 front flange is frozen, run one final
axisymmetric FEMM sweep because the 316L geometry close to the front coil changes.

No physical magnet purchase is required.

## Design inputs
B001:
- Sm2Co17 / S280 equivalent;
- Ø8 × 8;
- axial magnetization;
- conservative screening Br = 1.00 T.

Currents:
- 0 A
- 0.5 A
- 1.0 A
- 1.25 A

Positions:
- z = -5 ... +5 mm across the 10 mm stroke; use enough stations to resolve the
  minimum force constant and end effects.

P007 material sensitivity:
- μr = 1.000
- 1.005
- 1.020
- 1.050

Extract:
- Fz(z,I)
- K_F(z)
- minimum useful-direction force constant
- Bmax in magnet/nearby steel
- flux linkage / inductance if the coil model supports it.

## Modeling the service flange

Model the new P007 front flange as an axisymmetric 316L ring.
The four A4 screws and holes are non-axisymmetric; for the axisymmetric screen
they may be omitted or represented as μr≈1 material because they are outside the
active thin-can region. If the final result is unexpectedly sensitive, use 3D
magnetic FEA later; do not jump to 3D unless the 2D sensitivity indicates need.

## Decision

FEMM becomes the final numerical magnetic release model after:
1. serviceable P003↔P007 interface freeze;
2. P015 final geometry/material freeze;
3. CFD OUT/MID/IN force envelope.

Actual lot Br(T) and bench force remain production validation, not design inputs.
