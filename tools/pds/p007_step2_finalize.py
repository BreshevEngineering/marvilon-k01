from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def dump(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default="."); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    hygiene=load(root/"reports/control/K01_SOURCE_HYGIENE_CURRENT.json")
    pds=load(root/"control/pds/K01_P007_J2_LIFECYCLE.json")
    pd=load(root/"reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json")
    if hygiene.get("status")!="PASS_SOURCE_HYGIENE": raise SystemExit("HOLD: source hygiene not PASS")
    if (pds.get("lifecycle_stages") or {}).get("3_ARCHITECTURE_ALTERNATIVES",{}).get("status")!="PASS": raise SystemExit("HOLD: PDS architecture stage not PASS")
    if not str(pd.get("status","")).startswith("PASS_DRAWING_CANDIDATE_READY__HOLD_RELEASE"): raise SystemExit("HOLD: unexpected Product Definition readiness")
    p=root/"control/project/K01_NEXT_ACTIONS_CURRENT.json"; d=load(p)
    d["generated_utc"]=datetime.now(timezone.utc).isoformat()
    d["current_stage"]="P007 Product Definition Closure — Step 2 PASS; T07A pressure-shell refresh next"
    d["last_completed"]="Step 2: source hygiene/archive migration + PDS/navigation reconciliation"
    d["current_blocker"]="Full K01-D-006 remains blocked by Product Definition release gaps; T07A structural refresh and tolerance/seal/leak/inspection closure remain."
    d["next_1"]="Execute T07A MANUAL_CONTROLLED in existing SolidWorks Simulation on current frozen P007: +0.20 bar linear static (screening SF >= 2) and -0.20 bar linear buckling (first positive lambda1 >= 10). Save controlled study/result evidence. Do not create a new Simulation API executor and do not author full K01-D-006 yet."
    d["execution_mode"]="MANUAL_CONTROLLED"
    dump(p,d)
    print("STEP2_FINALIZE: PASS_TO_T07A_MANUAL_CONTROLLED")
    print("NEXT:",d["next_1"])
    return 0
if __name__=="__main__": raise SystemExit(main())
