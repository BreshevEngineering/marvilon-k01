# K01 drawing release plan

Professional release should use native SolidWorks 3D as design authority plus
short controlled manufacturing drawings carrying datums, fits, process and
inspection notes.

## Drawings to update/create immediately after Gate04B PASS

### K01-D-003 — P003 Cartridge Body
Must include:
- material EN 1.4404 / AISI 316L;
- Datum A mating face;
- Datum B Ø10 g6 pilot axis;
- Datum C clock hole;
- flange Ø34 × 3;
- 3× Ø4.50 THRU on PCD24 / 120°;
- Datum-C radial slot width 3.02 +0.01/0, overall radial length 4.00 THRU, center R12 / 0°;
- rear OD16 × 5 weld collar;
- M12×1 and controlled guide/stop dimensions;
- note: M4 fasteners clamp only.

### K01-D-006 — P007 Hermetic Magnetic Can
Must include:
- material EN 1.4404 / AISI 316L;
- L35;
- OD16 / ID14.1 root;
- OD10 / ID9.4 thin wall;
- t0.30 controlled;
- integral 1.00 mm blind end;
- concentricity/ovality inspection requirement;
- P003 butt-weld interface;
- no separate rear-cap weld.

### New P016 drawing
Must include:
- material: `316L CURRENT CAD; RELEASE SUBJECT TO LONG RUN MATERIAL COMPATIBILITY`;
- saddle R24 for actual Long Run OD48;
- Datum A height from OD48 tangent = 13.00;
- Ø6 passage;
- Ø10 H7 × 3.20 pilot bore;
- 3×M4-6H PCD24 / 120°;
- O-ring groove ID11.80 / OD15.80 / depth1.20;
- Datum C Ø3 H7 × 4 blind pin hole at R12 / 0°;
- post-weld finish-machining note.

### P017 clocking pin drawing
Simple turned part:
- EN 1.4404 / AISI 316L;
- Ø3 p6;
- L6.00;
- C0.2 both ends;
- clean/deburr/passivate as specified.

### K01-D-012 — K01-A-001 assembly drawing
Update with:
- final P003/P007 section;
- P003↔P007 360° containment butt weld symbol/process note;
- A/B/C Long Run interface;
- assembly sequence reference;
- IN/OUT hard-stop states;
- BOM revision.

## Separate weld/installation drawing
P016-to-Long-Run installation should be controlled on a dedicated
weld/installation drawing rather than on the P016 part drawing alone. It should
show fixture references, weld extent, post-weld machining datums, Ø20 channel
axis, 37.00 mm channel-axis→Datum-A chain, and inspection sequence.
