# Gate04C Typed API v1.1 — compile correction

Observed on the user's actual SOLIDWORKS 2018 interop DLL:

`Face2` does not expose `Select4` in C#.

This is expected from the SW object model: `Select4` is an `IEntity` method.
The v1.1 source now explicitly casts `Face2` to `Entity` before selection.

Also corrected proactively from the official C# signatures:
- `ISldWorks.OpenDoc6(..., out Errors, out Warnings)`
- `IModelDoc2.Save3(..., out Errors, out Warnings)`
- `IAssemblyDoc.AddMate5(..., out ErrorStatus)`

Gate04C geometry is unchanged.
Stable CAD remains protected.
