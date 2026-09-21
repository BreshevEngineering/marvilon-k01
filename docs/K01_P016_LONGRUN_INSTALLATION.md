# K01 P016 → Long Run — professional installation baseline (Datum C v2)

> **EDR-023 implementation update (2026-09-09):** the manufacturing/installation logic below remains applicable,
> but the earlier radial-slot implementation detail is superseded by the current Gate04B v7 baseline:
> relieved/diamond P017 + P003 Ø3.02 round mating hole. See `control/decisions/EDR-023_DATUM_C_KINEMATIC_BASELINE.json`.

## Kinematic locating hierarchy

A — final machined metal-to-metal mating face.
B — final Ø10 H7 pilot-bore axis.
C — one peripheral **relieved/diamond K01-P-017 locator**. P017 is pressed into P016 and engages the P003 Ø3.02 +0.01/0 round THRU mating hole. Radial relief is carried by P017; the P003 hole is round.

A + B establish axial position and the transverse axis. After A/B engagement the only remaining rigid-body degree of freedom is rotation about B. C therefore removes only that clocking DOF.

A second fully round peripheral locator would redundantly constrain pitch radius already located by B and may bind under independent machining errors. The accepted EDR-023 implementation avoids that redundancy by using a relieved/diamond P017 locator:

- P016: Ø3 H7 × 4.0 blind press-pin hole at R12 and the pattern-derived 30° free-gap midpoint;
- P017: Ø3 p6 × 4.0 press shank, 6.0 mm overall, radial minor 2.80 ±0.02 mm, tangential major 3.00 -0.01/0 mm; material baseline AISI 316L / EN 1.4404, native material-card assignment OPEN;
- P003: Ø3.02 +0.01/0 round mating hole, THRU, on the same Datum-C axis;
- P017 protrusion above Datum A: 2.0 mm;
- 3×M4 fasteners: clamp only; they do not establish A, B or C.

The earlier P003 radial-slot implementation is superseded design history only.

## P016-to-Long-Run manufacturing route

The current CAD assigns P016 as EN 1.4404 / AISI 316L. The actual production
Long Run material is still not evidenced, so final weld/material compatibility
remains OPEN and shall not be guessed.

Preferred sequence:

1. Prepare P016 saddle R24 and the actual Long Run OD48 joining zone.
2. Fixture P016 to Long Run using the Long Run/channel coordinate system.
3. Execute the qualified leak-tight P016-to-Long-Run joining process.
4. Cool completely.
5. Establish the actual Ø20 channel axis.
6. Finish-machine Datum A.
7. Finish-machine/ream Ø10 H7 Datum B relative to the actual channel axis.
8. Finish the P016 Ø3 H7 pin hole at R12 / the pattern-derived 30° free-gap midpoint and the 3×M4 pattern in the same
   controlled coordinate system.
9. Install P017 only after machining/inspection.
10. Machine/drill Ø6 passage through boss/Long Run wall in the controlled setup
    if process planning selects post-join port machining; deburr the inner wall.
11. Inspect channel-axis → Datum A = 37.00 mm and the 0.20 mm nominal pilot-end
    clearance to P016 counterbore bottom.
12. Leak-test the installed boss/Long Run joint.

Joining is a joining/sealing operation, not the positioning method.
