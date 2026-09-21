from __future__ import annotations
import argparse, fnmatch, json, subprocess
from pathlib import Path
from datetime import datetime, timezone
import sys

MEDTAS_DIR = Path(__file__).resolve().parents[1] / "medtas"
if str(MEDTAS_DIR) not in sys.path:
    sys.path.insert(0, str(MEDTAS_DIR))
from change_impact_v9 import build_plan as build_change_impact_plan

CLASS_ORDER={"C":1,"B":2,"A":3}

DEFAULT_RULES=[
    {"pattern":"control/requirements/**","class":"A","reason":"requirements govern design"},
    {"pattern":"control/release/**","class":"A","reason":"released-element control"},
    {"pattern":"cad/final_candidate/**","class":"A","reason":"release candidate CAD"},
    {"pattern":"control/product_definition/**","class":"B","reason":"candidate product definition / PMI"},
    {"pattern":"control/drawings/**","class":"B","reason":"candidate drawing/product definition"},
    {"pattern":"cad/candidates/**","class":"B","reason":"candidate geometry"},
    {"pattern":"control/analysis/**","class":"B","reason":"engineering analysis/control inputs"},
    {"pattern":"control/bom/**","class":"B","reason":"engineering BOM source/control"},
    {"pattern":"tools/**","class":"C","reason":"tooling"},
    {"pattern":"center/**","class":"C","reason":"instrument/UI"},
    {"pattern":"docs/**","class":"C","reason":"documentation"},
    {"pattern":".github/**","class":"C","reason":"CI/branch guard tooling"},
    {"pattern":"tests/**","class":"C","reason":"tests"},
]

def load(p:Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return default

def write(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")

def now():
    return datetime.now(timezone.utc).isoformat()

def norm(path):
    return str(path).replace("\\","/").lstrip("./")

def max_class(classes):
    return max(classes,key=lambda c:CLASS_ORDER.get(c,0)) if classes else "C"

def classify_path(path,rules):
    p=norm(path)
    hits=[r for r in rules if fnmatch.fnmatch(p,r["pattern"])]
    if not hits:
        return {"path":p,"class":"C","reason":"unclassified defaults to C; manually upgrade if engineering semantics are affected"}
    cls=max_class([x["class"] for x in hits])
    return {"path":p,"class":cls,"reason":"; ".join(x["reason"] for x in hits if x["class"]==cls)}

def requirement_registry_ids(repo:Path):
    r=load(repo/"control"/"requirements"/"K01_RELEASE_REQUIREMENTS_CURRENT.json",{}) or {}
    reqs=r.get("requirements") or {}
    if isinstance(reqs,dict):
        return set(reqs.keys())
    if isinstance(reqs,list):
        return {str(x.get("id")) for x in reqs if isinstance(x,dict) and x.get("id")}
    return set()

def validate_requirement_links(repo:Path, ids):
    if not ids:
        return []
    known=requirement_registry_ids(repo)
    return [rid for rid in ids if rid not in known]

def dependency_impact(repo:Path,changed_paths,changed_nodes,changed_entities=None,change_domain=None):
    if not change_domain:
        raise SystemExit("HOLD: controlled change_domain is required for graph-based impact analysis")
    return build_change_impact_plan(
        repo,
        list(changed_entities or []),
        str(change_domain),
        list(changed_nodes or []),
        list(changed_paths or []),
    )

def current_record_path(repo):
    return repo/"control"/"change"/"K01_CHANGE_CURRENT.json"

def save_record(repo,rec):
    write(repo/"control"/"change"/"records"/(rec["id"]+".json"),rec)
    write(current_record_path(repo),rec)

def cmd_begin(repo,args):
    policy=load(repo/"control"/"governance"/"K01_CHANGE_POLICY.json",{}) or {}
    rules=policy.get("classification_rules") or DEFAULT_RULES
    paths=[norm(x) for x in (args.paths or [])]
    classified=[classify_path(p,rules) for p in paths]
    inferred=max_class([x["class"] for x in classified]) if classified else (args.change_class or "C")
    cls=args.change_class or inferred
    if CLASS_ORDER.get(inferred,0)>CLASS_ORDER.get(cls,0):
        raise SystemExit("HOLD: requested class %s lower than path-inferred %s"%(cls,inferred))

    unknown_req=validate_requirement_links(repo,args.requirements or [])
    if unknown_req:
        raise SystemExit("HOLD: requirement IDs absent from current registry: "+", ".join(unknown_req))

    rec={
        "schema":"k01.change_record.v4",
        "id":args.id,
        "created_utc":now(),
        "updated_utc":now(),
        "status":"DRAFT",
        "class":cls,
        "title":args.title,
        "reason":args.reason,
        "planned_paths":paths,
        "planned_nodes":args.nodes or [],
        "planned_entities":args.entities or [],
        "change_domain":args.change_domain,
        "classification_evidence":classified,
        "requirements":args.requirements or [],
        "rationale":args.rationale,
        "verification_plan":args.verification or [],
        "revision_action":args.revision_action,
        "impact_status":"NOT_RUN",
        "impact_report":None,
        "implementation_status":"NOT_STARTED",
        "verification_status":"NOT_RUN",
        "verification_evidence":[],
        "promotion_status":"NOT_REQUESTED",
        "promotion_decision":None
    }

    if cls=="A":
        missing=[]
        if not rec["requirements"]:missing.append("requirements")
        if not rec["rationale"]:missing.append("rationale")
        if not rec["verification_plan"]:missing.append("verification_plan")
        if not rec["revision_action"]:missing.append("revision_action")
        if missing:
            raise SystemExit("HOLD: Class A missing "+", ".join(missing))
    if cls=="B" and not rec["verification_plan"]:
        raise SystemExit("HOLD: Class B requires verification plan")
    if cls in ("A","B") and not rec.get("change_domain"):
        raise SystemExit("HOLD: Class A/B requires --change-domain for deterministic graph impact")
    if cls in ("A","B") and not (rec.get("planned_entities") or rec.get("planned_nodes") or rec.get("planned_paths")):
        raise SystemExit("HOLD: Class A/B requires an entity, graph node or controlled path for impact seeding")

    save_record(repo,rec)
    print("change_begin: PASS",args.id,"class",cls)
    return 0

def cmd_impact(repo,args):
    cp=Path(args.change) if args.change else current_record_path(repo)
    if not cp.is_absolute():
        cp=repo/cp
    rec=load(cp,{}) or {}
    if not rec.get("id"):
        raise SystemExit("HOLD: change record missing")

    impact=dependency_impact(repo,rec.get("planned_paths") or [],rec.get("planned_nodes") or [],rec.get("planned_entities") or [],rec.get("change_domain"))
    report={
        "schema":"k01.prechange_impact.v3",
        "generated_utc":now(),
        "change_id":rec["id"],
        "change_class":rec["class"],
        "status":"PASS_PRECHANGE_IMPACT_ANALYZED",
        "planned_paths":rec.get("planned_paths") or [],
        "planned_nodes":rec.get("planned_nodes") or [],
        "planned_entities":rec.get("planned_entities") or [],
        "change_domain":rec.get("change_domain"),
        "impact":impact,
        "required_reverification":[x["node_id"] for x in impact.get("rebuild_order",[])],
        "counterpart_reviews":impact.get("counterpart_reviews",[]),
        "policy":{
            "analysis_precedes_write":True,
            "closed_nodes_reopen_only_if_dependency_changes_or_contradiction_detected":True
        }
    }
    rp=repo/"control"/"change"/"impact"/(rec["id"]+"_IMPACT.json")
    write(rp,report)

    rec["updated_utc"]=now()
    rec["status"]="IMPACT_ANALYZED"
    rec["impact_status"]="PASS_PRECHANGE"
    rec["impact_report"]=str(rp.relative_to(repo)).replace("\\","/")
    save_record(repo,rec)
    print("impact: PASS",rec["id"])
    print("impacted_nodes:",[x["node_id"] for x in impact.get("rebuild_order",[])])
    print("counterpart_reviews:",impact.get("counterpart_reviews",[]))
    return 0

def cmd_whatif(repo,args):
    impact=dependency_impact(repo,[norm(x) for x in args.paths or []],args.nodes or [],args.entities or [],args.change_domain)
    print(json.dumps({
        "schema":"k01.what_if_impact.v1",
        "status":"PASS",
        "paths":[norm(x) for x in args.paths or []],
        "nodes":args.nodes or [],
        "entities":args.entities or [],
        "change_domain":args.change_domain,
        "impact":impact
    },indent=2,ensure_ascii=False))
    return 0

def cmd_implementation(repo,args):
    rec=load(current_record_path(repo),{}) or {}
    if rec.get("class") in ("A","B") and rec.get("impact_status")!="PASS_PRECHANGE":
        raise SystemExit("HOLD: implementation cannot start before PASS_PRECHANGE")
    rec["updated_utc"]=now()
    rec["status"]="IMPLEMENTED"
    rec["implementation_status"]="COMPLETE"
    save_record(repo,rec)
    print("implementation_mark: PASS",rec.get("id"))
    return 0

def cmd_verify(repo,args):
    rec=load(current_record_path(repo),{}) or {}
    if rec.get("implementation_status")!="COMPLETE":
        raise SystemExit("HOLD: verification requires implementation_status COMPLETE")
    evidence=[norm(x) for x in (args.evidence or [])]
    missing=[x for x in evidence if not (repo/x).exists()]
    if missing:
        raise SystemExit("HOLD: verification evidence missing: "+", ".join(missing))
    rec["updated_utc"]=now()
    rec["verification_status"]=args.status
    rec["verification_evidence"]=evidence
    rec["status"]="VERIFIED" if args.status=="PASS" else "VERIFICATION_HOLD"
    save_record(repo,rec)
    print("verification:",args.status,rec.get("id"))
    return 0

def cmd_promote(repo,args):
    rec=load(current_record_path(repo),{}) or {}
    if rec.get("verification_status")!="PASS":
        raise SystemExit("HOLD: promotion requires verification PASS")
    if rec.get("class")=="A":
        if not rec.get("requirements") or not rec.get("rationale") or not rec.get("revision_action"):
            raise SystemExit("HOLD: Class A promotion missing requirement/rationale/revision action")
    rec["updated_utc"]=now()
    rec["promotion_status"]="APPROVED" if args.decision=="APPROVE" else "REJECTED"
    rec["promotion_decision"]=args.decision
    rec["status"]="PROMOTED" if args.decision=="APPROVE" else "REJECTED"
    save_record(repo,rec)
    print("promotion:",rec["promotion_status"],rec.get("id"))
    return 0

def staged_paths(repo):
    cp=subprocess.run(["git","-C",str(repo),"diff","--cached","--name-only"],
                      capture_output=True,text=True,errors="replace")
    return [norm(x) for x in cp.stdout.splitlines() if x.strip()]

def paths_covered(paths,planned):
    uncovered=[]
    for p in paths:
        if p.startswith("control/change/"):
            continue
        if not any(fnmatch.fnmatch(p,q) or p.startswith(q.rstrip("*")) for q in planned):
            uncovered.append(p)
    return uncovered

def cmd_guard(repo,args):
    paths=staged_paths(repo)
    if not paths:
        print("change_guard: PASS no staged files")
        return 0

    policy=load(repo/"control"/"governance"/"K01_CHANGE_POLICY.json",{}) or {}
    rules=policy.get("classification_rules") or DEFAULT_RULES
    classified=[classify_path(p,rules) for p in paths]
    cls=max_class([x["class"] for x in classified])
    print("staged_change_class:",cls)

    if cls=="C":
        print("change_guard: PASS Class C")
        return 0

    rec=load(current_record_path(repo),{}) or {}
    if rec.get("impact_status")!="PASS_PRECHANGE":
        print("HOLD: Class A/B staged change without PASS_PRECHANGE")
        return 2

    uncovered=paths_covered(paths,rec.get("planned_paths") or [])
    if uncovered:
        print("HOLD: staged engineering paths not covered by active change:",uncovered)
        return 2

    print("change_guard: PASS",rec.get("id"))
    return 0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=r"D:\BreshevEngineering\marvilon-k01")
    sub=ap.add_subparsers(dest="cmd",required=True)

    b=sub.add_parser("begin")
    b.add_argument("--id",required=True)
    b.add_argument("--class",dest="change_class",choices=["A","B","C"])
    b.add_argument("--title",required=True)
    b.add_argument("--reason",required=True)
    b.add_argument("--paths",nargs="*")
    b.add_argument("--nodes",nargs="*")
    b.add_argument("--entities",nargs="*")
    b.add_argument("--change-domain", choices=["requirement","interface_requirement","geometry","interface_geometry","material","product_definition","pmi","analysis_input","manufacturing_process","metadata","drawing_visual"])
    b.add_argument("--requirements",nargs="*")
    b.add_argument("--rationale")
    b.add_argument("--verification",nargs="*")
    b.add_argument("--revision-action")

    i=sub.add_parser("impact");i.add_argument("--change")

    w=sub.add_parser("what-if")
    w.add_argument("--paths",nargs="*")
    w.add_argument("--nodes",nargs="*")
    w.add_argument("--entities",nargs="*")
    w.add_argument("--change-domain", required=True, choices=["requirement","interface_requirement","geometry","interface_geometry","material","product_definition","pmi","analysis_input","manufacturing_process","metadata","drawing_visual"])

    sub.add_parser("implementation")

    v=sub.add_parser("verify")
    v.add_argument("--status",choices=["PASS","HOLD"],required=True)
    v.add_argument("--evidence",nargs="*")

    p=sub.add_parser("promote")
    p.add_argument("--decision",choices=["APPROVE","REJECT"],required=True)

    sub.add_parser("guard")

    args=ap.parse_args()
    repo=Path(str(args.repo_root).strip().strip('"')).resolve()
    handlers={
        "begin":cmd_begin,
        "impact":cmd_impact,
        "what-if":cmd_whatif,
        "implementation":cmd_implementation,
        "verify":cmd_verify,
        "promote":cmd_promote,
        "guard":cmd_guard
    }
    return handlers[args.cmd](repo,args)

if __name__=="__main__":
    raise SystemExit(main())
