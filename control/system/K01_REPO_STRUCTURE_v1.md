# K01 Repository Structure — v1

**Repository root**
`D:\BreshevEngineering\marvilon-k01\`

```text
marvilon-k01/
├─ master/                 # requirements/lifecycle/material status
├─ params/                 # controlled numeric parameter registry/projections
├─ control/
│  ├─ command_center/      # human engineering dashboard + data snapshots
│  └─ system/              # authority/release/process standards
├─ cad_api/                # external strongly-typed SW API source
├─ scripts/                # non-CAD orchestration / validation
├─ tools/                  # reusable engineering utilities
├─ bom/
│  └─ spec/                # BOM generation/audit specification
├─ reports/
│  ├─ cad/                 # CAD build/verify/readback evidence
│  ├─ bom/                 # BOM audits
│  ├─ calc/                # FEMM/FEA/CFD evidence
│  └─ ai/current/          # generated AI context
├─ docs/
│  ├─ design/              # controlled design reviews
│  └─ technology/          # manufacturing technology/router
├─ reference/              # external/reference geometry/docs
├─ tests/                  # automated tests
├─ handoff/                # release/reviewer handoffs
└─ archive/                # local non-Git controlled history / superseded artifacts; never active authority
```

## Stable CAD lives outside Git

`D:\Marvilon\K01\cad\...`

Native CAD is release-controlled separately. Git stores source, control, reports,
schemas, scripts and fingerprints — not as a substitute for CAD/PDM.

## One-off gate scripts

No new one-off root files. A gate-specific source belongs under:
`cad_api/gates/<gate-id>/`

Reusable logic belongs under:
`cad_api/lib/` or `tools/`.

## Command Center

`control/command_center/K01_Command_Center_v1.html`

It is a dashboard, not an independent authority. Its current data is a projection
of controlled state and must be regenerated/reconciled by the engineering build.
