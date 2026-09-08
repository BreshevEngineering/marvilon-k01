# MARVILON Engineering Digital Thread & Assurance System (MEDTAS) — v3

## Name

**System:** MARVILON Engineering Digital Thread & Assurance System — MEDTAS  
**Project instance:** K01 MEDTAS  
**Human UI:** K01 Engineering Control Center  
**Decision object:** Engineering Decision Record — EDR  
**Evidence object:** Evidence Reference Record — ERR  
**Controlled product/node record:** Configuration Item Dossier — CID  
**Change object:** Engineering Change Record — ECR

This terminology intentionally maps the K01 workflow to established professional
concepts: systems engineering decision analysis, configuration management,
technical data management, requirements verification, model-based/digital-thread
engineering and product-lifecycle traceability.

## Core rule

MEDTAS is not one "master file". It is a controlled graph of authoritative
artifacts with explicit ownership by data domain.

- Master: requirements, lifecycle, material status, OPEN gates, product identity.
- Native stable SOLIDWORKS: exact topology, feature tree, geometry and mate references.
- Parameter registry: shared controlled design variables and equations.
- EDR: why a decision was made; alternatives, criteria, evidence and rationale.
- ERR/source registry: literature, standard, calculation, test or supplier evidence.
- CID: complete history and current state of a part/interface/subassembly node.
- Solver reports: calculation evidence.
- Technology router: manufacturing/inspection process.
- BOM: generated output.
- Release package: frozen coherent product baseline.

## Design goal

Do not attempt to "remove people" from engineering. Make memory-dependent,
silent and uncontrolled human error difficult to introduce and easy to detect.

MEDTAS therefore uses:
- fail-closed gates;
- unique IDs;
- no direct writes to stable CAD by build tools;
- automated staleness propagation;
- machine-readable dependencies;
- checksums/fingerprints;
- reproducible scripts;
- explicit OPEN state;
- immutable evidence reports;
- controlled promotion;
- audit trail;
- later multi-person approval/PDM workflow.

The target is an **error-resistant engineering process**, not an imaginary
human-free process.
