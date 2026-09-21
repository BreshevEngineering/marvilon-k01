from __future__ import annotations
import argparse, json, subprocess, sys, os, re, hashlib
from pathlib import Path
from datetime import datetime

# One file. Python standard library only.
# No jsonschema, ezdxf, package imports, family files, plugin discovery, or pip.

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def save_json(path, data):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def require(cond,msg):
    if not cond: raise RuntimeError(msg)

def family_layout(family_id):
    if family_id!="CYLINDRICAL_TWO_VIEW_V1":
        raise RuntimeError("UNSUPPORTED_FAMILY_IN_SIMPLE_V1: "+family_id)
    return {
        "views":[
            {
                "id":"SECTION_MAIN","kind":"LONGITUDINAL_SECTION",
                "parent_orientation":"*Front","section_label":"A",
                "x_m":0.115,"y_m":0.145,"scale":8.0,
                "show_parent":False,"parent_x_m":0.050,"parent_y_m":0.225,
                "section_depth_m":0.0
            },
            {
                "id":"END_MAIN","kind":"MODEL_VIEW","orientation":"*Right",
                "x_m":0.285,"y_m":0.160,"scale":8.0
            }
        ],
        "slots":{
            "THREAD":[0.088,0.210],
            "THREAD_LEN":[0.108,0.205],
            "HEAD_OD":[0.338,0.185],
            "BORE":[0.330,0.150],
            "HOLE":[0.245,0.218],
            "PCD":[0.255,0.230],
            "ANGLE":[0.315,0.230],
            "RELIEF":[0.088,0.105],
        }
    }

def bind_cyl(sig,count=1):
    return {"kind":"CYLINDER" if count==1 else "CYLINDER_SET",
            "diameter_mm":float(sig["diameter_mm"]),"count":int(count)}

def build_legacy_spec(contract, output_root):
    require(contract["drawing_family"]=="CYLINDRICAL_TWO_VIEW_V1","family mismatch")
    layout=family_layout(contract["drawing_family"])
    mb=contract["model_bindings"]

    bindings={}
    bindings["THREAD_REGION"]={"kind":"CYLINDER","diameter_mm":float(mb["THREAD_REGION"]["geometry_signature"]["model_geometry_diameter_mm"]),"count":1}
    bindings["HEAD_OD"]=bind_cyl(mb["HEAD_OD"]["geometry_signature"])
    bindings["THROUGH_BORE"]=bind_cyl(mb["THROUGH_BORE"]["geometry_signature"])
    sh=mb["SERVICE_HOLES"]["geometry_signature"]
    bindings["SERVICE_HOLES"]={"kind":"CYLINDER_SET","diameter_mm":float(sh["diameter_mm"]),"count":int(sh["count"])}
    bindings["RELIEF_OD"]=bind_cyl(mb["RELIEF_OD"]["geometry_signature"])
    bindings["THREAD_END_1"]={"kind":"PLANE_AT_CYL_END","cylinder":"THREAD_REGION","end":"MIN_X","selection":"NEAREST_PLANE_TO_APPROX_CYL_TRIM_X__LARGEST_AREA_IF_COPLANAR"}
    bindings["THREAD_END_2"]={"kind":"PLANE_AT_CYL_END","cylinder":"THREAD_REGION","end":"MAX_X","selection":"NEAREST_PLANE_TO_APPROX_CYL_TRIM_X__LARGEST_AREA_IF_COPLANAR"}

    chars={c["id"]:c for c in contract["characteristics"]}
    c1=chars["P006-C01"]; c2=chars["P006-C02"]; c3=chars["P006-C03"]; c4=chars["P006-C04"]; c5=chars["P006-C05"]; c6=chars["P006-C06"]
    annotations=[]

    x,y=layout["slots"]["THREAD"]
    annotations.append({"id":"P006-C01-THREAD","kind":"BOUND_NOTE","view":"SECTION_MAIN","binding":"THREAD_REGION",
                        "text":f'{c1["requirement"]["designation"]}-{c1["requirement"]["tolerance_class"]}',
                        "state":"CONTROLLED","x_m":x,"y_m":y})
    x,y=layout["slots"]["THREAD_LEN"]
    annotations.append({"id":"P006-C01-LENGTH","kind":"LINEAR","view":"SECTION_MAIN",
                        "from_binding":"THREAD_END_1","to_binding":"THREAD_END_2",
                        "nominal_mm":float(c1["requirement"]["length_mm"]),"precision":2,
                        "state":"CONTROLLED","x_m":x,"y_m":y})

    x,y=layout["slots"]["HEAD_OD"]
    annotations.append({"id":"P006-C02-HEAD-OD","kind":"DIAMETER","view":"END_MAIN","binding":"HEAD_OD",
                        "nominal_mm":float(c2["requirement"]["diameter_mm"]),
                        "shaft_fit":c2["requirement"]["fit"],"precision":2,
                        "state":"CONTROLLED","x_m":x,"y_m":y})

    x,y=layout["slots"]["BORE"]
    annotations.append({"id":"P006-C03-BORE","kind":"DIAMETER","view":"SECTION_MAIN","binding":"THROUGH_BORE",
                        "nominal_mm":float(c3["requirement"]["diameter_mm"]),"suffix":" THRU","precision":2,
                        "state":"CONTROLLED","x_m":x,"y_m":y})

    r=c4["requirement"]; x,y=layout["slots"]["HOLE"]
    hole_text=f'{int(r["count"])}× Ø{r["diameter_mm"]:.2f} +{r["upper_tol_mm"]:.2f}/0 BLIND; DEPTH {r["depth_mm"]:.2f} ±{r["depth_sym_tol_mm"]:.2f}'
    annotations.append({"id":"P006-C04-HOLE","kind":"BOUND_NOTE","view":"END_MAIN","binding":"SERVICE_HOLES",
                        "text":hole_text,"state":"CONTROLLED","x_m":x,"y_m":y})
    x,y=layout["slots"]["PCD"]
    annotations.append({"id":"P006-C04-PCD","kind":"TED_NOTE","view":"END_MAIN","text":f'Ø{r["pcd_mm"]:.2f}',
                        "state":"CONTROLLED","x_m":x,"y_m":y})
    x,y=layout["slots"]["ANGLE"]
    annotations.append({"id":"P006-C04-ANGLE","kind":"TED_NOTE","view":"END_MAIN","text":f'{int(r["angle_deg"])}°',
                        "state":"CONTROLLED","x_m":x,"y_m":y})

    r=c6["requirement"]; x,y=layout["slots"]["RELIEF"]
    lo,hi=r["resulting_axial_float_mm"]
    annotations.append({"id":"P006-C06-RELIEF","kind":"BOUND_NOTE","view":"SECTION_MAIN","binding":"RELIEF_OD",
                        "text":f'RELIEF Ø{r["diameter_mm"]:.2f}×{r["width_mm"]:.2f}; P002 AXIAL FLOAT {lo:.2f}…{hi:.2f}',
                        "state":"CONTROLLED","x_m":x,"y_m":y})

    review_notes=["ENGINEERING REVIEW — NOT FOR MANUFACTURE"]
    # Do NOT author unreleased GTOL.
    review_notes.append("OPEN: POSITION Ø0.10 DATUM DESIGNATOR / THREAD-AXIS SEMANTIC BINDING NOT RELEASED.")
    if contract["document"]["general_tolerance"]["state"]=="OPEN":
        review_notes.append("OPEN: GENERAL TOLERANCE STANDARD / CLASS NOT RELEASED.")
    if contract["document"]["surface_texture"]["state"]=="OPEN":
        review_notes.append("OPEN: SURFACE TEXTURE / ROUGHNESS REQUIREMENTS NOT RELEASED.")
    if contract["document"]["revision"]["state"]=="OPEN":
        review_notes.append("OPEN: RELEASE REVISION.")
    review_notes.append("UNSPECIFIED NOMINAL GEOMETRY: CONTROLLED NATIVE SOLIDWORKS MODEL. DO NOT SCALE DRAWING.")
    review_notes.append("MATERIAL: "+contract["document"]["material"])

    scale=contract["document"]["scale"]
    scale_num=float(scale.split(":")[0])/float(scale.split(":")[1])

    return {
        "schema":"k01.drawing_system_spec.v1",
        "drawing_id":contract["drawing_id"],
        "part_id":contract["part_id"],
        "title":contract["document"]["title"],
        "status":"ENGINEERING_REVIEW__SIMPLE_V1",
        "model_path":contract["model"]["canonical_path"],
        "output_root":output_root,
        "sheet":contract["document"]["sheet"],
        "sheet_scale":scale_num,
        "projection":contract["document"]["projection"],
        "units":contract["document"]["units"],
        "material":contract["document"]["material"],
        "view_definitions":layout["views"],
        "bindings":bindings,
        "datum_features":[],
        "annotations":annotations,
        "title_block_properties":{
            "DrawingNo":contract["drawing_id"],"PartNo":contract["part_id"],
            "Title":contract["document"]["title"],"Material":contract["document"]["material"],
            "Status":"ENGINEERING REVIEW","Units":contract["document"]["units"],
            "Projection":contract["document"]["projection"],"Scale":scale,"Revision":""
        },
        "release_blockers":list(contract["release"]["blockers"]),
        "review_notes":review_notes,
        "review_note_x_m":0.025,"review_note_y_m":0.070,"review_note_step_m":0.0065
    }

def parse_output(stdout):
    res={}
    for line in stdout.splitlines():
        for key in ["DRAWING","PDF","DXF","REPORT","CANDIDATE ROOT","STATUS"]:
            marker=key+":"
            if line.startswith(marker):
                res[key.lower().replace(" ","_")]=line.split(":",1)[1].strip()
    return res

def result_exists(parsed):
    for k in ["drawing","pdf","dxf"]:
        p=parsed.get(k)
        if p and Path(p).exists(): return True
    return False

def main(repo,contract_path,outdir):
    repo=Path(repo); outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    result={
        "schema":"k01.drawing_system.simple_result.v1",
        "timestamp":datetime.now().isoformat(timespec="seconds"),
        "execution_state":"STARTED","release_state":"HOLD_RELEASE",
        "artifacts":{}
    }
    save_json(outdir/"RESULT_CURRENT.json",result)

    try:
        c=load_json(contract_path)
        require(c["schema"] in {"marvilon.drawing_contract.v2","marvilon.drawing_contract.v2_1"},"unsupported contract schema")
        require(Path(c["model"]["canonical_path"]).is_file(),"canonical model missing: "+c["model"]["canonical_path"])

        spec=build_legacy_spec(c,str(Path(r"D:\Marvilon\K01\cad\drawings\candidates")/c["drawing_id"]))
        spec_path=outdir/"legacy_spec.json"; save_json(spec_path,spec)
        result["artifacts"]["legacy_spec"]=str(spec_path)
        result["execution_state"]="SPEC_GENERATED"; save_json(outdir/"RESULT_CURRENT.json",result)

        backend=repo/r"cad_api\solidworks_2018_proven\current\K01_DRAWING_SYSTEM_V1\K01DrawingSystemV1.cs"
        require(backend.is_file(),"SolidWorks backend source missing")
        text=backend.read_text(encoding="utf-8-sig")
        require("V7_1_R1_MERGED_BOUND_CALLOUTS_DXF_RESULT_20260921" in text,
                "V7.1 backend marker missing; do not mutate unknown backend")

        wrapper=repo/r"tools\medtas\drawing_system_v1.py"
        require(wrapper.is_file(),"drawing_system_v1.py missing")

        cmd=["py","-3",str(wrapper),"--repo-root",str(repo),"--spec",str(spec_path),"--mode","review"]
        cp=subprocess.run(cmd,cwd=str(repo),capture_output=True,text=True,errors="replace")
        stdout=cp.stdout or ""; stderr=cp.stderr or ""
        (outdir/"BACKEND_STDOUT.log").write_text(stdout,encoding="utf-8")
        (outdir/"BACKEND_STDERR.log").write_text(stderr,encoding="utf-8")

        parsed=parse_output(stdout)
        result["backend_return_code"]=cp.returncode
        result["backend_status"]=parsed.get("status")
        for k in ["drawing","pdf","dxf","report","candidate_root"]:
            if parsed.get(k): result["artifacts"][k]=parsed[k]

        if result_exists(parsed):
            result["execution_state"]="GENERATED"
            result["status"]="RESULT_GENERATED__HOLD_RELEASE"
            rc=0
        else:
            result["execution_state"]="FAILED_NO_NATIVE_ARTIFACT"
            result["status"]="FAILED_NO_NATIVE_ARTIFACT"
            rc=3

        save_json(outdir/"RESULT_CURRENT.json",result)
        print("DRAWING="+c["drawing_id"])
        print("EXECUTION_STATE="+result["execution_state"])
        print("RELEASE_STATE=HOLD_RELEASE")
        print("BACKEND_RC="+str(cp.returncode))
        for k,v in result["artifacts"].items(): print(k.upper()+"="+str(v))
        print("RESULT_JSON="+str(outdir/"RESULT_CURRENT.json"))
        return rc
    except Exception as exc:
        result["execution_state"]="FAILED_UNSAFE"
        result["status"]="FAILED_UNSAFE"
        result["error"]=repr(exc)
        save_json(outdir/"RESULT_CURRENT.json",result)
        print("STATUS=FAILED_UNSAFE")
        print("ERROR="+repr(exc))
        print("RESULT_JSON="+str(outdir/"RESULT_CURRENT.json"))
        return 3

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=r"D:\BreshevEngineering\marvilon-k01")
    ap.add_argument("--contract",required=True)
    ap.add_argument("--outdir",required=True)
    a=ap.parse_args()
    raise SystemExit(main(a.repo_root,a.contract,a.outdir))
