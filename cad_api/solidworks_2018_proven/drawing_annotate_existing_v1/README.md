# K01 Drawing Annotate Existing V1

This is the pragmatic path for K01 drawings.

The system does **not** try to create a perfect drawing from zero.

Workflow:

1. Create/import the basic drawing views manually or by any reliable SolidWorks method.
2. Save the SLDDRW.
3. Run this API against the existing drawing.
4. API applies the engineering content that is tedious/error-prone:
   - fits;
   - tolerances;
   - dimension prefix/suffix;
   - thread/relief/hole callout text;
   - title-block properties;
   - controlled requirement notes.
5. API exports candidate SLDDRW + PDF + DXF + BMP.
6. User manually finishes layout/leaders/sections/hatching.

The source drawing is never modified; a candidate copy is created.

Infrastructure reliability:
- uses the already-proven SW2018 Runtime Core;
- retries the whole candidate transaction up to 3 times for COM/open/save failures;
- semantic target errors are fail-fast and are not hidden by retries.

D005 currently uses the exact drawing whose native attachment inventory passed.
