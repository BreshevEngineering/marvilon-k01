from __future__ import annotations
import argparse,json,hashlib,os,shutil,subprocess
from pathlib import Path
from datetime import datetime

EXPECTED_P007_SHA="615ad82ffe1b555ad7800723096fda297233e21a4deea5d84c2d75c1bdaa6653"

def load(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def run(c,cwd=None): return subprocess.run(c,cwd=cwd,capture_output=True,text=True,errors="replace")
def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in [w/"Microsoft.NET"/"Framework64"/"v4.0.30319"/"csc.exe",w/"Microsoft.NET"/"Framework"/"v4.0.30319"/"csc.exe"]:
        if p.exists():return p
    raise RuntimeError("csc.exe missing")
def redist():
    p=Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist")
    if (p/"SolidWorks.Interop.sldworks.dll").exists():return p
    raise RuntimeError("SOLIDWORKS 2018 api/redist missing")
def getref(scope,cid):
    for x in scope.get("safe_authoring_scope",[]) or []:
        if x.get("id")==cid:
            ents=((x.get("solidworks_binding") or {}).get("entities") or [])
            if len(ents)==1:return ents[0].get("persist_ref_b64")
    return None

def main(repo,pkg):
    print("="*88)
    print("STEP 13C - P007 DIMXPERT NOMINAL SAVE/CLOSE/REOPEN READBACK")
    print("="*88)
    envp=repo/"control"/"environment"/"K01_SOLIDWORKS_2018_RUNTIME.json"
    env=load(envp)
    if env.get("solidworks_product_year")!=2018 or env.get("expected_sldworks_interop_major")!=26:
        raise RuntimeError("SOLIDWORKS 2018 environment contract missing/mismatch")

    scopep=repo/"control"/"product_definition"/"K01_P007_PMI_AUTHORING_SCOPE.json"
    scope=load(scopep)
    if scope.get("status")!="READY_FOR_FIRST_CONTROLLED_PMI_WRITE":
        raise RuntimeError("P007 PMI scope is not ready")
    src=Path(scope["native_part"]["path"])
    if sha(src)!=EXPECTED_P007_SHA: raise RuntimeError("P007 authority hash changed")
    r02=getref(scope,"C02");r05=getref(scope,"C05")
    if not r02 or not r05: raise RuntimeError("C02/C05 persistent refs unavailable")

    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    canddir=Path(r"D:\Marvilon\K01\cad\candidates\p007_pmi_authoring")/("step13_"+stamp)
    canddir.mkdir(parents=True,exist_ok=False)
    cand=canddir/"K01-P-007_Hermetic_Magnetic_Can_PMI_STEP13_CANDIDATE.SLDPRT"
    shutil.copy2(src,cand)
    if sha(cand)!=EXPECTED_P007_SHA: raise RuntimeError("candidate copy mismatch")

    work=repo/"reports"/"cad"/"p007_pmi_step13";build=work/"build";build.mkdir(parents=True,exist_ok=True)
    manifest=work/"K01_P007_PMI_STEP13_MANIFEST_CURRENT.txt"
    manifest.write_text("C02_REF="+r02+"\nC05_REF="+r05+"\n",encoding="utf-8")

    rd=redist()
    refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll",rd/"SolidWorks.Interop.swdimxpert.dll"]
    for p in refs:
        if not p.exists(): raise RuntimeError("missing interop "+str(p))
    source=pkg/"payload"/"cad_api"/"p007_pmi"/"K01P007PmiStep13.cs"
    exe=build/"K01P007PmiStep13.exe"
    cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]
           +["/reference:"+str(x) for x in refs]+[str(source)],cwd=str(repo))
    if cp.returncode!=0:
        print(cp.stdout);print(cp.stderr);raise RuntimeError("P007 PMI C# compile failed")
    for p in refs: shutil.copy2(p,build/p.name)
    for n in ["SolidWorks.Interop.swpublished.dll","SolidWorks.Interop.swcommands.dll"]:
        p=rd/n
        if p.exists():shutil.copy2(p,build/p.name)
    print("compile: PASS")

    out=work/"K01_P007_PMI_STEP13_CURRENT.json"
    cp=run([str(exe),"--part",str(cand),"--manifest",str(manifest),"--output",str(out)],cwd=str(repo))
    if cp.stdout.strip():print(cp.stdout.strip())
    if cp.stderr.strip():print(cp.stderr.strip())
    print("PMI_return_code:",cp.returncode)
    if cp.returncode!=0: raise RuntimeError("P007 PMI save/reopen verification HOLD")
    o=load(out)
    o["source_authority_part"]=str(src)
    o["source_authority_sha256"]=EXPECTED_P007_SHA
    o["candidate_file_sha256"]=sha(cand)
    out.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
    print("P007_PMI_status:",o.get("status"))
    print("candidate:",cand)
    return o

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=r"D:\BreshevEngineering\marvilon-k01")
    ap.add_argument("--package-root",required=True)
    a=ap.parse_args()
    main(Path(a.repo_root).resolve(),Path(a.package_root).resolve())
