from __future__ import annotations
import argparse,copy,json,shutil
from datetime import datetime,timezone
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
M=R/"master"/"K01_master.json"
REPORT=R/"reports"/"cad"/"current"/"K01_MASTER_COMPLETENESS_PATCH_20260903.json"

PATCH={
"K01-P-001":{"description":"Calibration Rod","material":"AISI 316L / EN 1.4404","status":"ACTIVE / DESIGN BASELINE","qty_design":1,
 "controlled":{"OAL_mm":68.5,"RodD_mm":5.0,"M4_male_length_mm":3.5}},
"K01-P-002":{"description":"Rear Guide / Anti-Rotation Bushing","material":"TECAPEEK PVX black baseline","status":"ACTIVE / MATERIAL BASELINE","qty_design":1,
 "controlled":{"L_mm":7.5,"axial_float_min_mm":0.04,"axial_float_max_mm":0.08}},
"K01-P-004":{"description":"Front Guide Bushing","material":"TECAPEEK PVX black baseline","status":"ACTIVE / MATERIAL BASELINE","qty_design":1,
 "controlled":{"OD_mm":6.54,"ID_mm":5.055,"L_mm":8.0,"retention":"P014 removable metal ring"}},
"K01-P-006":{"description":"Retaining Plug","material":"AISI 316L / EN 1.4404","status":"ACTIVE / DESIGN BASELINE","qty_design":1,
 "controlled":{"L_mm":8.0,"thread":"M12x1","thread_engagement_mm":6.0,"front_relief_mm":0.06}},
"K01-P-008":{"description":"Internal Magnetic Follower","material":"AISI 316L / EN 1.4404","status":"ACTIVE / DESIGN BASELINE","qty_design":1,
 "controlled":{"OD_mm":8.8,"L_mm":16.0,"M4_usable_depth_mm":4.0,"magnet_pocket_D_mm":8.1,"magnet_pocket_depth_mm":8.2}},
"K01-P-009":{"description":"Rear Stop Washer / OUT Stop","material":"AISI 316L / EN 1.4404","status":"ACTIVE / DESIGN BASELINE","qty_design":1,
 "controlled":{"t_mm":0.5}},
"K01-P-017":{"description":"Datum C Relieved / Diamond Locator Pin","material":"AISI 316L / EN 1.4404 baseline","status":"PLANNED / DATUM C GATE OPEN","qty_design":1,
 "controlled":{"press_shank_D_mm":3.0,"press_depth_mm":4.0,"protrusion_mm":2.0,"radial_minor_mm":2.8}},
"K01-B-007":{"description":"Magnet Wire","material":"Enameled copper Ø0.20 mm conductor baseline","status":"ACTIVE / SUPPLIER OPEN","qty_design":2},
"K01-B-008":{"description":"H-Bridge / Current Driver","material":"Purchased electronics","status":"ACTIVE / SUPPLIER OPEN","qty_design":1,
 "controlled":{"supply_V":24,"regulated_bipolar_current_min_A":1.25}},
"K01-B-009":{"description":"Actuator Lead / Connector Set","material":"OPEN","status":"ACTIVE / SPEC OPEN","qty_design":1},
"K01-B-010":{"description":"Hall Sensor","material":"OPEN","status":"OPTIONAL DIAGNOSTIC","qty_design":0},
}
QTY_ACTIVE=["K01-P-003","K01-P-007","K01-P-013","K01-P-014","K01-P-015","K01-P-016","K01-B-001"]

def merge(dst,src):
    changes=[]
    for k,v in src.items():
        if isinstance(v,dict):
            if not isinstance(dst.get(k),dict):dst[k]={}
            sub=merge(dst[k],v)
            changes += [(k+"."+a,b,c) for a,b,c in sub]
        else:
            old=dst.get(k,"<MISSING>")
            if old!=v:
                dst[k]=v;changes.append((k,old,v))
    return changes

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    if not M.exists():raise FileNotFoundError(M)
    data=json.loads(M.read_text(encoding="utf-8"));new=copy.deepcopy(data);parts=new.setdefault("parts",{})
    changes=[]
    for pn,p in PATCH.items():
        d=parts.setdefault(pn,{})
        for path,old,val in merge(d,p):
            changes.append((pn+"."+path,old,val))
    for pn in QTY_ACTIVE:
        if pn in parts and parts[pn].get("qty_design")!=1:
            old=parts[pn].get("qty_design","<MISSING>");parts[pn]["qty_design"]=1;changes.append((pn+".qty_design",old,1))
    if "K01-P-007" in parts:
        ctrl=parts["K01-P-007"].setdefault("controlled",{})
        if ctrl.get("L_mm")!=35.0:
            old=ctrl.get("L_mm","<MISSING>");ctrl["L_mm"]=35.0;changes.append(("K01-P-007.controlled.L_mm",old,35.0))

    print("Master completeness changes:",len(changes))
    for p,old,newv in changes:print(p,":",repr(old),"->",repr(newv))
    print("Current master parts:",len(data.get("parts",{})),"Proposed:",len(new.get("parts",{})))
    if not a.apply:
        print("[DRY RUN] master not modified.");return 0
    b=R/".local_archive"/"master_backups"/f"K01_master_pre_completeness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(M,b)
    M.write_text(json.dumps(new,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({"status":"PASS","created_utc":datetime.now(timezone.utc).isoformat(),
      "backup":str(b),"changes":[{"path":p,"old":o,"new":n} for p,o,n in changes]},
      indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] master completeness patch applied.");print("Backup:",b);print("Report:",REPORT);return 0
if __name__=="__main__":raise SystemExit(main())
