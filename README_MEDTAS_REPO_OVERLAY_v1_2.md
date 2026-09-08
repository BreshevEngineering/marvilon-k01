# MEDTAS v1.2 — K01 Engineering Build Graph

This overlay advances MEDTAS from a status registry to a reproducible engineering build graph.

### Failure model fixed
v1.1 could exit after the selected-assembly line and lose the exception with the closing CMD. v1.2 adds:
- `[STAThread]` to the SolidWorks COM exporter;
- attach-to-open-document first, then silent `OpenDoc6` fallback;
- stage-by-stage exporter logging;
- partial error JSON written by the C# exporter;
- Python stdout/stderr capture and 300 s watchdog;
- persistent `K01_MEDTAS_LAST_FAILURE.json`;
- CMD `pause` on both PASS and HOLD.

The previous compiler warning about the unused `started` variable is removed; it was not the cause of the failure.

### CAD semantic state v1.2
The exporter records assembly configuration, component instances, referenced configurations, suppression, transforms, mates, part feature state, dimensions, material assignments, datums, and a geometry face inventory (surface type, area, bounding box, normal where available, edge count). Absolute paths/timestamps/native file hashes are removed from the canonical state hash.

### Current build frontier
The first live CAD semantic PASS unlocks the canonical snapshot. The automated downstream pass then builds tolerance, structural-model, drawing-intent and BOM-model nodes. CalculiX remains intentionally `MISSING` until the same structural semantics can be mapped to a neutral mesh without inventing face selections.
