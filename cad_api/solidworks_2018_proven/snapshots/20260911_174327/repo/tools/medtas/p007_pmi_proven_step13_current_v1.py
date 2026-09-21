#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

REBIND=Path("reports/control/K01_P007_CANONICAL_PERSISTENT_REBIND_CURRENT.json")
REBIND_RAW=Path("reports/cad/p007_pmi_authoring/K01_P007_CANONICAL_PERSISTENT_REBIND_RAW.json")
STEP=Path("reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json")
SCOPE=Path("control/product_definition/K01_P007_PMI_AUTHORING_SCOPE.json")
PC=Path("control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json")
EVIDENCE=Path("control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
ACTIVE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
OUT=Path("reports/control/K01_P007_PMI_PROVEN_CURRENT.json")
CORE_MANIFEST=Path("reports/control/K01_P007_PMI_PROVEN_CORE_MANIFEST_CURRENT.json")
PHASE_B=Path("reports/drawing/current/K01-D-006_P007_PHASE_B_WORKPACK_CURRENT.json")
PHASE_B_MD=Path("reports/drawing/current/K01-D-006_P007_PHASE_B_WORKPACK_CURRENT.md")
PROVEN_MANIFEST=Path("reports/control/K01_SOLIDWORKS_PROVEN_MANIFEST_CURRENT.json")
REGISTRY=Path("cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json")

DEFAULT_EXTERNAL_ROOT=Path(r"D:\BreshevEngineering\Additional\k01_step13_integrated")
EXTERNAL_WRITER_REL=Path("payload/tools/engineering/run_p007_pmi_step13.py")
EXTERNAL_CORE_REL=Path("payload/cad_api/p007_pmi/K01P007PmiStep13.cs")
CONTROLLED_CORE_DIR=Path("cad_api/solidworks_2018_proven/current/P007_DIMXPERT_WRITE_C02_C05")

def load(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");os.replace(str(t),str(p))
def write_text(p,s):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(s,encoding="utf-8");os.replace(str(t),str(p))
def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def run(c,cwd=None,timeout=420):
    return subprocess.run(c,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)
def sw_running():
    try:
        cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30)
        if "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower(): return True
    except: pass
    try:
        cp=run(["powershell","-NoProfile","-Command",
                "if (Get-Process SLDWORKS -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"],timeout=30)
        return cp.returncode==0
    except:return False
def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in [w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"]:
        if p.exists(): return p
    raise RuntimeError("csc.exe missing")
def redist():
    candidates=[]
    for k in ("ProgramFiles","ProgramFiles(x86)"):
        b=os.environ.get(k)
        if b:candidates.append(Path(b)/"SOLIDWORKS Corp/SOLIDWORKS/api/redist")
    candidates.append(Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"))
    for p in candidates:
        if (p/"SolidWorks.Interop.sldworks.dll").exists(): return p
    raise RuntimeError("SOLIDWORKS 2018 api/redist missing")
def frozen_writer_expected_sha(root):
    p=root/PROVEN_MANIFEST
    if not p.is_file(): return None
    try:
        m=load(p)
        for x in m.get("assets",[]) or []:
            if x.get("role")=="PROVEN_EXTERNAL_STEP13_WRITER":
                return x.get("sha256")
    except: return None
    return None
def binding_from_scope(scope,cid):
    for x in scope.get("safe_authoring_scope",[]) or []:
        if x.get("id")==cid:
            return x.get("solidworks_binding") or {}
    return {}
def binding_from_pc(pc,cid):
    for x in pc.get("characteristics",[]) or []:
        if x.get("id")==cid:
            return x.get("solidworks_binding") or {}
    return {}
def binding_from_raw(raw,cid):
    return ((raw.get("bindings") or {}).get(cid) or {})

def _num(v):
    try:return float(v)
    except:return None

def pick_persist_ref(binding,cid,expected_surface=None,expected_radius_mm=None):
    ents=binding.get("entities") or []
    candidates=[]
    for e in ents:
        ref=e.get("persist_ref_b64")
        if not ref: continue
        if expected_surface and str(e.get("surface_type") or "").lower()!=expected_surface.lower():
            continue
        if expected_radius_mm is not None:
            r=_num(e.get("radius_mm"))
            if r is None or abs(r-expected_radius_mm)>0.01:
                continue
        candidates.append(e)
    if len(candidates)!=1:
        raise RuntimeError(
            f"{cid} persistent-ref selection is not unique: "
            f"binding_type={binding.get('binding_type')} entities={len(ents)} matched={len(candidates)} "
            f"expected_surface={expected_surface} expected_radius_mm={expected_radius_mm}"
        )
    e=candidates[0]
    return e["persist_ref_b64"], {
        "binding_type":binding.get("binding_type"),
        "entity_count":len(ents),
        "selected_surface_type":e.get("surface_type"),
        "selected_radius_mm":e.get("radius_mm"),
        "selected_runtime_face_index":e.get("runtime_face_index")
    }

def resolve_current_ref(raw,pc,scope,cid,expected_surface,expected_radius_mm):
    # Direct raw output from the already-PASSed canonical rebind is first authority for
    # persistent IDs. Product-characteristic/scope copies are controlled fallbacks.
    sources=[
        ("REBIND_RAW",binding_from_raw(raw,cid)),
        ("PRODUCT_CHARACTERISTICS",binding_from_pc(pc,cid)),
        ("PMI_AUTHORING_SCOPE",binding_from_scope(scope,cid)),
    ]
    errors=[]
    for source,binding in sources:
        if not binding: continue
        try:
            ref,meta=pick_persist_ref(binding,cid,expected_surface,expected_radius_mm)
            meta["source"]=source
            return ref,meta
        except Exception as ex:
            errors.append(source+":"+repr(ex))
    raise RuntimeError(cid+" current persistent ref unavailable after deterministic binding selection; "+" | ".join(errors))

def refresh(root):
    for rel,to in [
        ("tools/medtas/rebuild_medtas_state.py",300),
        ("tools/medtas/technical_filter_map_v2_2.py",180),
        ("tools/assurance/engineering_step_gate.py",180),
        ("tools/assurance/build_engineering_dashboard.py",180),
    ]:
        p=root/rel
        if not p.is_file(): continue
        cp=run([sys.executable,str(p),"--repo-root",str(root)],cwd=root,timeout=to)
        if cp.stdout: print(cp.stdout,end="")
        if cp.stderr: print(cp.stderr,end="",file=sys.stderr)
def import_proven_core(root,external_root):
    writer=external_root/EXTERNAL_WRITER_REL
    core=external_root/EXTERNAL_CORE_REL
    need(writer.is_file(),"proven Step13 Python writer missing: "+str(writer))
    need(core.is_file(),"transitive proven Step13 C# core missing: "+str(core))
    expected=frozen_writer_expected_sha(root)
    actual_writer_sha=sha(writer)
    if expected:
        need(actual_writer_sha.lower()==str(expected).lower(),
             "external Step13 writer hash differs from frozen proven manifest")
    dst=root/CONTROLLED_CORE_DIR
    dst.mkdir(parents=True,exist_ok=True)
    writer_copy=dst/"run_p007_pmi_step13_PROVEN_FROZEN.py"
    core_copy=dst/"K01P007PmiStep13_PROVEN_FROZEN.cs"
    shutil.copy2(writer,writer_copy);shutil.copy2(core,core_copy)
    need(sha(writer_copy)==actual_writer_sha,"controlled writer copy hash mismatch")
    need(sha(core_copy)==sha(core),"controlled C# core copy hash mismatch")
    m={
      "schema":"k01.p007.pmi.proven_core_import.v1",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":"PASS_PROVEN_CORE_IMPORTED",
      "copy_only":True,"external_package_root":str(external_root),
      "historical_writer":{"source":str(writer),"controlled_copy":str(writer_copy),"sha256":sha(writer_copy)},
      "historical_csharp_core":{"source":str(core),"controlled_copy":str(core_copy),"sha256":sha(core_copy)},
      "rule":"The C# core is copied byte-for-byte and compiled unchanged. Only the outer current-state adapter is new."
    }
    write(root/CORE_MANIFEST,m)
    return writer_copy,core_copy,m
def compile_core(root,core_copy):
    rd=redist()
    refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll",rd/"SolidWorks.Interop.swdimxpert.dll"]
    for p in refs: need(p.is_file(),"missing interop "+str(p))
    build=root/"reports/cad/p007_pmi_proven_current/build";build.mkdir(parents=True,exist_ok=True)
    exe=build/"K01P007PmiStep13_PROVEN_CURRENT.exe"
    cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]
           +["/reference:"+str(x) for x in refs]+[str(core_copy)],cwd=root)
    if cp.stdout: print(cp.stdout,end="")
    if cp.stderr: print(cp.stderr,end="",file=sys.stderr)
    need(cp.returncode==0,"exact proven Step13 C# core failed to compile on current workstation")
    for p in refs: shutil.copy2(p,build/p.name)
    for n in ("SolidWorks.Interop.swpublished.dll","SolidWorks.Interop.swcommands.dll"):
        p=rd/n
        if p.is_file(): shutil.copy2(p,build/p.name)
    return exe
def phase_b(root,result,candidate,candidate_sha,canonical):
    wp={
      "schema":"k01.d006.p007.phase_b_workpack.v2",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":"READY_FOR_K01_D006_PROFESSIONAL_CANDIDATE_AFTER_PROVEN_PMI",
      "source_pmi_report":str(OUT).replace("\\","/"),
      "candidate":{"path":str(candidate),"sha256":candidate_sha},
      "canonical_p007":canonical,
      "verified_now":{
        "C02":"native DimXpert size nominal 14.10; semantic PASS; persist reopen state 0",
        "C05":"native DimXpert size nominal 33.00; semantic PASS; persist reopen state 0",
        "geometry_invariant":True
      },
      "next_characteristics":{
        "C01":"NEXT_NATIVE_DATUM_A_OR_DRAWING_DATUM_SYMBOL",
        "C03":"OPEN_UNTIL_CONTROLLED_VALUE_CONFIRMED",
        "C04":"NEXT_PATTERN_SEMANTICS; 3xØ2.90 PCD26.50 geometry already controlled",
        "C05":"NOMINAL_PMI_PASS; RELEASE_TOLERANCE_OPEN",
        "C06":"NEXT_OAL_35_SEMANTICS; RELEASE_TOLERANCE_OPEN",
        "C09":"CONTROLLED_MATERIAL_NOTE_AISI_316L_EN_1_4404",
        "C07":"OPEN_THIN_WALL_OD_TOLERANCE",
        "C08":"OPEN_THIN_WALL_ID_WALL_TOLERANCE",
        "C10":"OPEN_CONTAINMENT_JOINING_PROCESS",
        "C11":"OPEN_COAXIALITY",
        "C12":"OPEN_QUANTITATIVE_LEAK_ACCEPTANCE",
        "BLIND_END":"OPEN_RELEASE_TOLERANCE_AND_INSPECTION"
      },
      "drawing_policy":{
        "allowed":"professional candidate drawing with OPEN characteristics explicitly shown in workpack",
        "forbidden":"invent release tolerances/GD&T/process/leak values",
        "required_views":["main orthographic","section through thin can/blind end","J2 locator/flange detail"],
        "required_qa":["model link","native PMI readback","semantic lint","visual QA","inspection traceability"]
      }
    }
    write(root/PHASE_B,wp)
    md=f"""# K01-D-006 / P007 — Phase-B workpack

**Status:** READY_FOR_K01_D006_PROFESSIONAL_CANDIDATE_AFTER_PROVEN_PMI

## Proven now
- C02: native DimXpert nominal Ø14.10 — PASS.
- C05: native DimXpert nominal Ø33.00 — PASS.
- Save / close / reopen — PASS.
- C02/C05 persistent states — 0/0.
- Solid geometry fingerprint — invariant.
- Canonical P007 — unchanged.

## Next drawing/product-definition work
- C01 Datum A representation.
- C04 3×Ø2.90 / PCD26.50 pattern semantics.
- C06 OAL 35.00 semantics.
- C09 material AISI 316L / EN 1.4404.
- Build K01-D-006 professional candidate with section/detail views.

## Explicit OPEN — do not invent
C03, C07, C08, C10, C11, C12 and blind-end released tolerance/inspection acceptance.
"""
    write_text(root/PHASE_B_MD,md)
    return wp

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",required=True)
    ap.add_argument("--external-package-root",default=str(DEFAULT_EXTERNAL_ROOT))
    a=ap.parse_args()
    root=Path(a.repo_root).resolve();external=Path(a.external_package_root)
    rep={"schema":"k01.p007.pmi.proven_step13_current.v1","generated_utc":datetime.now(timezone.utc).isoformat(),
         "status":"RUNNING","canonical_native_CAD_mutated":False,"adapter_policy":"PROVEN_CORE_REUSE"}
    candidate=None
    try:
        need(not sw_running(),"SolidWorks process is running; close it before proven PMI write")
        rb=load(root/REBIND)
        need(rb.get("status")=="PASS_P007_CANONICAL_PERSISTENT_REFS_REBOUND_READY_FOR_NATIVE_PMI",
             "current P007 persistent rebind is not PASS")
        canonical=rb.get("canonical_p007") or {}
        src=Path(str(canonical.get("path") or ""))
        expected_sha=str(canonical.get("sha256") or "")
        need(src.is_file(),"canonical P007 missing: "+str(src))
        need(sha(src)==expected_sha,"canonical P007 hash changed after rebind")

        st=load(root/STEP)
        need(str(st.get("status") or "").startswith("PASS_TO_P007_NATIVE_DIMXPERT_CANDIDATE_WRITE"),
             "current engineering step gate does not authorize P007 native PMI candidate write")

        scope=load(root/SCOPE);pc=load(root/PC)
        need((root/REBIND_RAW).is_file(),"direct canonical rebind raw report missing: "+str(root/REBIND_RAW))
        raw_rebind=load(root/REBIND_RAW)
        need(raw_rebind.get("status")=="PASS","direct canonical rebind raw report is not PASS")
        need(raw_rebind.get("sha256_before")==expected_sha and raw_rebind.get("sha256_after")==expected_sha,
             "direct canonical rebind raw report does not match current canonical P007 SHA")

        # C02 is one Ø14.10 locator cylinder (R=7.05).
        # C05 is intentionally a composite binding: Ø33 OD cylinder + axial face set.
        # The proven Step13 core needs the Ø33 cylindrical face ref, not the whole composite.
        r02,r02_meta=resolve_current_ref(raw_rebind,pc,scope,"C02","cylinder",7.05)
        r05,r05_meta=resolve_current_ref(raw_rebind,pc,scope,"C05","cylinder",16.50)
        rep["binding_resolution"]={"C02":r02_meta,"C05":r05_meta}
        write(root/OUT,rep)
        print("C02 REF:",r02_meta)
        print("C05 REF:",r05_meta)

        writer_copy,core_copy,corem=import_proven_core(root,external)
        exe=compile_core(root,core_copy)
        print("PROVEN CORE COMPILE: PASS")
        print("PROVEN C# CORE SHA256:",corem["historical_csharp_core"]["sha256"])

        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        cdir=Path(r"D:\Marvilon\K01\cad\candidates\p007_pmi_authoring")/("proven_step13_current_"+stamp)
        cdir.mkdir(parents=True,exist_ok=False)
        candidate=cdir/"K01-P-007_Hermetic_Magnetic_Can_PMI_PROVEN_CURRENT_CANDIDATE.SLDPRT"
        shutil.copy2(src,candidate)
        need(sha(candidate)==expected_sha,"candidate copy mismatch")

        work=root/"reports/cad/p007_pmi_proven_current";work.mkdir(parents=True,exist_ok=True)
        manifest=work/"K01_P007_PMI_PROVEN_MANIFEST_CURRENT.txt"
        manifest.write_text("C02_REF="+r02+"\nC05_REF="+r05+"\n",encoding="utf-8")
        raw=work/"K01_P007_PMI_PROVEN_NATIVE_CURRENT.json"
        cp=run([str(exe),"--part",str(candidate),"--manifest",str(manifest),"--output",str(raw)],cwd=root,timeout=420)
        if cp.stdout: print(cp.stdout,end="")
        if cp.stderr: print(cp.stderr,end="",file=sys.stderr)
        need(cp.returncode==0,"proven Step13 C# core returned HOLD")
        need(raw.is_file(),"proven Step13 current native report missing")
        o=load(raw)

        need(str(o.get("status") or "").startswith("PASS_PMI_SAVE_REOPEN"),
             "proven core output status is not PASS")
        need((o.get("C02") or {}).get("semantic_pass") is True,"C02 semantic PASS missing")
        need((o.get("C05") or {}).get("semantic_pass") is True,"C05 semantic PASS missing")
        need(o.get("geometry_invariant") is True,"PMI changed solid geometry")
        rr=o.get("reopen_readback") or {}
        need(rr.get("pass") is True,"save-close-reopen readback not PASS")
        need(int(rr.get("C02_nominal_match_count",-1))==1,"C02 reopen match count !=1")
        need(int(rr.get("C05_nominal_match_count",-1))==1,"C05 reopen match count !=1")
        need(int(rr.get("C02_persist_state",-1))==0,"C02 persistent state !=0")
        need(int(rr.get("C05_persist_state",-1))==0,"C05 persistent state !=0")
        need(sha(src)==expected_sha,"canonical P007 changed during candidate PMI write")

        csha=sha(candidate)
        rep.update({
          "status":"PASS_P007_CURRENT_CANONICAL_PMI_C02_C05_PROVEN_STEP13_CORE",
          "canonical_p007":{"path":str(src),"sha256":expected_sha},
          "candidate":{"path":str(candidate),"sha256":csha},
          "proven_core_manifest":str(root/CORE_MANIFEST),
          "proven_writer_copy":str(writer_copy),
          "proven_csharp_core_copy":str(core_copy),
          "proven_csharp_core_sha256":corem["historical_csharp_core"]["sha256"],
          "binding_resolution":{"C02":r02_meta,"C05":r05_meta},
          "native_report":str(raw),
          "C02":o.get("C02"),"C05":o.get("C05"),
          "geometry_invariant":True,"reopen_readback":rr,
          "next":"K01_D006_PROFESSIONAL_CANDIDATE"
        })
        write(root/OUT,rep)

        prior=load(root/EVIDENCE) if (root/EVIDENCE).is_file() else None
        ev={
          "schema":"k01.p007.pmi_write_evidence.v3",
          "generated_utc":datetime.now(timezone.utc).isoformat(),
          "status":"PASS_CURRENT_CANONICAL_PMI_C02_C05_SAVE_CLOSE_REOPEN",
          "source_authority_part":str(src),"source_authority_sha256":expected_sha,
          "candidate_part":str(candidate),"candidate_file_sha256":csha,
          "proven_core_sha256":corem["historical_csharp_core"]["sha256"],
          "C02":o.get("C02"),"C05":o.get("C05"),
          "geometry_invariant":True,"reopen_readback":rr,
          "release_scope":"CANDIDATE_NATIVE_PMI_C02_C05_ONLY_NOT_R01_RELEASE",
          "prior_evidence":prior
        }
        write(root/EVIDENCE,ev)

        scope["generated_utc"]=datetime.now(timezone.utc).isoformat()
        scope["status"]="PASS_CURRENT_CANONICAL_PMI_C02_C05_READY_FOR_D006"
        scope["current_proven_pmi_report"]=str(OUT).replace("\\","/")
        scope["current_proven_candidate"]={"path":str(candidate),"sha256":csha}
        scope["next_step"]="K01_D006_PROFESSIONAL_CANDIDATE_PLUS_CONTROLLED_ADVANCED_PMI"
        write(root/SCOPE,scope)

        wp=phase_b(root,o,candidate,csha,{"path":str(src),"sha256":expected_sha})

        nxt=load(root/NEXT)
        nxt["current_stage"]="P007_CURRENT_CANONICAL_NATIVE_PMI_C02_C05_PASS_READY_FOR_K01_D006"
        nxt["last_completed"]="Current canonical P007 C02/C05 native DimXpert PMI was written using the unchanged proven Step13 C# core, then save-close-reopen verified with persistent states 0/0 and invariant solid geometry."
        nxt["last_evidence"]=[str(OUT).replace("\\","/"),str(raw),str(CORE_MANIFEST).replace("\\","/"),str(PHASE_B).replace("\\","/")]
        nxt["current_blocker"]="Professional K01-D-006 candidate must now be built without inventing unresolved C03/C07/C08/C10/C11/C12/blind-end release values."
        nxt["next_1"]="Build K01-D-006 professional candidate using proven C02/C05 PMI plus controlled C01/C04/C06/C09 content."
        nxt["next_2"]="Run drawing semantic lint, visual QA and inspection-characteristic traceability."
        nxt["then"]="Refresh P007 structural/buckling evidence and assemble final design-review dossier."
        write(root/NEXT,nxt)

        active={
          "schema":"k01.active_step_gate.v1",
          "step_id":"K01-STEP-P4-K01-D006-PROFESSIONAL-CANDIDATE",
          "active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION",
          "checkpoint_id":"K01-CP-20260910-BASELINE-02C-PROMOTED",
          "intent":"BUILD_K01_D006_PROFESSIONAL_CANDIDATE_FROM_PROVEN_NATIVE_PMI_AND_CONTROLLED_OPEN_ITEMS",
          "mutation_authorized":True,
          "result_on_pass":"PASS_TO_K01_D006_PROFESSIONAL_CANDIDATE",
          "required_files":[str(OUT).replace("\\","/"),str(EVIDENCE).replace("\\","/"),str(PHASE_B).replace("\\","/"),
                            "control/drawings/K01_D006_AUTHORING_INPUT.json",
                            "reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json"],
          "required_statuses":[
            {"file":str(OUT).replace("\\","/"),"path":["status"],"allowed_values":["PASS_P007_CURRENT_CANONICAL_PMI_C02_C05_PROVEN_STEP13_CORE"]},
            {"file":str(EVIDENCE).replace("\\","/"),"path":["status"],"allowed_values":["PASS_CURRENT_CANONICAL_PMI_C02_C05_SAVE_CLOSE_REOPEN"]},
            {"file":"reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json","path":["status"],"allowed_prefixes":["PASS"]}],
          "impact_declarations":{
            "requirements":"Do not invent unresolved release values.",
            "materials":"P007 remains AISI 316L / EN 1.4404.",
            "bom":"No geometry or quantity change is authorized by drawing creation.",
            "dimxpert_drawings":"C02/C05 native PMI is current and proven; advanced content must preserve explicit OPEN characteristics.",
            "inspection":"Only controlled characteristics may receive acceptance criteria.",
            "dependencies":"Any solid-geometry change invalidates current PMI evidence and requires impact propagation.",
            "technical_filter":"Drawing/manufacturing/tolerance/inspection categories remain explicit.",
            "rollback":"Drawing/advanced-PMI work occurs on candidate artifacts; canonical P007 remains unchanged.",
            "evidence":"Current proven PMI report + drawing model link + semantic lint + visual QA + inspection linkage."}}
        write(root/ACTIVE,active)

        refresh(root)
        print("STATUS:",rep["status"])
        print("PROVEN CORE SHA256:",rep["proven_csharp_core_sha256"])
        print("C02:",(o.get("C02") or {}).get("semantic_pass"),"persist",rr.get("C02_persist_state"))
        print("C05:",(o.get("C05") or {}).get("semantic_pass"),"persist",rr.get("C05_persist_state"))
        print("GEOMETRY INVARIANT:",o.get("geometry_invariant"))
        print("CANDIDATE:",candidate)
        print("PHASE-B WORKPACK:",root/PHASE_B)
        print("NEXT: K01-D-006 professional candidate")
        print("REPORT:",root/OUT)
        return 0
    except Exception as e:
        rep["status"]="HOLD_P007_PMI_PROVEN_STEP13_CURRENT"
        rep["error"]=repr(e)
        if candidate is not None: rep["candidate_path"]=str(candidate)
        write(root/OUT,rep)
        try: refresh(root)
        except Exception: pass
        print("STATUS:",rep["status"]);print("ERROR:",repr(e));print("REPORT:",root/OUT)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
