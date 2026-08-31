# CAD automation target architecture

```text
REQUIREMENTS
     |
     v
K01_master.json
     |
     +-------------------------+
     |                         |
     v                         v
k01_params.py            materials/status/gates
     |
     +---------------------------+
     |                           |
     v                           v
Reference CAD builder      SolidWorks API builder
(CadQuery / STEP)          (native SLDPRT/SLDASM)
     |                           |
     v                           v
GOLDEN_REF.step          Native SolidWorks tree
     |                           |
     +-------------+-------------+
                   |
                   v
             CAD_SNAPSHOT.json
                   |
                   v
              automated QA
     dimensions / volume / bbox /
     materials / BOM / interfaces /
     retired parts / open gates
                   |
                   v
                PASS/FAIL
```

## Rollout
Phase 1 — API connectivity and snapshot audit.
Phase 2 — create a disposable native test part by API.
Phase 3 — generate P016 native feature tree.
Phase 4 — compare native P016 vs golden reference STEP.
Phase 5 — generalize feature builders for K01.
