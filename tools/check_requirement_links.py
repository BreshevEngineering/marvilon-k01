from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/"control/requirements/requirements.json").read_text(encoding="utf-8"))
g=json.loads((ROOT/"control/technical_filter/K01_J2_C2R1_TECHNICAL_FILTER_v1.json").read_text(encoding="utf-8-sig"))
gate_ids={x["gate"] for x in g["gates"]}
bad=[]
for req in r["requirements"]:
    if not req["links"]["gates"]:
        bad.append((req["id"],"no linked gates"))
    for gid in req["links"]["gates"]:
        if gid not in gate_ids: bad.append((req["id"],f"unknown gate {gid}"))
if bad:
    print("FAIL requirement coverage links")
    for x in bad: print(" ",x)
    sys.exit(2)
print(f"PASS requirements linked to valid gates: {len(r['requirements'])}")
