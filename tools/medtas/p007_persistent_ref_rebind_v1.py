#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

START=Path("reports/control/K01_P007_PROFESSIONAL_START_CURRENT.json")
STEP=Path("reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json")
PC=Path("control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json")
SCOPE=Path("control/product_definition/K01_P007_PMI_AUTHORING_SCOPE.json")
AUTHORING=Path("control/drawings/K01_D006_AUTHORING_INPUT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
ACTIVE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
OUT=Path("reports/control/K01_P007_CANONICAL_PERSISTENT_REBIND_CURRENT.json")
RAW=Path("reports/cad/p007_pmi_authoring/K01_P007_CANONICAL_PERSISTENT_REBIND_RAW.json")
LOG=Path("reports/cad/p007_pmi_authoring/K01_P007_CANONICAL_PERSISTENT_REBIND.log")
CS=Path("cad_api/medtas/K01P007PersistentRefRebind.cs")
P007=Path(r"D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT")

def load(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");os.replace(str(t),str(p))
def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def sw_running():
    # First use tasklist; fall back to PowerShell because localized tasklist output
    # has previously escaped the simple parser on this workstation.
    try:
        cp=subprocess.run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],
                          capture_output=True,text=True,errors="ignore")
        if "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower():
            return True
    except Exception:
        pass
    try:
        cp=subprocess.run(
            ["powershell","-NoProfile","-Command",
             "if (Get-Process SLDWORKS -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"],
            capture_output=True,text=True,errors="ignore")
        return cp.returncode==0
    except Exception:
        return False
def find_redist(name):
    roots=[]
    for k in ("ProgramFiles","ProgramFiles(x86)"):
        b=os.environ.get(k)
        if b: roots += [Path(b)/"SOLIDWORKS Corp"/"SOLIDWORKS"/"api"/"redist",Path(b)/"SOLIDWORKS Corp"]
    for r in roots:
        p=r/name
        if p.exists():return p
    for r in roots:
        if not r.exists():continue
        try:
            hits=list(r.rglob(name))
            if hits:return sorted(hits,key=lambda p:len(str(p)))[0]
        except:pass
    return None
def compile_helper(root):
    wind=Path(os.environ.get("WINDIR",r"C:\Windows"))
    csc=wind/"Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not csc.exists(): csc=wind/"Microsoft.NET/Framework/v4.0.30319/csc.exe"
    sld=find_redist("SolidWorks.Interop.sldworks.dll");const=find_redist("SolidWorks.Interop.swconst.dll")
    for p in (csc,sld,const,root/CS): need(p is not None and Path(p).exists(),"compile dependency missing: "+str(p))
    bindir=root/"cad_api/medtas/bin";bindir.mkdir(parents=True,exist_ok=True)
    exe=bindir/"K01P007PersistentRefRebind.exe"
    cmd=[str(csc),"/nologo","/langversion:5","/platform:x64","/target:exe",
         "/out:"+str(exe),"/reference:"+str(sld),"/reference:"+str(const),
         "/reference:System.Web.Extensions.dll",str(root/CS)]
    cp=subprocess.run(cmd,cwd=str(root),capture_output=True,text=True,errors="replace")
    if cp.stdout:print(cp.stdout,end="")
    if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
    need(cp.returncode==0,"P007 persistent-reference helper compile failed")
    shutil.copy2(sld,bindir/Path(sld).name);shutil.copy2(const,bindir/Path(const).name)
    return exe
def update_binding(char, binding):
    char["solidworks_binding"]=binding
    char["binding_status"]="PASS_CANONICAL_PERSISTENT_REF"
    char["binding_part_sha256"]=sha(P007)
    char["binding_checkpoint"]="K01-CP-20260910-BASELINE-02C-PROMOTED"

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    rep={"schema":"k01.p007.canonical_persistent_rebind.v1","generated_utc":datetime.now(timezone.utc).isoformat(),
         "status":"RUNNING","native_CAD_mutated":False,"control_files_mutated":False}
    try:
        start=load(root/START);step=load(root/STEP)
        need(start.get("status")=="PASS_P007_CANONICAL_GEOMETRY_RECONCILED_READY_FOR_ENTITY_REBIND","p007-start has not PASSed")
        need(str(step.get("status") or "").startswith("PASS_TO_P007_PROFESSIONAL_DIMXPERT_CANDIDATE_AUTHORING"),"P007 step gate is not PASS")
        need(P007.is_file(),"canonical P007 missing")
        psha=sha(P007);need(psha==str((start.get("canonical_p007") or {}).get("sha256") or ""),"canonical P007 SHA changed after p007-start")
        need(not sw_running(),"SolidWorks process is running. Close SOLIDWORKS; if no visible session/unsaved work exists, terminate the orphan process, then rerun p007-rebind.")

        exe=compile_helper(root)
        (root/RAW).parent.mkdir(parents=True,exist_ok=True)
        cp=subprocess.run([str(exe),"--part",str(P007),"--out",str(root/RAW),"--log",str(root/LOG)],
                          cwd=str(root),capture_output=True,text=True,errors="replace")
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        need(cp.returncode==0,"persistent-reference helper failed")
        need((root/RAW).is_file(),"persistent-reference raw report missing")
        raw=load(root/RAW);need(raw.get("status")=="PASS","persistent-reference raw status not PASS")
        need(raw.get("native_CAD_mutated") is False,"helper reports native CAD mutation")
        need(raw.get("sha256_before")==psha and raw.get("sha256_after")==psha,"P007 binary SHA changed during rebind")
        counts=raw.get("counts") or {}
        need(counts.get("C01")==2 and counts.get("C02")==1 and counts.get("C04")==3 and counts.get("C05_flange_od")==1 and counts.get("C06_rear")==1,
             "canonical face classification counts are not exact")
        res=raw.get("resolution_after_close_reopen") or []
        need(res and all(x.get("resolved") is True and int(x.get("state",-1))==0 for x in res),"one or more persistent refs failed close/reopen resolution")
        bindings=raw.get("bindings") or {}
        for cid in ("C01","C02","C04","C05","C06"): need(cid in bindings,"binding missing "+cid)

        pc=load(root/PC)
        pc["generated_utc"]=datetime.now(timezone.utc).isoformat()
        pc["persistent_reference_state"]="PASS_CANONICAL_REBOUND_READY_FOR_CANDIDATE_PMI_WRITE"
        pc["canonical_persistent_rebind_report"]=str(RAW).replace("\\","/")
        pc["datum_A"]={"binding_mode":"COMPOSITE_COPLANAR_FACE_SET","binding_status":"PASS_CANONICAL_PERSISTENT_REF","entities":bindings["C01"]["entities"],
                       "part_sha256":psha,"checkpoint":"K01-CP-20260910-BASELINE-02C-PROMOTED"}
        cmap={x.get("id"):x for x in pc.get("characteristics") or []}
        for cid in ("C01","C02","C04","C05","C06"):
            need(cid in cmap,"product characteristic missing "+cid)
            update_binding(cmap[cid],bindings[cid])
        if "C03" in cmap:
            cmap["C03"]["binding_status"]="DERIVED_BINDING_READY_C02_AXIS_TO_DATUM_A"
            cmap["C03"]["binding_dependencies"]=["C01","C02"]
        pc.setdefault("authoring_policy",{})["persistent_ref_rebind_required"]=False
        pc["authoring_policy"]["persistent_refs_bound_to_part_sha256"]=psha
        write(root/PC,pc)

        scope=load(root/SCOPE);scope["generated_utc"]=datetime.now(timezone.utc).isoformat()
        scope["status"]="READY_FOR_CANONICAL_CANDIDATE_PMI_AUTHORING"
        scope["canonical_persistent_rebind_report"]=str(RAW).replace("\\","/")
        scope["native_part"]={"path":str(P007),"sha256_before_write":psha}
        smap={x.get("id"):x for x in scope.get("safe_authoring_scope") or []}
        for cid in ("C01","C02","C04","C05","C06"):
            if cid in smap:
                smap[cid]["solidworks_binding"]=bindings[cid]
                smap[cid]["binding_status"]="PASS_CANONICAL_PERSISTENT_REF"
        if "C03" in smap:
            smap["C03"]["binding_status"]="DERIVED_BINDING_READY_C02_AXIS_TO_DATUM_A"
            smap["C03"]["binding_dependencies"]=["C01","C02"]
        scope["next_step"]="CREATE_TIMESTAMPED_CANDIDATE_AND_AUTHOR_C01_C02_C03_C04_C05_C06_C09_NATIVE_PMI"
        write(root/SCOPE,scope)

        au=load(root/AUTHORING);au["generated_utc"]=datetime.now(timezone.utc).isoformat()
        au["persistent_reference_status"]="PASS_CANONICAL_REBOUND"
        au["persistent_reference_report"]=str(RAW).replace("\\","/")
        au["canonical_p007"]={"path":str(P007),"sha256":psha}
        au["next_authoring_scope"]=["C01","C02","C03","C04","C05","C06","C09"]
        write(root/AUTHORING,au)

        nxt=load(root/NEXT);nxt["current_stage"]="P007_CANONICAL_PERSISTENT_REFS_PASS_READY_FOR_NATIVE_PMI_CANDIDATE"
        nxt["last_completed"]="Canonical P007 face bindings C01/C02/C04/C05/C06 were regenerated from the CP-P stable part and all persistent IDs resolved after close/reopen with state=0. Canonical P007 binary SHA remained invariant."
        nxt["last_evidence"]=[str(OUT).replace("\\","/"),str(RAW).replace("\\","/"),str(PC).replace("\\","/")]
        nxt["current_blocker"]="Native DimXpert/PMI authoring must now occur on a timestamped candidate copy only. Canonical stable P007 remains read-only. C07/C08/C10/C11/C12 and blind-end release definitions remain OPEN."
        nxt["next_1"]="Create timestamped candidate copy from canonical P007 and author C01/C02/C03/C04/C05/C06/C09 using the canonical bindings."
        nxt["next_2"]="Save-close-reopen, extract native DimXpert, require geometry/binary baseline comparison and characteristic readback before accepting candidate."
        nxt["then"]="Derive K01-D-006 candidate, drawing semantic lint + visual QA, then inspection linkage."
        write(root/NEXT,nxt)

        active={
          "schema":"k01.active_step_gate.v1",
          "step_id":"K01-STEP-P4-P007-NATIVE-DIMXPERT-CANDIDATE",
          "active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION",
          "checkpoint_id":"K01-CP-20260910-BASELINE-02C-PROMOTED",
          "intent":"AUTHOR_TIMESTAMPED_P007_NATIVE_DIMXPERT_PMI_CANDIDATE_WITH_GEOMETRY_INVARIANCE",
          "mutation_authorized":True,
          "result_on_pass":"PASS_TO_P007_NATIVE_DIMXPERT_CANDIDATE_WRITE",
          "required_files":[str(START).replace("\\","/"),str(OUT).replace("\\","/"),str(PC).replace("\\","/"),str(SCOPE).replace("\\","/"),
                            "control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json","reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json"],
          "required_statuses":[
            {"file":str(START).replace("\\","/"),"path":["status"],"allowed_values":["PASS_P007_CANONICAL_GEOMETRY_RECONCILED_READY_FOR_ENTITY_REBIND"]},
            {"file":str(OUT).replace("\\","/"),"path":["status"],"allowed_values":["PASS_P007_CANONICAL_PERSISTENT_REFS_REBOUND_READY_FOR_NATIVE_PMI"]},
            {"file":str(SCOPE).replace("\\","/"),"path":["status"],"allowed_values":["READY_FOR_CANONICAL_CANDIDATE_PMI_AUTHORING"]},
            {"file":"control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json","path":["status"],"allowed_prefixes":["PASS_PILOT_SAVE_CLOSE_REOPEN"]},
            {"file":"reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json","path":["status"],"allowed_prefixes":["PASS"]}],
          "impact_declarations":{
            "requirements":"Author only already-controlled/candidate characteristics C01/C02/C03/C04/C05/C06/C09; do not invent C07/C08/C10/C11/C12/blind-end release values.",
            "materials":"P007 stays AISI 316L / EN 1.4404; material note C09 only.",
            "bom":"No quantity/geometry change is authorized by PMI authoring.",
            "dimxpert_drawings":"Write native PMI on timestamped P007 candidate; K01-D-006 is derived only after save-close-reopen verification.",
            "inspection":"Characteristic IDs remain stable and will feed the inspection template after candidate acceptance.",
            "dependencies":"Any geometry fingerprint change beyond PMI-only metadata is a hard HOLD.",
            "technical_filter":"Manufacturing/tolerance/release OPENs remain explicit; authoring does not imply release.",
            "rollback":"Delete/reject timestamped candidate on failure; canonical stable P007 is never overwritten.",
            "evidence":"Candidate path/SHA + pre/post geometry fingerprint + native DimXpert readback + save-close-reopen persistence."}}
        write(root/ACTIVE,active)

        rep.update({"status":"PASS_P007_CANONICAL_PERSISTENT_REFS_REBOUND_READY_FOR_NATIVE_PMI",
                    "control_files_mutated":True,"canonical_p007":{"path":str(P007),"sha256":psha},
                    "bindings":{k:{"binding_type":bindings[k].get("binding_type"),"entity_count":len(bindings[k].get("entities") or [])} for k in ("C01","C02","C04","C05","C06")},
                    "persistent_resolution_count":len(res),"next":"TIMESTAMPED_NATIVE_DIMXPERT_PMI_CANDIDATE"})
        write(root/OUT,rep)
        # Refresh step gate + panel, but do not make handoff every iteration.
        for tool in ("tools/medtas/technical_filter_map_v2_2.py","tools/assurance/engineering_step_gate.py","tools/assurance/build_engineering_dashboard.py"):
            p=root/tool
            if p.is_file():
                c=subprocess.run([sys.executable,str(p),"--repo-root",str(root)],cwd=str(root),text=True,capture_output=True,errors="replace")
                if c.stdout:print(c.stdout,end="")
                if c.stderr:print(c.stderr,end="",file=sys.stderr)
        print("STATUS:",rep["status"]);print("P007 SHA256:",psha);print("Persistent refs resolved after close/reopen:",len(res))
        print("NEXT: timestamped native DimXpert/PMI candidate C01/C02/C03/C04/C05/C06/C09");print("REPORT:",root/OUT)
        return 0
    except Exception as e:
        rep["status"]="HOLD_P007_CANONICAL_PERSISTENT_REBIND";rep["error"]=repr(e);write(root/OUT,rep)
        print("STATUS:",rep["status"]);print("ERROR:",repr(e));print("REPORT:",root/OUT);return 2
if __name__=="__main__": raise SystemExit(main())
