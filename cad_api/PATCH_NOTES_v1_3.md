# Gate04C Typed API v1.3 — package root/runtime path fix

## Evidence from the real run

v1.2:
- found SOLIDWORKS 2018 interop DLLs;
- found the .NET Framework compiler;
- compiled `K01Gate04C_Build.cs` successfully;
- started `K01Gate04C_Build.exe`.

It then failed before SOLIDWORKS CAD access because the EXE was launched from
`bin\`, causing:

`AppDomain.CurrentDomain.BaseDirectory = ...\cad_api\bin\`

while:

`K01_GATE04C_PARAMS_v1.json`

was stored in the package directory one level above.

## v1.3 fix

All three typed EXEs now resolve the package root by checking:
1. EXE directory;
2. EXE parent directory;
3. current working directory;
4. current working directory parent.

The three CMD launchers also copy the current parameter JSON into `bin\` before
each launch.

No CAD geometry, J2 dimensions, materials, BOM data, drawing requirements, or
FEMM gates changed.
