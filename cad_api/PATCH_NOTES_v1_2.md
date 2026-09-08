# Gate04C Typed API v1.2 — actual SW2018 interop signature correction

The user's real SOLIDWORKS 2018 interop compiler is authoritative.

Observed directly during compilation:

- `ISldWorks.OpenDoc6(..., ref int Errors, ref int Warnings)`
- `IModelDoc2.Save3(..., ref int Errors, ref int Warnings)`

Therefore v1.1's proactive `out` change was wrong for this installed interop
assembly. v1.2 restores `ref` for these methods and also uses `ref` for
`IAssemblyDoc.AddMate5` error status to match the same interop convention.

The valid v1.1 correction is retained:
- `Face2` is explicitly cast to `Entity` and selected through
  `IEntity.Select4`.

No controlled geometry, material, BOM, drawing, or FEMM requirement changed.
Stable CAD is still never the direct write target.
