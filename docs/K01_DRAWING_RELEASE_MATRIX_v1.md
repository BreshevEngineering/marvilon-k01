# K01 drawing release matrix

Final drawings are generated through the SolidWorks API after Datum C and the
serviceable P003↔P007 joint are frozen.

| ID | Drawing | Required contents |
|---|---|---|
| P001 | K01-D-001 | rod diameters/length, collar, tip, anti-rotation, material, finish |
| P002 | K01-D-002 | guide bore/OD, anti-rotation geometry, PEEK grade, clearances |
| P003 | K01-D-003 | all internal steps/stops, M12×1, A/B/C, P016 flange, P007 service joint |
| P004 | K01-D-004 | front guide geometry/fit/material |
| P006 | K01-D-006P | M12×1, Ø9.10 relief, Ø6 bore, service-tool feature |
| P007 | K01-D-007 | ID14.1/root, OD10/ID9.4/t0.30, blind wall, service flange, inspection |
| P008 | K01-D-008 | follower OD/pocket/M4/shoulder, magnet acceptance note |
| P009 | K01-D-009 | stop washer dimensions/material |
| P013 | K01-D-013 | end-cap geometry, bond face, no-preload note |
| P014 | K01-D-014 | ring geometry, spring material/temper |
| P015 | K01-D-015 | bobbin geometry, material, coil winding/lead exit |
| P016 | K01-D-016 | saddle/port, A/B, M4, O-ring groove, C press-pin hole, post-join machining |
| P017 | K01-D-017 | press shank and relieved/diamond clocking geometry |
| A001 | K01-D-012 | sectioned assembly, IN/OUT states, BOM, seals, fasteners, assembly notes |
| INSTALL | K01-D-018 | P016→Long Run installation/joining/finish-machining inspection chain |

## API drawing pipeline

Native SLDPRT/SLDASM + master → SLDDRW views/sections/dimensions/datums/notes/BOM
→ PDF release derivative + DXF only where manufacturing needs it → JSON drawing
manifest.

No independent manual redrawing is allowed.
