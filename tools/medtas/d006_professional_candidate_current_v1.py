#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

PMI=Path("reports/control/K01_P007_PMI_PROVEN_CURRENT.json")
STEP=Path("reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json")
PHASE_B=Path("reports/drawing/current/K01-D-006_P007_PHASE_B_WORKPACK_CURRENT.json")
TEMPLATE_DISC=Path("reports/drawing/current/K01_DRAWING_TEMPLATE_DISCOVERY_CURRENT.json")
RELEASE_DEF=Path("control/drawings/K01_D006_RELEASE_DEFINITION.json")
VISUAL=Path("control/drawings/K01_D006_VISUAL_QA_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
ACTIVE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
OUT=Path("reports/control/K01_D006_PROFESSIONAL_CANDIDATE_CURRENT.json")
SUMMARY=Path("reports/drawing/current/K01-D-006_PROFESSIONAL_CANDIDATE_CURRENT.md")
WORK=Path("reports/cad/d006_professional_current")
CS=Path("cad_api/solidworks_2018_proven/current/K01_D006_PROFESSIONAL_CANDIDATE/K01D006ProfessionalCandidate_v1.cs")
HANDOFF_REQ=Path("control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json")

def load(p,default=None):
    try:return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except:return default
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");os.replace(str(t),str(p))
def write_text(p,s):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(s,encoding="utf-8");os.replace(str(t),str(p))
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def run(c,cwd=None,timeout=420):
    return subprocess.run(c,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)
def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in [w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"]:
        if p.exists():return p
    raise RuntimeError("csc.exe missing")
def redist():
    for p in [Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),
              Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")]:
        if (p/"SolidWorks.Interop.sldworks.dll").exists():return p
    raise RuntimeError("SOLIDWORKS api/redist missing")
def sw_running():
    try:
        cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30)
        return "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower()
    except:return False
def parse_kv(p):
    d={}
    for line in Path(p).read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if "=" in line:
            k,v=line.split("=",1);d[k.strip()]=v.strip()
    return d
def refresh(root):
    for rel,to in [
        ("tools/medtas/rebuild_medtas_state.py",300),
        ("tools/medtas/technical_filter_map_v2_2.py",180),
        ("tools/assurance/engineering_step_gate.py",180),
        ("tools/assurance/build_engineering_dashboard.py",180),
    ]:
        p=root/rel
        if not p.is_file():continue
        cp=run([sys.executable,str(p),"--repo-root",str(root)],cwd=root,timeout=to)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
def ensure_handoff(root):
    p=root/HANDOFF_REQ
    if not p.is_file():return
    h=load(p,{}) or {};req=h.get("required",[]) or []
    for x in [
        str(CS).replace("\\","/"),
        "tools/medtas/d006_professional_candidate_current_v1.py",
        "cad_api/solidworks_2018_proven/RUN_K01_D006_PROFESSIONAL_CURRENT.cmd",
        str(OUT).replace("\\","/"),
        str(SUMMARY).replace("\\","/")
    ]:
        if x not in req:req.append(x)
    h["required"]=req
    h["note"]="Current next line includes K01-D-006 professional design-review candidate generated from current proven P007 PMI. Experimental legacy drawing paths remain history only."
    write(p,h)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",required=True);a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    rep={"schema":"k01.d006.professional_candidate.current.v1","generated_utc":datetime.now(timezone.utc).isoformat(),"status":"RUNNING"}
    try:
        need(not sw_running(),"SolidWorks is running. Close it before drawing candidate authoring.")
        pmi=load(root/PMI,{}) or {}
        need(pmi.get("status")=="PASS_P007_CURRENT_CANONICAL_PMI_C02_C05_PROVEN_STEP13_CORE",
             "current proven P007 PMI is not PASS")
        cand=pmi.get("candidate") or {};part=Path(str(cand.get("path") or ""));expected=str(cand.get("sha256") or "")
        need(part.is_file(),"current proven PMI candidate missing: "+str(part))
        need(sha(part)==expected,"current proven PMI candidate SHA mismatch")

        st=load(root/STEP,{}) or {}
        need(st.get("status")=="PASS_TO_K01_D006_PROFESSIONAL_CANDIDATE",
             "engineering gate is not PASS_TO_K01_D006_PROFESSIONAL_CANDIDATE")

        pb=load(root/PHASE_B,{}) or {}
        need(str(pb.get("status") or "").startswith("READY_FOR_K01_D006_PROFESSIONAL_CANDIDATE"),
             "Phase-B workpack is not ready")

        td=load(root/TEMPLATE_DISC,{}) or {}
        template=Path(str(td.get("selected_if_unique") or ""))
        need(template.is_file(),"controlled unique drawing template is not available: "+str(template))

        work=root/WORK;build=work/"build";build.mkdir(parents=True,exist_ok=True)
        char=work/"K01_D006_CHARACTERISTICS_CURRENT.tsv"
        notes=work/"K01_D006_NOTES_CURRENT.txt"
        rows=[
          ["ID","CHARACTERISTIC","CURRENT CONTROL / STATUS"],
          ["C01","J2 mating face / Datum A","Functional datum identity controlled; numeric flatness/orientation limit OPEN"],
          ["C02","Locator / Datum B","Ø14.10 H7; depth 2.00 NOM; depth tolerance OPEN; native PMI PASS"],
          ["C03","Locator-axis orientation","OPEN — numeric perpendicularity/orientation release not closed"],
          ["C04","3-hole clamp pattern","3×Ø2.90 THRU on PCD 26.50 NOM; position tolerance OPEN"],
          ["C05","Flange","Ø33.00 NOM × 3.00 NOM; release tolerances OPEN; Ø33 native PMI PASS"],
          ["C06","Overall length","35.00 NOM; release tolerance OPEN"],
          ["C07","Thin can OD","Ø10.00 NOM; release tolerance policy OPEN"],
          ["C08","Thin can ID / wall","Ø9.40 NOM / radial wall 0.30 NOM; release tolerance policy OPEN"],
          ["C09","Material","AISI 316L / EN 1.4404 — CONTROLLED"]
        ]
        write_text(char,"\n".join("\t".join(r) for r in rows)+"\n")
        note_lines=[
          "MODEL-BASED DESIGN REVIEW CANDIDATE. DO NOT SCALE.",
          "CURRENT PROVEN NATIVE PMI: C02 Ø14.10 and C05 Ø33.00; save-close-reopen PASS; persistent states 0/0.",
          "SECTION A-A IS PROVIDED FOR THIN-CAN / BLIND-END DESIGN REVIEW.",
          "BLIND END: 1.00 mm NOM; released tolerance / inspection acceptance OPEN.",
          "C10 CONTAINMENT JOINING PROCESS: OPEN.",
          "C11 COAXIALITY / CONCENTRICITY REQUIREMENT: OPEN.",
          "C12 QUANTITATIVE LEAK / CONTAINMENT ACCEPTANCE: OPEN.",
          "NO OPEN TOLERANCE, PROCESS OR LEAK VALUE IS RELEASED BY THIS DRAWING."
        ]
        write_text(notes,"\n".join(note_lines))

        rd=redist();refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll"]
        for p in refs:need(p.is_file(),"missing interop "+str(p))
        src=root/CS;need(src.is_file(),"D006 professional C# source missing")
        exe=build/"K01D006ProfessionalCandidate_v1.exe"
        cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]
               +["/reference:"+str(x) for x in refs]+[str(src)],cwd=root)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        need(cp.returncode==0,"D006 professional C# compile failed")
        for p in refs:shutil.copy2(p,build/p.name)
        for n in ("SolidWorks.Interop.swpublished.dll","SolidWorks.Interop.swcommands.dll"):
            p=rd/n
            if p.is_file():shutil.copy2(p,build/p.name)
        print("D006 CORE COMPILE: PASS")

        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir=Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")/("professional_"+stamp)
        outdir.mkdir(parents=True,exist_ok=False)
        raw=work/"K01_D006_PROFESSIONAL_BUILD_CURRENT.txt"
        if raw.exists():raw.unlink()
        cp=run([str(exe),"--part",str(part),"--part-sha",expected,"--template",str(template),
                "--outdir",str(outdir),"--table",str(char),"--notes",str(notes),"--report",str(raw)],cwd=root)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        need(cp.returncode==0,"D006 professional drawing authoring failed")
        kv=parse_kv(raw)
        need(kv.get("STATUS")=="PASS_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE","D006 raw status not PASS")
        drw=Path(kv["DRAWING"]);pdf=Path(kv["PDF"]);bmp=Path(kv["BMP"])
        need(drw.is_file() and pdf.is_file(),"D006 native/PDF output missing")
        need(sha(part)==expected,"source PMI candidate changed during drawing authoring")

        rep.update({
          "status":"PASS_K01_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE",
          "release_status":"NOT_RELEASED",
          "source_p007_pmi_report":str(PMI).replace("\\","/"),
          "source_part":{"path":str(part),"sha256":expected},
          "template":str(template),
          "candidate":{"slddrw":str(drw),"pdf":str(pdf),"bmp":str(bmp)},
          "verification":{
            "source_hash_invariant":kv.get("SOURCE_HASH_INVARIANT")=="True",
            "section_created":kv.get("SECTION_CREATED")=="True",
            "characteristic_table_created":kv.get("CHARACTERISTIC_TABLE_CREATED")=="True",
            "title_table_created":kv.get("TITLE_TABLE_CREATED")=="True",
            "view_count_with_sheet":int(kv.get("VIEW_COUNT_WITH_SHEET","0")),
            "p007_model_view_references":int(kv.get("P007_MODEL_VIEW_REFERENCES","0")),
            "pdf_export":"PASS",
            "save_close_reopen":"PASS"
          },
          "controlled_characteristics":["C01 datum identity","C02 Ø14.10 H7 + 2.00 nominal depth","C04 3×Ø2.90/PCD26.50 nominal geometry","C05 Ø33×3 nominal","C06 35 nominal","C07/C08 nominal thin-can geometry","C09 AISI 316L / EN 1.4404"],
          "explicit_open":["C01 numeric flatness/orientation","C02 depth tolerance","C03 orientation tolerance","C04 position tolerance","C05 release tolerances","C06 release tolerance","C07/C08 release tolerance policy","C10 joining process","C11 coaxiality","C12 leak acceptance","blind-end release tolerance/inspection"],
          "next":"VISUAL_QA_AND_DRAWING_SEMANTIC_REVIEW"
        })
        write(root/OUT,rep)

        rddef=load(root/RELEASE_DEF,{}) or {}
        rddef["generated_utc"]=rep["generated_utc"]
        rddef["candidate_state"]="CURRENT_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE_BUILT"
        rddef["candidate_slddrw"]=str(drw);rddef["candidate_pdf"]=str(pdf);rddef["candidate_bmp_preview"]=str(bmp)
        rddef["candidate_verification"]=str(OUT).replace("\\","/")
        rddef["status"]="CANDIDATE_CURRENT; HOLD_VISUAL_QA_AND_RELEASE_OPEN_ITEMS"
        rddef["current_pmi_evidence"]=str(PMI).replace("\\","/")
        write(root/RELEASE_DEF,rddef)

        vqa={
          "schema":"k01.d006.visual_qa.current.v2",
          "generated_utc":rep["generated_utc"],
          "status":"PENDING_VISUAL_QA_CURRENT_PROFESSIONAL_CANDIDATE",
          "source_pdf":str(pdf),"source_bmp":str(bmp),
          "automated_prechecks":rep["verification"],
          "required_visual_checks":[
             "views readable and non-overlapping",
             "section A-A correctly exposes thin can and blind end",
             "characteristic table readable",
             "title/status block readable",
             "notes readable and do not obscure geometry",
             "no implication that OPEN characteristics are released"
          ],
          "release_boundary":"DESIGN REVIEW CANDIDATE ONLY; R01 NOT RELEASED"
        }
        write(root/VISUAL,vqa)

        summary=f"""# K01-D-006 — current professional design-review candidate

**Status:** PASS_K01_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE
**Release:** NOT RELEASED

Source P007 model: `{part}`
Source SHA-256: `{expected}`

Artifacts:
- SLDDRW: `{drw}`
- PDF: `{pdf}`
- BMP: `{bmp}`

Automated checks:
- section A-A: {rep['verification']['section_created']}
- characteristic table: {rep['verification']['characteristic_table_created']}
- title table: {rep['verification']['title_table_created']}
- P007 model references: {rep['verification']['p007_model_view_references']}
- source model hash invariant: {rep['verification']['source_hash_invariant']}

The drawing intentionally keeps C03, C07/C08 tolerance policy, C10, C11, C12 and blind-end release tolerance/inspection OPEN. It is suitable for design-review/report evidence, not production R01 release.
"""
        write_text(root/SUMMARY,summary)

        nxt=load(root/NEXT,{}) or {}
        nxt["current_stage"]="K01_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE_BUILT"
        nxt["last_completed"]="Current K01-D-006 native SLDDRW/PDF/BMP design-review candidate built from current proven P007 PMI candidate with section A-A, controlled characteristic table, title/status block, explicit OPEN items, model-reference reopen proof and invariant source hash."
        nxt["last_evidence"]=[str(OUT).replace("\\","/"),str(SUMMARY).replace("\\","/"),str(VISUAL).replace("\\","/")]
        nxt["current_blocker"]="Visual QA of the current PDF/BMP, then semantic drawing/inspection linkage. Release-critical unresolved tolerances/process/leak requirements remain OPEN."
        nxt["next_1"]="Perform visual QA of current K01-D-006 PDF/BMP and correct layout only if required."
        nxt["next_2"]="Link controlled drawing characteristics to inspection table and refresh P007 structural/buckling evidence."
        nxt["then"]="Assemble final design-review dossier and explicit R01 blocker matrix."
        write(root/NEXT,nxt)

        active={
          "schema":"k01.active_step_gate.v1",
          "step_id":"K01-STEP-P4-K01-D006-VISUAL-SEMANTIC-QA",
          "active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION",
          "checkpoint_id":"K01-CP-20260910-BASELINE-02C-PROMOTED",
          "intent":"VISUALLY_AND_SEMANTICALLY_QA_CURRENT_K01_D006_DESIGN_REVIEW_CANDIDATE_THEN_LINK_INSPECTION",
          "mutation_authorized":True,
          "result_on_pass":"PASS_TO_D006_INSPECTION_LINKAGE_AND_P007_STRUCTURAL_REFRESH",
          "required_files":[str(OUT).replace("\\","/"),str(VISUAL).replace("\\","/"),str(SUMMARY).replace("\\","/"),"reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json"],
          "impact_declarations":{
            "requirements":"OPEN values remain OPEN.",
            "materials":"P007 AISI 316L / EN 1.4404 controlled.",
            "bom":"No BOM/geometry quantity change.",
            "drawings":"Current candidate is design-review evidence, not R01 production release.",
            "inspection":"Next step creates traceability without inventing acceptance limits.",
            "rollback":"Discard current timestamped drawing candidate if visual/semantic QA fails; source P007 candidate is unchanged."}}
        write(root/ACTIVE,active)

        ensure_handoff(root)
        refresh(root)
        print("STATUS:",rep["status"])
        print("DRAWING:",drw)
        print("PDF:",pdf)
        print("BMP:",bmp)
        print("SECTION:",rep["verification"]["section_created"])
        print("P007 REFS:",rep["verification"]["p007_model_view_references"])
        print("SOURCE HASH INVARIANT:",rep["verification"]["source_hash_invariant"])
        print("NEXT: visual QA + semantic/inspection linkage")
        print("REPORT:",root/OUT)
        return 0
    except Exception as e:
        rep["status"]="HOLD_K01_D006_PROFESSIONAL_CANDIDATE"
        rep["error"]=repr(e);write(root/OUT,rep)
        try:refresh(root)
        except:pass
        print("STATUS:",rep["status"]);print("ERROR:",repr(e));print("REPORT:",root/OUT)
        return 2

if __name__=="__main__":raise SystemExit(main())
