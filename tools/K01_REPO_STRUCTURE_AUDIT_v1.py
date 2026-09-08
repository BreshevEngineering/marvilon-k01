from __future__ import annotations
import hashlib,json,os,subprocess
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
OUT=R/"reports"/"cad"/"current"/"K01_REPO_STRUCTURE_AUDIT_20260903.json"

def tracked_files():
    try:
        out=subprocess.check_output(["git","ls-files"],cwd=R,text=True,errors="ignore")
        return {x.strip().replace("\\","/") for x in out.splitlines() if x.strip()}
    except Exception:return set()
def sha(p):
    h=hashlib.sha256()
    try:
        with p.open("rb") as f:
            for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
        return h.hexdigest()
    except Exception:return None
def main():
    tr=tracked_files();top=[];dups=defaultdict(list)
    for d in sorted([p for p in R.iterdir() if p.is_dir() and p.name not in (".git",".local_archive")],key=lambda p:p.name.lower()):
        files=[p for p in d.rglob("*") if p.is_file() and ".git" not in p.parts and ".local_archive" not in p.parts]
        ex=Counter(p.suffix.lower() or "<none>" for p in files)
        tf=sum(1 for p in files if str(p.relative_to(R)).replace("\\","/") in tr)
        for p in files:
            if p.stat().st_size<=5_000_000:
                h=sha(p)
                if h:dups[h].append(str(p.relative_to(R)))
        top.append({"directory":d.name,"files":len(files),"tracked":tf,"untracked":len(files)-tf,
                    "extensions":dict(ex.most_common(10)),
                    "samples":[str(p.relative_to(R)) for p in files[:12]]})
    duplicate_sets=[v for v in dups.values() if len(v)>1]
    root_files=[str(p.name) for p in R.iterdir() if p.is_file()]
    rep={"schema":"k01_repo_structure_audit_v1","created_utc":datetime.now(timezone.utc).isoformat(),
         "top_directories":top,"root_files":root_files,
         "duplicate_small_file_sets":duplicate_sets[:100],
         "focus":"Review overlapping cad_api/scripts/tools and legacy support dirs before moving anything."}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("="*96);print("K01 REPO DEEP STRUCTURE AUDIT");print("="*96)
    for r in top:
        print(f"{r['directory']:18} files={r['files']:4} tracked={r['tracked']:4} untracked={r['untracked']:4} ext={r['extensions']}")
    print("Root files:",root_files)
    print("Duplicate small-file sets:",len(duplicate_sets))
    for x in duplicate_sets[:20]:print("[DUP]",x)
    print("Report:",OUT);return 0
if __name__=="__main__":raise SystemExit(main())
