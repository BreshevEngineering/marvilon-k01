# K01 current gates — 2026-09-01

## Closed / conditional
- **API Gate 01 — PASS:** native SolidWorks read-only COM snapshot.
- **API Gate 02 — PASS:** native sketch + native Boss-Extrude created through API.
- **P003 flange geometry — PASS:** Ø34 x 3, 3x M4 clearance, one final solid body.
- **P003/P016 A+B locating architecture — CONDITIONAL PASS:** H7/g6 and named datums implemented.

## Immediate checks
1. Measure P003 pilot-end face to P016 counterbore-bottom annular face.
   Target: **0.20 mm** with Datum A fully seated.
2. Confirm one free rotational DOF remains with only Datum A + Datum B mates.
3. Freeze Datum C physical clocking without overconstraining A+B.

## Next major mechanical gates
1. **P016 -> Long Run:** production material, saddle/weld, post-weld Datum A finish, Ø10 H7 finish/inspection relative to actual Ø20 channel axis.
2. **P007 -> P003:** root seat, thick weld zone, qualified joining process, containment boundary, helium leak acceptance.
3. P014 production material / retention.
4. P015 production material / coil mounting / electrical lead and connector release.

## Verification still open
- B001 incoming D/L and Br(T).
- Breakaway force hot/cold both directions.
- CFD OUT/MID/IN envelope.
- Final magnetic FEM with actual B001 data.
- Thermal pulse test.
- Kinematic/hard-stop/no-power dwell tests.
