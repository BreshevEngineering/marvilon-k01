# K01 / MARVILON — SOLIDWORKS 2018 API WORKING RULES v1

Status: CONTROLLED ENGINEERING RULESET
Runtime: SOLIDWORKS 2018 / API revision 26 / .NET Framework v4 / C# 5
Purpose: stop repeated rediscovery of already-proven SOLIDWORKS API behaviour.

## 1. Primary rule — PROVEN FIRST

Before writing or changing any SOLIDWORKS API implementation:

1. Identify the required capability, not the file name.
2. Query `K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json`.
3. If a PROVEN implementation exists on SW2018/API 26, reuse it or adapt it.
4. Do not create a parallel implementation for the same capability unless the proven implementation has a documented capability gap.
5. If a new implementation is unavoidable, the reason must be recorded before coding.
6. After a successful new path, freeze its exact source + hash + runtime + evidence into the proven bundle.

A successful path is an engineering asset. It must not be rediscovered in a later chat.

## 2. Local interop DLL is the signature authority

SOLIDWORKS web/API documentation defines semantics, but the exact C# COM marshaling signature used by this workstation is determined by the installed `SolidWorks.Interop.*.dll` and the local compiler.

Known workstation rules from actual compile/runtime evidence:

- `IFace2` does not expose `Select4` here. Cast face to `SolidWorks.Interop.sldworks.Entity`, then call `IEntity.Select4`.
- `ISldWorks.OpenDoc6(..., ref int Errors, ref int Warnings)` on the installed SW2018 interop.
- `IModelDoc2.Save3(..., ref int Errors, ref int Warnings)` on the installed SW2018 interop.
- `ISldWorks.IActivateDoc3(..., ref int Errors)` on the installed SW2018 interop.
- `IDimXpertDimensionTolerance.GetUpperAndLowerLimit(ref double, ref double)` on the installed interop. Do not call it unless it is required for acceptance.
- `IModelDocExtension.GetObjectByPersistReference3(..., out int ErrorCode)` is proven by the P007 persistent-reference rebind.
- SOLIDWORKS interop defines an `Environment` type; always use `System.Environment`.
- Methods such as `FirstFeature`, `GetNextFeature`, `GetFirstSubFeature`, `GetNextSubFeature` can surface as `object`; use explicit `as Feature`.
- `swAddMateError_NoError = 1` in this SW2018 environment. Do not assume zero means success.

If the compiler contradicts a generic example, do not patch randomly. Compare with this registry and an already-proven local implementation first.

## 3. Native CAD write safety

Stable/canonical CAD is never the first write target.

Required write sequence:

`authority/hash check -> compile -> candidate copy -> native write -> save -> close -> reopen -> semantic readback -> geometry/assembly QA -> explicit promotion`

Rules:

- Compile before candidate creation whenever possible.
- Write to a timestamped candidate on D:.
- Canonical CAD remains read-only during authoring experiments.
- Candidate failure must not mutate canonical CAD.
- Promotion is a separate controlled transaction with backup/staging/rollback.
- Never move existing project folders automatically.
- Never select C: or `%LOCALAPPDATA%` as an automatic project destination.

## 4. Acceptance is semantic, not return-code based

SOLIDWORKS API booleans and COM return codes are diagnostics, not automatically engineering truth.

Proven example: P007 Step13 returned `InsertSizeDimension=False`, but it actually created:
- `Cylinder1 -> Diameter2 -> nominal 14.10`
- `Cylinder2 -> Diameter4 -> nominal 33.00`

It then saved, closed, reopened, resolved both persistent IDs with state 0, and preserved geometry.

Therefore a native-write PASS requires evidence appropriate to the operation, for example:
- expected feature/annotation exists;
- expected nominal/semantic value reads back;
- persistent reference resolves after close/reopen;
- geometry fingerprint is invariant for PMI-only operations;
- mate/interference state is correct for assembly operations;
- canonical source hash remains unchanged when the operation is candidate-only.

## 5. P007 DimXpert rule

Capability `P007_DIMXPERT_WRITE_C02_C05` already has a PROVEN path: historical Step13.

Do not use `K01P007DimXpertPhaseA.cs` as the primary path for C02/C05 while the proven Step13 writer is available.

The experimental Phase-A C# writer is retained only as:
- diagnostic work,
- comparison evidence,
- possible future replacement after it independently passes the same regression suite.

The immediate engineering path is:
`freeze actual Step13 writer + transitive K01P007PmiStep13.cs core -> copy core byte-for-byte into controlled proven area -> adapt only current authority/hash/persistent-ref inputs -> run save-close-reopen regression -> continue to K01-D-006`.

The experimental `K01P007DimXpertPhaseA.cs` path is not to be debugged further on the current critical path.

## 6. Selection rules

For face selection:
- cast `Face2 -> Entity`;
- call `IEntity.Select4`;
- verify `SelectionMgr.GetSelectedObjectCount2(-1)`;
- verify `GetSelectedObjectType3(...) == swSelFACES`;
- for commands that depend on the active document, explicitly verify the active document path.

Do not rely on coordinate/ray selection if a persistent entity handle is available.

## 7. Geometry interrogation rules

- `IFace2.GetBox` is approximate. Do not use it for micrometre-level acceptance.
- Prefer analytic surface parameters (`PlaneParams`, `CylinderParams`) for engineering classification.
- Use persistent references for identity across save/reopen.
- Keep geometry fingerprint separate from file SHA: PMI metadata may change the file while solid geometry remains invariant.

## 8. Process isolation

Build, verify, drawings, simulation, and promotion are separate stages.

A drawing API failure must not corrupt a CAD build.
A verification failure must not write stable CAD.
A report-generation failure must not silently change product state.

## 9. Required evidence for every proven API capability

Freeze:
- exact source file;
- SHA-256;
- SOLIDWORKS revision;
- interop/compiler assumptions;
- input authority path/hash;
- output artifact path/hash;
- PASS report;
- log;
- known anomalies;
- exact acceptance criterion.

The frozen copy is immutable evidence. The working source may evolve, but a new version needs a new proven record.

The frozen capability must include **all transitive executable source dependencies**. Freezing only an outer Python orchestrator is incomplete if it compiles or invokes an unfrozen C#/VBA/EXE source. A PROVEN capability bundle must be sufficient to reconstruct the exact implementation path without rediscovering hidden files.

For adapted reuse, preserve the proven core byte-for-byte where possible and change only the outer authority/input adapter. Record the core SHA-256 in the new run evidence.

## 10. Chat / AI continuity rule

At the start of any new SOLIDWORKS automation task, the AI must inspect:
1. this rules file;
2. `K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json`;
3. `K01_SOLIDWORKS_PROVEN_MANIFEST_CURRENT.json` if present;
4. the current engineering checkpoint / step gate;
5. the actual proven source for the requested capability.

Do not begin by generating a fresh COM implementation from general knowledge.

## 11. Current lesson / root cause

The September 11 delay occurred because a new C# DimXpert writer was developed in parallel to a Step13 implementation that had already proven the same C02/C05 capability on September 8.

The information existed, but it was fragmented:
- runtime rules in `control/environment/K01_SOLIDWORKS_2018_RUNTIME.json`;
- old compile corrections in `cad_api/README_RUN_FIRST.txt`;
- Step13 evidence in product-definition/report files;
- the actual Step13 writer outside the repository under `D:\BreshevEngineering\Additional\...`;
- no mandatory capability registry blocked a parallel rewrite.

This ruleset + proven registry + freeze tool closes that process gap.

## 12. Current proven P007 DimXpert input contract — 2026-09-11

Current canonical P007 C02/C05 authoring has now passed using the unchanged frozen Step13 C# core.

- Proven core SHA-256: `2d6546a84b32261c3e99bbe7f8754d205ecf7b8f741069722b822a71bdf8c636`.
- Current status: `PASS_P007_CURRENT_CANONICAL_PMI_C02_C05_PROVEN_STEP13_CORE`.
- C02 API primitive: unique cylindrical entity radius 7.05 mm (Ø14.10) from `CYLINDRICAL_FACE`.
- C05 engineering binding is composite (`FLANGE_OD_PLUS_AXIAL_FACE_SET`, 4 entities). The API primitive is the unique cylindrical entity radius 16.50 mm (Ø33.00).
- Binding authority order for this adapter: current raw canonical rebind report -> product-characteristic binding -> PMI authoring scope.
- Raw rebind SHA must match current canonical P007 SHA.
- The known `InsertSizeDimension=False` anomaly remains acceptable only when semantic creation, save-close-reopen, persistent state 0/0, and invariant solid geometry all PASS.

This binding/API distinction is permanent: do not assume one product characteristic equals one API entity.
