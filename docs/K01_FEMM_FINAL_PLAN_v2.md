# K01 FEMM final plan

Yes — a final magnetic calculation is still required.

Existing FEM evidence remains a valid screening baseline:
`K_F,min ≈ 1.00 N/A` at conservative `Br=1.00 T` across the ±5-mm stroke.

The final FEMM model is run **after** the removable P003↔P007 front-flange
geometry and P015 are frozen because the new 316L front flange changes the
magnetic boundary near the front coil.

No physical magnet purchase is required.

Inputs:
- B001 Sm2Co17/S280 equivalent, Ø8×8, axial, Br=1.00 T design lower bound.
- I = 0 / 0.5 / 1.0 / 1.25 A.
- z = -5...+5 mm.
- P007 316L μr sensitivity = 1.000 / 1.005 / 1.020 / 1.050.

Outputs:
- Fz(z,I)
- force constant K_F(z)
- minimum useful-direction K_F over full stroke
- Bmax
- flux linkage / inductance where model supports it.

Sequence:
serviceable flange freeze → refresh assembly/structural screen → FEMM → CFD
OUT/MID/IN → final actuator force budget.
