# K01-D-006 / K01-P-007 — MBD authoring checklist

**Rule:** live CAD owns nominal geometry. Tolerance/GD&T content must be authored in native PMI/MBD before drawing release. Legacy draft values are comparison candidates only.

## Engineering drift requiring resolution
- **P007-DRAWING-DRIFT-C02** — Live CAD locator is Ø14.10 × 2.00 mm while the legacy draft candidate says Ø14.10 H7 × 1.70. **Recommended:** Protect the verified frozen CAD geometry and supersede the 1.70-mm legacy draft candidate unless contrary functional evidence is produced. Do not resize P007 merely to make the draft match.

- **C01 — J2 face / datum A flatness**: `FLATNESS 0.03` → **MBD_AUTHORING_REQUIRED**
- **C02 — Locator / datum B**: `Ø14.10 H7 × 1.70` → **LIVE_CAD_CONFLICT_REVIEW**
- **C03 — Locator axis perpendicularity to A**: `PERP Ø0.03 TO A` → **MBD_AUTHORING_REQUIRED**
- **C04 — J2 clamp clearance pattern**: `3×Ø2.90 THRU; PCD26.50 BASIC; 120° BASIC; POS Ø0.15 |A|B` → **MBD_AUTHORING_REQUIRED**
- **C05 — Flange size**: `Ø33.00 ±0.05 × 3.00 ±0.05` → **MBD_AUTHORING_REQUIRED**
- **C06 — Overall length**: `35.00 ±0.05` → **MBD_AUTHORING_REQUIRED**
- **C07 — Thin can OD**: `Ø10.00; release tolerance/general-tolerance coverage OPEN` → **MBD_AUTHORING_REQUIRED**
- **C08 — Thin can ID**: `Ø9.40; release tolerance/general-tolerance coverage OPEN` → **MBD_AUTHORING_REQUIRED**
- **C09 — Material**: `AISI 316L / EN 1.4404` → **CONTROLLED_PRODUCT_DATA**
- **C10 — Containment weld interface/process**: `OPEN` → **OPEN_SPEC**
- **C11 — Critical concentricity/coaxiality control**: `OPEN` → **MBD_AUTHORING_REQUIRED**
- **C12 — Leak/containment acceptance reference**: `OPEN` → **OPEN_REQUIREMENT**

## Current blockers
- C01
- C02
- C03
- C04
- C05
- C06
- C07
- C08
- C10
- C11
- C12
