from __future__ import annotations
import argparse, datetime as dt, json, math, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
TF=Path("reports/engineering/K01_P004_TECHNICAL_FILTER_CURRENT.json")
CALC=Path("reports/engineering/K01_P004_THERMAL_TOLERANCE_SCREEN_CURRENT.json")
EDR40=Path("control/decisions/EDR-040_P004_GUIDE_CLEARANCE_AUTHORITY_BOUNDARY.json")
EDR41=Path("control/decisions/EDR-041_P004_SEAT_AXIAL_TOLERANCE_ARCHITECTURE.json")
REP=Path("reports/engineering/K01_P004_SEAT_AXIAL_TOLERANCE_ARCHITECTURE_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")
ANALYSIS=Path("reports/control/K01_ANALYSIS_REGISTER_CURRENT.json")

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
        if cp.returncode:raise SystemExit("HOLD: state guard failed before seat/axial architecture analysis.")

def close(a,b,tol=1e-9):
    return abs(float(a)-float(b))<=tol

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
    for rel in (PD,READ,CALC,EDR40,NEXT,GATE,FRONT):
        if not (repo/rel).is_file():raise SystemExit("HOLD: missing "+str(rel))
    n=rd(repo/NEXT,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-SEAT-AXIAL-TOL-ARCH":
        raise SystemExit("HOLD: frontier is not at P004 seat/axial tolerance architecture.")

    calc=rd(repo/CALC,{}) or {}
    results=calc.get("results") or {}
    seat=results.get("seat_clearance_nominal_mm") or {}
    axial=results.get("axial_float_nominal_mm") or {}
    for label,row in (("seat",seat),("axial",axial)):
        if any(row.get(k) is None for k in ("Tmin","Tref","Tmax")):
            raise SystemExit("HOLD: thermal screen incomplete for "+label)

    band_lo=0.04;band_hi=0.08
    seat_nom=float(seat["Tref"]); seat_cold=float(seat["Tmin"]); seat_hot=float(seat["Tmax"])
    axial_nom=float(axial["Tref"]); axial_cold=float(axial["Tmin"]); axial_hot=float(axial["Tmax"])

    seat_cold_shift=seat_cold-seat_nom
    seat_hot_shift=seat_hot-seat_nom
    seat_room_lo=band_lo-seat_hot_shift
    seat_room_hi=band_hi-seat_cold_shift
    seat_mid=(seat_room_lo+seat_room_hi)/2.0
    seat_half=(seat_room_hi-seat_room_lo)/2.0
    seat_current_sym=min(seat_nom-seat_room_lo,seat_room_hi-seat_nom)

    axial_cold_shift=axial_cold-axial_nom
    axial_hot_shift=axial_hot-axial_nom
    axial_room_lo=band_lo-axial_hot_shift
    axial_room_hi=band_hi-axial_cold_shift
    axial_mid=(axial_room_lo+axial_room_hi)/2.0
    axial_half=(axial_room_hi-axial_room_lo)/2.0
    axial_current_sym=min(axial_nom-axial_room_lo,axial_room_hi-axial_nom)

    # Verify expected order/sign: PEEK OD growth reduces seat clearance hot; PEEK bushing length growth reduces axial float hot.
    if not (seat_cold>seat_nom>seat_hot and axial_cold>axial_nom>axial_hot):
        raise SystemExit("HOLD: thermal-screen direction changed; architecture analysis assumptions are stale.")

    report={
      "schema":"k01.p004.seat_axial_tolerance_architecture.current.v1",
      "generated_utc":now(),
      "status":"PASS_ARCHITECTURE_SCREEN__PRODUCTION_TOLERANCES_REMAIN_OPEN",
      "authority_classification":{
        "seat_band_0p04_0p08":"CONTROLLED_DESIGN_CHAIN_BAND",
        "axial_band_0p04_0p08":"CONTROLLED_DESIGN_CHAIN_BAND",
        "full_temperature_applicability":"OPEN — not explicitly distinguished from reference-temperature acceptance in the current requirement architecture",
        "production_process_capability":"OPEN"},
      "seat":{
        "nominal_20C_mm":seat_nom,
        "thermal_nominal_mm":{"Tmin":seat_cold,"Tref":seat_nom,"Tmax":seat_hot},
        "if_band_must_hold_at_all_service_temperatures":{
          "required_20C_clearance_window_mm":[seat_room_lo,seat_room_hi],
          "window_midpoint_mm":seat_mid,
          "symmetric_combined_clearance_half_budget_about_current_nominal_mm":seat_current_sym,
          "maximum_symmetric_half_budget_if_centered_mm":seat_half},
        "engineering_finding":"Current 0.060 mm nominal is close to the thermally centered value; no nominal geometry change is justified by this screen alone.",
        "release_state":"TOLERANCE_ALLOCATION_OPEN"},
      "axial":{
        "nominal_20C_mm":axial_nom,
        "thermal_nominal_mm":{"Tmin":axial_cold,"Tref":axial_nom,"Tmax":axial_hot},
        "if_band_must_hold_at_all_service_temperatures":{
          "required_20C_float_window_mm":[axial_room_lo,axial_room_hi],
          "window_midpoint_mm":axial_mid,
          "symmetric_combined_float_half_budget_about_current_nominal_mm":axial_current_sym,
          "maximum_symmetric_half_budget_if_centered_mm":axial_half},
        "engineering_finding":"Current 0.050 mm nominal is strongly biased toward the low-clearance boundary if the full 0.04...0.08 band must hold across -40...+55 C; this leaves only about 0.0061 mm symmetric combined closure budget.",
        "architecture_options":[
          {"id":"A","description":"Keep 0.050 nominal and use a very tight/asymmetric stack.","state":"NOT_RELEASED","risk":"likely poor manufacturing margin for multi-part PEEK/metal stack without demonstrated capability"},
          {"id":"B","description":"Shift nominal axial float toward ~0.0586...0.060 mm, by controlled stack geometry change, then reallocate tolerances.","state":"CANDIDATE_FOR_REVIEW","benefit":"roughly centers the thermal-safe room-temperature window and materially increases combined tolerance budget"},
          {"id":"C","description":"Declare 0.04...0.08 as a 20 C/reference-temperature acceptance band only and verify service non-binding separately.","state":"REQUIREMENT_CHANGE_CANDIDATE","risk":"changes requirement applicability; cannot be assumed"}],
        "release_state":"ARCHITECTURE_DECISION_OPEN"},
      "no_false_release":[
        "No P003 Ø6.60 production tolerance is released.",
        "No P004 Ø6.54 production tolerance is released.",
        "No P004 L8.00 production tolerance is released.",
        "No dimensional value is changed in native CAD.",
        "No DimXpert/PMI/drawing value is authored."],
      "next_independent_work":"Close P004 datum/GPS/surface/edge/inspection architecture while numeric guide and seat/axial production tolerance dependencies remain explicit."}

    wr(repo/REP,report)
    wr(repo/EDR41,{
      "schema":"k01.edr.v1",
      "decision_id":"EDR-041",
      "date":"2026-09-17",
      "subject":"P004 seat and axial tolerance architecture under thermal variation",
      "status":"ACCEPTED_ARCHITECTURE_FINDING__NO_PRODUCTION_TOLERANCE_RELEASE",
      "decision":[
        "Retain P003/P004 seat nominal clearance 0.060 mm as the current architecture nominal; it is near the thermally centered safe-window value and no CAD change is justified by screening alone.",
        "Do not release seat production tolerances until the 0.04...0.08 band temperature applicability and manufacturing/metrology capability are explicitly controlled.",
        "Do not release P004 axial production tolerance around the current 0.050 mm nominal under a full-temperature 0.04...0.08 interpretation; the low-side combined budget is too narrow to accept without capability evidence.",
        "Evaluate an axial nominal shift toward approximately 0.0586...0.060 mm only as a controlled architecture-change candidate if full-temperature applicability is confirmed.",
        "Continue independent P004 datum/GPS/surface/inspection definition; guide numeric limits and seat/axial production tolerances remain OPEN dependencies."],
      "derived_results":{
        "seat_room_window_if_full_temp_band_mm":[seat_room_lo,seat_room_hi],
        "seat_current_nominal_symmetric_combined_half_budget_mm":seat_current_sym,
        "seat_thermal_center_mm":seat_mid,
        "axial_room_window_if_full_temp_band_mm":[axial_room_lo,axial_room_hi],
        "axial_current_nominal_symmetric_combined_half_budget_mm":axial_current_sym,
        "axial_thermal_center_mm":axial_mid},
      "authority_boundary":"These are worst-case architecture calculations from the current thermal screen and design-chain bands; they are not production tolerances.",
      "impact":{"CAD":"NONE","assembly":"NONE","DimXpert":"HOLD","D004":"HOLD","BOM":"NONE","inspection":"architecture may proceed; numeric limits remain open"}})

    pd=rd(repo/PD,{}) or {}
    set_characteristic(pd,"P004-C02",{
      "name":"P003 seat OD",
      "nominal":"Ø6.54",
      "status":"DERIVED",
      "derived":{"nominal_clearance_20C_mm":0.06,
                 "temperature_screen_room_window_if_full_service_band_mm":[seat_room_lo,seat_room_hi],
                 "source":"EDR-038 + EDR-041"},
      "production_tolerance":"OPEN",
      "dependency":"temperature applicability + process capability + P003/P004 joint allocation"})
    set_characteristic(pd,"P004-C03",{
      "name":"OAL / axial float chain",
      "nominal":"8.00",
      "status":"DERIVED",
      "derived":{"nominal_axial_float_20C_mm":axial_nom,
                 "temperature_screen_room_window_if_full_service_band_mm":[axial_room_lo,axial_room_hi],
                 "source":"EDR-038 + EDR-041"},
      "production_tolerance":"OPEN",
      "architecture_state":"CURRENT_0p050_NOMINAL_NOT_CENTERED_FOR_FULL_TEMP_BAND",
      "dependency":"temperature applicability and/or controlled axial nominal architecture decision"})
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__DATUM_GPS_SURFACE_INSPECTION_NEXT"
    pd["product_definition_ready"]=False
    wr(repo/PD,pd)

    ready=rd(repo/READ,{}) or {}
    ready["generated_utc"]=now()
    ready["status"]="PARTIAL__GUIDE_WAITING_DEPENDENCY__SEAT_AXIAL_SCREENED"
    ready["seat_tolerance_state"]="OPEN__ARCHITECTURE_SCREEN_COMPLETE"
    ready["axial_tolerance_state"]="OPEN__ARCHITECTURE_DECISION_REQUIRED"
    ready["next_blocker"]="P004-DATUM-GPS-SURFACE-INSPECTION-BASIS"
    ready["next"]="Define functional datum system, bore↔OD geometric relationship, face orientation, functional surface texture/edge conditions and inspection methods without inventing numeric tolerance values."
    wr(repo/READ,ready)

    if (repo/TF).is_file():
        tf=rd(repo/TF,{}) or {}
        for row in tf.get("checks") or []:
            if row.get("id")=="TF-THERMAL":
                row["state"]="PASS_SCREEN__RELEASE_APPLICABILITY_OPEN"
            if row.get("id")=="TF-TOL":
                row["state"]="PARTIAL__GUIDE_WAITING_DEPENDENCY__SEAT_AXIAL_ARCHITECTURE_SCREENED"
            if row.get("id")=="TF-MFG":
                row["state"]="PARTIAL__ROUTE_DEFINED__CAPABILITY_EVIDENCE_OPEN"
            if row.get("id")=="TF-INSPECT":
                row["state"]="PARTIAL__METHOD_ARCHITECTURE_NEXT__NUMERIC_LIMITS_OPEN"
        tf["generated_utc"]=now();wr(repo/TF,tf)

    if (repo/ANALYSIS).is_file():
        ar=rd(repo/ANALYSIS,{}) or {}
        for row in ar.get("domains") or []:
            if isinstance(row,dict) and row.get("domain")=="Tolerance/Variation":
                row["status"]="P004_GUIDE_WAITING_DEPENDENCY__SEAT_AXIAL_ARCHITECTURE_SCREENED"
                row["decision_supported"]="P004 seat nominal retained; axial 0.050 nominal flagged as poorly centered if 0.04...0.08 must hold over -40...+55 C. No production tolerance released."
                row["limitations"]=list(dict.fromkeys((row.get("limitations") or [])+[
                  "P001/P004 numeric guide-clearance min/max not released",
                  "seat/axial design-band temperature applicability not explicitly released",
                  "production capability data not yet available"]))
        ar["generated_utc"]=now();wr(repo/ANALYSIS,ar)

    f=rd(repo/FRONT,{}) or {};g=rd(repo/GATE,{}) or {};n=rd(repo/NEXT,{}) or {}
    blocker="P004-DATUM-GPS-SURFACE-INSPECTION-BASIS"
    nid="K01-NA-P004-DATUM-GPS-SURFACE-INSPECTION"
    exp="PASS_P004_DATUM_GPS_SURFACE_INSPECTION_ARCHITECTURE__NUMERIC_OPEN_ITEMS_PRESERVED"
    text="Define P004 functional datum system, bore-to-OD geometric relationship, face orientation, functional surface classes/texture decision basis, edge treatment and inspection methods. Preserve all OPEN numeric guide/seat/axial limits; no CAD/DimXpert/drawing mutation."
    auth=[str(REP).replace("\\","/"),str(EDR41).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/")]

    n.update({"schema":"k01.next_actions.current.v33_program_front",
              "active_blocker":blocker,"current_blocker":blocker+":OPEN",
              "next_1":text,"next_action_id":nid,"expected_closure":exp,
              "execution_mode":"ENGINEERING_DEFINITION__NO_NATIVE_MUTATION",
              "authority_set":auth,
              "release_blockers":[{"id":blocker,"state":"OPEN","role":"P004 datum/GPS/surface/edge/inspection architecture","class":"L5_EXECUTABLE_BLOCKER"}]})
    wr(repo/NEXT,n)
    g.update({"schema":"k01.active_step_gate.v13_program_front","generated_utc":now(),
              "intent":nid,"intent_text":text,"active_blocker":blocker,
              "expected_closure":exp,"mutation_authorized":False,
              "mutation_scope":"ENGINEERING_DEFINITION_ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING; NO BOM AUTHORITY MUTATION",
              "result_on_pass":exp,"required_files":auth})
    wr(repo/GATE,g)
    f.update({"generated_utc":now(),
              "active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},
              "next_allowed_action":{"id":nid,"text":text,"authority_set":auth,
                                     "expected_closure":exp,
                                     "execution_mode":"ENGINEERING_DEFINITION__NO_NATIVE_MUTATION"}})
    timing=f.setdefault("timing",{})
    timing["ACTIVE_NOW"]=[blocker]
    deps=timing.setdefault("WAITING_DEPENDENCY",[])
    for dep in [
      "P004 guide-clearance numeric limits — system radial/angular/optical repeatability allocation",
      "P004 seat production tolerance — temperature applicability + process capability",
      "P004 axial production tolerance/nominal — temperature applicability / architecture decision"]:
        if dep not in deps:deps.append(dep)
    wr(repo/FRONT,f)

    cm=rd(repo/CENTER,{}) or {}
    if cm:
        cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,
                   "p004_tolerance_architecture":{
                     "guide":"WAITING_DEPENDENCY",
                     "seat":"SCREENED__PRODUCTION_TOLERANCE_OPEN",
                     "axial":"SCREENED__ARCHITECTURE_DECISION_OPEN",
                     "authority":"EDR-041"}})
        wr(repo/CENTER,cm)

    subprocess.run([sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)

    print("PASS: EDR-041 P004 seat/axial tolerance architecture screened.")
    print("NO PRODUCTION TOLERANCE RELEASED.")
    print("SEAT full-temp room window:",seat_room_lo,"...",seat_room_hi,"mm")
    print("AXIAL full-temp room window:",axial_room_lo,"...",axial_room_hi,"mm")
    print("NEXT: datum/GPS/surface/edge/inspection architecture.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
