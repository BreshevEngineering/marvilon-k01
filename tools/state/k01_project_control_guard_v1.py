from __future__ import annotations
import argparse, datetime as dt, hashlib, json
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
P={
 "epoch":Path("control/state/K01_STATE_EPOCH_CURRENT.json"),
 "frontier":Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json"),
 "goal":Path("control/project/K01_GOAL_LOCK_CURRENT.json"),
 "next":Path("control/project/K01_NEXT_ACTIONS_CURRENT.json"),
 "gate":Path("control/project/K01_ACTIVE_STEP_GATE.json"),
 "temporal":Path("reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json"),
 "semantic":Path("reports/control/K01_SEMANTIC_COHERENCE_CURRENT.json"),
 "registry":Path("control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json"),
 "coverage":Path("reports/control/K01_ENGINEERING_SYSTEM_COVERAGE_CURRENT.json"),
 "spine":Path("reports/control/K01_PROJECT_CONTROL_SPINE_CURRENT.json"),
 "analysis":Path("reports/control/K01_ANALYSIS_REGISTER_CURRENT.json"),
 "bom":Path("reports/control/K01_BOM_RELEASE_STATUS_CURRENT.json"),
 "git":Path("reports/control/K01_GIT_GITHUB_STATUS_CURRENT.json"),
 "decision_identity":Path("reports/control/K01_DECISION_IDENTITY_COHERENCE_CURRENT.json"),
 "value_coherence":Path("reports/control/K01_ENGINEERING_VALUE_COHERENCE_CURRENT.json"),
 "characteristics":Path("control/product_definition/K01_CONTROLLED_CHARACTERISTIC_REGISTRY_CURRENT.json"),
 "references":Path("control/engineering/K01_ENGINEERING_REFERENCE_REGISTRY_CURRENT.json"),
 "sw_api_standard":Path("cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_OPERATING_STANDARD_CURRENT.txt"),
 "matrix":Path("reports/control/K01_PROJECT_CONTROL_MATRIX_CURRENT.json"),
 "report":Path("reports/control/K01_PROJECT_COVERAGE_COHERENCE_CURRENT.json"),
}

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def sha(p):
    h=hashlib.sha256();
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def issue(xs,rule,detail):xs.append({"rule":rule,"detail":detail})

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root).resolve();now=dt.datetime.now(dt.timezone.utc).isoformat()
    x={};issues=[]
    for k,r in P.items():
        if k in {"matrix","report"}:continue
        q=repo/r
        if not q.is_file(): issue(issues,"COV-00",f"required project-control source missing: {r}"); x[k]={}
        else:x[k]=rd(q,{}) or {}
    epoch=x.get("epoch",{}).get("state_epoch")
    frontier=x.get("frontier",{}); goal=x.get("goal",{}); nxt=x.get("next",{}); gate=x.get("gate",{})
    fnext=(frontier.get("next_allowed_action") or {}).get("id")
    fblock=frontier.get("active_blocker"); fblock=fblock.get("id") if isinstance(fblock,dict) else fblock
    # Global state identity/coherence
    if frontier.get("state_epoch")!=epoch: issue(issues,"COV-STATE-01",f"Completion Frontier epoch {frontier.get('state_epoch')!r} != global epoch {epoch!r}")
    if goal.get("next_action_id") and goal.get("next_action_id")!=fnext: issue(issues,"COV-STATE-02",f"Goal Lock NEXT {goal.get('next_action_id')!r} != frontier {fnext!r}")
    if nxt.get("next_action_id")!=fnext: issue(issues,"COV-STATE-03",f"Next Actions NEXT {nxt.get('next_action_id')!r} != frontier {fnext!r}")
    if gate.get("intent")!=fnext: issue(issues,"COV-STATE-04",f"Active Step intent {gate.get('intent')!r} != frontier {fnext!r}")
    if x.get("semantic",{}).get("state_epoch")!=epoch: issue(issues,"COV-STATE-05","Semantic report is not bound to current State Epoch")
    if x.get("temporal",{}).get("state_epoch")!=epoch: issue(issues,"COV-STATE-06","Temporal report is not bound to current State Epoch")
    if x.get("semantic",{}).get("status")!="PASS_SEMANTIC_COHERENCE": issue(issues,"COV-STATE-07","Semantic coherence is not PASS")
    if x.get("temporal",{}).get("status")!="PASS_TEMPORAL_COHERENCE": issue(issues,"COV-STATE-08","Temporal coherence is not PASS")
    if x.get("decision_identity",{}).get("status")!="PASS_DECISION_IDENTITY_COHERENCE":
        issue(issues,"COV-CONFIG-01","Decision identity coherence is not PASS")
    if x.get("value_coherence",{}).get("status")!="PASS_ENGINEERING_VALUE_COHERENCE":
        issue(issues,"COV-ENGVAL-01","Engineering value coherence is not PASS")
    if x.get("references",{}).get("status")!="CONTROLLED_REFERENCE_INDEX":
        issue(issues,"COV-DATA-01","Engineering reference registry missing/not controlled")
    timing=frontier.get("timing") or {}
    if len(timing.get("ACTIVE_NOW") or [])!=1: issue(issues,"COV-07",f"Expected exactly one ACTIVE_NOW, got {timing.get('ACTIVE_NOW')!r}")

    # Source coverage: use the already-existing 17-domain registry, do not create a competing taxonomy.
    registry=x.get("registry",{}); coverage=x.get("coverage",{})
    reg_domains=registry.get("domains") or []; cov_domains=coverage.get("domains") or []
    reg_ids=[d.get("id") for d in reg_domains if d.get("id")]; cov_by={d.get("id"):d for d in cov_domains if d.get("id")}
    for did in reg_ids:
        if did not in cov_by: issue(issues,"COV-01",f"Mandatory engineering domain missing from current coverage: {did}")
    # Required persistent categories that have historically been lost from chat/project navigation.
    for did in ("EBOM","MBOM","STRUCTURAL_FEA","MAGNETIC_FEMM","FLOW_CFD","CONFIGURATION_RELEASE_BASELINE","REPO_HANDOFF_TOOLCHAIN"):
        if did not in reg_ids: issue(issues,"COV-18",f"Critical persistent domain absent from registry: {did}")

    # State identity and projection freshness are intentionally separate.
    # Authorities define the State Epoch; generated CURRENT ledgers are observed
    # after generation and guarded for drift without feeding back into epoch identity.
    tracked={r.get("path") for r in (x.get("epoch",{}).get("source_fingerprints") or []) if r.get("path")}
    observed={r.get("path") for r in (x.get("epoch",{}).get("projection_observations") or []) if r.get("path")}
    registry_rel=str(P["registry"]).replace('\\','/')
    if registry_rel not in tracked:
        issue(issues,"COV-FRESH-01",f"Engineering domain registry authority is not bound into current State Epoch fingerprint: {registry_rel}")
    required_observed=[str(P[k]).replace('\\','/') for k in ("coverage","spine","analysis","bom","git","decision_identity","value_coherence")]
    for rel in required_observed:
        if rel not in observed:
            issue(issues,"COV-FRESH-02",f"Cross-cutting generated projection is not recorded in current projection observations: {rel}")

    # Build a compact matrix from existing authorities/projections.
    analysis_by={d.get("domain"):d for d in (x.get("analysis",{}).get("domains") or []) if d.get("domain")}
    map_analysis={"STRUCTURAL_FEA":"Structural/SWSIM","MAGNETIC_FEMM":"FEMM","FLOW_CFD":"Flow/CFD","TOLERANCE_VARIATION":"Tolerance/Variation","PRESSURE_VACUUM_CONTAINMENT":"Pressure/Vacuum/Containment","EBOM":"EBOM","MBOM":"MBOM","INSPECTION_METROLOGY":"Inspection/Metrology","CONFIGURATION_RELEASE_BASELINE":"Configuration/Release"}
    rows=[]
    for rec in reg_domains:
        did=rec.get("id"); c=cov_by.get(did,{})
        arow=analysis_by.get(map_analysis.get(did),{})
        row={
          "id":did,"title":rec.get("title"),"release_relevance":rec.get("release_relevance"),
          "coverage_state":c.get("coverage_state") or "MISSING",
          "runtime_state":(c.get("runtime_probe") or {}).get("state"),
          "analysis_status":arow.get("status"),"trust_level":arow.get("trust_level"),
          "decision_supported":arow.get("decision_supported"),
          "declared_gaps":c.get("declared_gaps") or [],
        }
        if did=="EBOM":row["domain_status"]=x.get("bom",{}).get("status")
        if did=="MBOM":row["domain_status"]=x.get("bom",{}).get("status")
        if did=="REPO_HANDOFF_TOOLCHAIN":row["git_github"]=x.get("git",{})
        rows.append(row)
    matrix={
      "schema":"k01.project_control_matrix.current.v1","generated_utc":now,"state_epoch":epoch,
      "status":"CONTROLLED_PROJECT_COVERAGE_PROJECTION",
      "current_lifecycle_level":frontier.get("current_lifecycle_level"),"current_deliverable":frontier.get("current_deliverable"),
      "active_engineering_object":frontier.get("active_engineering_object"),"active_blocker":fblock,
      "global_next_action_id":fnext,"global_next_action":(frontier.get("next_allowed_action") or {}).get("text"),
      "timing":timing,"domains":rows,
      "source_digests":{k:sha(repo/P[k]) if (repo/P[k]).is_file() else None for k in ("registry","coverage","spine","analysis","bom","git","decision_identity","value_coherence","characteristics","references","sw_api_standard")},
      "rule":"Projection only. Engineering values remain in domain authorities."
    }
    wr(repo/P["matrix"],matrix)
    status="PASS_PROJECT_COVERAGE" if not issues else "HOLD_PROJECT_COVERAGE"
    rep={
      "schema":"k01.project_coverage_coherence.current.v1","generated_utc":now,"state_epoch":epoch,"status":status,
      "domain_count_registry":len(reg_ids),"domain_count_coverage":len(cov_by),"issues":issues,
      "matrix":str(P["matrix"]).replace('\\','/'),
      "rule":"PASS means all mandatory domains are represented and globally coherent; it does not mean all engineering domains are closed."
    }
    wr(repo/P["report"],rep)
    print(status,"issues=",len(issues))
    for i in issues:print("HOLD:",json.dumps(i,ensure_ascii=False))
    if not issues:
        print("LIFECYCLE:",frontier.get("current_lifecycle_level"))
        print("DELIVERABLE:",frontier.get("current_deliverable"))
        print("ACTIVE:",frontier.get("active_engineering_object"))
        print("NEXT:",(frontier.get("next_allowed_action") or {}).get("text"))
    return 0 if not issues else 2

if __name__=="__main__": raise SystemExit(main())
