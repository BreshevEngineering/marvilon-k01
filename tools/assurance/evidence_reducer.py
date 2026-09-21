from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone

def load(p:Path,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def write(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")

def sha(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def source_record(repo,rel):
    p=repo/rel
    if not p.exists():
        return {"source":rel,"state":"MISSING","sha256":None,"payload":None}
    return {"source":rel,"state":"PRESENT","sha256":sha(p),"payload":load(p,{})}

def build_evidence(repo):
    sources=[
        "control/snapshot/K01_GATE04E_CURRENT_SNAPSHOT.json",
        "control/project/K01_DEPENDENCY_STATE.json",
        "control/project/K01_PROJECT_CLOSURE_MATRIX.json",
        "control/analysis/K01_FIXED_COIL_FEMM_BENCHMARK.json",
        "control/analysis/K01_MAGNETIC_FORCE_QUALIFICATION.json",
        "control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json",
        "control/bom/K01_BOM_RELEASE_WORKLIST.json",
        "control/bom/K01_BOM_BLOCKER_DIAGNOSIS.json",
        "control/drawings/K01_D006_RELEASE_DEFINITION.json",
        "control/drawings/K01_DRAWING_PROGRAM_STATUS.json",
        "control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json",
        "control/change/K01_CHANGE_CURRENT.json"
    ]
    records=[source_record(repo,x) for x in sources]

    cp=subprocess.run(
        ["git","-C",str(repo),"log","--decorate=short","--pretty=format:%H|%cI|%s|%D","-n","30"],
        capture_output=True,text=True,errors="replace"
    )
    history=[]
    if cp.returncode==0:
        for line in cp.stdout.splitlines():
            parts=line.split("|",3)
            if len(parts)>=3:
                history.append({
                    "commit":parts[0],"date":parts[1],"subject":parts[2],
                    "decorations":parts[3] if len(parts)>3 else ""
                })

    evidence={
        "schema":"k01.evidence.index.v3",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "records":records,
        "release_history":history,
        "policy":{
            "center_reads_only_this_evidence_projection":True,
            "center_has_no_engineering_constants":True,
            "verdict_logic_outside_center":True
        }
    }
    ep=repo/"evidence"/"current"/"K01_EVIDENCE_INDEX.json"
    write(ep,evidence)
    return evidence,ep

def reduce_evidence(evidence):
    recs={r["source"]:r for r in evidence.get("records",[])}
    blockers=[]
    graph=[]
    contradictions=[]

    def payload(path):
        return (recs.get(path) or {}).get("payload") or {}

    for path,rec in recs.items():
        if rec.get("state")=="MISSING":
            blockers.append({"severity":"HOLD","id":"MISSING:"+path,"reason":"required evidence source missing"})

    closure=payload("control/project/K01_PROJECT_CLOSURE_MATRIX.json")
    for domain in closure.get("domains",[]) or []:
        graph.append({"id":domain.get("id"),"status":domain.get("status"),"source":"closure_matrix"})
        status=str(domain.get("status",""))
        if "HOLD" in status or "OPEN" in status or "DEFERRED" in status:
            blockers.append({"severity":"HOLD","id":domain.get("id"),"reason":status})

    bom=payload("control/bom/K01_BOM_RELEASE_WORKLIST.json")
    for section in ("ebom","mbom"):
        for item in (bom.get(section) or {}).get("open_items",[]) or []:
            blockers.append({"severity":"HOLD","id":item,"reason":section.upper()+" release blocker"})

    drawing=payload("control/drawings/K01_D006_RELEASE_DEFINITION.json")
    for item in drawing.get("release_blockers",[]) or []:
        blockers.append({"severity":"HOLD","id":"K01-D-006:"+item,"reason":"drawing release blocker"})

    force=payload("control/analysis/K01_MAGNETIC_FORCE_QUALIFICATION.json")
    for item in force.get("remaining_release_blockers",[]) or []:
        blockers.append({"severity":"HOLD","id":"FEMM:"+item,"reason":"physical force qualification blocker"})

    change=payload("control/change/K01_CHANGE_CURRENT.json")
    if change and change.get("status") not in ("PROMOTED","REJECTED"):
        blockers.append({"severity":"INFO","id":"CHANGE:"+str(change.get("id")),"reason":str(change.get("status"))})

    if str(closure.get("overall_status","")).startswith("PASS") and any(b["severity"]=="HOLD" for b in blockers):
        contradictions.append({"id":"RELEASE_PASS_WITH_BLOCKERS","detail":"closure overall PASS while HOLD blockers exist"})
        blockers.append({"severity":"HOLD","id":"CONTRADICTION:RELEASE_PASS_WITH_BLOCKERS","reason":"contradictory evidence"})

    seen=set()
    unique=[]
    for blocker in blockers:
        key=(blocker["severity"],blocker["id"])
        if key not in seen:
            seen.add(key)
            unique.append(blocker)

    return {
        "schema":"k01.center.view.v3",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "verdict":"HOLD" if any(b["severity"]=="HOLD" for b in unique) or contradictions else "PASS",
        "blockers":unique,
        "graph":graph,
        "release_history":evidence.get("release_history",[]),
        "contradictions":contradictions,
        "screens":["BLOCKERS","GRAPH","RELEASE_HISTORY"],
        "policy":{
            "instrument_only":True,
            "no_local_engineering_data":True,
            "no_local_verdict_logic":True,
            "no_state_changing_actions":True
        }
    }

def build(repo):
    evidence,ep=build_evidence(repo)
    view=reduce_evidence(evidence)
    vp=repo/"evidence"/"current"/"K01_CENTER_VIEW.json"
    write(vp,view)
    return ep,vp,view
