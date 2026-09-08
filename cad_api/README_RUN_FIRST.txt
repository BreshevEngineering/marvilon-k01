K01 Gate04C — STRONGLY TYPED SOLIDWORKS API PACK v1.4
=====================================================

This package returns to the already-proven K01/SOLIDWORKS architecture:
external C# compiled against SolidWorks.Interop.sldworks.dll and
SolidWorks.Interop.swconst.dll.

NO Python COM. NO pywin32. NO VBA macro. NO manual rebuild of P003/P007.

RECOMMENDED LOCATION
--------------------
Extract the folder to:

D:\BreshevEngineering\marvilon-k01\cad_api\gate04c_typed\

Keep all package files together.

RUN
---
Start SOLIDWORKS 2018 normally, then double-click:

00_GATE04C_ALL.cmd

It performs three isolated stages:
1) K01Gate04C_Build.cs      -> native candidate P003/P007
2) K01Gate04C_Verify.cs     -> verification copy of A001
3) K01Gate04C_Drawings.cs   -> DRAFT_API SLDDRW + PDF for P003/P007

Each stage is compiled separately. A drawing API problem therefore cannot corrupt
or block the native CAD writer; a verification problem cannot modify stable CAD.

You can also run stages separately:
01_GATE04C_BUILD_ONLY.cmd
02_GATE04C_VERIFY_ONLY.cmd
03_GATE04C_DRAWINGS_ONLY.cmd

OUTPUT CAD
----------
D:\Marvilon\K01\cad\candidates\gate04c\
  K01-P-003_Cartridge_Body_GATE04C_CANDIDATE.SLDPRT
  K01-P-007_Hermetic_Magnetic_Can_GATE04C_CANDIDATE.SLDPRT

D:\Marvilon\K01\cad\candidates\gate04c\verification\
  K01-A-001_GATE04C_VERIFY.SLDASM

OUTPUT DRAWINGS
---------------
D:\Marvilon\K01\cad\drawings\gate04c_draft\
  K01-D-003_*_DRAFT_API.SLDDRW
  K01-D-003_*_DRAFT_API.PDF
  K01-D-006_*_DRAFT_API.SLDDRW
  K01-D-006_*_DRAFT_API.PDF

REPORTS
-------
D:\BreshevEngineering\marvilon-k01\reports\cad\current\
  K01_GATE04C_TYPED_BUILD.json
  K01_GATE04C_TYPED_VERIFY.json
  K01_GATE04C_TYPED_DRAWINGS.json
  K01_GATE04C_TYPED_*.log

DESIGN CONTROLS
---------------
P003 / P007 material: AISI 316L / EN 1.4404.
P003 J2 flange: OD36, material added inward in the existing 5-mm rear zone.
P003 pilot: OD14.10 g6 x 1.50 outward.
P003 seal: 16x1.5; compound OPEN.
P003 gland: ID16.00 / OD20.20 nominal / depth1.10.
P003 thread: M3x0.5-6H; first typed build uses native D2.50 tap-drill geometry
plus controlled thread metadata to avoid Toolbox/Hole-Wizard token instability.
P007: OD36 x3 flange inward; existing ID14.10 H7 locator retained; L35 retained.
Clamp pattern: one seed + native circular pattern, 3x120 degrees on PCD28.
P007 clearance: D3.40.

STABLE CAD POLICY
-----------------
The writer archives an old candidate, copies stable CAD to a candidate filename,
and modifies only the candidate. Stable P003/P007/A001 are never the direct
write target.

AFTER PASS
----------
Do not promote automatically. Run the existing K01 review/export/interference QA,
then promote P003+P007 atomically. Only after that:
master -> SW properties -> BOM comparison -> Git release records -> Gate04B ->
P007 static/buckling refresh -> P015/B001/B007 freeze -> final FEMM -> bench test.


V1.1 SW2018 COMPILE CORRECTIONS
-------------------------------
The first typed build reached the real SOLIDWORKS 2018 compiler and exposed a
specific interop-interface issue. v1.1 corrects it and also pre-corrects other
C# [Out] signatures before the next run:

- IFace2 does not expose Select4 directly in this interop assembly.
  Faces are explicitly cast to SolidWorks.Interop.sldworks.Entity and selected
  through IEntity::Select4, which is the documented SW2018 API path.
- ISldWorks::OpenDoc6 errors/warnings use C# `out`.
- IModelDoc2::Save3 errors/warnings use C# `out`.
- IAssemblyDoc::AddMate5 error status uses C# `out`.

No geometry or controlled Gate04C dimensions changed from v1.


V1.2 CORRECTION
---------------
The actual compiler output from the user's installed SW2018 interop DLL proves
that OpenDoc6 and Save3 use `ref`, not `out`, in this installation.
v1.2 follows those exact installed signatures. Face selection remains corrected
through IEntity.Select4.


V1.3 PATH CORRECTION
--------------------
The v1.2 C# source compiled successfully against the user's real SW2018 interop,
so the typed API stack is now proven to compile.

The runtime failure was only package-root resolution:
the EXE is intentionally built in `bin\`, so AppDomain.BaseDirectory points to
`...\bin\`, while K01_GATE04C_PARAMS_v1.json is one directory above.

v1.3 fixes this in two independent ways:
1. each EXE searches its own directory, parent directory, current working
   directory, and parent working directory for K01_GATE04C_PARAMS_v1.json;
2. each CMD also copies the current parameter JSON into `bin\` before launch.

This is an infrastructure-path correction only. No Gate04C CAD geometry changed.


V1.4 COMPILE CORRECTION
-----------------------
The actual SW2018 interop namespace also defines an `Environment` type.
All application/runtime environment references are now explicitly qualified as
`System.Environment`, removing that namespace ambiguity.
