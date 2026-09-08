# K01 project structure — target state

## CAD filesystem (not normal Git)

D:\Marvilon\K01\cad\
- assemblies\        stable production assemblies only
- parts\             stable production SLDPRT only
- drawings\          stable SLDDRW only
- candidates\        **current active candidate(s) only**
  - archive\
    - accepted_history\
    - rejected\
    - superseded_reference\
    - verification\
    - simulation\
    - simulation_workdirs\
    - runtime_logs\
- archive\           pre-promotion / released snapshots

## Git repository

D:\BreshevEngineering\marvilon-k01\
- master\            authoritative engineering register/requirements
- params\            generated parameter projections
- bom\               generated BOM projections
- docs\               current engineering decisions/process
- tools\              active automation only
- control\            active launchers only
- tests\              automated QA
- reports\cad\current accepted compact JSON evidence
- .github\workflows   CI
- .local_archive\     ignored local development history

Root should contain only project-level README/configuration, not dozens of
historical RUN/PATCH launchers.

## Truth hierarchy

1. `master/K01_master.json` — engineering identity, requirements, lifecycle.
2. stable native SolidWorks geometry — actual released/current geometry.
3. generated reports/BOM/drawings — projections, never independent truth.
4. archive — evidence/history, never an active design source.
