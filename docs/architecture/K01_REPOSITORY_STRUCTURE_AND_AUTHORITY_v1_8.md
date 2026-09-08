# K01 repository structure and authority — MEDTAS v1.8

The repository is intentionally split by **authority**, not by file extension.

```text
marvilon-k01/
├─ control/                     # authoritative engineering intent/contracts
│  ├─ requirements/             # requirements and acceptance criteria
│  ├─ parameters/               # controlled numerical design parameters
│  ├─ materials/                # controlled material state
│  ├─ drawings/                 # drawing/product-definition characteristic registry
│  └─ medtas/v1/                # build graph, bindings, schemas, policies
├─ docs/architecture/           # architecture and process documentation
├─ drawings/
│  ├─ work/                     # non-release working drawings
│  ├─ release_candidate/        # generated SLDDRW/PDF candidates
│  └─ released/                 # approved drawing packs only
├─ bom/
│  ├─ metadata/                 # controlled product metadata
│  ├─ supplier/                 # supplier/MPN evidence
│  └─ released/                 # approved BOM exports
├─ analysis/
│  ├─ structural/               # controlled solver-neutral definitions / solver inputs
│  ├─ magnetic/                 # FEMM definitions / controlled inputs
│  ├─ thermal/
│  └─ flow/
├─ reports/                     # generated/materialized evidence; rebuildable where possible
│  ├─ control/                  # current project, priority, graph views, AI handoff
│  ├─ cad/                      # raw CAD API evidence
│  ├─ medtas/                   # canonical CAD, MBD, product definition, tolerance, analysis evidence
│  ├─ engineering/              # formal engineering reports and source evidence
│  ├─ bom/                      # generated BOM artifacts
│  ├─ drawing/                  # drawing release plans / QA
│  └─ tests/                    # qualification/test evidence
├─ tools/medtas/                # controlled automation implementation
└─ tests/                       # software/engineering qualification tests
```

## External native CAD workspace

The current K01 native SolidWorks workspace may remain outside the Git repository. MEDTAS resolves it from the current controlled CAD semantic binding. Native CAD is geometry authority, but its binary bytes are not semantic state hashes.

## Source-of-truth rule

There is no single absolute source-of-truth file. Authority is distributed by engineering domain:

- requirements: controlled requirement records;
- design parameters: `control/parameters`;
- material decisions: `control/materials` plus production certificates when manufactured;
- nominal geometry / feature topology / mates: native SolidWorks + canonical semantic snapshot;
- product definition: canonical Product Definition assembled from native CAD semantics, reviewed native MBD/DimXpert, controlled parameters and explicit specifications;
- BOM identity/quantity: canonical BOM model reconciled against native assembly occurrences;
- drawings: derived representation of Product Definition, never an independent tolerance source;
- verification evidence: solver/test artifacts registered in the Engineering Build Graph;
- current UI state: materialized view only and always reconstructible.

## Migration rule

MEDTAS may create missing canonical directories but does not automatically move, delete or rename existing engineering files. Migration is review-only until explicitly approved.
