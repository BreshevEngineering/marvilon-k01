# K01 CAD control pipeline — stable filenames

This package replaces the experimental `sw_review_export_v04/v05...` sequence.

## Why the last v05 failed

The active SOLIDWORKS document was not a Part, so the old script intentionally
raised:

`RuntimeError: v05 currently supports Part documents only.`

The stable exporter no longer fails in that situation:
- active Part -> exports that Part;
- active Assembly -> exports every unique resolved child Part.

## Repository policy

Commit:
- `tools/*.py`
- `master/*.json`
- `params/*.py`
- `reports/cad/current/*.json`
- `.githooks/*`

Do not commit:
- native SLDPRT/SLDASM binaries;
- routine STEP exports;
- BMP/screenshots;
- temporary handoff ZIPs.

The JSON files use stable filenames, so Git history itself is the change log.
A new export overwrites the same `<part>.json`; `git diff` shows what changed.

## Important migration rule

Do NOT hard-code materials or dimensions inside `k01_audit.py`.

The uploaded draft `k01_audit.py` had:
- P007 hard-coded as `Inconel 625`, while the current project baseline is 316L;
- part-specific dimensions embedded directly in tool code.

This package moves intent into `master/cad_contracts.json` and reads material
from `master/K01_master.json`.

## Stable SOLIDWORKS dimension names

Rename only controlled/interface dimensions, not every dimension.

Initial P007 names:
- `CAN_OD`
- `CAN_BORE`

After these are installed and linked to `K01_equations.txt`, change their
contract severity from `WARN` to `ERROR`.

For P003, wait until the P003<->P007 production pilot/shoulder is frozen, then
name only those interface dimensions.

## Fast workflow after each meaningful CAD edit

1. Open the fully resolved `K01-A-001_Calibration_Module.SLDASM`
   (or a single Part).
2. Run:
   `RUN_K01_FAST_AUDIT.cmd`
3. If PASS:
   `git add tools master params reports/cad/current .githooks RUN_K01_FAST_AUDIT.cmd`
4. Commit.

## Pre-commit hook

After the pipeline has passed manually once:

`SETUP_K01_GIT_HOOKS.cmd`

The hook runs the text audit only. It will not start SOLIDWORKS.

## Two-speed QA

Fast:
- native tree/subfeatures
- controlled dimensions
- material
- one-solid-body rule
- external equation link
- source SLDPRT SHA-256 freshness
- master/params comparison

Slow / release:
- STEP AP242 export
- BREP geometry check
- interference
- Simulation/FEMM results
- drawings/PMI
- physical acceptance tests
