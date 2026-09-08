# K01 manufacturing, inspection and assembly router — design-freeze baseline

This document defines the manufacturing logic. Exact machining dimensions stay
on native CAD/drawings.

## MAKE parts

### P001 Calibration Rod — 316L
Route: turn/grind rod → machine working tip/collar/anti-rotation feature →
deburr/polish gas-wetted surfaces → dimensional inspection → straightness/runout
check → clean.

### P002 Rear Guide / Anti-Rotation Bushing — TECAPEEK PVX baseline
Route: turn OD/ID → machine anti-rotation geometry → finish bore → inspect
diametral clearance/endplay interface → clean. No uncontrolled reaming in
assembly.

### P003 Cartridge Body — 316L
Route: turn coaxial functional diameters and internal steps → M12×1 internal
retention geometry → mill/drill front P016 flange pattern → machine Datum-C hole
from same datum system as A/B → machine final rear P007 service-flange/pilot/
seal-gland/3×M3 features → inspect A/B/C and stop chain → passivate/clean.

### P004 Front Guide Bushing — TECAPEEK PVX baseline
Turn OD/ID and shoulder → finish bore → inspect fit/clearance → clean.

### P006 Retaining Plug — 316L
Turn body/Ø9.10 relief/Ø6 bore → cut M12×1 → add service-tool feature →
inspect relief and thread → clean. M12×1 and 6-mm engagement remain baseline.

### P007 Hermetic Magnetic Can — 316L
Machine from certified stock. Deep-drill/bore ID9.4 leaving integral rear wall →
finish ID14.1/root region → finish OD10 thin wall with supported low-force
workholding → machine front removable-service flange and Ø16 H7 counterbore →
drill 3×Ø3.4 clamp holes → inspect wall thickness/ovality/runout and flange face.
No rear-cap weld.

### P008 Internal Magnetic Follower — 316L
Turn OD/pocket/shoulder → machine M4 interface → inspect magnet pocket and
P001 shoulder interface → clean. Pocket final acceptance remains tied to B001
functional-size specification; failed Ø8.20 direct-edit candidate is rejected.

### P009 Rear Stop Washer — 316L
Turn washer → deburr → thickness/OD/ID inspection → correct SW material metadata.

### P013 Follower End Cap — 316L
Turn cap → inspect annular bond face → clean for qualified adhesive process.
No preload on B001.

### P014 Front Guide Retaining Ring — 1.4310/AISI301 spring stainless candidate
Finalize spring temper → laser cut/stamp/machine → deburr/edge-finish → verify
installation/removal and stop function.

### P015 Dual Coil Bobbin — PPS production grade OPEN
After grade freeze: machine/mold bobbin → wind two fixed coils per winding spec →
terminate leads → resistance/insulation check → thermal pulse validation.

### P016 Long Run Interface Boss
Material must be compatible with actual Long Run. Rough-machine saddle/port →
join to Long Run in fixture → cool → finish Datum A and Ø10 H7 B relative to
actual Ø20 channel axis → finish M4 pattern and C press-pin hole → clean/leak test.

### P017 Datum-C relieved/diamond pin
Turn Ø3 press shank → grind/mill two radial-relief flats on protruding section →
inspect major/minor widths and orientation → press into P016 after P016 finish
machining.

## Subassembly sequence

1. Verify cleaned P003, P001, P002, P004, P006, P008, P009, P013, P014.
2. Install guide/stop stack into P003 from the designed service direction.
3. Set P002 axial float using P006 relief; install P006.
4. Install P001 and verify free guide motion.
5. Assemble P008/B001/P013 follower group; verify P008-to-P001 shoulder contact
   and no M4 bottoming.
6. Verify full 10.00-mm hard-stop travel before closing P007.
7. Install P007 static seal, slide P007 over follower, seat Ø16 pilot and metal
   faces, install 3×M3 clamps in cross/120° sequence.
8. Verify no P008↔P007 rub throughout the 10-mm stroke.
9. Slide/install P015 outside P007 and complete electrical termination.
10. Install complete K01 cartridge on P016 using A/B/C, then 3×M4 clamps.
11. Verify OUT flush and IN channel-axis position.
12. Electrical functional test, resistance, actuation check, then optical
    calibration verification.
13. Production validation later adds leak test, breakaway, thermal, magnetic
    bench and gas compatibility evidence.

## Service sequence

External module removal: undo J1 only.  
Internal follower service: remove module if convenient, then undo J2.  
No containment weld cutting is permitted in normal service.
