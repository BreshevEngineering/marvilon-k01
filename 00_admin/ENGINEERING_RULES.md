# Engineering rules

1. One numeric source:
   - controlled geometry lives in `params/k01_params.py`;
   - the same numeric dimension shall not be independently edited in JSON, Excel and CAD.

2. Native SolidWorks is the production CAD authority after verification.

3. Reference STEP is a golden geometry/check artifact, not a substitute for an editable production tree.

4. Every MAKE part must have:
   - PartNo;
   - Description;
   - Material or explicit `OPEN`;
   - revision/status;
   - manufacturing notes where required.

5. Every interface must define:
   - locating features;
   - datum scheme;
   - fit/tolerance;
   - retention;
   - sealing where applicable;
   - verification method.

6. Retired part numbers are never reused.

7. Design alternatives are retained in decision/change logs with reason for rejection or hold.

8. No PASS without evidence. OPEN is preferable to an invented value.
