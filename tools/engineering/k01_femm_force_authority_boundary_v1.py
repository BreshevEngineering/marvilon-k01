from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
REQ=Path("control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json")
SUM=Path("reports/femm/final_candidate_20260916_v3/K01_FEMM_FINAL_CANDIDATE_SUMMARY_V3.json")
EDR=Path("control/decisions/EDR-039_FEMM_DERIVED_SCREEN_AUTHORITY_BOUNDARY.json")
REP=Path("reports/engineering/K01_FEMM_FORCE_REQUIREMENT_BOUNDARY_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def find_req(x,rid):
    if isinstance(x,dict):
        if str(x.get("id") or x.get("requirement_id") or "")==rid:return x
        if rid in x and isinstance(x[rid],dict):return x[rid]
        for v in x.values():
            q=find_req(v,rid)
            if q is not None:return q
    elif isinstance(x,list):
        for v in x:
            q=find_req(v,rid)
            if q is not None:return q
    return None

def guard(repo):
    for tool in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        cp=subprocess.run([sys.executable,"tools/state/"+tool,"--repo-root",str(repo),"--write-report"],cwd=repo,text=True)
        if cp.returncode:
            raise SystemExit("HOLD: state guards must PASS before FEMM authority classification.")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(R))
    a=ap.parse_args()
    repo=Path(a.repo_root)
    guard(repo)

    if not (repo/REQ).is_file() or not (repo/SUM).is_file():
        raise SystemExit("HOLD: requirement or FEMM V3 summary missing.")

    reqall=rd(repo/REQ,{}) or {}
    req=find_req(reqall,"REQ-K01-ACT-FORCE-001")
    if not req:
        raise SystemExit("HOLD: REQ-K01-ACT-FORCE-001 not found in current release requirements.")

    # The requirement schema may not contain a literal numeric_acceptance_status.
    # Determine the numeric-acceptance state from the authoritative requirement
    # fields without modifying the requirement.
    explicit_numeric=req.get("numeric_acceptance_status")
    acceptance=req.get("acceptance")
    lifecycle=str(req.get("lifecycle_status") or req.get("status") or "").upper()
    coverage=str(req.get("coverage_status") or "").upper()
    release_blocker=bool(req.get("release_blocker",False))
    numeric_value_present=acceptance not in (None,"",[],{})

    if explicit_numeric is not None:
        numeric_open=str(explicit_numeric).upper()=="OPEN"
        numeric_basis="EXPLICIT numeric_acceptance_status="+repr(explicit_numeric)
    else:
        numeric_open=(not numeric_value_present) and (
            lifecycle in ("OPEN","CANDIDATE","PARTIAL","")
            or "OPEN" in coverage
            or coverage=="UNCOVERED"
            or release_blocker
        )
        numeric_basis=(
            "DERIVED_FROM_REQUIREMENT_SCHEMA: acceptance="+repr(acceptance)
            +", lifecycle_status="+repr(lifecycle)
            +", coverage_status="+repr(coverage)
            +", release_blocker="+repr(release_blocker)
        )

    if not numeric_open:
        raise SystemExit(
            "HOLD: REQ-K01-ACT-FORCE-001 no longer proves numeric acceptance OPEN. "
            +numeric_basis
        )

    s=rd(repo/SUM,{}) or {}
    criterion=float(s.get("criterion_N_per_A"))
    derived=2.0*(0.25+0.185447243+0.03)
    if abs(criterion-derived)>1e-9:
        raise SystemExit(f"HOLD: FEMM criterion {criterion} != derived screen {derived}")

    sc=s.get("scenarios") or {}
    keys=["CANDIDATE_350_BR1_BOUND","SENSITIVITY_350_BR095"]
    for k in keys:
        if (sc.get(k) or {}).get("verdict")!="PASS_NUMERICAL_SCREEN":
            raise SystemExit("HOLD: FEMM scenario not numerical-screen PASS: "+k)

    report={
      "schema":"k01.femm_force_requirement_boundary.current.v1",
      "generated_utc":now(),
      "status":"PASS_EVIDENCE_CLASSIFICATION__REQ_ACT_FORCE_NUMERIC_OPEN",
      "requirement_id":"REQ-K01-ACT-FORCE-001",
      "requirement_numeric_acceptance_status":"OPEN",
      "requirement_numeric_acceptance_basis":numeric_basis,
      "requirement_authority_snapshot":{
        "acceptance":acceptance,
        "lifecycle_status":req.get("lifecycle_status"),
        "coverage_status":req.get("coverage_status"),
        "release_blocker":req.get("release_blocker"),
        "verification_method":req.get("verification_method")},
      "requirement_release_state":"OPEN/CANDIDATE — NOT CLOSED BY FEMM",
      "derived_screen":{
        "class":"DERIVED_ENGINEERING_SCREEN__NOT_RELEASE_REQUIREMENT",
        "formula":"2*(F_breakaway_max + abs(F_CFD_max) + F_inertia)",
        "inputs_N":{"F_breakaway_max":0.25,"F_CFD_max":0.185447243,"F_inertia":0.03},
        "safety_factor":2.0,
        "force_at_1A_N":derived,
        "equivalent_KF_at_1A_N_per_A":derived},
      "femm_v3":{
        "overall":s.get("overall"),
        "candidate_350_BR1_KFmin_N_per_A":sc[keys[0]]["K_F_min_N_per_A"],
        "candidate_margin_pct":sc[keys[0]]["margin_pct"],
        "sensitivity_350_BR095_KFmin_N_per_A":sc[keys[1]]["K_F_min_N_per_A"],
        "sensitivity_margin_pct":sc[keys[1]]["margin_pct"]},
      "verdict":"FEMM V3 passes the current derived numerical design screen only.",
      "explicit_non_verdicts":[
        "Does not release numeric acceptance for REQ-K01-ACT-FORCE-001.",
        "Does not reinstate historical passive-coupling 5 N / 15 N criteria.",
        "Does not constitute B001 lot qualification, P015 thermal/winding qualification, bench correlation or product release."],
      "remaining_release_evidence":[
        "released numeric REQ-K01-ACT-FORCE-001 envelope",
        "B001 supplier/lot Br(T) and tolerances",
        "P015 production winding/driver/thermal definition",
        "hot/cold breakaway measurement both directions",
        "qualified gas/mechanical load envelope",
        "physical F(x,I,T) bench test and FEMM correlation"]}

    wr(repo/REP,report)
    wr(repo/EDR,{
      "schema":"k01.edr.v1",
      "decision_id":"EDR-039",
      "date":"2026-09-17",
      "subject":"FEMM V3 derived screening criterion versus released actuator-force requirement",
      "status":"ACCEPTED_EVIDENCE_CLASSIFICATION",
      "decision":"Classify K_F,min >= 0.930894486 N/A at nominal 1 A as a derived engineering design screen only. FEMM V3 PASS is numerical-candidate evidence, not closure of REQ-K01-ACT-FORCE-001.",
      "basis":{
        "derived_formula":"2*(0.25 + 0.185447243 + 0.03)=0.930894486 N; at 1 A the coefficient screen is numerically 0.930894486 N/A",
        "requirement_numeric_acceptance_status":"OPEN",
        "requirement_numeric_acceptance_basis":numeric_basis,
        "requirement_acceptance_field":acceptance,
        "requirement_lifecycle_status":req.get("lifecycle_status"),
        "requirement_release_blocker":req.get("release_blocker"),
        "FEMM_summary":str(SUM).replace("\\","/")},
      "accepted":[
        "CANDIDATE_350_BR1_BOUND: K_F,min=1.003471389 N/A, +7.796% versus derived screen — PASS_NUMERICAL_SCREEN",
        "SENSITIVITY_350_BR095: K_F,min=0.953259402 N/A, +2.403% versus derived screen — PASS_NUMERICAL_SCREEN"],
      "not_accepted":[
        "REQ-K01-ACT-FORCE-001 numeric acceptance is NOT released.",
        "Historical passive 5 N / 15 N targets are NOT inherited.",
        "FEMM numerical PASS is NOT physical qualification or product release."],
      "release_boundary":"Requirement closure requires released numeric force/force-coefficient envelope plus physical qualification evidence; FEMM remains one evidence class.",
      "downstream_impact":{
        "P004":"NONE — active Product Definition frontier unchanged",
        "FEMM":"evidence semantics corrected",
        "requirements":"NO MUTATION; numeric acceptance remains OPEN",
        "BOM":"NONE","CAD":"NONE","drawing":"NONE"}})

    cm=rd(repo/CENTER,{}) or {}
    if cm:
        cm["generated_utc"]=now()
        cm["femm_authority_boundary"]={
          "numerical_design_candidate":"PASS",
          "derived_screen":"PASS",
          "REQ-K01-ACT-FORCE-001_numeric_acceptance":"OPEN",
          "physical_qualification":"OPEN",
          "release":"HOLD",
          "authority":"control/decisions/EDR-039_FEMM_DERIVED_SCREEN_AUTHORITY_BOUNDARY.json"}
        wr(repo/CENTER,cm)

    # Keep the project-wide analysis ledger semantically explicit.
    ar_path=repo/"reports/control/K01_ANALYSIS_REGISTER_CURRENT.json"
    ar=rd(ar_path,{}) or {}
    domains=ar.get("domains") if isinstance(ar,dict) else None
    if isinstance(domains,list):
        for row in domains:
            if isinstance(row,dict) and str(row.get("domain","")).upper()=="FEMM":
                row["status"]="NUMERICAL_DESIGN_CANDIDATE_PASS__RELEASE_REQUIREMENT_OPEN__PHYSICAL_QUALIFICATION_OPEN"
                row["trust_level"]="ENGINEERING"
                row["evidence"]=list(dict.fromkeys((row.get("evidence") or [])+[
                    str(SUM).replace("\\","/"),
                    str(REP).replace("\\","/")]))
                row["decision_supported"]="350-turn magnetic candidate passes the derived numerical screen only; REQ-K01-ACT-FORCE-001 numeric acceptance and physical qualification remain open."
                row["limitations"]=list(dict.fromkeys((row.get("limitations") or [])+[
                    "REQ-K01-ACT-FORCE-001 numeric acceptance remains OPEN",
                    "B001 lot magnetic data open",
                    "P015 production winding/thermal definition open",
                    "physical F(x,I,T) bench correlation open"]))
        ar["generated_utc"]=now()
        wr(ar_path,ar)

    print("PASS: FEMM V3 evidence classified without closing REQ-K01-ACT-FORCE-001.")
    print("DERIVED SCREEN:",derived,"N/A at 1 A")
    print("REQ-K01-ACT-FORCE-001 numeric_acceptance_status: OPEN")
    print("EDR:",repo/EDR)
    print("REPORT:",repo/REP)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
