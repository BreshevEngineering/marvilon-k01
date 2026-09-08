from __future__ import annotations
import argparse,copy,json,shutil
from datetime import datetime,timezone
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
M=R/"master"/"K01_master.json"
REPORT=R/"reports"/"cad"/"current"/"K01_MASTER_COMPLETENESS_PATCH_V2_20260903.json"

# Restores only entries proven by earlier authoritative K01_master_v2/current CAD
# plus explicitly approved current additions. Existing newer fields are preserved.
PATCH={
"K01-P-001":{"description":"Calibration Rod","material":"AISI 316L / EN 1.4404","status":"ACTIVE","qty_design":1,"qty_unit":"ea",
 "controlled":{"OAL_mm":68.5,"RodD_mm":5.0,"M4_male_length_mm":3.5}},
"K01-P-002":{"description":"Rear Guide / Anti-Rotation Bushing","material":"TECAPEEK PVX black baseline","status":"ACTIVE / MATERIAL BASELINE","qty_design":1,"qty_unit":"ea",
 "controlled":{"L_mm":7.5,"axial_float_min_mm":0.04,"axial_float_max_mm":0.08}},
"K01-P-004":{"description":"Front Guide Bushing","material":"TECAPEEK PVX black baseline","status":"ACTIVE / MATERIAL BASELINE","qty_design":1,"qty_unit":"ea",
 "controlled":{"OD_mm":6.54,"ID_mm":5.055,"L_mm":8.0,"retention":"P014 removable metal ring"}},
"K01-P-006":{"description":"Retaining Plug","material":"AISI 316L / EN 1.4404","status":"ACTIVE","qty_design":1,"qty_unit":"ea",
 "controlled":{"L_mm":8.0,"thread":"M12x1","thread_engagement_mm":6.0,
               "front_relief_D_mm":9.10,"front_relief_depth_mm":0.06}},
"K01-P-008":{"description":"Internal Magnetic Follower","material":"AISI 316L / EN 1.4404","status":"ACTIVE","qty_design":1,"qty_unit":"ea",
 "controlled":{"OD_mm":8.8,"L_mm":16.0,"M4_usable_depth_mm":4.0,
               "magnet_pocket_D_mm":8.1,"magnet_pocket_depth_mm":8.2},
 "cad_local_controls":{"entry_chamfer":"0.10 x 45 deg"},
 "note":"Current native pocket Ø8.10. Final purchased-magnet fit remains a production acceptance gate; failed direct Ø8.20 edit is rejected."},
"K01-P-009":{"description":"Rear Stop Washer / OUT Stop","material":"AISI 316L / EN 1.4404","status":"ACTIVE","qty_design":1,"qty_unit":"ea",
 "controlled":{"t_mm":0.5}},
"K01-P-017":{"description":"Datum C Relieved / Diamond Locator Pin","material":"AISI 316L / EN 1.4404 baseline",
 "status":"PLANNED / DATUM C GATE OPEN","qty_design":1,"qty_unit":"ea",
 "controlled":{"press_shank_D_mm":3.0,"press_depth_mm":4.0,"protrusion_mm":2.0,
               "radial_minor_mm":2.8,"tangential_major_nominal_mm":3.0}},
"K01-B-007":{"description":"Magnet Wire","material":"Enameled copper Ø0.20 mm conductor",
 "status":"ACTIVE / SUPPLIER OPEN","qty_design":"AR","qty_unit":"m",
 "controlled":{"wire_baseline_mm":0.2,"turns_per_coil":324,
               "final_procurement_length":"OPEN_AFTER_P015_WINDING_FREEZE"}},
"K01-B-008":{"description":"H-Bridge / Current Driver","material":"Purchased electronics",
 "status":"ACTIVE / SUPPLIER OPEN","qty_design":1,"qty_unit":"ea",
 "controlled":{"supply_V":24,"regulated_bipolar_current_min_A":1.25}},
"K01-B-009":{"description":"Actuator Lead / Connector Set","material":"OPEN",
 "status":"ACTIVE / SPEC OPEN","qty_design":1,"qty_unit":"set"},
"K01-B-010":{"description":"Hall Sensor","material":"OPEN",
 "status":"OPTIONAL DIAGNOSTIC","qty_design":0,"qty_unit":"ea"},
}
QTY_ACTIVE=["K01-P-003","K01-P-007","K01-P-013","K01-P-014","K01-P-015","K01-P-016","K01-B-001"]

def merge(dst,src,prefix=""):
    changes=[]
    for k,v in src.items():
        path=f"{prefix}.{k}" if prefix else k
        if isinstance(v,dict):
            if not isinstance(dst.get(k),dict): dst[k]={}
            changes += merge(dst[k],v,path)
        else:
            old=dst.get(k,"<MISSING>")
            if old!=v:
                dst[k]=v;changes.append((path,old,v))
    return changes

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    data=json.loads(M.read_text(encoding="utf-8"));new=copy.deepcopy(data)
    parts=new.setdefault("parts",{})
    changes=[]
    for pn,p in PATCH.items():
        d=parts.setdefault(pn,{})
        for path,old,val in merge(d,p):
            changes.append((f"{pn}.{path}",old,val))
    for pn in QTY_ACTIVE:
        if pn in parts and parts[pn].get("qty_design")!=1:
            old=parts[pn].get("qty_design","<MISSING>");parts[pn]["qty_design"]=1
            changes.append((pn+".qty_design",old,1))
        if pn in parts and "qty_unit" not in parts[pn]:
            parts[pn]["qty_unit"]="ea";changes.append((pn+".qty_unit","<MISSING>","ea"))
    if "K01-P-007" in parts:
        ctrl=parts["K01-P-007"].setdefault("controlled",{})
        if ctrl.get("L_mm")!=35.0:
            old=ctrl.get("L_mm","<MISSING>");ctrl["L_mm"]=35.0
            changes.append(("K01-P-007.controlled.L_mm",old,35.0))

    new.setdefault("cad_environment",{})
    env=new["cad_environment"]
    for k,v in {
      "current_development":"SOLIDWORKS 2018 revision 26.0.1",
      "final_migration_target":"SOLIDWORKS 2026",
      "migration_rule":"Complete/freeze K01 on current configured workstation; migrate stable native CAD after design freeze."
    }.items():
        if env.get(k)!=v:
            old=env.get(k,"<MISSING>");env[k]=v;changes.append(("cad_environment."+k,old,v))

    print("Master completeness v2 changes:",len(changes))
    for p,old,v in changes:print(p,":",repr(old),"->",repr(v))
    print("Current parts:",len(data.get("parts",{})),"Proposed parts:",len(new.get("parts",{})))
    if not a.apply:
        print("[DRY RUN] master not modified.");return 0
    b=R/".local_archive"/"master_backups"/f"K01_master_pre_completeness_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(M,b)
    M.write_text(json.dumps(new,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({"status":"PASS","created_utc":datetime.now(timezone.utc).isoformat(),
      "backup":str(b),"changes":[{"path":p,"old":o,"new":v} for p,o,v in changes]},
      indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] master completeness v2 applied.");print("Backup:",b);print("Report:",REPORT);return 0
if __name__=="__main__":raise SystemExit(main())
