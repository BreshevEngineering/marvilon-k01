#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))

PROMOTION=Path("reports/control/K01_BASELINE_02C_PROMOTION_APPLY_CURRENT.json")
POST_QA=Path("reports/cad/current/K01_BASELINE_02C_POST_PROMOTION_ASSEMBLY_QA.json")
BASELINE=Path("control/baseline/K01_ENGINEERING_BASELINE.json")
CADSEM=Path("reports/medtas/cad/current/K01_CAD_SEM_A001.json")
DERIVED=Path("reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json")
EBOM=Path("reports/bom/current/K01_EBOM_A001_CURRENT.json")
MBOM=Path("reports/bom/current/K01_MBOM_A001_CURRENT.json")
CHECKPOINT_PTR=Path("control/project/K01_CHECKPOINT_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
P0P6=Path("control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json")
ACTIVE_STEP=Path("control/project/K01_ACTIVE_STEP_GATE.json")
CHANGE_CURRENT=Path("control/change/K01_CHANGE_CURRENT.json")
PROMO_CHANGE=Path("control/change/CHG-K01-BASELINE-02C-PROMOTION-001.json")
PROMO_CHANGE_RECORD=Path("control/change/records/CHG-K01-BASELINE-02C-PROMOTION-001.json")
D006_CHANGE=Path("control/change/CHG-K01-D006-CANDIDATE-001.json")
OUT=Path("reports/control/K01_BASELINE_02C_POST_PROMOTION_FINALIZE_CURRENT.json")
CANONICAL_A001=Path(r"D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM")

def load(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def write_json(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+".tmp")
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(str(t),str(p))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def near(v,t,tol):
    try:return abs(float(v)-float(t))<=tol
    except:return False
def base_id(x):
    m=re.search(r"(K01-(?:P|B|A)-\d{3})",str(x or ""),re.I)
    return m.group(1).upper() if m else str(x or "")
def run(cmd,root,timeout=600):
    cp=subprocess.run(cmd,cwd=str(root),capture_output=True,text=True,errors="replace",timeout=timeout)
    if cp.stdout: print(cp.stdout,end="")
    if cp.stderr: print(cp.stderr,end="",file=sys.stderr)
    if cp.returncode!=0: raise RuntimeError("command failed rc=%d: %s"%(cp.returncode," ".join(str(x) for x in cmd)))
    return cp

def validate_promotion(root):
    pp=root/PROMOTION; qp=root/POST_QA
    need(pp.is_file(),"promotion report missing")
    need(qp.is_file(),"post-promotion QA report missing")
    p=load(pp); q=load(qp)
    need(str(p.get("status") or "").startswith("PASS_ENGINEERING_BASELINE_PROMOTED_PENDING_SNAPSHOT_STALE_BOM"),
         "promotion is not successful: "+str(p.get("status")))
    need(p.get("native_CAD_mutated") is True,"promotion does not confirm native CAD mutation")
    post=p.get("poststate") or {}
    for k in ("P003","P016","P017","A001"):
        need(isinstance(post.get(k),dict),"poststate missing "+k)
        fp=Path(str(post[k].get("path") or ""))
        need(fp.is_file(),"stable file missing: "+str(fp))
        actual=sha(fp); expected=str(post[k].get("sha256") or "")
        need(actual.lower()==expected.lower(),f"{k} SHA mismatch actual={actual} expected={expected}")
    need(str(Path(post["A001"]["path"])).lower()==str(CANONICAL_A001).lower(),"A001 is not canonical stable identity")
    need(q.get("status")=="PASS_STABLE_ASSEMBLY_QA","post-promotion assembly QA is not PASS")
    need(int(q.get("component_count",-1))==14,"post-promotion component count != 14")
    need(int(q.get("active_mate_errors",-1))==0,"post-promotion active mate errors != 0")
    need(q.get("moving_group_pass") is True,"moving group is not PASS")
    need(int(q.get("unexpected_interference_total",-1))==0,"unexpected interference != 0")
    need(q.get("original_limit_restored") is True,"LimitDistance not restored")
    need(near(q.get("p017_press_depth_mm"),4.0,0.02),"P017 press depth invalid")
    need(near(q.get("p017_protrusion_mm"),2.0,0.02),"P017 protrusion invalid")
    return p,q

def update_baseline(root,promo):
    bp=root/BASELINE; old=load(bp); old_cad=deepcopy(old.get("cad") or {})
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    history=root/"reports/control/baseline_history"/f"K01_ENGINEERING_BASELINE_PRE_CP_P_{stamp}.json"
    write_json(history,old)
    a=promo["poststate"]["A001"]
    new=deepcopy(old)
    new["updated_utc"]=datetime.now(timezone.utc).isoformat()
    new["cad"]={
      "assembly":str(a["path"]),"logical_source":"cad/assemblies/K01-A-001_Calibration_Module.SLDASM",
      "sha256":str(a["sha256"]),"component_count":14,"authority":"DESIGN_AND_ANALYSIS",
      "promotion_checkpoint":"BASELINE_02C","post_promotion_qa":str(POST_QA).replace("\\","/")}
    sim=deepcopy(new.get("simulation") or {})
    sim["assembly_binding"]="HISTORICAL_PRE_BASELINE02C_CAD"
    sim["bound_cad"]=old_cad
    sim["freshness"]="STALE_RELATIVE_TO_CURRENT_CAD_BASELINE"
    sim["stale_reason"]="Preserved historical Simulation evidence is not silently rebound after A001/P003/P016 promotion and P017 addition."
    new["simulation"]=sim
    new["baseline_transition"]={"id":"K01-BASELINE-02C","previous_cad":old_cad,
      "promotion_report":str(PROMOTION).replace("\\","/"),"post_promotion_qa":str(POST_QA).replace("\\","/"),
      "rule":"CAD authority promoted; release-only OPEN items remain OPEN."}
    write_json(bp,new)
    return history,new

def fresh_semantic(root):
    run([sys.executable,str(root/"tools/medtas/run_cad_sem_a001.py"),"--repo-root",str(root)],root)
    cad=load(root/CADSEM); a=cad.get("assembly") or {}
    need(base_id(a.get("assembly_id"))=="K01-A-001","semantic assembly is not K01-A-001")
    need(int(a.get("component_instance_count",-1))==14,"semantic component count != 14")
    active=[x for x in (cad.get("instances") or []) if not x.get("suppressed")]
    need(len(active)==14,"active semantic occurrence count != 14")
    p17=[x for x in active if base_id(x.get("document_id"))=="K01-P-017"]
    need(len(p17)==1,"semantic P017 quantity != 1")
    return cad

def fresh_snapshot(root,cad):
    import build_downstream_v1_8 as d
    graph=d.load_graph(root); derived=d.evaluate(root)
    need((derived.get("K01.CAD.SEM.A001") or {}).get("state") in ("PASS","PASS_WITH_LIMITATIONS"),
         "CAD semantic node is not fresh")
    d.build_snapshot(root,graph,cad,derived)
    run([sys.executable,str(root/"tools/medtas/rebuild_medtas_state.py"),"--repo-root",str(root)],root,300)

def fresh_bom(root):
    run([sys.executable,str(root/"tools/medtas/build_bom_v1_9.py"),"--repo-root",str(root)],root,300)
    eb=load(root/EBOM); mb=load(root/MBOM)
    for n,v in (("EBOM",eb),("MBOM",mb)):
        need(int(v.get("modeled_occurrence_total",-1))==14,n+" modeled occurrence count != 14")
        need(int(v.get("modeled_quantity_total",-1))==14,n+" modeled quantity != 14")
        need(int(v.get("suppressed_occurrence_count",-1))==0,n+" suppressed occurrence count != 0")
    p17=[x for x in (eb.get("items") or []) if x.get("source")=="CAD_MODELED" and str(x.get("part_number") or "").upper()=="K01-P-017"]
    need(len(p17)==1 and int(p17[0].get("quantity") or 0)==1,"EBOM P017 quantity != 1")
    bad=[x for x in (eb.get("issues") or []) if str(x).startswith(("BOM-OCCURRENCE-PARITY","BOM-REGISTRY-MISSING","BOM-SUPPRESSION-UNEXPLAINED"))]
    need(not bad,"EBOM structural integrity issues: "+repr(bad))
    run([sys.executable,str(root/"tools/medtas/rebuild_medtas_state.py"),"--repo-root",str(root)],root,300)
    return eb,mb,load(root/DERIVED)

def write_cp_p(root,promo,qa,baseline,cad,eb,mb,derived):
    day=str(promo.get("generated_utc") or "")[:10].replace("-","") or datetime.now().strftime("%Y%m%d")
    cp_id=f"K01-CP-{day}-BASELINE-02C-PROMOTED"
    cp_rel=Path("control/checkpoints")/(cp_id+".json"); cp=root/cp_rel
    nodes=derived.get("nodes") or {}
    obj={
      "schema":"k01.engineering_checkpoint.v1","checkpoint_id":cp_id,"created_utc":datetime.now(timezone.utc).isoformat(),
      "active_line":"K01-BASELINE-02C","status":"CANONICAL_ENGINEERING_BASELINE_PROMOTED",
      "maturity":"CANONICAL_ENGINEERING_BASELINE","evidence_state":"PASS","freshness":"RECOMPUTED_AFTER_PROMOTION",
      "authority":"CANONICAL_DESIGN_AND_ANALYSIS","previous_checkpoint":"K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED",
      "cad":{"assembly":baseline["cad"]["assembly"],"sha256":baseline["cad"]["sha256"],"component_count":14,"p017_quantity":1},
      "promotion_evidence":{"apply":str(PROMOTION).replace("\\","/"),"post_promotion_qa":str(POST_QA).replace("\\","/"),
        "moving_group_pass":qa.get("moving_group_pass"),"unexpected_interference_total":qa.get("unexpected_interference_total"),
        "p017_press_depth_mm":qa.get("p017_press_depth_mm"),"p017_protrusion_mm":qa.get("p017_protrusion_mm")},
      "semantic_state":{"state":(nodes.get("K01.CAD.SEM.A001") or {}).get("state"),
        "state_hash":(nodes.get("K01.CAD.SEM.A001") or {}).get("state_hash"),
        "artifact_hash":(nodes.get("K01.CAD.SEM.A001") or {}).get("artifact_hash")},
      "snapshot_state":{"state":(nodes.get("K01.SNAPSHOT.A001") or {}).get("state"),
        "state_hash":(nodes.get("K01.SNAPSHOT.A001") or {}).get("state_hash"),
        "artifact_hash":(nodes.get("K01.SNAPSHOT.A001") or {}).get("artifact_hash")},
      "bom":{"ebom_status":eb.get("status"),"mbom_status":mb.get("status"),"modeled_occurrences":14,"p017_quantity":1},
      "materials":{"P003":"AISI 316L / EN 1.4404 CONTROLLED","P016":"AISI 316L current CAD; production Long Run compatibility/weld route OPEN",
        "P017":"AISI 316L / EN 1.4404 baseline; native material-card assignment OPEN"},
      "release":{"R01":"NOT_RELEASED","note":"CP-P closes the canonical engineering-baseline transition only."},
      "next_transition":"P007_CANONICAL_REBIND_AND_PROFESSIONAL_DIMXPERT_PMI_AUTHORING"}
    if cp.exists():
        old=load(cp); need((old.get("cad") or {}).get("sha256")==obj["cad"]["sha256"],"existing CP-P has different A001 hash")
    else: write_json(cp,obj)
    write_json(root/CHECKPOINT_PTR,{"schema":"k01.checkpoint.current.v1","project":"K01","checkpoint_id":cp_id,
      "path":str(cp_rel).replace("\\","/"),"status":"CANONICAL_ENGINEERING_BASELINE_PROMOTED",
      "active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION",
      "previous_checkpoint":"K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED",
      "next_expected_checkpoint":"P007 professional DimXpert/PMI candidate checkpoint after geometry-invariant save/close/reopen readback",
      "rule":"Pointer only; domain authorities remain in K01_AUTHORITY_MAP_CURRENT.json."})
    for rel in (PROMO_CHANGE,PROMO_CHANGE_RECORD):
        p=root/rel
        if p.is_file():
            ch=load(p); ch["updated_utc"]=datetime.now(timezone.utc).isoformat()
            ch["status"]="CLOSED_ENGINEERING_BASELINE_PROMOTED"; ch["implementation_status"]="COMPLETE"
            ch["verification_status"]="PASS_POST_PROMOTION_QA_SNAPSHOT_BOM_PARITY"; ch["promotion_status"]="PROMOTED"
            ch["promotion_decision"]="PASS_CANONICAL_ENGINEERING_BASELINE; R01_NOT_RELEASED"; write_json(p,ch)
    if (root/D006_CHANGE).is_file(): write_json(root/CHANGE_CURRENT,load(root/D006_CHANGE))
    write_json(root/NEXT,{"schema":"k01.next_actions.v4","active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION",
      "current_stage":"CP_P_PASS_READY_FOR_CANONICAL_P007_REBIND_AND_DIMXPERT_AUTHORING","checkpoint_id":cp_id,
      "last_completed":"Baseline-02C canonical promotion + post-QA + fresh semantic snapshot + EBOM/MBOM parity: A001=14 modeled occurrences, P017=1.",
      "next_1":"Reconcile canonical stable K01-P-007 against the existing Step13 PMI candidate and Product Characteristics.",
      "next_2":"Author/verify C01/C02/C03/C04/C05/C06/C09 through native DimXpert/PMI with geometry-invariant save-close-reopen readback.",
      "then":"Regenerate K01-D-006 candidate from native PMI, run semantic lint + visual QA, then bind inspection characteristics.",
      "release_open":"C07/C08/C10/C11/C12 and blind-end release specifications remain OPEN; do not invent them.",
      "filesystem_rule":"Do not relocate existing folders/files; candidate authoring must not overwrite canonical stable P007."})
    mpath=root/P0P6
    if mpath.is_file():
        m=load(mpath); m["generated_utc"]=datetime.now(timezone.utc).isoformat(); g=m.get("gates") or {}
        p0=g.get("P0_CURRENT_BASELINE") or {}; p0["status"]="PASS_BASELINE_02C_CANONICAL"; it=p0.get("items") or {}
        it.update({"Baseline_02C_canonical_promotion":"PASS","post_promotion_snapshot":"PASS",
                   "post_promotion_stale_reduction":"PASS_MEDTAS_RECOMPUTED",
                   "post_promotion_EBOM":"PASS_STRUCTURE_PARITY_14_OCCURRENCES_P017_X1"})
        p0["items"]=it; g["P0_CURRENT_BASELINE"]=p0
        p1=g.get("P1_FUNCTION_INTERFACES") or {}; i1=p1.get("items") or {}; i1["J1_Datum_C"]="PASS_CANONICAL_BASELINE"; p1["items"]=i1; g["P1_FUNCTION_INTERFACES"]=p1
        p4=g.get("P4_CANDIDATE_TPD") or {}; i4=p4.get("items") or {}; i4["EBOM"]=f"{eb.get('status')}; 14 occurrences; P017 x1"; i4["MBOM"]=f"{mb.get('status')}; release/process OPENs preserved"; p4["items"]=i4; g["P4_CANDIDATE_TPD"]=p4
        m["gates"]=g; write_json(mpath,m)
    write_json(root/ACTIVE_STEP,{
      "schema":"k01.active_step_gate.v1","step_id":"K01-STEP-P4-P007-PROFESSIONAL-DIMXPERT-AUTHORING",
      "active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION","checkpoint_id":cp_id,
      "intent":"RECONCILE_CANONICAL_P007_AND_AUTHOR_GEOMETRY_INVARIANT_DIMXPERT_PMI_CANDIDATE",
      "mutation_authorized":True,"result_on_pass":"PASS_TO_P007_PROFESSIONAL_DIMXPERT_CANDIDATE_AUTHORING",
      "required_files":[str(cp_rel).replace("\\","/"),"control/drawings/K01_D006_AUTHORING_INPUT.json",
        "control/drawings/K01_D006_RELEASE_DEFINITION.json","control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json",
        "control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json","docs/architecture/K01_DIMXPERT_DRAWING_PIPELINE_v1.md",
        str(PROMOTION).replace("\\","/"),str(EBOM).replace("\\","/"),"reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json"],
      "required_statuses":[
        {"file":"reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json","path":["status"],"allowed_prefixes":["PASS"]},
        {"file":"control/drawings/K01_D006_AUTHORING_INPUT.json","path":["status"],"allowed_values":["READY_FOR_CANDIDATE_AUTHORING"]},
        {"file":"control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json","path":["status"],"allowed_prefixes":["PASS_PILOT_SAVE_CLOSE_REOPEN"]},
        {"file":str(PROMOTION).replace("\\","/"),"path":["status"],"allowed_prefixes":["PASS_ENGINEERING_BASELINE_PROMOTED"]},
        {"file":"control/change/K01_CHANGE_CURRENT.json","path":["id"],"allowed_values":["CHG-K01-D006-CANDIDATE-001"]}],
      "impact_declarations":{
        "requirements":"No release values are invented; unresolved P007 tolerances/process/leak criteria remain OPEN.",
        "materials":"P007 remains AISI 316L / EN 1.4404; no material change.",
        "bom":"PMI authoring must be geometry-invariant and must not alter A001 quantities.",
        "dimxpert_drawings":"Author candidate C01/C02/C03/C04/C05/C06/C09, then derive K01-D-006; C07/C08/C10/C11/C12/blind-end remain OPEN.",
        "inspection":"Prepare candidate characteristic traceability; no released inspection acceptance.",
        "dependencies":"Any P007 geometry change invalidates bindings/drawing/affected analyses and stops authoring.",
        "technical_filter":"Apply mapped P007 product-definition/drawing categories with explicit OPEN/N/A disposition.",
        "rollback":"Work on timestamped P007 candidate copy only; canonical stable P007 is read-only.",
        "evidence":"PMI save-close-reopen readback + persistent refs + geometry fingerprint invariance + drawing lint/visual QA."}})
    return cp_id

def refresh_next_gate_and_panel(root):
    run([sys.executable,str(root/"tools/medtas/technical_filter_map_v2_2.py"),"--repo-root",str(root)],root,180)
    run([sys.executable,str(root/"tools/assurance/engineering_step_gate.py"),"--repo-root",str(root)],root,180)
    panel=root/"tools/assurance/build_engineering_dashboard.py"
    if panel.is_file(): run([sys.executable,str(panel),"--repo-root",str(root)],root,180)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",required=True); a=ap.parse_args()
    root=Path(a.repo_root).resolve(); out=root/OUT
    rep={"schema":"k01.baseline_02c.post_promotion_finalize.v1","generated_utc":datetime.now(timezone.utc).isoformat(),
         "status":"RUNNING","native_CAD_mutated":False,"phases":[]}
    try:
        promo,qa=validate_promotion(root); rep["phases"].append({"id":"PROMOTION_EVIDENCE","status":"PASS"})
        hist,baseline=update_baseline(root,promo); rep["phases"].append({"id":"BASELINE_AUTHORITY","status":"PASS","history_copy":str(hist)})
        cad=fresh_semantic(root); rep["phases"].append({"id":"CAD_SEMANTIC","status":"PASS","occurrences":14,"P017":1})
        fresh_snapshot(root,cad); rep["phases"].append({"id":"SNAPSHOT_FRESHNESS","status":"PASS"})
        eb,mb,derived=fresh_bom(root); rep["phases"].append({"id":"EBOM_MBOM","status":"PASS","ebom":eb.get("status"),"mbom":mb.get("status"),"occurrences":14,"P017":1})
        cp=write_cp_p(root,promo,qa,baseline,cad,eb,mb,derived); rep["phases"].append({"id":"CP_P","status":"PASS","checkpoint":cp})
        refresh_next_gate_and_panel(root)
        rep["status"]="PASS_CP_P_CANONICAL_BASELINE_READY_FOR_P007_DIMXPERT"; rep["checkpoint"]=cp; rep["canonical_a001"]=baseline["cad"]; rep["next"]="P007 canonical rebind -> native DimXpert/PMI C01/C02/C03/C04/C05/C06/C09 -> K01-D-006 -> inspection"
        write_json(out,rep)
        print("STATUS:",rep["status"]); print("CHECKPOINT:",cp); print("CANONICAL A001:",baseline["cad"]["assembly"]); print("A001 SHA256:",baseline["cad"]["sha256"])
        print("EBOM modeled occurrences: 14"); print("K01-P-017 qty: 1"); print("NEXT: P007 professional DimXpert/PMI"); print("REPORT:",out); return 0
    except Exception as e:
        rep["status"]="HOLD_POST_PROMOTION_FINALIZE"; rep["error"]=repr(e); write_json(out,rep)
        print("STATUS:",rep["status"]); print("REPORT:",out); print("ERROR:",repr(e)); return 2
if __name__=="__main__": raise SystemExit(main())
