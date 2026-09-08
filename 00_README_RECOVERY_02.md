# K01 Engineering Recovery 02

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

This package fixes the current engineering blockers without another MEDTAS redesign.

## Fixed

### Gate04E P006
The previous selector incorrectly required the underlying planar surface normal to be +X.

The corrected builder:
- uses `IFace2.Normal` for the actual planar-face normal;
- accepts both X directions with `abs(nx) > 0.90`;
- selects the maximum-X end plane;
- writes face-selection diagnostics into the build report.

This addresses the exact runtime error:
`Could not identify the positive-X planar end face of P006.`

### Git classifier
The old script looked for `.gitignore` relative to `control\git`.

The replacement resolves the repository root explicitly and does not require `.gitignore` to exist.

### BOM
The current C2R1 BOM is a real 13-row BOM even though it has metadata HOLDs.

`NORMALIZE_BOM.cmd`:
- derives canonical K01-P/K01-B identity from the component path;
- keeps filename-derived descriptions explicitly review-only;
- shows observed SOLIDWORKS material separately from material release status;
- does not write metadata back into CAD.

### Command Center
The stable five-page UI is retained, but the useful integrations are restored:
- open current C2R1 full assembly;
- open production A001;
- build/verify P006;
- start SOLIDWORKS live bridge;
- FEMM check;
- BOM refresh/normalization;
- current AI Handoff ZIP;
- Git/GitHub.

The Center remains optional. Direct engineering scripts remain usable without it.

### Drawings
No new pseudo-drawing is generated.

Drawing V3 stays rejected. The next actual native drawing pilot is P006 after Gate04E PASS, using a controlled DRWDOT and only selected named model-feature dimensions / native hole callouts. Once accepted, the same compiler pattern is applied to P003/P007.

## Recommended run

`02_RUN_K01_ENGINEERING_RECOVERY.cmd`

It performs:
1. core preflight;
2. Gate04E;
3. FEMM fingerprint;
4. BOM normalization;
5. Git classification.

Return the Gate04E output first if the run stops.
