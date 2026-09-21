from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
REQ=Path("control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
TF=Path("reports/engineering/K01_P004_TECHNICAL_FILTER_CURRENT.json")
CALC=Path("reports/engineering/K01_P004_THERMAL_TOLERANCE_SCREEN_CURRENT.json")
EDR=Path("control/decisions/EDR-040_P004_GUIDE_CLEARANCE_AUTHORITY_BOUNDARY.json")
REP=Path("reports/engineering/K01_P004_GUIDE_CLEARANCE_AUTHORITY_BOUNDARY_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def run_guard(repo):
    for t in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        cp=subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo,text=True)
        if cp.returncode:
            raise SystemExit("HOLD: state guard failed before P004 guide authority decision.")

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

def text_hits(x,needles,path="$",out=None):
    if out is None:out=[]
    if isinstance(x,dict):
        for k,v in x.items():
            text_hits(v,needles,path+"."+str(k),out)
    elif isinstance(x,list):
        for i,v in enumerate(x):text_hits(v,needles,f"{path}[{i}]",out)
    elif isinstance(x,str):
        low=x.lower()
        if any(n.lower() in low for n in needles):
            out.append({"path":path,"text":x})
    return out

def set_characteristic(pd,cid,updates):
    chars=pd.get("characteristics")
    if not isinstance(chars,list):
        chars=[];pd["characteristics"]=chars
    for c in chars:
        if isinstance(c,dict) and c.get("id")==cid:
            c.update(updates);return
    row={"id":cid};row.update(updates);chars.append(row)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args()
    repo=Path(a.repo_root);run_guard(repo)
    for rel in (PD,READ,CALC,NEXT,GATE,FRONT):
        if not (repo/rel).is_file():raise SystemExit("HOLD: missing "+str(rel))

    n=rd(repo/NEXT,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-GUIDE-CLEARANCE-REQ-TOL":
        raise SystemExit("HOLD: Completion Frontier is not at P004 guide-clearance authority closure.")

    pd=rd(repo/PD,{}) or {}
    ready=rd(repo/READ,{}) or {}
    calc=rd(repo/CALC,{}) or {}
    reqall=rd(repo/REQ,{}) or {} if (repo/REQ).is_file() else {}

    req_guide=find_req(reqall,"REQ-GUIDE-001")
    req_opt=find_req(reqall,"REQ-OPT-004")
    requirement_hits=text_hits(reqall,[
        "slip-fit","full-length interference","working rod is","angular repeatability",
        "reference-signal repeatability","guide clearance","sliding clearance"])

    thermal=((calc.get("results") or {}).get("guide_clearance_nominal_mm") or {})
    tmin=thermal.get("Tmin");tref=thermal.get("Tref");tmax=thermal.get("Tmax")
    if tref is None:
        raise SystemExit("HOLD: current P004 thermal screen does not expose guide nominal clearance.")

    guide_req_text=(req_guide or {}).get("text") or (req_guide or {}).get("requirement") or (req_guide or {}).get("description")
    opt_req_text=(req_opt or {}).get("text") or (req_opt or {}).get("requirement") or (req_opt or {}).get("description")

    report={
      "schema":"k01.p004.guide_clearance_authority_boundary.current.v1",
      "generated_utc":now(),
      "status":"PASS_AUTHORITY_BOUNDARY__NUMERIC_GUIDE_LIMITS_OPEN",
      "part_id":"K01-P-004",
      "interface":"P004 bore Ø5.055 ↔ P001 rod Ø5.000",
      "controlled_facts":{
        "P001_nominal_diameter_mm":5.000,
        "P004_nominal_bore_mm":5.055,
        "nominal_diametral_clearance_20C_mm":0.055,
        "thermal_screen_nominal_mm":{"Tmin":tmin,"Tref":tref,"Tmax":tmax},
        "functional_requirement":"sliding/slip guide; full-length interference prohibited"},
      "requirement_authority":{
        "REQ-GUIDE-001_found":req_guide is not None,
        "REQ-GUIDE-001_snapshot":req_guide,
        "REQ-OPT-004_found":req_opt is not None,
        "REQ-OPT-004_snapshot":req_opt,
        "relevant_current_requirement_text_hits":requirement_hits},
      "authority_finding":{
        "numeric_Cguide_min_released":False,
        "numeric_Cguide_max_released":False,
        "lower_bound_logic":"Must remain positive after size/form/thermal/process effects with adequate anti-binding margin.",
        "upper_bound_logic":"Must be constrained by allowable rod radial/angular play and ultimately system optical/reference repeatability.",
        "current_gap":"No controlled numeric system allocation was found that converts rod/target repeatability into a released maximum P001↔P004 diametral clearance."},
      "non_authoritative_references_policy":[
        "Handbook/example sliding clearances may support plausibility only; they do not define K01 product acceptance.",
        "Material-manufacturer sliding/bearing guidance supports material/process suitability only; it does not define K01 guide-clearance limits."],
      "decision_effect":{
        "P004_C01_size_tolerance":"OPEN",
        "P001_rod_size_tolerance_for_guide_function":"OPEN",
        "nominal_0p055_clearance":"DERIVED geometry, not release acceptance",
        "thermal_values":"SCREENING evidence, not release acceptance",
        "Product_Definition_READY":False,
        "D004_DimXpert":"BLOCKED_UPSTREAM"},
      "dependency_to_close":[
        "released numeric allowable radial/angular guide play or equivalent guide-clearance envelope",
        "trace from that mechanical play to target/reference-signal repeatability acceptance",
        "then worst-case allocation between P001 size/form and P004 bore size/form"]}

    wr(repo/REP,report)
    wr(repo/EDR,{
      "schema":"k01.edr.v1",
      "decision_id":"EDR-040",
      "date":"2026-09-17",
      "subject":"P004/P001 guide-clearance numeric authority boundary",
      "status":"ACCEPTED_AUTHORITY_BOUNDARY__NUMERIC_LIMITS_OPEN",
      "decision":"Do not release a numeric P001↔P004 guide-clearance min/max or production bore/rod tolerance from nominal geometry, handbook examples, or material guidance. Keep the guide tolerance chain OPEN until system radial/angular/optical repeatability is numerically allocated.",
      "accepted":[
        "P004 nominal bore Ø5.055 and P001 nominal rod Ø5.000 give 0.055 mm nominal diametral clearance at 20 C.",
        "Current thermal screen values are valid screening evidence only.",
        "Slip-fit/no-full-length-interference remains the controlled qualitative function."],
      "not_accepted":[
        "No numeric Cguide_min is released.",
        "No numeric Cguide_max is released.",
        "No P004 Ø5.055 production tolerance is released.",
        "No P001 Ø5 production tolerance is released by this decision.",
        "External example clearances are not K01 acceptance authority."],
      "dependency":"System-level numeric radial/angular/target repeatability allocation.",
      "downstream_impact":{"CAD":"NONE","DimXpert":"HOLD","D004":"HOLD","P001_D001":"guide-size release remains coupled/open","BOM":"NONE","assembly":"NONE"}})

    set_characteristic(pd,"P004-C01",{
      "name":"Guide bore",
      "nominal":"Ø5.055",
      "status":"OPEN",
      "authority_state":"NUMERIC_GUIDE_LIMITS_NOT_RELEASED",
      "derived_nominal_clearance_mm":0.055,
      "thermal_screen_nominal_mm":{"Tmin":tmin,"Tref":tref,"Tmax":tmax},
      "dependency":"SYSTEM-LEVEL-GUIDE-PLAY-ACCEPTANCE",
      "source":"EDR-040"})
    blockers=pd.get("open_release_blockers") or []
    blockers=[x for x in blockers if "guide-clearance" not in str(x).lower()]
    blockers.insert(0,"P001/P004 guide-clearance numeric min/max and size/form tolerance allocation — WAITING_DEPENDENCY on system radial/angular/optical repeatability allocation")
    pd["open_release_blockers"]=blockers
    pd["product_definition_ready"]=False
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__GUIDE_NUMERIC_LIMITS_WAITING_DEPENDENCY"
    wr(repo/PD,pd)

    ready["generated_utc"]=now()
    ready["status"]="PARTIAL__GUIDE_NUMERIC_LIMITS_WAITING_DEPENDENCY"
    ready["product_definition_ready"]=False
    ready["guide_clearance_state"]="WAITING_DEPENDENCY__NUMERIC_SYSTEM_ALLOCATION"
    ready["waiting_dependency"]=[
      "P001/P004 guide clearance min/max from radial/angular/optical repeatability allocation"]
    ready["next_blocker"]="P004-SEAT-AXIAL-TOLERANCE-ARCHITECTURE"
    ready["next"]="Resolve temperature applicability and worst-case manufacturing architecture for P003/P004 seat clearance and P004 axial float without inventing production tolerances."
    wr(repo/READ,ready)

    if (repo/TF).is_file():
        tf=rd(repo/TF,{}) or {}
        for row in tf.get("checks") or []:
            if row.get("id")=="TF-REQ":
                row["state"]="PARTIAL__GUIDE_NUMERIC_LIMITS_WAITING_SYSTEM_REQUIREMENT"
            if row.get("id")=="TF-TOL":
                row["state"]="PARTIAL__GUIDE_OPEN__SEAT_AXIAL_NEXT"
        tf["generated_utc"]=now();wr(repo/TF,tf)

    f=rd(repo/FRONT,{}) or {};g=rd(repo/GATE,{}) or {};n=rd(repo/NEXT,{}) or {}
    blocker="P004-SEAT-AXIAL-TOLERANCE-ARCHITECTURE"
    nid="K01-NA-P004-SEAT-AXIAL-TOL-ARCH"
    exp="PASS_P004_SEAT_AXIAL_ARCHITECTURE_SCREENED__NO_FALSE_TOLERANCE_RELEASE"
    text="Resolve authority/applicability of the 0.04...0.08 P004 seat and axial bands across temperature; calculate worst-case room-temperature tolerance windows and architecture options. Do not release arbitrary production tolerances or mutate CAD."
    auth=[str(REP).replace("\\","/"),str(EDR).replace("\\","/"),str(PD).replace("\\","/"),str(CALC).replace("\\","/")]

    n.update({"schema":"k01.next_actions.current.v32_program_front",
              "active_blocker":blocker,"current_blocker":blocker+":OPEN",
              "next_1":text,"next_action_id":nid,"expected_closure":exp,
              "execution_mode":"ENGINEERING_ANALYSIS_DECISION__NO_NATIVE_MUTATION",
              "authority_set":auth,
              "waiting_dependency":[
                {"id":"P004-GUIDE-CLEARANCE-NUMERIC","state":"WAITING_DEPENDENCY","dependency":"system radial/angular/optical repeatability allocation"}],
              "release_blockers":[{"id":blocker,"state":"OPEN","role":"Seat/axial temperature-aware tolerance architecture","class":"L5_EXECUTABLE_BLOCKER"}]})
    wr(repo/NEXT,n)

    g.update({"schema":"k01.active_step_gate.v12_program_front","generated_utc":now(),
              "intent":nid,"intent_text":text,"active_blocker":blocker,
              "expected_closure":exp,"mutation_authorized":False,
              "mutation_scope":"ENGINEERING_ANALYSIS_DECISION_ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING; NO BOM AUTHORITY MUTATION",
              "result_on_pass":exp,"required_files":auth})
    wr(repo/GATE,g)

    f.update({"generated_utc":now(),
              "active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},
              "next_allowed_action":{"id":nid,"text":text,"authority_set":auth,
                                     "expected_closure":exp,
                                     "execution_mode":"ENGINEERING_ANALYSIS_DECISION__NO_NATIVE_MUTATION"}})
    timing=f.setdefault("timing",{})
    timing["ACTIVE_NOW"]=[blocker]
    wait=timing.setdefault("WAITING_DEPENDENCY",[])
    dep="P004 guide-clearance numeric limits — system radial/angular/optical repeatability allocation"
    if dep not in wait:wait.insert(0,dep)
    wr(repo/FRONT,f)

    cm=rd(repo/CENTER,{}) or {}
    if cm:
        cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,
                   "p004_guide_clearance":{"state":"WAITING_DEPENDENCY","nominal_mm":0.055,
                                          "numeric_minmax":"OPEN","authority":"EDR-040"}})
        wr(repo/CENTER,cm)

    subprocess.run([sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)

    print("PASS: EDR-040 authority boundary accepted.")
    print("GUIDE NUMERIC MIN/MAX: OPEN / WAITING_DEPENDENCY")
    print("NEXT: P004 seat + axial tolerance architecture.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
