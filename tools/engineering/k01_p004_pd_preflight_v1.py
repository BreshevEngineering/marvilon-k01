from __future__ import annotations
import argparse, datetime as dt, hashlib, json
from pathlib import Path

REPO_DEFAULT=Path(r"D:\BreshevEngineering\marvilon-k01")
CAD_DEFAULT=Path(r"D:\Marvilon\K01")

OUT_JSON=Path("reports/engineering/K01_P004_PRODUCT_DEFINITION_PREFLIGHT_CURRENT.json")
OUT_MD=Path("reports/engineering/K01_P004_PRODUCT_DEFINITION_PREFLIGHT_CURRENT.md")
WORKPACK=Path("control/product_definition/K01_P004_PRODUCT_DEFINITION_WORKPACK_CURRENT.json")
FILTER=Path("reports/engineering/K01_P004_TECHNICAL_FILTER_CURRENT.json")
CALC=Path("reports/engineering/K01_P004_CALCULATION_REGISTER_CURRENT.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
EDR47=Path("control/decisions/EDR-047_P004_AXIAL_RECENTER.json")
DISP=Path("control/decisions/K01_DECISION_AUTHORITY_DISPOSITION_EDR047.json")

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(REPO_DEFAULT));ap.add_argument("--cad-root",default=str(CAD_DEFAULT));a=ap.parse_args()
 repo=Path(a.repo_root);cad=Path(a.cad_root)
 part=cad/r"cad\parts\K01-P-004_Front_Guide_Bushing.SLDPRT"
 # Canonical P004 OAL is derived from the accepted EDR-047 authority and
 # must match both Product Definition and the hash-locked native file.
 def rdj(p):
  return json.loads(p.read_text(encoding="utf-8-sig"))
 for req in (repo/PD,repo/EDR47,repo/DISP):
  if not req.is_file(): raise SystemExit("HOLD_P004_PREFLIGHT_MISSING_AUTHORITY: "+str(req))
 edr47=rdj(repo/EDR47); disp=rdj(repo/DISP); pd_current=rdj(repo/PD)
 if disp.get("canonical_active_path") != str(EDR47).replace("\\","/"):
  raise SystemExit("HOLD_P004_PREFLIGHT_BAD_EDR047_DISPOSITION")
 if sha(repo/EDR47) != disp.get("canonical_sha256"):
  raise SystemExit("HOLD_P004_PREFLIGHT_EDR047_HASH_MISMATCH")
 if not part.is_file() or sha(part) != (disp.get("native_cad_evidence") or {}).get("sha256"):
  raise SystemExit("HOLD_P004_PREFLIGHT_NATIVE_SHA_STALE__RUN_TYPED_NATIVE_TRUTH")
 oal=float((edr47.get("promotion_evidence") or {}).get("oal_after_mm"))
 c03=next((c for c in pd_current.get("characteristics",[]) if c.get("id")=="P004-C03"),None)
 if not c03 or abs(float(c03.get("nominal"))-oal)>1e-9:
  raise SystemExit("HOLD_P004_PREFLIGHT_PRODUCT_DEFINITION_OAL_MISMATCH")
 axial_float=round(11.05-(3.00+oal),6)
 if abs(axial_float-0.06)>1e-9:
  raise SystemExit("HOLD_P004_PREFLIGHT_AXIAL_FLOAT_UNEXPECTED")
 oal_s=f"{oal:.2f}"
 p003=cad/r"cad\parts\K01-P-003_Cartridge_Body.SLDPRT"
 p001=cad/r"cad\parts\K01-P-001_Calibration_Rod.SLDPRT"
 p014=cad/r"cad\parts\K01-P-014_Front_Guide_Retaining_Ring.SLDPRT"

 functions=[
  {"id":"F01","text":"Radially guide P001 calibration rod."},
  {"id":"F02","text":"Maintain controlled sliding clearance without binding."},
  {"id":"F03","text":"Locate as a slip-fit bushing in P003 seat."},
  {"id":"F04","text":"Be axially retained by P014 / housing stack without adhesive or preload."},
  {"id":"F05","text":"Avoid binding across operating temperature/environment."},
  {"id":"F06","text":"Remain manufacturable, inspectable and replaceable."},
 ]
 interfaces=[
  {"id":"IF-01","P004":"bore Ø5.055 nominal","mate":"P001 rod Ø5 nominal","function":"sliding guide","status":"REQUIREMENT_BAND_OPEN"},
  {"id":"IF-02","P004":"OD Ø6.54 nominal","mate":"P003 seat Ø6.60 nominal","function":"radial locating/slip fit","status":"FUNCTIONAL_BAND_DEFINED"},
  {"id":"IF-03","P004":f"axial faces / L{oal_s} nominal","mate":"P003 stack + P014","function":"axial retention/float","status":"NOMINAL_CHAIN_EVIDENCE_EXISTS__TOLERANCE_OPEN"},
  {"id":"IF-04","P004":"TECAPEEK PVX surfaces","mate":"temperature/environment","function":"thermal stability / tribology / clean service","status":"PRODUCTION_MATERIAL_PROCESS_OPEN"},
 ]

 calculations=[
  {
   "id":"P004-CALC-001","question":"P003 seat-to-P004 OD nominal diametral clearance",
   "equation":"6.60 - 6.54","result_mm":0.06,"requirement_mm":[0.04,0.08],
   "interpretation":"Nominal satisfies the functional band. Worst-case tolerance budget remains to be allocated.",
   "derived_budget":"For symmetric half-widths t_seat+t_P004 <= 0.02 mm; equivalently total tolerance fields T_seat+T_P004 <= 0.04 mm.",
   "status":"DERIVED__TOLERANCE_ALLOCATION_OPEN"
  },
  {
   "id":"P004-CALC-002","question":"P004 bore-to-P001 nominal diametral guide clearance",
   "equation":"5.055 - 5.000","result_mm":0.055,
   "requirement_mm":None,
   "interpretation":"Nominal clearance is known; min/max functional requirement is not yet controlled, therefore no production tolerance may be released.",
   "status":"DERIVED_NOMINAL_ONLY__REQUIREMENT_OPEN"
  },
  {
   "id":"P004-CALC-003","question":"P004 nominal axial float from current dimension architecture",
   "formula_id":"AXIAL_FLOAT = STACK_TOTAL - (RETAINER_THICKNESS + P004_OAL)",
   "inputs":{
     "stack_total_mm":11.05,
     "retainer_thickness_mm":3.00,
     "P004_OAL_nominal_mm":oal
   },
   "equation":f"11.05 - (3.00 + {oal_s})",
   "result_mm":axial_float,
   "requirement_mm":[0.04,0.08],
   "authority":str(EDR47).replace("\\","/"),
   "authority_sha256":sha(repo/EDR47),
   "native_P004_sha256":sha(part),
   "interpretation":"Canonical EDR-047 / native-CAD-bound nominal axial float. Production tolerance allocation remains open.",
   "status":"DERIVED_CANONICAL_CURRENT__WORST_CASE_PRODUCTION_TOLERANCE_OPEN"
  }
 ]

 technical_filter={
  "schema":"k01.p004.technical_filter.current.v1","generated_utc":now(),"status":"HOLD_DECISIONS_OPEN",
  "object":"K01-P-004",
  "sequence":"FUNCTION -> REQUIREMENTS -> LOAD/ENVIRONMENT -> INTERFACES -> OPTIONS -> TECHNICAL FILTER -> DECISION -> CAD -> VERIFICATION",
  "checks":[
   {"id":"TF-FUNCTION","topic":"Function/failure modes","state":"DEFINED_FOR_REVIEW"},
   {"id":"TF-REQ","topic":"Functional clearance/axial requirements","state":"PARTIAL__GUIDE_BAND_OPEN"},
   {"id":"TF-ENV","topic":"Temperature/media/environment","state":"PARTIAL__THERMAL_RECALC_REQUIRED"},
   {"id":"TF-INTERFACE","topic":"P001/P003/P014 interfaces","state":"DEFINED_FOR_REVIEW"},
   {"id":"TF-STRENGTH","topic":"Strength/stiffness","state":"N_A_CANDIDATE__REQUIRES_RATIONALE","rationale":"Low-load guide bushing; verify no retention/clamp load is intentionally applied."},
   {"id":"TF-THERMAL","topic":"Thermal expansion / binding risk","state":"OPEN"},
   {"id":"TF-TOL","topic":"Tolerance sensitivity / worst-case chains","state":"OPEN"},
   {"id":"TF-MFG","topic":"Manufacturability / PEEK process stability","state":"OPEN"},
   {"id":"TF-AVAIL","topic":"Production-grade TECAPEEK PVX availability","state":"OPEN"},
   {"id":"TF-ASSEMBLY","topic":"Assembly/service/replaceability","state":"PARTIAL"},
   {"id":"TF-INSPECT","topic":"Inspectability/metrology","state":"OPEN"},
   {"id":"TF-RELIABILITY","topic":"Wear/galling/creep/failure modes","state":"OPEN"},
   {"id":"TF-COST","topic":"Cost after function/reproducibility","state":"LATER"},
   {"id":"TF-CONCEPT","topic":"Preserve no-adhesive slip-fit concept","state":"CONTROLLED_BASELINE"},
   {"id":"TF-SOURCE","topic":"Standards/literature/manufacturer data applicability","state":"OPEN"},
  ]
 }

 dod=[
  "IF-02 tolerance allocation closes 0.04...0.08 mm clearance worst-case.",
  "IF-01 functional guide clearance min/nom/max is controlled and tolerance budget allocated.",
  f"L{oal_s} axial chain closes required axial float worst-case.",
  "Functional datum system is released.",
  "Bore-to-OD axis relation is released.",
  "Face orientation to functional axis is released if function requires it.",
  "Guide-bore surface texture is justified and released.",
  "OD locating/slip surface texture is justified and released.",
  "Face texture is released or N/A with rationale.",
  "Exact production TECAPEEK PVX grade/material authority is controlled.",
  "Thermal expansion check covers Tmin/Tnom/Tmax and stainless-to-PEEK interfaces.",
  "Manufacturing route is defined.",
  "PEEK dimensional conditioning / measurement temperature is defined.",
  "Inspection methods and measurement resolution are defined.",
  "Edge/deburr requirements are defined.",
  "Only after all above: PRODUCT_DEFINITION_READY=true; then drawing/DimXpert authoring may begin in the drawing branch."
 ]

 workpack={
  "schema":"k01.p004.product_definition_workpack.current.v1","generated_utc":now(),"status":"READ_ONLY_PREPARATION__NOT_READY",
  "part_id":"K01-P-004","title":"Front Guide Bushing",
  "native_identity":{"path":str(part),"exists":part.is_file(),"sha256":sha(part) if part.is_file() else None},
  "related_native":{
   "P003":{"path":str(p003),"exists":p003.is_file(),"sha256":sha(p003) if p003.is_file() else None},
   "P001":{"path":str(p001),"exists":p001.is_file(),"sha256":sha(p001) if p001.is_file() else None},
   "P014":{"path":str(p014),"exists":p014.is_file(),"sha256":sha(p014) if p014.is_file() else None},
  },
  "known_nominals":{"OD_mm":6.54,"BORE_mm":5.055,"LENGTH_mm":oal},
  "material":{"baseline":"TECAPEEK PVX black / Ensinger candidate baseline","release_state":"OPEN_PRODUCTION_GRADE_PROCESS_QUALIFICATION"},
  "functions":functions,"interfaces":interfaces,"calculations":[x["id"] for x in calculations],
  "definition_of_done":dod,
  "drawing_gate":{"state":"BLOCKED_UPSTREAM_PRODUCT_DEFINITION","rule":"No D004/DimXpert tolerance authoring before Product Definition READY."},
  "mutation":"NONE"
 }

 report={
  "schema":"k01.p004.product_definition_preflight.current.v1","generated_utc":now(),
  "status":"PASS_PREP_COMPLETE__HOLD_ENGINEERING_DECISIONS",
  "part":"K01-P-004","native_exists":part.is_file(),
  "functions":functions,"interfaces":interfaces,"calculations":calculations,
  "current_blockers":[
   "P001↔P004 guide clearance functional min/max requirement",
   "P003/P004 production tolerance allocation",
   "P004 axial worst-case tolerance allocation",
   "production TECAPEEK PVX grade/process data",
   "thermal expansion/creep/wear applicability",
   "datum/GPS release decisions",
   "surface texture decisions",
   "manufacturing route and metrology/conditioning",
  ],
  "next_engineering_action":"Close P004 requirements/interfaces and execute Technical Filter for tolerance/material/process candidates. No CAD or drawing mutation.",
  "drawing":"WAITING_UPSTREAM",
  "dimxpert":"WAITING_UPSTREAM",
  "bom_impact":"P004 material/process row remains HOLD until production grade/process is released.",
  "assembly_impact":"No canonical A001 mutation authorized by this preflight.",
 }

 wr(repo/WORKPACK,workpack);wr(repo/FILTER,technical_filter);wr(repo/CALC,{"schema":"k01.p004.calculation_register.current.v1","generated_utc":now(),"calculations":calculations});wr(repo/OUT_JSON,report)
 md=[
  "# K01-P-004 PRODUCT DEFINITION PREFLIGHT","",
  f"Status: **{report['status']}**","",
  "## Functions",
 ]+[f"- {x['id']}: {x['text']}" for x in functions]+[
  "","## Nominal calculations",
 ]+[f"- **{x['id']}** — {x['equation']} = **{x['result_mm']} mm** — {x['status']}" for x in calculations]+[
  "","## Blockers",
 ]+[f"- {x}" for x in report["current_blockers"]]+[
  "","## Gate",
  "**NO CAD / DIMXPERT / DRAWING AUTHORING YET.**",
  "",
  "Next: controlled requirements + Technical Filter + worst-case tolerance/material/process decisions."
 ]
 (repo/OUT_MD).parent.mkdir(parents=True,exist_ok=True);(repo/OUT_MD).write_text("\n".join(md)+"\n",encoding="utf-8")
 print("PASS: P004 Product Definition preflight prepared.")
 print("WORKPACK:",repo/WORKPACK)
 print("TECHNICAL FILTER:",repo/FILTER)
 print("CALCULATIONS:",repo/CALC)
 print("REPORT:",repo/OUT_MD)
 print("NO CAD / DIMXPERT / DRAWING MUTATION OCCURRED.")
 return 0
if __name__=="__main__":raise SystemExit(main())
