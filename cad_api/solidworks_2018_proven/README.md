# SOLIDWORKS 2018 proven API area

This directory is the single navigation point for K01 SOLIDWORKS automation knowledge.

It is **not** a second source tree. Working code remains at its authoritative repository path.
The `snapshots/` tree contains immutable copied evidence produced by `RUN_FREEZE_PROVEN_API.cmd`.

Use this order before any SOLIDWORKS API work:

1. Read `K01_SOLIDWORKS_API_RULES_v1.md`.
2. Check `K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json`.
3. Run capability preflight.
4. Reuse the proven source.
5. Create a new implementation only when a documented capability gap exists.
6. Freeze every newly proven implementation.

The current highest-priority proven capability is the September 8 Step13 P007 DimXpert C02/C05 writer.
