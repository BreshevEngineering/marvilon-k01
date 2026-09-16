#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

CAPTURE_CS = Path(r"cad_api/solidworks_2018_proven/current/K01_DRAWING_PLACEMENT_V1/K01DrawingPlacementCaptureV1.cs")
BUILD = Path(r"reports/cad/drawing_placement_v1_current/build")


def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, errors="replace", timeout=timeout)


def need(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def sha256(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def artifact(p: Path):
    return {"path": str(p), "exists": p.is_file(), "sha256": sha256(p) if p.is_file() else None, "size_bytes": p.stat().st_size if p.is_file() else None}


def load_manifest(candidate: Path):
    p = candidate / "candidate_manifest.json"
    need(p.is_file(), "candidate_manifest.json missing: " + str(p))
    m = json.loads(p.read_text(encoding="utf-8"))
    need(m.get("schema") == "k01.drawing_candidate.v1", "wrong candidate manifest schema")
    return p, m


def save_manifest(path: Path, m: dict):
    m["updated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def latest_candidate(output_root: Path):
    q = sorted([p for p in output_root.glob("drawing_system_v1_*") if p.is_dir() and (p / "candidate_manifest.json").is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    need(bool(q), "no Drawing System v1 candidate found under " + str(output_root))
    return q[0]


def spec_for(root: Path, drawing_id: str):
    q = sorted((root / "control" / "drawings" / "spec").glob(drawing_id + "*_DRAWING_SPEC*.json"))
    need(bool(q), "drawing spec not found for " + drawing_id)
    return q[-1]


def output_root_for_spec(spec_path: Path):
    s = json.loads(spec_path.read_text(encoding="utf-8"))
    return Path(s["output_root"]), s




def refresh_control(root: Path):
    script=root/"tools"/"medtas"/"drawing_control_v1.py"
    if not script.is_file(): return
    cp=run([sys.executable,str(script),"--repo-root",str(root)],cwd=root,timeout=120)
    if cp.stdout: print(cp.stdout,end="")
    if cp.stderr: print(cp.stderr,end="")

def prepare_manual(root: Path, drawing_id: str, candidate: Path | None):
    sp = spec_for(root, drawing_id); out, spec = output_root_for_spec(sp); candidate = candidate or latest_candidate(out)
    mp, m = load_manifest(candidate); generated = Path(m["paths"]["generated"]); manual = Path(m["paths"]["manual_finish"]); manual.mkdir(parents=True, exist_ok=True)
    src_d = generated / (drawing_id + ".SLDDRW"); src_p = generated / (drawing_id + ".PDF")
    need(src_d.is_file(), "generated drawing missing: " + str(src_d))
    dst_d = manual / (drawing_id + "_ISO_FINISH.SLDDRW"); shutil.copy2(src_d, dst_d)
    dst_p = manual / (drawing_id + "_ISO_FINISH.PDF")
    if src_p.is_file(): shutil.copy2(src_p, dst_p)
    m["state"] = "MANUAL_FINISH_PREPARED";m["manual_finish"] = {"drawing": artifact(dst_d), "pdf": artifact(dst_p)};save_manifest(mp,m)
    print("STATUS: PASS_DRAWING_MANUAL_FINISH_PREPARE_V1");print("CANDIDATE: " + str(candidate));print("EDIT THIS FILE: " + str(dst_d));print("EXPORT PDF HERE: " + str(dst_p));refresh_control(root)


def import_manual(root: Path, drawing_id: str, drawing: Path, pdf: Path | None, candidate: Path | None):
    sp = spec_for(root, drawing_id); out, spec = output_root_for_spec(sp); candidate = candidate or latest_candidate(out)
    mp,m=load_manifest(candidate);manual=Path(m["paths"]["manual_finish"]);manual.mkdir(parents=True,exist_ok=True);need(drawing.is_file(),"manual drawing missing")
    dst_d=manual/(drawing_id+"_ISO_FINISH.SLDDRW");shutil.copy2(drawing,dst_d);dst_p=manual/(drawing_id+"_ISO_FINISH.PDF")
    if pdf and pdf.is_file():shutil.copy2(pdf,dst_p)
    elif drawing.with_suffix(".PDF").is_file():shutil.copy2(drawing.with_suffix(".PDF"),dst_p)
    m["state"]="MANUAL_FINISH_IMPORTED";m["manual_finish"]={"drawing":artifact(dst_d),"pdf":artifact(dst_p)};save_manifest(mp,m)
    print("STATUS: PASS_DRAWING_MANUAL_FINISH_IMPORT_V1");print("CANDIDATE: "+str(candidate));print("MANUAL DRAWING: "+str(dst_d));refresh_control(root)


def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in (w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"):
        if p.exists(): return p
    raise RuntimeError("csc.exe missing")


def redist():
    for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
        if (p/"SolidWorks.Interop.sldworks.dll").exists(): return p
    raise RuntimeError("SOLIDWORKS API redist missing")


def sw_running():
    cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30);return "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower()


def cleanup_owned_sw(was_running):
    if was_running or not sw_running():return
    for _ in range(10):
        time.sleep(.5)
        if not sw_running():return
    run(["taskkill","/F","/T","/IM","SLDWORKS.exe"],timeout=30)


def capture(root: Path, drawing_id: str, candidate: Path | None):
    sp=spec_for(root,drawing_id);out,spec=output_root_for_spec(sp);candidate=candidate or latest_candidate(out);mp,m=load_manifest(candidate);manual=Path(m["paths"]["manual_finish"]);drawing=manual/(drawing_id+"_ISO_FINISH.SLDDRW");need(drawing.is_file(),"manual-finish drawing missing; run prepare-manual/import-manual first: "+str(drawing));need(not sw_running(),"Close SolidWorks before placement capture")
    rd=redist();refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll"];build=root/BUILD;build.mkdir(parents=True,exist_ok=True);exe=build/"K01DrawingPlacementCaptureV1.exe"
    cmd=[str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]+["/reference:"+str(x) for x in refs]+["/reference:System.Web.Extensions.dll",str(root/CAPTURE_CS)]
    cp=run(cmd,cwd=root);print(cp.stdout,end="");print(cp.stderr,end="");need(cp.returncode==0,"placement capture C# compile failed")
    for x in refs:shutil.copy2(x,build/x.name)
    evidence=Path(m["paths"]["evidence"]);evidence.mkdir(parents=True,exist_ok=True);local_profile=evidence/"placement_profile.json";report=evidence/"placement_capture_report.txt";was=sw_running()
    try:
        cp=run([str(exe),"--drawing",str(drawing),"--spec",str(sp),"--out",str(local_profile),"--report",str(report)],cwd=root,timeout=900);print(cp.stdout,end="");print(cp.stderr,end="");need(cp.returncode==0,"placement capture failed")
    finally:cleanup_owned_sw(was)
    controlled=root/"control"/"drawings"/"placement"/(drawing_id+"_PLACEMENT_CURRENT.json");controlled.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(local_profile,controlled)
    m["state"]="PLACEMENT_CAPTURED";m["placement"]={"candidate_profile":artifact(local_profile),"controlled_profile":artifact(controlled),"capture_report":artifact(report)};m["manual_finish"]={"drawing":artifact(drawing),"pdf":artifact(manual/(drawing_id+"_ISO_FINISH.PDF"))};save_manifest(mp,m)
    print("CONTROLLED PLACEMENT: "+str(controlled));print("NEXT: rerun Drawing System v1; engine will apply this placement automatically.");refresh_control(root)


def register_exemplar(root: Path, drawing_id: str, part_id: str, drawing: Path, pdf: Path | None, output_root: Path):
    need(drawing.is_file(),"exemplar drawing missing: "+str(drawing));stamp=dt.datetime.now().strftime("%Y%m%d_%H%M%S");candidate=output_root/("drawing_system_v1_EXEMPLAR_"+stamp);generated=candidate/"generated";manual=candidate/"manual_finish";evidence=candidate/"evidence";generated.mkdir(parents=True);manual.mkdir();evidence.mkdir();dst_d=manual/(drawing_id+"_ISO_FINISH.SLDDRW");shutil.copy2(drawing,dst_d);dst_p=manual/(drawing_id+"_ISO_FINISH.PDF")
    if pdf and pdf.is_file():shutil.copy2(pdf,dst_p)
    elif drawing.with_suffix(".PDF").is_file():shutil.copy2(drawing.with_suffix(".PDF"),dst_p)
    m={"schema":"k01.drawing_candidate.v1","candidate_id":candidate.name,"drawing_id":drawing_id,"part_id":part_id,"engine":"MARVILON_DRAWING_SYSTEM_V1","engine_revision":"1.1-candidate-lifecycle","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"state":"LEGACY_MANUAL_EXEMPLAR_REGISTERED","release":"HOLD","legacy_exemplar":True,"paths":{"candidate_root":str(candidate),"generated":str(generated),"manual_finish":str(manual),"evidence":str(evidence)},"manual_finish":{"drawing":artifact(dst_d),"pdf":artifact(dst_p)}};(candidate/"candidate_manifest.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("STATUS: PASS_DRAWING_EXEMPLAR_REGISTER_V1");print("CANDIDATE: "+str(candidate));print("MANUAL FINISH: "+str(dst_d));refresh_control(root)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",required=True);sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("prepare-manual");p.add_argument("--drawing-id",required=True);p.add_argument("--candidate")
    p=sub.add_parser("import-manual");p.add_argument("--drawing-id",required=True);p.add_argument("--drawing",required=True);p.add_argument("--pdf");p.add_argument("--candidate")
    p=sub.add_parser("capture");p.add_argument("--drawing-id",required=True);p.add_argument("--candidate")
    p=sub.add_parser("register-exemplar");p.add_argument("--drawing-id",required=True);p.add_argument("--part-id",required=True);p.add_argument("--drawing",required=True);p.add_argument("--pdf");p.add_argument("--output-root",required=True)
    a=ap.parse_args();root=Path(a.repo_root).resolve()
    try:
        if a.cmd=="prepare-manual":prepare_manual(root,a.drawing_id,Path(a.candidate) if a.candidate else None)
        elif a.cmd=="import-manual":import_manual(root,a.drawing_id,Path(a.drawing),Path(a.pdf) if a.pdf else None,Path(a.candidate) if a.candidate else None)
        elif a.cmd=="capture":capture(root,a.drawing_id,Path(a.candidate) if a.candidate else None)
        else:register_exemplar(root,a.drawing_id,a.part_id,Path(a.drawing),Path(a.pdf) if a.pdf else None,Path(a.output_root))
        return 0
    except Exception as e:
        print("STATUS: HOLD_DRAWING_CANDIDATE_LIFECYCLE_V1");print("ERROR:",repr(e));return 2

if __name__=="__main__":raise SystemExit(main())
