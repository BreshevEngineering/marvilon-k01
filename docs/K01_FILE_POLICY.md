# K01 file policy

## CAD workspace

Only stable production files are allowed as sources in the top assembly:

- `cad/assemblies/K01-A-001_Calibration_Module.SLDASM`
- `cad/parts/K01-P-xxx_*.SLDPRT`

`cad/candidates` is temporary engineering evidence only. The top assembly shall
never remain permanently linked to a candidate timestamp filename.

## Candidate states

After a gate closes:
- ACCEPTED geometry -> promote to stable production filename after backup.
- REJECTED -> `cad/archive/rejected/<date>/`
- VERIFICATION assemblies -> `cad/archive/verification/<date>/`
- Simulation result sets -> `cad/archive/simulation/<date>/`
- temporary `~$*` files -> delete only with SOLIDWORKS closed.

## Git repository

Track:
- master JSON;
- params/source scripts;
- current gate summaries;
- small JSON/CSV evidence;
- BOM projection;
- requirements/change control;
- QA tests.

Do not track in ordinary Git:
- SLDPRT/SLDASM/SLDDRW;
- CWR/rsl/large solver output;
- handoff zips;
- generated screenshots;
- generated STEP unless deliberately placed in Git LFS/PDM.

## Root folder

Root should contain only project-level entry points and control files.
Gate-specific debug patches/readmes belong in a local archive or `docs/history`,
not permanently in the root.
