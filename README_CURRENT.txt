K01 STAGE3 CONTROL V9 — CURRENT ORDER

KEY CORRECTIONS
1) Gate04B v6 failed only because P016 was the active document.
   Gate04B v7 auto-opens/activates stable K01-A-001.
2) The 78-change master output with B007 qty=2 is the OLD/SUPERSEDED patch.
   Use ONLY 03_MASTER_COMPLETENESS_V2_DRYRUN; it must print B007 qty_design='AR'.
3) CFD positional envelope is CLOSED:
   OUT 0 mm |Fx|=0.185399974 N
   MID 5 mm |Fx|=0.185420895 N
   IN 10 mm |Fx|=0.185447243 N
   F_CFD,max=0.185447243 N.
4) Do NOT manually change J2 to M3 yet.
   3×M3 remains the preferred count/size, but the previous OD34/PCD28 flange
   is too tight: with Ø3.4 holes outer ligament is only 1.3 mm.
   Run Gate04C0 read-only first.
   Current compact screen is OD36 / PCD28; backup OD38 / PCD30.
   Exact O-ring face-gland dimensions remain supplier/ISO3601 controlled.

RUN NOW
1 control\01_GATE04B_DATUM_C_V7_AUTOACTIVATE.cmd
2 control\02_GATE04C0_J2_ENVELOPE_PROBE_READONLY.cmd
3 control\03_MASTER_COMPLETENESS_V2_DRYRUN.cmd
4 control\04_REPO_DEEP_STRUCTURE_AUDIT_V2.cmd

NO APPLY / NO GIT COMMIT YET.

After Gate04B PASS + Gate04C0 envelope confirmation:
- freeze exact J2 flange OD / PCD / O-ring gland;
- Gate04C native P003/P007 M3 service joint;
- assembly QA/interference;
- structural refresh;
- final FEMM;
- API drawings;
- final BOM/property sync;
- Git commit/push and design-freeze tag.
