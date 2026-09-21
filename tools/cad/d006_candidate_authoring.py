from __future__ import annotations
import argparse,json,hashlib,os,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone

EXPECTED_P007_SHA="615ad82ffe1b555ad7800723096fda297233e21a4deea5d84c2d75c1bdaa6653"
CHANGE_ID="CHG-K01-D006-CANDIDATE-001"

def load(p,default=None):
    try:return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:return default
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def run(c,cwd=None):return subprocess.run(c,cwd=cwd,capture_output=True,text=True,errors="replace")
def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in [w/"Microsoft.NET"/"Framework64"/"v4.0.30319"/"csc.exe",
              w/"Microsoft.NET"/"Framework"/"v4.0.30319"/"csc.exe"]:
        if p.exists():return p
    raise RuntimeError("csc.exe not found")
def redist():
    p=Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist")
    if (p/"SolidWorks.Interop.sldworks.dll").exists():return p
    raise RuntimeError("SOLIDWORKS 2018 API redist not found")
def parse_kv(p):
    d={}
    for line in Path(p).read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if "=" in line:
            k,v=line.split("=",1);d[k.strip()]=v.strip()
    return d

def add_report_to_change(repo,report_rel):
    cc=repo/"tools"/"governance"/"change_control.py"
    cp=run([sys.executable,str(cc),"--repo-root",str(repo),"implementation"],cwd=str(repo))
    if cp.stdout.strip():print(cp.stdout.strip())
    if cp.returncode!=0:
        if cp.stderr.strip():print(cp.stderr.strip())
        raise RuntimeError("change implementation mark failed")

    recp=repo/"control"/"change"/"K01_CHANGE_CURRENT.json"
    rec=load(recp,{}) or {}
    rec["verification_status"]="HOLD_VISUAL_QA_AND_RELEASE_SPECS"
    rec["verification_evidence"]=[report_rel]
    rec["status"]="VERIFICATION_HOLD"
    rec["updated_utc"]=datetime.now(timezone.utc).isoformat()
    write(recp,rec)
    write(repo/"control"/"change"/"records"/(CHANGE_ID+".json"),rec)

def main(repo:Path):
    print("="*96)
    print("K01 STEP 16 - ACTUAL K01-D-006 CANDIDATE DRAWING AUTHORING")
    print("="*96)

    # Gate on Step15R2 and active pre-change record.
    s15=load(repo/"reports"/"engineering"/"K01_ITERATION15_CURRENT.json",{}) or {}
    if s15.get("status")!="PASS_GOVERNANCE_FOUNDATION_AND_PRECHANGE_D006_IMPACT":
        raise RuntimeError("Step15R2 PASS checkpoint missing")
    rec=load(repo/"control"/"change"/"K01_CHANGE_CURRENT.json",{}) or {}
    if rec.get("id")!=CHANGE_ID or rec.get("class")!="B" or rec.get("impact_status")!="PASS_PRECHANGE":
        raise RuntimeError("D006 Class-B change is not authorized for implementation")
    print("prechange_gate: PASS",CHANGE_ID)

    author=load(repo/"control"/"drawings"/"K01_D006_AUTHORING_INPUT.json",{}) or {}
    if author.get("status")!="READY_FOR_CANDIDATE_AUTHORING":
        raise RuntimeError("K01_D006_AUTHORING_INPUT not ready")

    pmi=load(repo/"control"/"product_definition"/"K01_P007_PMI_WRITE_EVIDENCE.json",{}) or {}
    part=Path(str(pmi.get("source_authority_part") or ""))
    if not part.exists():
        # Controlled fallback from known Gate04E authority.
        part=Path(r"D:\Marvilon\K01\cad\candidates\gate04d_c2r1\K01-P-007_Hermetic_Magnetic_Can_GATE04D_C2R1_CANDIDATE.SLDPRT")
    if not part.exists():
        raise RuntimeError("P007 authority part not found")
    actual=sha(part)
    if actual.lower()!=EXPECTED_P007_SHA:
        raise RuntimeError("P007 authority hash mismatch "+actual)
    print("P007_authority_guard: PASS",actual)

    # Build controlled note content from existing release definition; no invented release values.
    definition=load(repo/"control"/"drawings"/"K01_D006_RELEASE_DEFINITION.json",{}) or {}
    proven=definition.get("already_proven") or {}
    blockers=definition.get("release_blockers") or []
    nextscope=definition.get("next_authoring_scope") or []

    block1=[
        "CONTROLLED NOMINALS / CURRENT EVIDENCE",
        "1. OAL: 35.00 mm",
        "2. LOCATOR: DIA 14.10 mm nominal; H7/g6 pair architecture",
        "3. FLANGE OD: 33.00 mm nominal",
        "4. CLAMP: 3X DIA 2.90 ON PCD 26.50 mm",
        "5. CAN: OD 10.00 / ID 9.40 / radial wall 0.30 mm nominal",
        "6. BLIND END: 1.00 mm nominal",
        "7. MATERIAL: AISI 316L / EN 1.4404",
        "",
        "NEXT CONTROLLED AUTHORING:",
    ] + ["- "+str(x) for x in nextscope]

    block2=[
        "RELEASE BLOCKERS - DO NOT INFER",
    ] + ["- "+str(x) for x in blockers] + [
        "",
        "This candidate is for engineering review only.",
        "No unresolved tolerance/process/leak value is released by this sheet."
    ]

    work=repo/"reports"/"cad"/"d006_candidate"
    build=work/"build";build.mkdir(parents=True,exist_ok=True)
    notes=work/"K01_D006_NOTE_CONTENT_CURRENT.txt"
    notes.write_text("\n".join(block1)+"\n---BLOCK---\n"+"\n".join(block2),encoding="utf-8")

    out_native=Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")/("step16_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_native.mkdir(parents=True,exist_ok=False)
    report_txt=work/"K01_D006_CANDIDATE_BUILD_CURRENT.txt"
    if report_txt.exists():report_txt.unlink()

    # Compile against current machine's SW2018 interop.
    rd=redist()
    refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll"]
    src=repo/"tools"/"cad"/"K01D006Candidate.cs"
    if not src.exists():
        raise RuntimeError("installed C# source missing")
    exe=build/"K01D006Candidate.exe"
    cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]
           +["/reference:"+str(x) for x in refs]+[str(src)],cwd=str(repo))
    if cp.returncode!=0:
        print(cp.stdout);print(cp.stderr)
        raise RuntimeError("D006 C# compile failed")
    for p in refs:shutil.copy2(p,build/p.name)
    for n in ["SolidWorks.Interop.swpublished.dll","SolidWorks.Interop.swcommands.dll"]:
        p=rd/n
        if p.exists():shutil.copy2(p,build/p.name)
    print("compile: PASS")

    cp=run([str(exe),
            "--part",str(part),
            "--part-sha",EXPECTED_P007_SHA,
            "--outdir",str(out_native),
            "--notes",str(notes),
            "--report",str(report_txt)],cwd=str(repo))
    if cp.stdout.strip():print(cp.stdout.strip())
    if cp.stderr.strip():print(cp.stderr.strip())
    print("drawing_author_return_code:",cp.returncode)
    if cp.returncode!=0:
        raise RuntimeError("D006 candidate drawing authoring failed")

    kv=parse_kv(report_txt)
    if kv.get("STATUS")!="PASS_AUTOMATED_D006_CANDIDATE_BUILD":
        raise RuntimeError("D006 report not PASS")
    drw=Path(kv["DRAWING"]);pdf=Path(kv["PDF"]);bmp=Path(kv["BMP"])
    if not drw.exists() or not pdf.exists():
        raise RuntimeError("candidate output missing")

    verify={
        "schema":"k01.d006.candidate_verify.v1",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "status":"PASS_AUTOMATED_BUILD; HOLD_VISUAL_QA_AND_RELEASE_SPECS",
        "change_id":CHANGE_ID,
        "change_class":"B",
        "prechange_impact_status":"PASS_PRECHANGE",
        "source_part":str(part),
        "source_part_sha256_before":kv.get("SOURCE_SHA_BEFORE"),
        "source_part_sha256_after":kv.get("SOURCE_SHA_AFTER"),
        "geometry_hash_invariant":kv.get("GEOMETRY_HASH_INVARIANT")=="True",
        "solidworks_revision":kv.get("SOLIDWORKS_REVISION"),
        "workstation_contract":kv.get("WORKSTATION_CONTRACT"),
        "template":kv.get("TEMPLATE"),
        "candidate_slddrw":str(drw),
        "candidate_pdf":str(pdf),
        "candidate_bmp_preview":str(bmp),
        "slddrw_bytes":int(kv.get("DRAWING_BYTES","0")),
        "pdf_bytes":int(kv.get("PDF_BYTES","0")),
        "bmp_created":kv.get("BMP_CREATED")=="True",
        "bmp_bytes":int(kv.get("BMP_BYTES","0")),
        "view_count_with_sheet":int(kv.get("VIEW_COUNT_WITH_SHEET","0")),
        "p007_model_view_references":int(kv.get("P007_MODEL_VIEW_REFERENCES","0")),
        "references_ok":kv.get("REFERENCES_OK")=="True",
        "automated_checks":{
            "source_hash_guard":"PASS",
            "source_hash_invariant":"PASS" if kv.get("GEOMETRY_HASH_INVARIANT")=="True" else "HOLD",
            "drawing_save_close_reopen":"PASS",
            "P007_references":"PASS" if kv.get("REFERENCES_OK")=="True" else "HOLD",
            "PDF_export":"PASS",
            "BMP_preview":"PASS" if kv.get("BMP_CREATED")=="True" else "WARN"
        },
        "visual_qa":"OPEN",
        "release_blockers":blockers,
        "policy":"Candidate exists. Do not promote until visual QA and unresolved release characteristics are closed or explicitly carried as OPEN."
    }
    report_json=work/"K01_D006_CANDIDATE_VERIFY_CURRENT.json"
    write(report_json,verify)

    # Update controlled drawing definition with candidate evidence, without removing release blockers.
    definition["generated_utc"]=verify["generated_utc"]
    definition["candidate_state"]="BUILT_AWAITING_VISUAL_QA"
    definition["candidate_slddrw"]=str(drw)
    definition["candidate_pdf"]=str(pdf)
    definition["candidate_bmp_preview"]=str(bmp)
    definition["candidate_verification"]="reports/cad/d006_candidate/K01_D006_CANDIDATE_VERIFY_CURRENT.json"
    definition["status"]="CANDIDATE_BUILT; HOLD_VISUAL_QA_AND_RELEASE_SPECS"
    write(repo/"control"/"drawings"/"K01_D006_RELEASE_DEFINITION.json",definition)

    add_report_to_change(repo,"reports/cad/d006_candidate/K01_D006_CANDIDATE_VERIFY_CURRENT.json")

    # Refresh closure and evidence-only center.
    cm=load(repo/"control"/"project"/"K01_PROJECT_CLOSURE_MATRIX.json",{}) or {}
    by={x.get("id"):x for x in cm.get("domains",[]) if isinstance(x,dict)}
    if "DRAWINGS_DIMXPERT" in by:
        by["DRAWINGS_DIMXPERT"].update({
            "status":"D006_CANDIDATE_BUILT; HOLD_VISUAL_QA_AND_RELEASE_SPECS",
            "candidate_verification":"reports/cad/d006_candidate/K01_D006_CANDIDATE_VERIFY_CURRENT.json"
        })
    cm["domains"]=list(by.values())
    cm["generated_utc"]=verify["generated_utc"]
    cm["overall_status"]="HOLD_ENGINEERING_CLOSURE"
    write(repo/"control"/"project"/"K01_PROJECT_CLOSURE_MATRIX.json",cm)

    center=repo/"tools"/"assurance"/"build_center_state.py"
    if center.exists():
        c=run([sys.executable,str(center),"--repo-root",str(repo)],cwd=str(repo))
        if c.stdout.strip():print(c.stdout.strip())
        if c.returncode!=0 and c.stderr.strip():print(c.stderr.strip())


    # Controlled engineering closure plans generated from current evidence.
    # These are work plans, not released values and not alternate status authorities.
    tol_plan={
        "schema":"k01.p007.functional_tolerance_plan.v1",
        "generated_utc":verify["generated_utc"],
        "status":"ACTIVE_ENGINEERING_CLOSURE_PLAN",
        "change_id":CHANGE_ID,
        "drawing":"K01-D-006",
        "model":"K01-P-007",
        "principle":"Tolerances are derived from functional interfaces and verified by stackup/inspection; manufacturing capability alone is not the acceptance basis.",
        "functional_chain":[
            {
                "id":"FT-01",
                "function":"Seat P007 repeatably against mating structure",
                "datum_or_feature":"Datum A = functional mating face set",
                "drawing_characteristics":["C01 flatness/orientation strategy"],
                "method":"derive from J2 contact/seal/preload function and inspection setup",
                "numeric_status":"OPEN"
            },
            {
                "id":"FT-02",
                "function":"Locate P007 axis relative to J2",
                "datum_or_feature":"Datum B = locator cylindrical feature / axis",
                "drawing_characteristics":["C02 locator size/fit","C03 orientation to A"],
                "method":"derive fit and orientation from assembly clearance, alignment and service requirement",
                "numeric_status":"PARTIALLY_CONTROLLED; released tolerance still review"
            },
            {
                "id":"FT-03",
                "function":"Permit 3-fastener assembly without forcing/misalignment",
                "datum_or_feature":"3-hole pattern",
                "drawing_characteristics":["C04 hole size/pattern/position"],
                "method":"fixed/floating fastener tolerance stackup across P003↔P007 interface",
                "numeric_status":"OPEN_RELEASE_TOLERANCE"
            },
            {
                "id":"FT-04",
                "function":"Maintain magnetic/containment radial envelope",
                "datum_or_feature":"P007 OD10 / ID9.4 thin can zone",
                "drawing_characteristics":["C07","C08","C11"],
                "method":"radial tolerance stackup including P015 ID, P007 wall, internal moving envelope and coaxial error",
                "numeric_status":"OPEN"
            },
            {
                "id":"FT-05",
                "function":"Maintain containment end-wall integrity",
                "datum_or_feature":"blind end",
                "drawing_characteristics":["blind-end tolerance"],
                "method":"strength/stability/manufacturing/inspection closure",
                "numeric_status":"OPEN"
            }
        ],
        "release_rule":"K01-D-006 cannot be promoted until required functional tolerances have numeric limits, stackup/analysis evidence and inspection method."
    }
    write(repo/"control"/"drawings"/"K01_P007_FUNCTIONAL_TOLERANCE_PLAN.json",tol_plan)

    j2_plan={
        "schema":"k01.j2_containment_closure_plan.v1",
        "generated_utc":verify["generated_utc"],
        "status":"ACTIVE_ENGINEERING_CLOSURE_PLAN",
        "interface":"P003↔P007 J2",
        "current_facts":{
            "fastener_architecture":"3 x M2.5 / PCD26.5 / P007 Ø2.90 clearance",
            "locator_architecture":"Ø14.10 H7/g6 pair architecture",
            "seal_architecture":"static face O-ring / 16 x 1.5 nominal gland architecture",
            "P007_material":"AISI 316L / EN 1.4404"
        },
        "closure_items":[
            {
                "id":"J2-FASTENER",
                "open":["exact screw standard/head","length","material/grade","finish/lubrication","torque-preload calibration"],
                "evidence_required":["joint separation/contact check","thread/galling/service rationale","assembly instruction"]
            },
            {
                "id":"J2-SEAL",
                "open":["media envelope","exact compound/supplier","squeeze/compression force","surface finish/flatness limits","quantitative leak acceptance","test method"],
                "evidence_required":["seal compatibility basis","gland/squeeze check","leak verification plan"]
            },
            {
                "id":"P007-CONTAINMENT-PROCESS",
                "open":["weld vs adhesive applicability","process specification","inspection/acceptance"],
                "rule":"Do not carry legacy weld into active MBOM unless current design explicitly requires it."
            }
        ],
        "release_rule":"Containment process and seal/fastener definitions must close before D006/R01 release."
    }
    write(repo/"control"/"product_definition"/"K01_J2_CONTAINMENT_CLOSURE_PLAN.json",j2_plan)

    summary={
        "schema":"k01.iteration16.summary.v1",
        "generated_utc":verify["generated_utc"],
        "status":"PASS_D006_CANDIDATE_BUILT_WITH_VISUAL_AND_RELEASE_HOLDS",
        "candidate_slddrw":str(drw),
        "candidate_pdf":str(pdf),
        "candidate_bmp_preview":str(bmp),
        "source_geometry_invariant":verify["geometry_hash_invariant"],
        "p007_model_view_references":verify["p007_model_view_references"],
        "visual_qa":"OPEN",
        "release_blocker_count":len(blockers),
        "change_status":"VERIFICATION_HOLD",
        "functional_tolerance_plan":"control/drawings/K01_P007_FUNCTIONAL_TOLERANCE_PLAN.json",
        "j2_containment_plan":"control/product_definition/K01_J2_CONTAINMENT_CLOSURE_PLAN.json",
        "next_actions":[
            "Review BMP/PDF visual layout; correct layout only as Class B implementation under same change.",
            "Add controlled Datum A/B and C03/C04/C05/C06 drawing semantics after visual layout is stable.",
            "Keep C07/C08/C10/C11/C12/blind-end tolerance OPEN until engineering decisions are controlled.",
            "Continue parallel BOM/J2/magnetic closure lanes from K01_EXECUTION_POLICY.json."
        ]
    }
    write(repo/"reports"/"engineering"/"K01_ITERATION16_CURRENT.json",summary)

    print("\n"+"="*96)
    print("STEP 16 SUMMARY")
    print("="*96)
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    print("VISIBLE RESULT: actual SLDDRW + PDF + BMP preview created in native CAD workspace.")
    return 0

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=r"D:\BreshevEngineering\marvilon-k01")
    a=ap.parse_args()
    raise SystemExit(main(Path(str(a.repo_root).strip().strip('"')).resolve()))
