# K01 J2 Compact Flange Trade Study v1

**Status:** SCREENING — not release data.

Current OD36 / 3×M3 / PCD28 remains a verified functional reference, but promotion stays on HOLD until compactness is resolved. OD36 was only optimal inside fixed assumptions; it was not proven globally optimal for K01.

## Alternatives

| Alt | Geometry | Inner ligament | Outer ligament | Disposition |
|---|---|---:|---:|---|
| C0 | OD36 round, 3×M3, PCD28 | 2.00 | 2.30 | verified reference |
| C1 | OD34 round, 3×M3, PCD27 | 1.50 | 1.80 | backup study |
| C2 | OD33 round, 3×M2.5, PCD26.5 | 1.50 | 1.80 | **preferred first CAD study** |
| C3 | 3-lobed M2.5, PCD26.5 | 1.50 | local | only if C2 still too large |

## Why C2 first

C2 attacks packaging while preserving the simpler manufacturing route: turning + drilling/tapping. It avoids adding a milled three-lobe profile unless that extra operation is actually justified. Typical ISO 4762 M2.5 head geometry is about Ø4.5×2.5 mm versus M3 about Ø5.5×3.0 mm. Head outer radial envelope is therefore about Ø31 mm for M2.5/PCD26.5 versus Ø33.5 mm for M3/PCD28.

## Fastener material-capacity screen

Metric coarse tensile-stress-area screening:
- M2.5×0.45: As ≈ 3.39 mm²; at 450 MPa → ≈1526 N/screw.
- M3×0.5: As ≈ 5.03 mm²; at 450 MPa → ≈2264 N/screw.

The previous pressure reaction 3.1225 N is only 0.068% of the combined 0.2%-proof screen of three M2.5 screws. Therefore pressure does **not** size the screws. Governing unknowns are seal compression, preload scatter, thread stripping/bearing, stainless galling, service cycles and tool access. Torque remains OPEN until grade/finish/lubrication are frozen.

## C2 hard gates before selection

1. Native CAD + exact tool/interference envelope.
2. Thread engagement, stripping and head-bearing check.
3. Local flange bending / contact screen or FEA.
4. Seal compression and flange-separation check.
5. Thermal expansion/preload sensitivity.
6. Repeated-service and anti-galling strategy.
7. P007 +0.20 bar static refresh.
8. P007 -0.20 bar buckling refresh.
9. Manufacturing route and inspection plan.
10. Standard fastener availability / BOM.
11. Assembly verification and atomic promotion gate.

## Recommendation

Build **C2 round OD33 / 3×M2.5 / PCD26.5** first. Move to C3 three-lobed only if C2 still violates packaging requirements.
