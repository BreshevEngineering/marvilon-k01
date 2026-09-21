from __future__ import annotations
import argparse, datetime as dt, hashlib, json, re
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
REPORT=Path("reports/control/K01_ENGINEERING_VALUE_COHERENCE_CURRENT.json")

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default
def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def issue(xs,rule,detail):xs.append({"rule":rule,"detail":detail})
def eq(a,b,tol=1e-9):
    try:return abs(float(a)-float(b))<=tol
    except Exception:return False
def find_char(pd,cid):
    return next((x for x in (pd.get("characteristics") or []) if isinstance(x,dict) and x.get("id")==cid),{})

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root).resolve()
    issues=[]; expected_oal=7.99; expected_float=0.06
    paths={
      "disp":Path("control/decisions/K01_DECISION_AUTHORITY_DISPOSITION_EDR047.json"),
      "edr":Path("control/decisions/EDR-047_P004_AXIAL_RECENTER.json"),
      "pd":Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json"),
      "wp":Path("control/product_definition/K01_P004_PRODUCT_DEFINITION_WORKPACK_CURRENT.json"),
      "calc":Path("reports/engineering/K01_P004_CALCULATION_REGISTER_CURRENT.json"),
      "trace":Path("control/product_definition/K01-P-004_EDR047_AUTHORITY_TRACE_CURRENT.json"),
      "d004spec":Path("control/drawings/spec/K01-D-004_P004_DRAWING_SPEC_v1.json"),
      "d004trace":Path("control/drawings/trace/K01-D-004_TRACE_CURRENT.json"),
      "delta":Path("control/drawings/trace/K01-D-004_EDR047_NOMINAL_DELTA_CURRENT.json"),
      "edr52":Path("control/decisions/EDR-052_P004_PHYSICAL_EVIDENCE_ACQUISITION_PLAN.json"),
      "chars":Path("control/product_definition/K01_CONTROLLED_CHARACTERISTIC_REGISTRY_CURRENT.json"),
      "swstd":Path("cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_OPERATING_STANDARD_CURRENT.txt"),
    }
    d={}
    for k,p in paths.items():
        q=repo/p
        if not q.is_file(): issue(issues,"VAL-00",f"missing {p}"); d[k]={}
        elif q.suffix.lower()==".json": d[k]=rd(q,{}) or {}
        else:d[k]=q.read_text(encoding="utf-8-sig",errors="replace")
    disp=d.get("disp",{}); edr=d.get("edr",{})
    if disp.get("canonical_active_path")!=str(paths["edr"]).replace("\\","/"): issue(issues,"VAL-01","EDR-047 disposition canonical path mismatch")
    if (repo/paths["edr"]).is_file() and sha(repo/paths["edr"])!=disp.get("canonical_sha256"): issue(issues,"VAL-02","EDR-047 canonical hash mismatch")
    if not eq((edr.get("promotion_evidence") or {}).get("oal_after_mm"),expected_oal): issue(issues,"VAL-03","EDR-047 promoted OAL != 7.99")

    native=(disp.get("native_cad_evidence") or {})
    np=Path(native.get("path") or "")
    if not np.is_file(): issue(issues,"VAL-04",f"native P004 missing: {np}")
    elif sha(np)!=native.get("sha256"): issue(issues,"VAL-05","native P004 SHA changed; typed native-truth refresh required")
    if not eq(native.get("value_mm"),expected_oal): issue(issues,"VAL-06","native evidence value != 7.99")

    c03=find_char(d.get("pd",{}),"P004-C03")
    if not eq(c03.get("nominal"),expected_oal): issue(issues,"VAL-10",f"Product Definition P004-C03 nominal={c03.get('nominal')!r}")
    if not eq((c03.get("derived") or {}).get("nominal_axial_float_20C_mm"),expected_float): issue(issues,"VAL-11","Product Definition axial float != 0.06")
    if "8.060" in json.dumps(c03,ensure_ascii=False) or "8.06" in json.dumps(c03,ensure_ascii=False):
        issue(issues,"VAL-12","superseded H_nom=8.060 branch remains in active P004-C03")

    wp=d.get("wp",{})
    if not eq((wp.get("known_nominals") or {}).get("LENGTH_mm"),expected_oal): issue(issues,"VAL-20","workpack LENGTH_mm != 7.99")
    if (wp.get("native_identity") or {}).get("sha256")!=native.get("sha256"): issue(issues,"VAL-21","workpack native SHA != canonical native SHA")

    calc=next((x for x in (d.get("calc",{}).get("calculations") or []) if x.get("id")=="P004-CALC-003"),{})
    if not eq(calc.get("result_mm"),expected_float): issue(issues,"VAL-30","CALC-003 result != 0.06")
    calc_inputs=calc.get("inputs") or {}
    if not eq(calc_inputs.get("P004_OAL_nominal_mm"),expected_oal):
        issue(issues,"VAL-31","CALC-003 structured input P004_OAL_nominal_mm != 7.99")
    if not eq(calc_inputs.get("stack_total_mm"),11.05) or not eq(calc_inputs.get("retainer_thickness_mm"),3.00):
        issue(issues,"VAL-32","CALC-003 structured stack inputs are not 11.05 / 3.00 mm")
    try:
        calc_recomputed=float(calc_inputs.get("stack_total_mm"))-(float(calc_inputs.get("retainer_thickness_mm"))+float(calc_inputs.get("P004_OAL_nominal_mm")))
        if not eq(calc_recomputed,expected_float) or not eq(calc_recomputed,calc.get("result_mm")):
            issue(issues,"VAL-33","CALC-003 structured inputs do not reproduce 0.06 mm/result_mm")
    except Exception:
        issue(issues,"VAL-33","CALC-003 structured inputs are incomplete/non-numeric")
    if calc.get("authority")!=str(paths["edr"]).replace("\\","/"):
        issue(issues,"VAL-34","CALC-003 authority is not canonical EDR-047")
    if (repo/paths["edr"]).is_file() and calc.get("authority_sha256")!=sha(repo/paths["edr"]):
        issue(issues,"VAL-35","CALC-003 authority SHA is stale")
    if np.is_file() and calc.get("native_P004_sha256")!=sha(np):
        issue(issues,"VAL-36","CALC-003 native P004 SHA is stale")

    tr=d.get("trace",{}).get("canonical_change") or {}
    if str(tr.get("new_nominal")) not in {"7.99","7.990"}: issue(issues,"VAL-40","authority trace new nominal != 7.99")
    if not eq(tr.get("derived_axial_float_new_mm"),expected_float): issue(issues,"VAL-41","authority trace derived float != 0.06")

    spec_txt=json.dumps(d.get("d004spec",{}),ensure_ascii=False)
    if "7.99" not in spec_txt: issue(issues,"VAL-50","D004 spec does not contain canonical 7.99 nominal")
    dtrace_txt=json.dumps(d.get("d004trace",{}),ensure_ascii=False)
    if '"8.00"' in dtrace_txt or "8.00" in dtrace_txt: issue(issues,"VAL-51","D004 current trace still contains 8.00 nominal")
    delta_txt=json.dumps(d.get("delta",{}),ensure_ascii=False)
    if "7.99" not in delta_txt: issue(issues,"VAL-52","D004 EDR047 delta does not contain 7.99")

    e52_txt=json.dumps(d.get("edr52",{}),ensure_ascii=False)
    if "P004 OAL 8.00" in e52_txt: issue(issues,"VAL-60","EDR-052 still asks to measure OAL 8.00")
    if "P004 OAL 7.99" not in e52_txt: issue(issues,"VAL-61","EDR-052 does not bind FAI OAL to 7.99")

    chars=d.get("chars",{}).get("characteristics") or []
    cc=next((x for x in chars if x.get("id")=="CHAR-P004-OAL-NOMINAL"),{})
    if not eq(cc.get("value"),expected_oal): issue(issues,"VAL-70","controlled characteristic OAL != 7.99")
    if (cc.get("native_binding") or {}).get("sha256")!=native.get("sha256"): issue(issues,"VAL-71","characteristic native SHA mismatch")

    swstd=d.get("swstd","")
    for token in ("API-005","dynamic","API-020","API-032","8.000 -> 7.990"):
        if token not in swstd: issue(issues,"VAL-80",f"SW2018 operating standard missing expected contract token: {token}")

    status="PASS_ENGINEERING_VALUE_COHERENCE" if not issues else "HOLD_ENGINEERING_VALUE_COHERENCE"
    rep={"schema":"k01.engineering_value_coherence.current.v1","generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
         "status":status,"scope":["CHAR-P004-OAL-NOMINAL","CHAR-P004-AXIAL-FLOAT-NOMINAL-20C"],
         "expected":{"P004_OAL_mm":expected_oal,"axial_float_20C_mm":expected_float},
         "native_sha256":native.get("sha256"),"issues":issues,
         "rule":"Conflicting active values across authority/Product Definition/native CAD/drawing/calculation/inspection are a hard HOLD."}
    wr(repo/REPORT,rep)
    print(status,"issues=",len(issues))
    for x in issues: print("HOLD:",json.dumps(x,ensure_ascii=False))
    print("REPORT:",repo/REPORT)
    return 0 if not issues else 2
if __name__=="__main__":raise SystemExit(main())
