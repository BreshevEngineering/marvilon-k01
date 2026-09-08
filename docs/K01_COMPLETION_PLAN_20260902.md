# K01 completion plan — 2026-09-02

## Definition of "complete"

Separate two states:

1. **DESIGN FREEZE** — all geometry, materials/specifications, interfaces, calculations,
   drawings/notes, BOM and force budgets are frozen. This can be completed now without
   buying B001 or manufacturing hardware.
2. **PRODUCTION RELEASE** — supplier CoC/incoming inspection, physical breakaway,
   weld qualification, leak test, bench actuation, thermal and optical repeatability.
   These are acceptance/qualification activities and do not block design freeze.

## Already closed

- P003/P007 interface architecture: PASS.
- P003 native-history rear OD16 x 5 mm collar candidate: PASS.
- P007 native-history trim to L35: PASS.
- Gate03I assembly: 26 mates before/after, 0 errors, zero transform shift.
- Manual interference: no new P003/P007 pair.
- P007 +0.20 bar static: PASS screen; reaction 3.1225 N matches analytical 3.123 N.
- P007 -0.20 bar eigen-buckling: PASS screen; lambda1 = 1883.6.
- Fixed-coil magnetic concept: PASS screen at nominal B001, Br lower bound 1.00 T.
- P015 current geometry: keep.

## Remaining design-freeze sequence

1. Promote Gate03G P003 and Gate03H P007 to the **stable production filenames**.
   Do not make K01-A-001 reference files under `cad/candidates`.
2. Keep P008 current native geometry. Gate04A direct D1 edit is rejected because it
   translated the complete part axis by -0.050 mm.
3. Freeze fit without buying a magnet:
   - P008 pocket nominal Ø8.10, drawing fit H9;
   - B001 functional diameter acceptance Ø8 h9 or equivalent incoming sorting;
   - stock MTS ±0.1 remains only a supplier candidate and may need sorting.
4. Freeze P014 material.
5. Freeze P015 production PPS/winding/lead/driver specification.
6. Correct P009 and P013 CAD material metadata to controlled 316L.
7. Freeze Datum C and P016-to-Long-Run installation/inspection route.
8. Freeze optical target/anti-rotation release definition.
9. Run **one final CFD set only**: OUT / MID / IN, same BC and mesh, gas-wetted
   `SG Force(X)2`. No hot sweep now unless the result is close to the force limit.
10. Close actuator force budget using design acceptance:
    - breakaway acceptance max = 0.25 N;
    - current capability = 1.25 A;
    - K_F,min screen = 1.00 N/A;
    - inertia = 0.03 N;
    - therefore allowable CFD max = 0.345 N.
11. Synchronize master/BOM/Git and create design-freeze commit/tag.
12. Move project to SW2026 laptop and integrate frozen K01 into authoritative MARV project.

## CFD answer

CFD is still needed, but only as **one of the last design calculations**.
It is not necessary to repeat the old broad Flow Simulation program.
Run only OUT/MID/IN at the controlled worst operating boundary condition.

If max |Fx| <= 0.345 N, the current 1.25 A actuator capability closes the
force budget for the specified breakaway acceptance <=0.25 N.

## Physical tasks intentionally deferred

- purchase B001;
- actual B001 D/L and Br(T);
- breakaway measurement;
- P013 bond qualification;
- P007 WPS and helium leak;
- actuator bench test;
- thermal pulse verification;
- final optical repeatability.

These become production-release gates, not blockers for CAD/design completion.
