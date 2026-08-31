# SolidWorks API rollout

Do not begin by letting Python rewrite production geometry.

## Test 1 — read-only probe
1. Start SOLIDWORKS 2026.
2. Open the native P016 part.
3. Install Python package:
   `pip install pywin32`
4. Run:
   `python cad_api/sw_api_probe.py`
5. Send back `reports/CAD_SNAPSHOT_probe.json`.

Expected result:
- active part title/path;
- bounding box;
- complete feature names/types.

Only after this PASS do we create the API write/generation test.

## Why
The local SOLIDWORKS installation, language, templates and COM registration must be verified before a production builder is trusted.
