# MEDTAS v8.3 changelog

- English-only Control Center UI; no mixed Russian gate labels.
- Technical Filter redesigned for readability.
- Added lightweight J2 interface and axial-stack SVG visual context.
- Digital Thread redesigned from software architecture page into an operational K01 lifecycle/thread map.
- Added live tool-mesh status concept for SOLIDWORKS, FEMM, BOM, drawings and GitHub.
- Corrected P006 SW2018 compile defect by removing invalid `ModelDoc2.GetPartBox`.
- P006 builder now locates the positive-X planar face from PartDoc bodies/plane parameters.
- Added Gate04E full C2R1 + P006 verification assembly generator.
- T03 becomes CAD-scope PASS only after both P006 candidate build and full-assembly link verification pass.
- P006 production material is explicitly OPEN; no material is inferred.
- Normalized seal assumption wording to FKM candidate / FFKM fallback.
- Preflight checks English-only UI and v8.3 artifacts.
- AI Handoff includes newer digital-thread / P006 / FEMM / GitHub evidence when present.
