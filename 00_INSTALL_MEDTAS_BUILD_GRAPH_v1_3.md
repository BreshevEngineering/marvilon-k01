# K01 MEDTAS v1.3 installation

Overlay target: `D:\BreshevEngineering\marvilon-k01\`

Extract this archive directly over the repository root, preserving existing files. This package is incremental over v1.2.

## Important changes

1. `K01CadSemanticA001.cs` no longer uses C# `dynamic` to call the SolidWorks application. The v1.2 failure `TYPE_E_ELEMENTNOTFOUND` occurred during dynamic COM binding before `OpenDoc6`. v1.3 compiles against the installed SolidWorks interop assemblies and uses early-bound `SldWorks / ModelDoc2 / AssemblyDoc / Component2` interfaces.
2. `03_RUN_MEDTAS_PIPELINE.cmd` locates the installed SolidWorks interop DLLs, compiles the exporter, extracts CAD semantics, builds downstream nodes, creates a neutral-solver face-map candidate, runs CalculiX preflight and rebuilds derived state.
3. `OPEN_K01_COMMAND_CENTER_V9.cmd` starts the existing v8 API backend in the background and a local unified proxy on `http://127.0.0.1:8790/`. Existing Command Center tabs continue to use the v8 API; the new **Build Graph** tab uses the MEDTAS graph feed.
4. `K01.STRUCT.FACE_MAP.P006` is now a first-class fail-closed node between the solver-neutral structural model and CalculiX. Runtime face indices are explicitly non-authoritative.

## Normal workflow

- Keep SolidWorks open.
- Run `03_RUN_MEDTAS_PIPELINE.cmd` when CAD/build state must be refreshed.
- Run `OPEN_K01_COMMAND_CENTER_V9.cmd` for the persistent local engineering center.
- Use the **Build Graph** tab to inspect frontier, hashes, failures, evidence and CalculiX readiness.

Do not open `reports\control\K01_MEDTAS_CENTER_CURRENT.html` as the primary center; it remains a generated diagnostic/materialized artifact only.
