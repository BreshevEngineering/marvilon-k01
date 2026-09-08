# K01 Engineering Decision Audit — First System Pass

This is not a declaration that every existing solution is wrong. It identifies where evidence is already strong and where the current evidence chain is incomplete.

## Highest-priority reopened / incomplete decisions

1. **J2 flange / fastener compactness — REOPENED**
   - OD36 works, but packaging optimality was not proven.
   - Run C2 compact study first.

2. **P007 thin wall 0.30 mm — PARTIAL**
   - Static/buckling evidence exists.
   - Still needs production-process capability, ovality/runout, thermal and final-flange refresh.

3. **P015 coil/bobbin — OPEN**
   - Production material grade, winding, leads and thermal state are not released.
   - Blocks final FEMM and production release.

4. **B001 magnet — OPEN**
   - Supplier lot magnetic data and temperature dependence are missing.

5. **P013/B001 retention — OPEN**
   - Retention method needs mechanical/thermal/cleanliness qualification.

6. **P014 spring retaining ring — OPEN**
   - Material/temper and fatigue behavior are not frozen.

7. **Datum C / P017 — concept good, implementation OPEN**
   - Need native CAD, press fit, manufacturing and inspection evidence.

8. **J1 P016↔P003 production interface — PARTIAL**
   - Functional datum logic is sound.
   - Long Run production material and final manufacturing sequence remain open.

9. **P006 service plug — PARTIAL**
   - M12×1 retained.
   - Service-tool feature, anti-galling and repeated-service review still open.

10. **Rod/bushing system — PARTIAL**
    - Need final polymer/material, creep/wear/thermal clearance and production tolerance evidence.

## System-level decisions to backfill as EDRs

- hermetic magnetic actuation vs alternative feedthrough architectures;
- closed metallic can material/thickness principle;
- magnetic follower architecture;
- dual-coil actuation architecture;
- overall service strategy;
- SW2018→SW2026 configuration-management strategy.

## New project rule

No future non-trivial decision moves from idea directly into production CAD without an EDR ID. CAD feature names, reports and change-control entries should carry the EDR ID where practical.
