from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math, shutil
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
EDR=Path("control/decisions/EDR-038_P004_MATERIAL_THERMAL_PROCESS_BASIS.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
INSP=Path("reports/inspection/K01-P-004_INSPECTION_PLAN_CURRENT.json")
CALC=Path("reports/engineering/K01_P004_THERMAL_TOLERANCE_SCREEN_CURRENT.json")
BOM=Path("reports/control/K01_BOM_RELEASE_STATUS_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
def rd(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def clr(T,seat,od,as_=16e-6,ap=30e-6):
 d=T-20.0;return seat*(1+as_*d)-od*(1+ap*d)
def guide(T,bore,rod,as_=16e-6,ap=30e-6):
 d=T-20.0;return bore*(1+ap*d)-rod*(1+as_*d)
def axial(T,span_steel,p004,as_=16e-6,ap=30e-6):
 d=T-20.0;return span_steel*(1+as_*d)-p004*(1+ap*d)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root)
 n=rd(repo/NEXT);g=rd(repo/GATE);f=rd(repo/FRONT)
 if n.get("next_action_id")!="K01-NA-P004-PD-ENGINEERING-CLOSURE":raise SystemExit("HOLD: main frontier is not P004 Product Definition closure.")
 Tmin=-40.0;Tref=20.0;Tmax=55.0
 vals={
  "seat_clearance_nominal_mm":{"Tmin":clr(Tmin,6.60,6.54),"Tref":clr(Tref,6.60,6.54),"Tmax":clr(Tmax,6.60,6.54)},
  "guide_clearance_nominal_mm":{"Tmin":guide(Tmin,5.055,5.000),"Tref":guide(Tref,5.055,5.000),"Tmax":guide(Tmax,5.055,5.000)},
  "axial_float_nominal_mm":{"Tmin":axial(Tmin,8.05,8.00),"Tref":axial(Tref,8.05,8.00),"Tmax":axial(Tmax,8.05,8.00)}
 }
 # Required 20C manufacturing band if the 0.04..0.08 seat band is required across Tmin..Tmax.
 cold_shift=vals["seat_clearance_nominal_mm"]["Tmin"]-0.06
 hot_shift=vals["seat_clearance_nominal_mm"]["Tmax"]-0.06
 room_min=0.04-hot_shift
 room_max=0.08-cold_shift
 axial_cold_shift=vals["axial_float_nominal_mm"]["Tmin"]-0.05
 axial_hot_shift=vals["axial_float_nominal_mm"]["Tmax"]-0.05
 axial_room_min=0.04-axial_hot_shift
 axial_room_max=0.08-axial_cold_shift

 calc={"schema":"k01.p004.thermal_tolerance_screen.current.v1","generated_utc":now(),"status":"PASS_SCREEN__TOLERANCE_RELEASE_OPEN",
       "temperature_basis":{"Tmin_C":Tmin,"Tref_C":Tref,"Tmax_C":Tmax,
          "basis":["MARV 2EX documented system operation down to -40 C and up to 50 C","K01 local J2/P007 conservative design maximum 55 C"],
          "applicability":"Conservative P004 design screen; if qualified local P004 envelope becomes narrower, recalculate."},
       "material_inputs":{"TECAPEEK_PVX_CLTE_1_per_K":30e-6,"316L_CLTE_1_per_K":16e-6,
          "sources":["Ensinger TECAPEEK PVX black technical data: CLTE 3e-5 1/K in 23-100 C range","Outokumpu Supra 316L/1.4404: CLTE 16e-6 1/K, 20-100 C"]},
       "results":vals,
       "derived_if_functional_band_applies_over_full_temperature":{
          "seat_clearance_required_at_service_mm":[0.04,0.08],
          "required_20C_manufacturing_clearance_window_mm":[room_min,room_max],
          "available_window_width_mm":room_max-room_min,
          "axial_float_required_at_service_mm":[0.04,0.08],
          "required_20C_axial_window_mm":[axial_room_min,axial_room_max],
          "axial_window_width_mm":axial_room_max-axial_room_min},
       "interpretation":[
          "Nominal P003/P004 seat clearance stays positive from -40 to +55 C.",
          "Nominal P001/P004 guide clearance stays positive from -40 to +55 C.",
          "Nominal P004 axial float stays inside 0.04...0.08 mm across the conservative temperature screen.",
          "The original 20 C seat-clearance manufacturing band 0.04...0.08 cannot by itself guarantee 0.04...0.08 at both temperature extremes because PEEK and 316L expand differently.",
          "Therefore final production tolerances must be allocated to a narrower 20 C acceptance window, or the service-band requirement must be explicitly scoped to reference temperature.",
          "Guide clearance still lacks a controlled functional min/max requirement; no bore/rod production tolerance is released."
       ]}
 wr(repo/CALC,calc)

 edr={"schema":"k01.edr.v1","decision_id":"EDR-038","subject":"P004 material, thermal and manufacturing/inspection basis","date":"2026-09-17",
      "status":"ACCEPTED_ENGINEERING_BASIS__PRODUCT_DEFINITION_PARTIAL",
      "problem":"P004 Product Definition cannot allocate production tolerances or proceed to PMI/drawing until production material, thermal behavior and process/metrology basis are controlled.",
      "requirements":["REQ-GUIDE-001 slip-fit; no full-length interference","REQ-GUIDE-002 removable metal retention; no adhesive/no axial preload",
                      "P004 seat functional clearance 0.04...0.08 mm","P004 axial float target 0.04...0.08 mm"],
      "accepted":[
        "Design material: Ensinger TECAPEEK PVX black bearing-grade PEEK modification.",
        "Production route basis: qualified TECAPEEK PVX stock -> CNC turning -> precision bore finishing -> controlled deburr/clean -> dimensional stabilization -> inspection.",
        "Reference dimensional specification/verification temperature: 20 C per ISO 1:2022; actual part temperature shall be recorded for FAI/critical acceptance.",
        "Conservative thermal screen for P004: -40 C to +55 C until a narrower local qualified envelope is controlled.",
        "Use TECAPEEK PVX CLTE 30e-6 1/K and EN 1.4404/316L CLTE 16e-6 1/K for this screening model.",
        "Supplier/lot CoC, stock form/effectivity and process capability remain release evidence; design material selection does not equal procurement qualification."
      ],
      "rejected_or_not_accepted":[
        "Do not release ±0.01 mm on P003/P004 merely because it mathematically fits the room-temperature stack.",
        "Do not assign P004 guide-bore tolerance before guide clearance min/max requirement is controlled.",
        "Do not assign generic Ra values before function/process/inspection decision.",
        "Do not author DimXpert/PMI or D004 yet."
      ],
      "evidence":["reports/engineering/K01_P004_THERMAL_TOLERANCE_SCREEN_CURRENT.json","K01 project V22 dimension architecture",
                  "Ensinger TECAPEEK PVX black manufacturer technical data","Outokumpu 316L/1.4404 physical-property data","ISO 1:2022"],
      "impact":{"CAD":"NONE","DimXpert":"NONE","Drawing":"WAITING_UPSTREAM","BOM":"P004 material identity narrowed; supplier lot/process/effectivity remains HOLD","Inspection":"basis created; final limits open"},
      "stale_triggers":["P004 local temperature envelope changes","material changed from TECAPEEK PVX black","P003 material changes from 316L","functional clearance band changes","production process changes"]}
 wr(repo/EDR,edr)

 chars=[
  {"id":"P004-C01","name":"Guide bore","nominal":"Ø5.055","status":"OPEN","blocker":"functional guide clearance min/max + tolerance allocation"},
  {"id":"P004-C02","name":"P003 seat OD","nominal":"Ø6.54","status":"DERIVED/CANDIDATE","blocker":"temperature-aware tolerance allocation + process capability"},
  {"id":"P004-C03","name":"OAL","nominal":"8.00","status":"DERIVED/CANDIDATE","blocker":"temperature-aware axial stack tolerance allocation"},
  {"id":"P004-C04","name":"OD-to-bore relation","status":"OPEN","blocker":"GPS value after guide clearance allocation"},
  {"id":"P004-C05","name":"Face orientation","status":"OPEN","blocker":"functional datum/GPS decision"},
  {"id":"P004-C06","name":"Guide surface texture","status":"OPEN","blocker":"process/wear/inspection decision"},
  {"id":"P004-C07","name":"OD slip-fit surface texture","status":"OPEN","blocker":"process/assembly decision"},
  {"id":"P004-C08","name":"Material","value":"TECAPEEK PVX black (Ensinger)","status":"RELEASED_DESIGN_MATERIAL__PROCUREMENT_QUALIFICATION_OPEN","source":"EDR-038"},
  {"id":"P004-C09","name":"Manufacturing route","value":"qualified stock -> CNC turning -> precision bore finishing -> deburr/clean -> stabilization -> inspection","status":"RELEASED_ENGINEERING_BASIS","source":"EDR-038"},
  {"id":"P004-C10","name":"Measurement reference temperature","value":"20 C; record actual part temperature for critical acceptance","status":"RELEASED_ENGINEERING_BASIS","source":"EDR-038 / ISO 1:2022"},
  {"id":"P004-C11","name":"Edge/deburr","status":"OPEN","blocker":"functional edge decision before drawing"}
 ]
 pd={"schema":"k01.product_definition.current.v1","generated_utc":now(),"part_id":"K01-P-004","title":"Front Guide Bushing",
     "status":"PARTIAL_PRODUCT_DEFINITION__ENGINEERING_BASIS_CLOSED","product_definition_ready":False,
     "functions":["radial guidance P001","sliding clearance","slip fit in P003","axial retention by P014","no thermal binding","serviceable/replaceable"],
     "material":{"designation":"TECAPEEK PVX black","manufacturer":"Ensinger","state":"RELEASED_DESIGN_MATERIAL__PROCUREMENT_QUALIFICATION_OPEN"},
     "temperature_screen_C":[Tmin,Tmax],"characteristics":chars,
     "open_release_blockers":["P001/P004 guide-clearance functional min/max","temperature-aware P003/P004 tolerance allocation","P004 axial worst-case tolerance allocation",
                              "functional datum/GPS limits","surface texture decisions","edge treatment","production process capability/FAI","final inspection acceptance limits"],
     "drawing_gate":"HOLD_UPSTREAM_PRODUCT_DEFINITION","dimxpert_gate":"HOLD_UPSTREAM_PRODUCT_DEFINITION"}
 wr(repo/PD,pd)

 insp={"schema":"k01.p004.inspection_plan.current.v1","generated_utc":now(),"status":"PARTIAL_LIMITS_OPEN","part_id":"K01-P-004",
       "measurement_reference":{"temperature_C":20,"standard":"ISO 1:2022","requirement":"record actual part temperature for critical acceptance; compensate/hold if outside controlled lab condition"},
       "characteristics":[
        {"id":"P004-C01","method":"calibrated bore gauge / air gauge / qualified plug-gauge strategy","acceptance":"OPEN"},
        {"id":"P004-C02","method":"calibrated micrometer / comparator","acceptance":"OPEN"},
        {"id":"P004-C03","method":"micrometer / comparator","acceptance":"OPEN"},
        {"id":"P004-C04","method":"CMM or controlled spindle/indicator setup","acceptance":"OPEN"},
        {"id":"P004-C05","method":"CMM or comparator setup","acceptance":"OPEN"},
        {"id":"P004-C06/P004-C07","method":"profilometer when texture values are released","acceptance":"OPEN"}
       ],
       "FAI":"REQUIRED_FOR_FIRST_PRODUCTION_PROCESS__FINAL_SCOPE_OPEN"}
 wr(repo/INSP,insp)

 readiness={"schema":"k01.p004.product_definition_readiness.current.v1","generated_utc":now(),
            "status":"PARTIAL__MATERIAL_THERMAL_PROCESS_BASIS_CLOSED","product_definition_ready":False,
            "closed_by_EDR_038":["design material identity","conservative thermal model","manufacturing route basis","measurement reference temperature basis"],
            "open_blocker_count":8,"next_blocker":"P004-GUIDE-CLEARANCE-REQUIREMENT-AND-TOLERANCE-ALLOCATION",
            "next":"Control P001↔P004 guide-clearance min/max requirement, then allocate room-temperature production tolerances jointly with P003/P004 axial stack."}
 wr(repo/READ,readiness)

 if (repo/BOM).exists():
  b=rd(repo/BOM);b["generated_utc"]=now();b["P004_update"]={"material_design_identity":"TECAPEEK PVX black (Ensinger)","state":"DESIGN_MATERIAL_CLOSED__PROCUREMENT_PROCESS_QUALIFICATION_OPEN","source":"EDR-038"}
  wr(repo/BOM,b)

 # Advance frontier to precise next blocker, still no native mutation.
 blocker="P004-GUIDE-CLEARANCE-REQ-TOL-ALLOCATION";nid="K01-NA-P004-GUIDE-CLEARANCE-REQ-TOL";exp="PASS_P004_GUIDE_REQUIREMENT_CONTROLLED__TOLERANCE_ALLOCATION_READY"
 text="Control P001↔P004 guide-clearance functional min/max across -40...+55 C design screen, then allocate P001/P004 bore/rod tolerance budget. No CAD/DimXpert/drawing mutation."
 n.update({"schema":"k01.next_actions.current.v31_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,
           "expected_closure":exp,"execution_mode":"ENGINEERING_DECISION__NO_NATIVE_MUTATION",
           "authority_set":[str(PD).replace("\\","/"),str(READ).replace("\\","/"),str(CALC).replace("\\","/"),str(EDR).replace("\\","/")],
           "release_blockers":[{"id":blocker,"state":"OPEN","role":"Functional guide clearance requirement + tolerance allocation","class":"L5_EXECUTABLE_BLOCKER"}]})
 wr(repo/NEXT,n)
 g.update({"schema":"k01.active_step_gate.v11_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,
           "expected_closure":exp,"mutation_authorized":False,"mutation_scope":"ENGINEERING_DECISION_ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING; NO BOM AUTHORITY MUTATION",
           "result_on_pass":exp,"required_files":n["authority_set"]})
 wr(repo/GATE,g)
 f.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},
           "next_allowed_action":{"id":nid,"text":text,"authority_set":n["authority_set"],"expected_closure":exp,"execution_mode":"ENGINEERING_DECISION__NO_NATIVE_MUTATION"}})
 f.setdefault("timing",{})["ACTIVE_NOW"]=[blocker]
 wr(repo/FRONT,f)
 print("PASS: EDR-038 P004 material/thermal/process engineering basis accepted.")
 print("P004 PRODUCT DEFINITION: PARTIAL; CAD/DimXpert/D004 remain HOLD.")
 print("THERMAL SCREEN:",repo/CALC)
 print("NEXT:",text)
 return 0
if __name__=="__main__":raise SystemExit(main())
