# MEDTAS v1.8 — priority-driven release closure

## Decision
CalculiX is retained as independent engineering assurance but removed from the current K01 release critical path. The current primary path is Product Definition → Drawings/BOM → unresolved product-release requirements.

## Added
- `K01.PRODUCT.DEFINITION.GATE04E` first-class graph node.
- `K01_RELEASE_PRIORITY_POLICY_v1_8.json` and materialized `K01_RELEASE_PRIORITY_CURRENT.json`.
- Product Definition accepts explicit reviewed native CAD semantic bindings as a transitional authority while MBD/DimXpert is being authored. Open tolerances/specs remain fail-closed.
- Per-drawing release gates: one blocked drawing no longer blocks generation of another drawing whose definition is complete.
- AI handoff ZIP restored in Command Center and as `22_BUILD_AI_HANDOFF.cmd`.
- AI handoff now includes a SHA-256 manifest of current control/semantic/evidence files and excludes native CAD binaries.
- Repository structure/authority architecture document.
- Windows controlled-action launcher qualification.

## Center fixes
- Fixed the Windows action launch contract: `CREATE_NEW_CONSOLE` is used without `DETACHED_PROCESS`; controlled CMD is launched through `%COMSPEC% /d /c call`.
- Action launch failures are logged to `reports/medtas/logs/current/K01_CENTER_ACTIONS.log`.
- AI ZIP button restored on Overview and Evidence pages.
- CalculiX UI moved to **Deferred Assurance** and removed from the immediate causal frontier.
- Dashboard shows `DO NOW`, module geometry conclusion, Product Definition, BOM and drawing readiness.

## Drawing architecture
- Full native MBD remains preferred.
- MBD absence no longer forces a parallel handwritten truth. Product Definition may use an explicit native datum/dimension/geometry binding plus controlled parameter/specification.
- Open tolerance, weld/process, optical datum and ambiguous semantic ownership remain blockers.
- Drawing generation is per drawing and still uses `AutoDimension = false`.

## Structural assurance
- SolidWorks service analysis remains primary current structural evidence.
- Face-map, Gmsh, bolt equivalence and CalculiX are preserved in the DAG as `assurance_optional` and can be reopened without losing work.
