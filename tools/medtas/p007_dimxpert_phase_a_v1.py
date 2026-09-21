#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

REBIND=Path("reports/control/K01_P007_CANONICAL_PERSISTENT_REBIND_CURRENT.json")
STEP=Path("reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json")
EVIDENCE=Path("control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json")
SCOPE=Path("control/product_definition/K01_P007_PMI_AUTHORING_SCOPE.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
ACTIVE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
OUT=Path("reports/control/K01_P007_DIMXPERT_PHASE_A_CURRENT.json")
PHASE_B=Path("reports/drawing/current/K01-D-006_P007_PHASE_B_WORKPACK_CURRENT.json")
PHASE_B_MD=Path("reports/drawing/current/K01-D-006_P007_PHASE_B_WORKPACK_CURRENT.md")
HIST_STEP13_REPORT=Path("reports/cad/p007_pmi_step13/K01_P007_PMI_STEP13_CURRENT.json")
HIST_STEP13_SCRIPT=Path(r"D:\\BreshevEngineering\\Additional\\k01_step13_integrated\\payload\\tools\\engineering\\run_p007_pmi_step13.py")
CS=Path("cad_api/medtas/K01P007DimXpertPhaseA.cs")
P007=Path(r"D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT")
CAND_ROOT=Path(r"D:\Marvilon\K01\cad\candidates\p007_pmi_authoring")

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
    try:
        cp=subprocess.run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],capture_output=True,text=True,errors="ignore")
        if "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower(): return True
    except: pass
    try:
        cp=subprocess.run(["powershell","-NoProfile","-Command",
            "if (Get-Process SLDWORKS -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"],
            capture_output=True,text=True,errors="ignore")
        return cp.returncode==0
    except:return False
def find_file(names):
    roots=[]
    for k in ("ProgramFiles","ProgramFiles(x86)"):
        b=os.environ.get(k)
        if b:
            roots += [Path(b)/"SOLIDWORKS Corp"/"SOLIDWORKS"/"api"/"redist",Path(b)/"SOLIDWORKS Corp"]
    for r in roots:
        for n in names:
            p=r/n
            if p.exists(): return p
    for r in roots:
        if not r.exists(): continue
        try:
            for n in names:
                hits=list(r.rglob(n))
                if hits:return sorted(hits,key=lambda p:len(str(p)))[0]
        except:pass
    return None
def compile_helper(root):
    wind=Path(os.environ.get("WINDIR",r"C:\Windows"))
    csc=wind/"Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not csc.exists():csc=wind/"Microsoft.NET/Framework/v4.0.30319/csc.exe"
    sw=find_file(["SolidWorks.Interop.sldworks.dll"])
    const=find_file(["SolidWorks.Interop.swconst.dll"])
    dx=find_file(["SolidWorks.Interop.swdimxpert.dll","swdimxpert.dll"])
    for p in (csc,sw,const,dx,root/CS):need(p is not None and Path(p).exists(),"compile dependency missing: "+str(p))
    bindir=root/"cad_api/medtas/bin";bindir.mkdir(parents=True,exist_ok=True)
    exe=bindir/"K01P007DimXpertPhaseA.exe"
    cmd=[str(csc),"/nologo","/optimize+","/platform:x64","/target:exe",
         "/out:"+str(exe),"/reference:"+str(sw),"/reference:"+str(const),"/reference:"+str(dx),
         "/reference:System.Web.Extensions.dll",str(root/CS)]
    cp=subprocess.run(cmd,cwd=str(root),capture_output=True,text=True,errors="replace")
    if cp.stdout:print(cp.stdout,end="")
    if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
    need(cp.returncode==0,"P007 DimXpert Phase-A helper compile failed")
    for dll in (sw,const,dx):
        dst=bindir/Path(dll).name
        if not dst.exists():shutil.copy2(dll,dst)
    return exe
def run_backend(root,rel,timeout=240):
    p=root/rel
    if not p.is_file():return None
    cp=subprocess.run([sys.executable,str(p),"--repo-root",str(root)],cwd=str(root),capture_output=True,text=True,errors="replace",timeout=timeout)
    if cp.stdout:print(cp.stdout,end="")
    if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
    return cp.returncode

def write_text_atomic(p,text):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(text,encoding="utf-8");os.replace(str(t),str(p))

def build_phase_b_workpack(root,rep,rr):
    optional=rep.get("optional_native_pmi") or {}
    nc=(rr.get("nominal_counts") or {})
    wp={
      "schema":"k01.d006.p007.phase_b_workpack.v1",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":"READY_FOR_ADVANCED_PMI_AND_PROFESSIONAL_DRAWING_CANDIDATE",
      "source_phase_a_report":str(OUT).replace("\\","/"),
      "candidate":rep.get("candidate"),
      "canonical_p007":rep.get("canonical_p007"),
      "geometry_invariant":True,
      "phase_a_native_pmi":{
        "C02_locator_nominal_14p10":"PASS",
        "C05_flange_od_33":"PASS",
        "C04_hole_diameter_2p90":"PASS" if optional.get("C04_hole_diameter_2p90") else "NOT_PRESENT_OPTIONAL",
        "C06_oal_35":"PASS" if optional.get("C06_OAL_35") else "NOT_PRESENT_OPTIONAL",
        "C05_flange_thickness_3":"PASS" if optional.get("C05_flange_thickness_3") else "NOT_PRESENT_OPTIONAL"
      },
      "next_characteristics":{
        "C01":{"state":"NEXT_NATIVE_AUTHORING","definition":"Composite coplanar Datum A on mating face set"},
        "C02":{"state":"NOMINAL_NATIVE_PASS_RELEASE_SEMANTICS_PARTIAL","definition":"Ø14.10 locator; H7 architecture controlled; depth nominal 2.00, depth tolerance OPEN"},
        "C03":{"state":"OPEN_UNTIL_CONTROLLED_VALUE_CONFIRMED","definition":"Perpendicularity / orientation relative to Datum A"},
        "C04":{"state":"PARTIAL" if optional.get("C04_hole_diameter_2p90") else "NEXT_NATIVE_AUTHORING",
               "definition":"3×Ø2.90 on PCD26.50; pattern/basic/position semantics not yet released"},
        "C05":{"state":"NOMINAL_NATIVE_PASS_RELEASE_TOLERANCE_OPEN","definition":"Ø33 flange and thickness 3.00"},
        "C06":{"state":"PARTIAL" if optional.get("C06_OAL_35") else "NEXT_NATIVE_AUTHORING","definition":"Overall length 35.00; release tolerance OPEN"},
        "C07":{"state":"OPEN","definition":"Thin-wall OD tolerance"},
        "C08":{"state":"OPEN","definition":"Thin-wall ID / wall-thickness tolerance"},
        "C09":{"state":"CONTROLLED_NOTE","definition":"Material AISI 316L / EN 1.4404"},
        "C10":{"state":"OPEN","definition":"Containment joining process / weld-or-adhesive applicability"},
        "C11":{"state":"OPEN","definition":"Coaxiality/concentricity requirement and tolerance"},
        "C12":{"state":"OPEN","definition":"Quantitative leak / containment acceptance"},
        "BLIND_END":{"state":"OPEN","definition":"Blind-end released thickness/tolerance/inspection requirement"}
      },
      "drawing_candidate_policy":{
        "allowed":"Build K01-D-006 professional candidate with OPEN characteristics explicitly identified",
        "forbidden":"Do not claim manufacturing release, do not invent tolerance/GD&T/process/leak values",
        "required_views":["primary orthographic views","section through thin can and blind end","detail of J2 locator/flange interface"],
        "required_notes":["material AISI 316L / EN 1.4404","candidate/not released boundary","OPEN characteristic table"],
        "qa":["native PMI semantic lint","save-close-reopen model link","visual QA","inspection characteristic traceability"]
      },
      "center_projection":{
        "current_stage":"P007 Phase-A native PMI PASS",
        "next_stage":"Advanced PMI + K01-D-006 professional candidate",
        "release":"R01 NOT RELEASED"
      }
    }
    write(root/PHASE_B,wp)
    lines=[
      "# K01-D-006 / P007 — Phase-B workpack",
      "",
      "**Status:** READY_FOR_ADVANCED_PMI_AND_PROFESSIONAL_DRAWING_CANDIDATE",
      "",
      "Phase A has established native candidate PMI for C02 and C05 with save-close-reopen semantic proof and invariant geometry.",
      "",
      "## Next",
      "- C01: native Datum A representation.",
      "- C04/C06/C05-thickness: retain if Phase A created them; otherwise author next.",
      "- C09: controlled material note AISI 316L / EN 1.4404.",
      "- Build a new K01-D-006 candidate derived from native PMI.",
      "- Add section/detail views for thin can, blind end, and J2 locator interface.",
      "",
      "## Do not release yet",
      "- C03 perpendicularity value if not already controlled.",
      "- C07/C08 thin-wall tolerances.",
      "- C10 containment joining process.",
      "- C11 coaxiality/concentricity.",
      "- C12 quantitative leak acceptance.",
      "- blind-end released tolerance / inspection acceptance.",
      "",
      "These stay explicitly OPEN; no value may be invented to make the drawing look complete.",
    ]
    write_text_atomic(root/PHASE_B_MD,"\n".join(lines)+"\n")
    return wp

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    rep={"schema":"k01.p007.dimxpert.phase_a.v1","generated_utc":datetime.now(timezone.utc).isoformat(),
         "status":"RUNNING","canonical_native_CAD_mutated":False,"candidate_native_CAD_mutated":False}
    candidate=None
    try:
        rb=load(root/REBIND);st=load(root/STEP)
        need(rb.get("status")=="PASS_P007_CANONICAL_PERSISTENT_REFS_REBOUND_READY_FOR_NATIVE_PMI","P007 canonical persistent rebind is not PASS")
        need(str(st.get("status") or "").startswith("PASS_TO_P007_NATIVE_DIMXPERT_CANDIDATE_WRITE"),"P007 native DimXpert write gate is not PASS")
        need(P007.is_file(),"canonical P007 missing")
        canonical_sha=sha(P007)
        need(canonical_sha==str((rb.get("canonical_p007") or {}).get("sha256") or ""),"canonical P007 SHA changed after rebind")
        need(not sw_running(),"SolidWorks process is running. Close SolidWorks before candidate PMI authoring.")

        # Regression anchor: the same workstation previously created C02/C05 successfully in Step13.
        historical={}
        hp=root/HIST_STEP13_REPORT
        if hp.is_file():
            try:
                h=load(hp)
                historical["report"]=str(hp)
                historical["status"]=h.get("status")
                historical["C02"]=h.get("C02")
                historical["C05"]=h.get("C05")
                historical["reopen_readback"]=h.get("reopen_readback")
            except Exception as ex:
                historical["report_read_error"]=repr(ex)
        if HIST_STEP13_SCRIPT.is_file():
            historical["script"]=str(HIST_STEP13_SCRIPT)
            historical["script_sha256"]=sha(HIST_STEP13_SCRIPT)
        rep["historical_step13_regression_anchor"]=historical
        write(root/OUT,rep)

        # Compile before creating a candidate: compiler/API failures cannot create a partial CAD artifact.
        exe=compile_helper(root)

        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        cdir=CAND_ROOT/("cp_p_"+stamp);cdir.mkdir(parents=True,exist_ok=False)
        candidate=cdir/"K01-P-007_Hermetic_Magnetic_Can_PMI_CP_P_CANDIDATE.SLDPRT"
        shutil.copy2(P007,candidate)
        need(sha(candidate)==canonical_sha,"fresh candidate copy is not byte-identical to canonical source")

        raw=cdir/"K01_P007_DIMXPERT_PHASE_A_RAW.json";log=cdir/"K01_P007_DIMXPERT_PHASE_A.log"
        cp=subprocess.run([str(exe),"--part",str(candidate),"--out",str(raw),"--log",str(log)],
                          cwd=str(root),capture_output=True,text=True,errors="replace",timeout=420)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        if raw.is_file():
            try:
                rep["raw_failure_or_pass"]=load(raw)
                write(root/OUT,rep)
            except Exception:
                pass
        need(cp.returncode==0,"P007 DimXpert Phase-A helper failed")
        need(raw.is_file(),"P007 DimXpert Phase-A raw report missing")
        rr=load(raw)
        need(str(rr.get("status") or "").startswith("PASS_PHASE_A_"),"P007 DimXpert Phase-A raw status is not PASS")
        need(rr.get("geometry_invariant") is True,"P007 candidate geometry changed during PMI authoring")
        nc=rr.get("nominal_counts") or {}
        need(int(nc.get("C02_14p10",-1))==1,"C02 Ø14.10 semantic reopen count !=1")
        need(int(nc.get("C05_OD_33",-1))==1,"C05 Ø33 semantic reopen count !=1")
        pres=rr.get("persistent_resolution_after_reopen") or {}
        for cid in ("C02","C05"):
            x=pres.get(cid) or {}
            need(x.get("resolved") is True and int(x.get("state",-1))==0,cid+" annotation persistent reference did not resolve after reopen")
        need(sha(P007)==canonical_sha,"canonical P007 changed during candidate-only PMI authoring")

        candidate_sha=sha(candidate)
        rep.update({
          "status":"PASS_P007_NATIVE_DIMXPERT_PHASE_A_SAVE_CLOSE_REOPEN",
          "candidate_native_CAD_mutated":True,
          "canonical_p007":{"path":str(P007),"sha256":canonical_sha},
          "candidate":{"path":str(candidate),"sha256":candidate_sha,"directory":str(cdir)},
          "raw_report":str(raw),"log":str(log),
          "geometry_fingerprint":rr.get("geometry_fingerprint_after_reopen"),
          "semantic_reopen":{
            "annotation_count":rr.get("annotation_count_after"),
            "nominal_counts":nc,
            "persistent_resolution":pres
          },
          "required_native_pmi":["C02 locator nominal Ø14.10","C05 flange OD nominal Ø33.00"],
          "optional_native_pmi":{
            "C04_hole_diameter_2p90":int(nc.get("C04_hole_2p90",0))>=1,
            "C06_OAL_35":int(nc.get("C06_OAL_35",0))>=1,
            "C05_flange_thickness_3":int(nc.get("C05_thickness_3",0))>=1
          },
          "release_boundary":rr.get("release_boundary") or [],
          "next":"ADVANCED_PMI_AND_K01_D006_CANDIDATE"
        })
        write(root/OUT,rep)

        old=load(root/EVIDENCE)
        ev={
          "schema":"k01.p007.pmi_write_evidence.v2",
          "generated_utc":datetime.now(timezone.utc).isoformat(),
          "status":"PASS_CANONICAL_PHASE_A_SAVE_CLOSE_REOPEN",
          "scope":["C02 locator nominal diameter 14.10","C05 flange OD nominal 33.00"],
          "optional_scope":{
            "C04_hole_diameter_2p90":rep["optional_native_pmi"]["C04_hole_diameter_2p90"],
            "C06_OAL_35":rep["optional_native_pmi"]["C06_OAL_35"],
            "C05_flange_thickness_3":rep["optional_native_pmi"]["C05_flange_thickness_3"]
          },
          "source_authority_part":str(P007),"source_authority_sha256":canonical_sha,
          "candidate_part":str(candidate),"candidate_file_sha256":candidate_sha,
          "geometry_invariant":True,"saved":True,
          "reopen_readback":rep["semantic_reopen"],
          "api_return_policy":"InsertSizeDimension/InsertLocationDimension boolean is diagnostic only; save-close-reopen semantic readback is acceptance authority.",
          "historical_pilot":old,
          "not_released_by_this_evidence":["C01 composite Datum-A native representation","C02 H7 fit-code write",
            "C03 perpendicularity","C04 pattern position/basic semantics","C05 released tolerance semantics",
            "C07","C08","C10","C11","C12","blind-end released tolerance/inspection"]
        }
        write(root/EVIDENCE,ev)

        scope=load(root/SCOPE)
        scope["generated_utc"]=datetime.now(timezone.utc).isoformat()
        scope["status"]="PASS_PHASE_A_READY_FOR_ADVANCED_PMI_AND_DRAWING_CANDIDATE"
        scope["phase_a_report"]=str(OUT).replace("\\","/")
        scope["phase_a_candidate"]={"path":str(candidate),"sha256":candidate_sha}
        scope["phase_a_required_pass"]=["C02","C05"]
        scope["phase_a_optional_results"]=rep["optional_native_pmi"]
        scope["next_step"]="ADVANCED_PMI_REVIEW_THEN_K01_D006_DERIVED_CANDIDATE"
        write(root/SCOPE,scope)

        nxt=load(root/NEXT)
        nxt["current_stage"]="P007_NATIVE_DIMXPERT_PHASE_A_PASS_READY_FOR_ADVANCED_PMI_AND_D006"
        nxt["last_completed"]="Timestamped P007 candidate contains native DimXpert C02 Ø14.10 and C05 Ø33.00, survived save-close-reopen, persistent annotation IDs resolved, and geometry remained invariant. Canonical P007 remained unchanged."
        nxt["last_evidence"]=[str(OUT).replace("\\","/"),str(raw),str(EVIDENCE).replace("\\","/")]
        nxt["current_blocker"]="Advanced PMI must not invent unreleased tolerances/GD&T. Author only evidence-supported semantics; then derive K01-D-006 with explicit OPEN callouts."
        nxt["next_1"]="Review Phase-A semantic readback and retain successful optional C04/C06/C05-thickness PMI if present."
        nxt["next_2"]="Author only approved advanced PMI semantics and/or proceed to K01-D-006 candidate with OPEN release characteristics explicitly identified."
        nxt["then"]="Drawing semantic lint + visual QA + inspection characteristic linkage + P007 structural/buckling evidence."
        write(root/NEXT,nxt)

        active={
          "schema":"k01.active_step_gate.v1",
          "step_id":"K01-STEP-P4-P007-ADVANCED-PMI-D006-CANDIDATE",
          "active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION",
          "checkpoint_id":"K01-CP-20260910-BASELINE-02C-PROMOTED",
          "intent":"REVIEW_PHASE_A_NATIVE_PMI_AND_BUILD_PROFESSIONAL_K01_D006_CANDIDATE_WITH_OPEN_ITEMS_EXPLICIT",
          "mutation_authorized":True,
          "result_on_pass":"PASS_TO_P007_ADVANCED_PMI_AND_D006_CANDIDATE",
          "required_files":[str(OUT).replace("\\","/"),str(EVIDENCE).replace("\\","/"),
                            "control/drawings/K01_D006_AUTHORING_INPUT.json",
                            "control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json",
                            "reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json"],
          "required_statuses":[
            {"file":str(OUT).replace("\\","/"),"path":["status"],"allowed_values":["PASS_P007_NATIVE_DIMXPERT_PHASE_A_SAVE_CLOSE_REOPEN"]},
            {"file":str(EVIDENCE).replace("\\","/"),"path":["status"],"allowed_values":["PASS_CANONICAL_PHASE_A_SAVE_CLOSE_REOPEN"]},
            {"file":"reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json","path":["status"],"allowed_prefixes":["PASS"]}],
          "impact_declarations":{
            "requirements":"No OPEN release values may be converted to released drawing tolerances.",
            "materials":"P007 remains AISI 316L / EN 1.4404; C09 is controlled product data.",
            "bom":"No quantity or geometry change authorized.",
            "dimxpert_drawings":"Phase-A PMI is candidate evidence. K01-D-006 may show OPEN characteristics explicitly but cannot claim production release.",
            "inspection":"Generate traceability rows only for controlled characteristics; OPEN acceptance stays OPEN.",
            "dependencies":"Any geometry change is a hard HOLD and invalidates Phase-A evidence.",
            "technical_filter":"P007/D006 manufacturing, tolerance, inspection and containment categories remain explicit.",
            "rollback":"Reject timestamped PMI candidate if advanced authoring/drawing QA fails; canonical P007 is untouched.",
            "evidence":"Native candidate + semantic reopen + persistent IDs + geometry fingerprint + drawing semantic/visual QA."}}
        write(root/ACTIVE,active)

        # Prepare the next engineering step in parallel from the verified Phase-A evidence.
        phase_b=build_phase_b_workpack(root,rep,rr)
        rep["phase_b_workpack"]=str(PHASE_B).replace("\\","/")
        rep["phase_b_status"]=phase_b.get("status")
        write(root/OUT,rep)

        # Keep Center state current in THIS engineering branch as a materialized view.
        # The other Center branch may improve UX, but it must consume these same authorities/feeds.
        run_backend(root,"tools/medtas/rebuild_medtas_state.py",300)
        run_backend(root,"tools/medtas/technical_filter_map_v2_2.py",180)
        run_backend(root,"tools/assurance/engineering_step_gate.py",180)
        run_backend(root,"tools/assurance/build_engineering_dashboard.py",180)

        print("STATUS:",rep["status"])
        print("CANDIDATE:",candidate)
        print("CANDIDATE SHA256:",candidate_sha)
        print("C02 Ø14.10 reopen count:",nc.get("C02_14p10"))
        print("C05 Ø33.00 reopen count:",nc.get("C05_OD_33"))
        print("OPTIONAL:",rep["optional_native_pmi"])
        print("CANONICAL P007 unchanged:",canonical_sha)
        print("PHASE-B WORKPACK:",root/PHASE_B);print("NEXT: advanced PMI review -> K01-D-006 professional candidate")
        print("REPORT:",root/OUT)
        return 0
    except Exception as e:
        rep["status"]="HOLD_P007_DIMXPERT_PHASE_A"
        rep["error"]=repr(e)
        if candidate is not None:rep["candidate_path"]=str(candidate)
        write(root/OUT,rep)
        # Keep the existing Center/materialized view current even on HOLD.
        # Engineering control/evidence remains the authority.
        try:
            run_backend(root,"tools/medtas/rebuild_medtas_state.py",300)
            run_backend(root,"tools/medtas/technical_filter_map_v2_2.py",180)
            run_backend(root,"tools/assurance/engineering_step_gate.py",180)
            run_backend(root,"tools/assurance/build_engineering_dashboard.py",180)
        except Exception:
            pass
        print("STATUS:",rep["status"]);print("ERROR:",repr(e));print("REPORT:",root/OUT)
        return 2

if __name__=="__main__": raise SystemExit(main())
