# K01 D006 automation-first native PMI V6

This is a controlled SW2018 compatibility bridge. It does **not** rebuild the drawing.

Sequence on timestamped copies only:
1. copy the proven P007 PMI evidence part to `p007_drawing_authoring`;
2. change only PMI semantics: C02 `Diameter2/Cylinder1` -> hole fit H7, C05 `Diameter4/Cylinder2` -> tolerance NONE (OPEN release tolerance); save-close-reopen and prove solid geometry invariant;
3. copy the existing linked D006 candidate and reference-safely relink only that copy to the drawing-authoring part;
4. preserve existing views and use native SW2018 Drawing View `Import annotations` with DimXpert ON and Design annotations OFF through a narrow Windows UI Automation bridge;
5. machine-verify exact C02/C05 identities and tolerance semantics in the drawing;
6. save SLDDRW/PDF/BMP only on semantic PASS; source drawing and proven PMI evidence part are SHA-invariant.

A bridge/UI mismatch is HOLD with diagnostics. It is never converted to manual redraw.
