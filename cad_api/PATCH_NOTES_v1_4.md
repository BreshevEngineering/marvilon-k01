# Gate04C Typed API v1.4 — namespace ambiguity fix

Observed from the user's actual SOLIDWORKS 2018 compile:

`Environment` is ambiguous between:
- `System.Environment`
- `SolidWorks.Interop.sldworks.Environment`

v1.4 explicitly qualifies all runtime-environment references as:

- `System.Environment.CurrentDirectory`
- `System.Environment.NewLine`

No CAD geometry, materials, fits, BOM, drawing, Git, or FEMM requirements changed.
Stable CAD remains protected.
