from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

BUILD_REL=Path("reports/cad/current/K01_GATE04B_DATUM_C_BUILD.json")
QA_REL=Path("reports/cad/current/K01_GATE04B_DATUM_C_ASSEMBLY_QA.json")
PARTS_REL=Path("control/product/parts.json")
CHECKPOINT_PTR_REL=Path("control/project/K01_CHECKPOINT_CURRENT.json")
TF_MAP_REL=Path("reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json")
TF_REL=Path("control/change/K01_BASELINE_02C_PROMOTION_TECHNICAL_FILTER_REVIEW.json")
OUT_REL=Path("reports/control/K01_BASELINE_02C_PROMOTION_PREFLIGHT_CURRENT.json")

def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def add(rows,name,ok,actual=None,expected=None):
    rows.append({"check":name,"status":"PASS" if ok else "FAIL","actual":actual,"expected":expected})
    return ok

def main():
    ap=argparse.ArgumentParser(description="K01 Baseline-02C read-only canonical-promotion preflight")
    ap.add_argument("--repo-root",required=True)
    a=ap.parse_args(); root=Path(a.repo_root).resolve()
    rows=[]
    build=load(root/BUILD_REL); qa=load(root/QA_REL); parts=load(root/PARTS_REL)
    cp_ptr=load(root/CHECKPOINT_PTR_REL); tf=load(root/TF_REL)
    cp_rel=cp_ptr.get("path")
    cp=load(root/cp_rel) if cp_rel and (root/cp_rel).is_file() else {}
    tf_map=load(root/TF_MAP_REL) if (root/TF_MAP_REL).is_file() else {}

    add(rows,"current checkpoint id",cp_ptr.get("checkpoint_id")=="K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED",cp_ptr.get("checkpoint_id"),"K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED")
    add(rows,"immutable checkpoint resolves",bool(cp) and cp.get("checkpoint_id")==cp_ptr.get("checkpoint_id"),cp.get("checkpoint_id"),cp_ptr.get("checkpoint_id"))
    add(rows,"checkpoint",cp.get("status")=="VERIFIED_CANDIDATE_PENDING_CANONICAL_PROMOTION",cp.get("status"),"VERIFIED_CANDIDATE_PENDING_CANONICAL_PROMOTION")
    add(rows,"technical-filter change review",str(tf.get("status","")).startswith("PASS_TO_PREFLIGHT"),tf.get("status"),"PASS_TO_PREFLIGHT...")
    add(rows,"Gate04B producer",build.get("status")=="PASS",build.get("status"),"PASS")
    add(rows,"candidate assembly QA",qa.get("status")=="PASS_CANDIDATE_ASSEMBLY_QA",qa.get("status"),"PASS_CANDIDATE_ASSEMBLY_QA")
    add(rows,"component count",qa.get("component_count")==14,qa.get("component_count"),14)
    add(rows,"active mate errors",qa.get("active_mate_errors")==0,qa.get("active_mate_errors"),0)
    add(rows,"unexpected interference",qa.get("unexpected_interference_total")==0,qa.get("unexpected_interference_total"),0)
    add(rows,"moving group",qa.get("moving_group_pass") is True,qa.get("moving_group_pass"),True)
    add(rows,"stroke restore",qa.get("original_limit_restored") is True,qa.get("original_limit_restored"),True)
    add(rows,"P017 depth",abs(float(qa.get("p017_press_depth_mm",999))-4.0)<=0.02,qa.get("p017_press_depth_mm"),4.0)
    add(rows,"P017 protrusion",abs(float(qa.get("p017_protrusion_mm",999))-2.0)<=0.02,qa.get("p017_protrusion_mm"),2.0)

    for part,key in [("P003","p003_candidate"),("P016","p016_candidate"),("P017","p017_candidate")]:
        expected=((build.get(part) or {}).get("native"))
        actual=qa.get(key)
        add(rows,f"{part} build/QA identity",actual==expected,actual,expected)

    p3=(build.get("P003") or {}).get("result") or {}
    add(rows,"P003 Through-All",p3.get("end_condition")=="THROUGH_ALL_BOTH",p3.get("end_condition"),"THROUGH_ALL_BOTH")
    add(rows,"P003 C-center error",float(p3.get("center_error_mm",999))<=0.02,p3.get("center_error_mm"),"<=0.02 mm")
    add(rows,"P003 Datum-A mapping error",float(p3.get("datumA_mapping_error_mm",999))<=0.02,p3.get("datumA_mapping_error_mm"),"<=0.02 mm")
    add(rows,"P003 model-to-sketch mapping",p3.get("sketch_center_mapping")=="MODEL_TO_SKETCH_TRANSFORM",p3.get("sketch_center_mapping"),"MODEL_TO_SKETCH_TRANSFORM")

    p17=(parts.get("items") or {}).get("K01-P-017")
    add(rows,"P017 product registry",p17 is not None,bool(p17),True)
    if p17:
        add(rows,"P017 release hold",p17.get("release_state")=="HOLD",p17.get("release_state"),"HOLD")
        add(rows,"P017 material baseline explicit","316L" in str(p17.get("material_authority","")),p17.get("material_authority"),"contains 316L")
        add(rows,"P017 native material remains open","OPEN" in str(p17.get("material_status","")).upper(),p17.get("material_status"),"OPEN")

    frozen={}
    for name,raw,expected in [
      ("canonical_A001",qa.get("canonical_assembly"),qa.get("canonical_sha256")),
      ("verification_A001",qa.get("verification_assembly"),qa.get("verification_sha256")),
      ("P003_candidate",qa.get("p003_candidate"),None),
      ("P016_candidate",qa.get("p016_candidate"),None),
      ("P017_candidate",qa.get("p017_candidate"),None)
    ]:
        p=Path(raw) if raw else None
        exists=bool(p and p.is_file())
        add(rows,f"{name} exists",exists,str(p) if p else None,True)
        if exists:
            h=sha256(p); frozen[name]={"path":str(p),"sha256":h,"size":p.stat().st_size}
            if expected: add(rows,f"{name} SHA guard",h.lower()==str(expected).lower(),h,expected)

    # Toolchain applicability checks. These do not approve mutation; they ensure we do not
    # accidentally run known-wrong paths.
    tool_observations=[]
    obsolete=root/"tools/sw_gate04b_close_datum_c.py"
    if obsolete.is_file():
        txt=obsolete.read_text(encoding="utf-8-sig",errors="replace")
        add(rows,"obsolete radial-slot closer positively identified","RADIAL SLOT" in txt and "CreateSketchSlot" in txt,True,True)
        tool_observations.append("tools/sw_gate04b_close_datum_c.py present; DO NOT EXECUTE for current EDR-023")
    else:
        tool_observations.append("tools/sw_gate04b_close_datum_c.py absent; no blocker because this superseded path is not required")

    finalpromo=root/"tools/medtas/final_assembly_promotion_v2_2.py"
    if finalpromo.is_file():
        txt=finalpromo.read_text(encoding="utf-8-sig",errors="replace")
        add(rows,"final-candidate/R01 promoter positively identified","cad/final_candidate" in txt or "K01_FINAL_ASSEMBLY_BASELINE" in txt,True,True)
        tool_observations.append("final_assembly_promotion_v2_2.py present; keep isolated from Baseline-02C stable promotion")
    else:
        tool_observations.append("final_assembly_promotion_v2_2.py absent; no blocker for Baseline-02C")

    stablepromo=root/"scripts/K01_PROMOTE_P003_P007.py"
    add(rows,"existing atomic stable-promotion source collected",stablepromo.is_file(),str(stablepromo),True)

    ok=all(r["status"]=="PASS" for r in rows)
    report={
      "schema":"k01.baseline_02c.promotion_preflight.v2",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":"PASS_READY_FOR_APPLICABLE_STABLE_PROMOTION_SOURCE_REVIEW" if ok else "HOLD_PREFLIGHT",
      "native_CAD_mutated":False,
      "mutation_allowed_by_this_tool":False,
      "checks":rows,
      "frozen_inputs":frozen,
      "technical_filter_global_state":{
        "path":str(TF_MAP_REL),
        "status":tf_map.get("status","MISSING"),
        "unmapped":tf_map.get("unmapped",[])
      },
      "tool_observations":tool_observations,
      "tool_disposition":{
        "tools/sw_gate04b_close_datum_c.py":"DO_NOT_EXECUTE_CURRENT_EDR023",
        "tools/medtas/final_assembly_promotion_v2_2.py":"DO_NOT_USE_FOR_BASELINE_02C_STABLE_PROMOTION",
        "scripts/K01_PROMOTE_P003_P007.py":"REVIEW_REUSE_ADAPT_PRECEDENT"
      },
      "next":"Review scripts/K01_PROMOTE_P003_P007.py and runners plus tools/sw_post_promotion_qa.py. Define exact P003/P016/P017 stable targets, P017 new stable identity path, backup/rollback, A001 reference update, and post-promotion verification before any write."
    }
    out=root/OUT_REL; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STATUS:",report["status"]); print("REPORT:",out)
    for r in rows:
        if r["status"]!="PASS": print("FAIL:",r["check"],"actual=",r["actual"],"expected=",r["expected"])
    return 0 if ok else 2

if __name__=="__main__":
    raise SystemExit(main())
