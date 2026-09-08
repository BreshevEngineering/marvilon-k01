# INSTALL / UPDATE TO K01 MEDTAS v5

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

Do not create a nested MEDTAS-v5 project directory.

Launch:

`control\command_center\OPEN_K01_COMMAND_CENTER_V5.cmd`

## What v5 changes

- task-driven Dashboard with explicit CURRENT TASK;
- Digital Thread dependency view;
- visible Live Reports layer;
- automatic stable-vs-C2 interference DELTA QA;
- P003/P006 M12x1 functional interface dossier — no blind whitelist;
- corrected SW2018 drawing compiler cast for `InsertNote`;
- fixed false FOUND drawing-path logic;
- raw + reconciled automatic BOM;
- controlled identity/material authority map;
- current C2 mechanical screening report;
- one-click AI Handoff from the latest reports/logs/BOM/drawings;
- local Git status remains read-only.

## Current project state carried into v5

Gate04D-C2 BUILD: PASS  
Gate04D-C2 VERIFY: PASS / 0 active mate errors  
Raw interference: HOLD because P003/P006 was unclassified  
Raw BOM: HOLD / 13 rows / 26 metadata issues

The next controlled task is:

`T03 — Stable-vs-C2 Interference Delta`

Run it from the v5 Dashboard. If it passes, the next engineering task becomes
O-ring compound / clamp preload closure.

Installation does NOT:
- promote P003/P007 to stable;
- commit Git;
- alter production A001;
- declare full C2 release PASS.
