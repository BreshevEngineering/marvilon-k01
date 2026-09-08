K01 Gate04C VERIFY V2

The previous saved verification file was not the failed in-memory state:
the read-only diagnostic shows 26 mates / 0 errors and stable P003/P007 paths.

Critical correction:
SOLIDWORKS 2018 swAddMateError_NoError = 1.
The previous verifier treated AddMate5 ErrorStatus=1 as failure, although it was success.

VERIFY V2 does not use Transform2 clocking.
It validates and suppresses only the obsolete J2 mates:
- Concentric5: P003/P007 legacy concentric
- Coincident5: P006/P007 legacy axial

Then it replaces P003/P007 candidates and creates:
- K01_J2_PILOT_CONCENTRIC: D14.10 pilot/locator
- K01_J2_AXIAL_FACE: direct P003/P007 metal faces
- K01_J2_CLOCKING_M3: one M3-hole axis pair

Old mates are suppressed, not deleted.
The verification file is saved even on HOLD.
Run only RUN_GATE04C_VERIFY_V2.cmd.
Do not rebuild candidates or run drawings yet.
