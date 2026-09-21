# K01 ISO/TPD/GPS Drawing Standard Profile v1

This profile is the controlled basis for K01-D-006 and later Marvilon mechanical drawings. It is deliberately ISO/GPS-based, not a mixture of ISO and ASME conventions.

## Standards stack

- ISO 128-1:2020 — general execution of 2D/3D technical drawings.
- ISO 128-2:2022 — line types, line conventions, leaders/reference lines.
- ISO 129-1:2018 — presentation of dimensions and associated tolerances.
- ISO 3098-2:2000 — lettering.
- ISO 5455:1979 — drawing scales.
- ISO 5456-2:1996 — orthographic projection. K01 freezes **first-angle projection**.
- ISO 5457:1999 + Amd 1:2010 — drawing-sheet size/layout.
- ISO 7200:2004 — title-block/document-header fields.
- ISO 8015:2011 — GPS fundamentals.
- ISO 1101:2017 — geometrical tolerancing.
- ISO 5459:2024 — datums/datum systems.
- ISO 14405-1:2025 — linear sizes.
- ISO 16792:2021 — digital product definition; K01 uses 3D model + 2D drawing.

## Hard K01 rules

1. No hybrid ISO/ASME notation on one drawing.
2. First-angle projection is the project default; the controlled title block/sheet format must contain the first-angle symbol.
3. Use ISO 5455 preferred enlargement scales: 2:1, 5:1, 10:1, 20:1, 50:1. K01-D-006 uses 5:1 for main section/end view and 2:1 for parent/isometric unless a documented exception is approved.
4. 3:1 and 4:1 are not used in the controlled profile.
5. Dimension values are independent of drawing scale.
6. No uncontrolled general ± tolerance is allowed merely because the SOLIDWORKS template contains one. General-tolerance strategy must be an explicit engineering decision.
7. C02 Ø14.10 H7 and C05 Ø33.00 must stay linked to the controlled 3D PMI/Cxx authority; no free-text duplicates.
8. Material is AISI 316L / EN 1.4404.
9. One title block only. Full file paths/names, API status, persistent-reference state and debug information do not belong on the manufacturing drawing.
10. Production release requires both semantic QA and visual QA. Successful SLDDRW/PDF creation is not a standards-compliance PASS.

## Current D006 target

- A3 landscape.
- Main longitudinal section: SCALE 5:1.
- Flange end view: SCALE 5:1.
- Parent/side view retained only when required to generate the section: SCALE 2:1.
- Small isometric for orientation: SCALE 2:1, no manufacturing dimensions.
- Detail view may use 10:1 if the locator/seat annotation becomes crowded.

The current automated drawing remains a design-review candidate until the controlled K01 `.drwdot/.slddrt` pair and final visual/semantic QA are frozen.
