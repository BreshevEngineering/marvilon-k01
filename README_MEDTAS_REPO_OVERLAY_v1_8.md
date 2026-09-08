# K01 MEDTAS repository overlay v1.8

Install by extracting the ZIP directly into the repository root, normally:

```text
D:\BreshevEngineering\marvilon-k01\
```

Replace files when prompted. Do not create a nested `K01_MEDTAS_repo_overlay_v1_8` directory inside the repository.

## Normal daily workflow

1. Keep the validated mechanical geometry frozen unless contrary evidence appears.
2. Run `03_RUN_MEDTAS_PIPELINE.cmd` after meaningful design/product-definition changes.
3. Work primarily from `OPEN_K01_COMMAND_CENTER_V11.cmd`.
4. Current priority is **Product Definition / Drawings / BOM**, then release-critical requirements.
5. Do **not** spend project time on CalculiX unless its deferred-assurance reopen condition is met.
6. Use the **Build AI Handoff ZIP** button (or `22_BUILD_AI_HANDOFF.cmd`) before sending the current project state for AI review.

## Drawing path

```text
native CAD semantics
  + controlled parameters/materials
  + reviewed native MBD where available
  + explicit semantic bindings during MBD migration
        ↓
canonical Product Definition
        ↓
per-drawing release plan
        ↓
SLDDRW / PDF release candidates
        ↓
semantic + visual QA
```

Open tolerance/process/datum definitions are never invented by the drawing generator.

## CalculiX

The commands remain available under Deferred Assurance, but v1.8 does not run the face-map/Gmsh/CalculiX chain automatically in the 8-stage pipeline.
