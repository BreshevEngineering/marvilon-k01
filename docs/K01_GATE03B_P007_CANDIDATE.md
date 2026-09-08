# K01 Gate 03B — P007 candidate

## Why the geometry changes

Gate03A proved the current production geometry has:
- P003 rear face: OD 14.000 / bore ID 10.917.
- P007 current sleeve bore: ID 14.100.
- Current axial overlap P003↔P007: exactly 5.000 mm.
- P007 thin ID start is 2.000 mm behind the P003 rear face.
- P007 thin OD start is 3.000 mm behind the P003 rear face.

That means the existing 5 mm sleeve overlap is not needed to preserve the
magnetic thin-zone position. Gate03B removes only that overlap and creates a
butt-weld neck matching the existing P003 rear cross-section.

## Candidate section from weld plane

x=0..1 mm:
- OD 14.000
- ID 10.917
- radial wall 1.5415 mm
- direct thickness match to P003 rear end

x=1..2 mm:
- OD 16.000
- ID 10.917

x=2..3 mm:
- OD 16.000
- ID 9.400

x=3..34 mm:
- OD 10.000
- ID 9.400
- wall 0.300 mm

x=34..35 mm:
- blind rear wall, 1.000 mm axial thickness

## Status

CANDIDATE ONLY. Do not replace production P007 yet.

Next gate after native build:
- insert candidate into copied K01-A-001,
- mate weld face to current P003 rear face,
- verify downstream thin-zone stations are unchanged,
- collision/interference,
- then Static/Buckling.
