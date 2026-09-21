# K01 Rotational Drawing API R1

Purpose: generate a **usable rough drawing by API**, not a perfect released drawing.

The existing proven `K01DrawingSystemV1.cs` remains the authoring engine.

This family layer supplies:
- a repeatable runner;
- a rotational-family policy;
- part-specific Drawing Specs.

The API should create SLDDRW + PDF + DXF with all currently controlled information
placed on the sheet. Manual finishing is expected for:
- leader routing;
- annotation spacing;
- text overlap;
- view spacing;
- hatch/presentation cleanup.

A release HOLD must not stop generation.

## D005

Run:

`RUN_GENERATE_K01_D005_ROUGH_DRAWING.cmd`

Expected result:
a new timestamped candidate under:

`D:\Marvilon\K01\cad\drawings\candidates\K01-D-005\drawing_system_v1_YYYYMMDD_HHMMSS\generated\`

with:
- `K01-D-005.SLDDRW`
- `K01-D-005.PDF`
- `K01-D-005.DXF`
- `K01-D-005.BMP`

The generated sheet intentionally includes open engineering items as review notes.
