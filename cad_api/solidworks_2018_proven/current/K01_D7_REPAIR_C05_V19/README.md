# K01 D7 repair C05 V19

Purpose: remove the only D7 blocker proven on the SAME K01-D-006 exemplar.

Allowed mutation:
- delete exactly one visible drawing DisplayDimension classified as C05 (`Cylinder2/Diameter4` or unique linked Ø33 semantic fallback) from P007 drawing views.

Required before mutation:
- exactly one visible Datum A;
- exactly one visible C02 Ø14.10 H7;
- exactly one visible C05;
- zero other visible dimensions.

Required after save/reopen:
- Datum A remains 1;
- C02 remains 1;
- C05 becomes 0;
- other visible dimensions remain 0.

The helper does not alter the P007 model PMI, canonical CAD, dimensions, tolerances, sheet environment, or other annotations.
Deletion uses the already proven SW2018 path:
`Annotation.Select3` -> `ModelDocExtension.DeleteSelection2(swDelete_Absorbed)`.
