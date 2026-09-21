from __future__ import annotations
import argparse, datetime as dt, json, re, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
REP=Path("reports/engineering/K01_P004_MATING_AUTHORITY_RECOVERY_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")
TEXT_EXT={".json",".md",".txt",".csv",".yaml",".yml"}

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def now():return dt.datetime.now(dt.timezone.utc).isoformat()

def guard(repo):
    for t in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        cp=subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo,text=True)
        if cp.returncode:raise SystemExit("HOLD: state guard failed before mating-authority recovery.")

def context_hits(repo,patterns,max_hits=120):
    hits=[];roots=[repo/"control/product_definition",repo/"reports/product_definition",repo/"control/decisions",repo/"reports/engineering",repo/"control/requirements",repo/"control/product",repo/"docs"]
    regs=[re.compile(x,re.I) for x in patterns]
    for root in roots:
        if not root.exists():continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in TEXT_EXT:continue
            try:
                if p.stat().st_size>5_000_000:continue
                lines=p.read_text(encoding="utf-8-sig",errors="ignore").splitlines()
            except Exception:continue
            for i,line in enumerate(lines,1):
                if any(r.search(line) for r in regs):
                    lo=max(0,i-3);hi=min(len(lines),i+2)
                    hits.append({"path":p.relative_to(repo).as_posix(),"line":i,"context":"\n".join(lines[lo:hi])[:1600]})
                    if len(hits)>=max_hits:return hits
    return hits

def part_records(repo,part):
    out=[]
    for rr in ("control/product_definition","reports/product_definition","control/decisions"):
        root=repo/rr
        if not root.exists():continue
        for p in root.rglob("*.json"):
            if part.lower() not in p.name.lower():continue
            d=rd(p,{}) or {};out.append({"path":p.relative_to(repo).as_posix(),"schema":d.get("schema"),"status":d.get("status"),"product_definition_ready":d.get("product_definition_ready"),"next_blocker":d.get("next_blocker")})
    return out

def classify(records,hits,part):
    released=False;reasons=[]
    for c in records:
        st=str(c.get("status") or "").upper()
        if c.get("product_definition_ready") is True or ("RELEASED" in st and "HOLD" not in st and "PARTIAL" not in st):released=True;reasons.append("explicit READY/RELEASED in "+c["path"])
    if not records:reasons.append("no part-specific product-definition/current decision record found")
    if not released:reasons.append("no explicit READY/RELEASED mating-part Product Definition proven")
    return {"part":part,"released_authority_proven":released,"reasons":reasons,"candidate_records":records,"relevant_hits":hits}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root);guard(repo)
    n=rd(repo/NEXT,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-MATING-AUTHORITY-RECOVERY":raise SystemExit("HOLD: frontier not at P004 mating-authority recovery.")

    p003_hits=context_hits(repo,[r"\b6[.,]60\b",r"P004\s+seat",r"P003.*P004"])
    p014_hits=context_hits(repo,[r"\bP014\b",r"11[.,]05",r"\b12[.,]00\b",r"axial\s+float",r"retaining\s+ring"])
    p003=classify(part_records(repo,"P003"),p003_hits,"K01-P-003")
    p014=classify(part_records(repo,"P014"),p014_hits,"K01-P-014")

    result={"schema":"k01.p004.mating_authority_recovery.current.v1","generated_utc":now(),"status":"PASS_AUTHORITY_INVENTORY__JOINT_TOLERANCE_DECISION_READY","question":"What controlled P003/P014 authorities exist for P004 seat and axial chains?","P003":p003,"P014":p014,"known_nominal_chain":{"P003_seat_mm":6.60,"P004_OD_mm":6.54,"seat_nominal_clearance_mm":0.06,"P004_length_mm":8.00,"axial_float_nominal_mm":0.05,"architecture_tokens":["P014 groove X11.05..12","P014 rear face = IN metal stop X12"]},"authority_rule":"Nominal/build/DXF/review-drawing evidence proves architecture only. Only controlled Product Definition/release records release production tolerances.","decision_readiness":{"joint_tolerance_budget_decision":"READY_FOR_ENGINEERING_DECISION","P003_released_PD_proven":p003["released_authority_proven"],"P014_released_PD_proven":p014["released_authority_proven"],"note":"Top-down interface budgets may be decided before mating-part PD READY; allocated mating-part values then become explicit downstream requirements for their later Product Definitions."},"native_mutation":"NONE"}
    wr(repo/REP,result)

    f=rd(repo/FRONT,{}) or {};g=rd(repo/GATE,{}) or {};n=rd(repo/NEXT,{}) or {};blocker="P004-JOINT-TOLERANCE-ALLOCATION-DECISION";nid="K01-NA-P004-JOINT-TOLERANCE-DECISION";exp="PASS_P004_SEAT_AXIAL_TOLERANCE_BUDGET_DECIDED__DOWNSTREAM_PART_ALLOCATIONS_EXPLICIT";text="Decide top-down worst-case tolerance budgets for P003↔P004 seat and P003/P014↔P004 axial chains at 20 C using EDR-045 and recovered mating authorities. Allocate values only where manufacturing/metrology basis supports them; otherwise create explicit downstream P003/P014 allocation requirements. No CAD/DimXpert/drawing mutation.";auth=[str(REP).replace("\\","/"),"control/decisions/EDR-045_P004_REFERENCE_TEMPERATURE_AND_SERVICE_CLEARANCE.json","control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json","reports/product_definition/K01-P-004_READINESS_CURRENT.json"]
    n.update({"schema":"k01.next_actions.current.v37_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"ENGINEERING_TOLERANCE_DECISION__NO_NATIVE_MUTATION","authority_set":auth});wr(repo/NEXT,n)
    g.update({"schema":"k01.active_step_gate.v17_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"ENGINEERING TOLERANCE DECISION ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING","required_files":auth});wr(repo/GATE,g)
    f.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"ENGINEERING_TOLERANCE_DECISION__NO_NATIVE_MUTATION"}});f.setdefault("timing",{})["ACTIVE_NOW"]=[blocker];wr(repo/FRONT,f)

    ready=rd(repo/READ,{}) or {};ready["generated_utc"]=now();ready["mating_authority_recovery"]="PASS";ready["P003_released_PD_proven"]=p003["released_authority_proven"];ready["P014_released_PD_proven"]=p014["released_authority_proven"];ready["next_blocker"]=blocker;ready["next"]=text;wr(repo/READ,ready)
    cm=rd(repo/CENTER,{}) or {}
    if cm:cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"p004_mating_authority_recovery":{"P003_released_PD_proven":p003["released_authority_proven"],"P014_released_PD_proven":p014["released_authority_proven"],"report":str(REP).replace("\\","/")}});wr(repo/CENTER,cm)

    subprocess.run([sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
    print("PASS: P004 mating authorities inventoried.");print("P003 RELEASED PD PROVEN:",p003["released_authority_proven"]);print("P014 RELEASED PD PROVEN:",p014["released_authority_proven"]);print("REPORT:",repo/REP);print("NEXT: joint P003/P004/P014 tolerance allocation decision.")
    return 0

if __name__=="__main__":raise SystemExit(main())
