# K01-D-006 Manual Finish Workpack — CURRENT

## Objective
Finish the **existing linked K01-D-006 SLDDRW candidate** as a professional native SOLIDWORKS drawing while preserving model/PMI associativity and the digital thread.

The structural drawing is not rebuilt from zero. API owns the candidate copy, existing views/section, scale/position refinement, native-PMI transfer bridge, semantic verification, exports and source invariance. Human work is the final 10–20% visual last mile only after semantic PMI transfer PASS.

## Recommended current action

1. Do **not** open SOLIDWORKS to recreate the drawing or retype C02/C05. Keep SOLIDWORKS closed for the controlled automation-first run.

2. The proven Step13 PMI source remains immutable evidence. The automation creates a separate drawing-authoring copy and corrects only PMI semantics there:
   - C02 `Cylinder1/Diameter2` -> `Ø14.10 H7`;
   - C05 `Cylinder2/Diameter4` -> nominal `Ø33.00`, tolerance type NONE because release tolerance is OPEN.

3. The existing linked K01-D-006 candidate is copied, not rebuilt. Its existing longitudinal/section, flange-end, side and isometric views are preserved and refined.

4. On the timestamped drawing copy, the SW2018 compatibility bridge uses the native Drawing View import path:
   - `Import annotations` = ON;
   - `DimXpert annotations` = ON;
   - `Design annotations` = OFF.

5. Machine verification must identify exact native PMI bindings after import:
   - C02 = `Cylinder1/Diameter2`, tolerance type FIT, hole fit `H7`;
   - C05 = `Cylinder2/Diameter4`, tolerance type NONE.
   `DIMXPERT_COUNT=0` is HOLD, never PASS.

6. Only after semantic PASS, use this workpack for the final human visual cleanup: annotation placement, leader routing, spacing, line/font cleanup and visual QA. Do not replace native PMI with typed dimensions.

7. Remove from the drawing sheet:
    - API status text;
    - persistent-ref information;
    - large OPEN-items table;
    - giant full filename;
    - duplicate title/status tables;
    - redundant side view.

8. Keep one standard title block only.

9. Use a short review marking:
    `DESIGN REVIEW - NOT FOR MANUFACTURE`

10. Show only controlled engineering content. Keep unresolved release items in the external workpack, not as large sheet text.

## Suggested view placement on A3 landscape

- left/centre: longitudinal section, 5:1
- upper/right: flange end view, 5:1
- lower/right: J2 Detail B, 8:1 or 10:1 if needed
- small corner: isometric, 2:1

A4 landscape may be used only if the imported PMI remains comfortably readable.

## Current data that may be shown

- C02: Ø14.10 H7; depth 2.00 nominal; native PMI Ø14.10 PASS; depth tolerance OPEN
- C04: 3×Ø2.90 THRU on PCD Ø26.50 nominal; position tolerance OPEN
- C05: Ø33.00 nominal × 3.00 nominal; native PMI Ø33 PASS; release tolerances OPEN
- C06: OAL 35.00 nominal; release tolerance OPEN
- C07: Ø10.00 nominal; tolerance OPEN
- C08: Ø9.40 nominal / wall 0.30 nominal; tolerance OPEN
- blind end: 1.00 nominal; release tolerance/inspection OPEN
- C09 material: AISI 316L / EN 1.4404

Do not invent C03/C10/C11/C12 or any missing release tolerance.

## Finish rule

Manual work is limited to final presentation after automated semantic PASS.
The value semantics must remain model-linked / registry-controlled.

After final visual save, rerun automated semantic QA before any release claim.
