# MARVILON MEDTAS — K01 repository overlay v1.7

MEDTAS v1.7 turns the K01 engineering project into a reproducible build graph rather than a set of manually maintained statuses.

## Causal model

```text
Requirements
  ↓
Parameters / materials
  ↓
Native CAD semantic state
  ↓
Canonical engineering snapshot
  ├─ MBD / tolerance ─→ drawing definition ─→ SLDDRW/PDF ─→ drawing QA
  ├─ structural model ─→ SOLIDWORKS Simulation
  │                  └→ qualified face map ─→ neutral geometry ─→ mesh
  │                                           └→ bolt/contact equivalence ─→ CalculiX ─→ reconciliation
  ├─ FEMM model/run/verification
  └─ canonical BOM ─→ CSV artifact ─→ parity verification
                         ↓
                  engineering verification
                         ↓
                       baseline
```

## Hash model

`STATE_HASH` answers: **which engineering state should this node represent?**

`ARTIFACT_HASH` answers: **are these the exact physical outputs that were verified?**

Binary SOLIDWORKS file SHA is diagnostic only. A save that does not alter engineering semantics must not alter the semantic state hash.

## MBD status

MEDTAS does not invent tolerances to make the drawing path green. Native MBD/DimXpert characteristics are read machine-to-machine. Missing/ambiguous ownership remains a controlled blocker until reviewed and authored.

## Solver equivalence

A second solver is useful only if it solves the same engineering problem. MEDTAS therefore gates CalculiX on:
- persistent boundary-role identity;
- face-map qualification;
- equivalent material/load/contact definitions;
- explicit M2.5 preload/load-path representation;
- controlled neutral mesh and input deck.

## Command Center

`OPEN_K01_COMMAND_CENTER_V11.cmd` launches the current secure single-process Center. It displays materialized project/build state but is not itself a source of engineering truth.

## Project structure

The logical directory layout is controlled by `control/medtas/v1/spec/K01_PROJECT_LAYOUT_v1_7.json`. The structure auditor may create missing empty zones, but it never relocates or deletes engineering artifacts automatically.
