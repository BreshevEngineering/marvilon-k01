# K01 Data Authority — v1

No single file owns the entire project. Authority is separated by data domain.

| Domain | Authority |
|---|---|
| Requirements, lifecycle, material status, OPEN gates | `master/K01_master.json` after current repair |
| Native topology, feature tree, local geometry, actual mate references | stable native SOLIDWORKS CAD |
| Cross-part controlled design parameters / equations | controlled parameter registry + CAD readback |
| Production identity properties | SOLIDWORKS custom properties, reconciled to master |
| BOM | generated from production assembly + master-only BUY/consumable items |
| Calculations | versioned solver inputs + immutable result reports |
| Manufacturing technology | controlled technology/router registry |
| Release | immutable release package + hashes + release checklist |

Rule: one numeric parameter must not have two independent editable owners.
