# Gate04D-C2 native CAD runbook

This is the next controlled CAD study, not a production release.

Baseline:
- P003/P007 316L/1.4404
- round flange OD33
- 3×M2.5
- PCD26.5
- P007 flange t3
- P003 zone5
- pilot Ø14.10 H7/g6 unchanged
- current 16×1.5 seal geometry unchanged
- P007 L35

Use SOLIDWORKS 2018 revision 26.x.

Recommended first run:
`00_GATE04D_C2_BUILD_AND_VERIFY.cmd`

The builder:
- copies stable P003/P007 to `candidates\gate04d_c2`;
- checks C2 packaging arithmetic before CAD writes;
- builds native candidate features only;
- keeps stable CAD untouched.

The verifier:
- copies stable A001 to a new verification assembly;
- suppresses only guarded legacy J2 mates;
- replaces only P003/P007 with C2 candidates;
- creates pilot/face/M2.5 clocking mates;
- requires 0 active mate errors.

PASS does NOT authorize promotion. EDS-001 mechanical, thermal, sealing,
serviceability, manufacturing and evidence gates remain mandatory.
