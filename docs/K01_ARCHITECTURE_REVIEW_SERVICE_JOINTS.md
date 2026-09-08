# K01 architecture review — why two detachable joints are correct

## Conclusion

Two detachable joints are justified by two different service boundaries:

**J1 — P016 ↔ P003:** installation/removal boundary.  
It allows the whole calibration cartridge to be removed from the Long Run
without opening the cartridge.

**J2 — P003 ↔ P007:** internal-service boundary.  
It allows access to P006 and the P008/B001/P013 follower group.

With the current rear-loaded internal stack, one detachable joint cannot provide
both functions without a major topology redesign. A single P016↔P003 joint plus
a permanently closed P007 would make the internal follower non-serviceable.
Moving the opening to a removable rear cap still leaves two service joints and
places a seal/closure closer to the magnetic active region.

Therefore: **keep two joints, but standardize their engineering philosophy.**

## Common joint philosophy

Both joints:
1. locate axially on metal-to-metal faces;
2. locate radially on a cylindrical H7/g6 pilot;
3. use a static axial O-ring seal;
4. use screws only as clamps;
5. allow disassembly without cutting, welding or disturbing the Long Run.

The joints should be similar in logic, not artificially identical in dimensions.

### J1 P016↔P003 — keep
- Ø10 H7/g6 pilot, 3.2/3.0 engagement;
- 12×1.5 O-ring baseline;
- 3×M4 on PCD24;
- M4×10 A4-70 gives ~7 mm nominal thread engagement;
- Datum C uses a relieved/diamond locator to avoid radial overconstraint.

### J2 P003↔P007 — optimize
- Ø16 H7/g6 pilot;
- 1.5-mm cross-section static face-seal philosophy;
- 3×M3 on PCD28, not 4×M3;
- OD34 flange candidate.

Three screws at 120° are preferred here because the seal and structure are
axisymmetric. The measured/analytical pressure resultant is only ~3.123 N, so
pressure strength does not justify four screws.

Parker's O-ring handbook describes axial face compression as a standard static
seal arrangement and notes that static O-rings do not require large bolting
forces when the gland is correctly designed. Final gland dimensions and gas-side
surface finish shall be taken from the selected O-ring standard/supplier, not
invented from CAD convenience.

## Why not a threaded P007 can

A direct thread on the current OD16/ID14.1 P007 root leaves little radial metal,
adds 316L-on-316L galling risk, twists the seal during service and requires
rotating a long thin can. A piloted bolted flange is more robust and easier to
inspect.

## Why not weld

Permanent P003↔P007 welding is rejected as the production baseline because it
prevents routine service access to P006/follower hardware.
