# MEDTAS v8.1

- Fixes the v8 PowerShell state-engine parser error by precomputing all evidence predicates.
- Preflight now uses the native PowerShell parser on the state engine and Center server before launch.
- Adds dependency-aware `ready_now` actions instead of treating the first unresolved row as the only possible work.
- Adds the controlled technical-filter path directly in the Center.
- Adds a Digital Thread tab and an architecture model aligned with NIST digital-thread principles.
- Adds a read-only SOLIDWORKS live bridge: active document/configuration/dirty flag/feature count/component count flow back into MEDTAS.
- Existing explicit Center actions remain the controlled MEDTAS -> SOLIDWORKS direction.
- No native CAD, current event ledger, mutable result evidence or Git index is overwritten by design.
