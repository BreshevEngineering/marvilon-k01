# MEDTAS v1.3

- Root-caused v1.2 CAD semantic failure: dynamic COM binder fails with `0x8002802B TYPE_E_ELEMENTNOTFOUND` while dispatching `OpenDoc6`.
- Replaced dynamic SolidWorks application calls with early-bound SolidWorks interop.
- Added automatic interop discovery/compile diagnostics.
- Added unified local Center v9: legacy v8 API + MEDTAS graph sidecar under one browser origin.
- Added Build Graph tab to existing Command Center UI.
- Added `K01.STRUCT.FACE_MAP.P006` and face-signature candidate generation.
- CalculiX now fails closed on unconfirmed boundary-role mapping rather than generating a misleading `.inp`.
- Existing FEM/FEMM evidence remains registered in the graph and Center.
