from __future__ import annotations
import hashlib,json,os,subprocess
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
OUT=R/"reports"/"cad"/"current"/"K01_REPO_STRUCTURE_AUDIT_V2_20260903.json"

def tracked_set():
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
def snippet(p):
    if p.stat().st_size>8192:return ""
    try:
        b=p.read_bytes()[:500]
        for enc in ("utf-8","utf-16","cp1251","latin1"):
            try:
                s=b.decode(enc)
                return " ".join(s.replace("\r"," ").replace("\n"," ").split())[:180]
            except Exception:pass
    except Exception:pass
    return ""
def main():
    tr=tracked_set();top=[];dups=defaultdict(list)
    for d in sorted([p for p in R.iterdir() if p.is_dir() and p.name not in (".git",".local_archive")],key=lambda p:p.name.lower()):
        files=[p for p in d.rglob("*") if p.is_file() and ".git" not in p.parts and ".local_archive" not in p.parts]
        ex=Counter(p.suffix.lower() or "<none>" for p in files)
        tf=sum(1 for p in files if str(p.relative_to(R)).replace("\\","/") in tr)
        for p in files:
            if p.stat().st_size<=5_000_000:
                h=sha(p)
                if h:dups[h].append(str(p.relative_to(R)))
        top.append({"directory":d.name,"files":len(files),"tracked":tf,"untracked":len(files)-tf,
                    "extensions":dict(ex.most_common(12)),
                    "samples":[str(p.relative_to(R)) for p in files[:16]]})
    duplicate_sets=[v for v in dups.values() if len(v)>1]
    root=[]
    for p in sorted([x for x in R.iterdir() if x.is_file()],key=lambda x:x.name.lower()):
        rel=str(p.relative_to(R)).replace("\\","/")
        root.append({"name":p.name,"size":p.stat().st_size,"tracked":rel in tr,"snippet":snippet(p)})
    rep={"schema":"k01_repo_structure_audit_v2","created_utc":datetime.now(timezone.utc).isoformat(),
         "top_directories":top,"root_files":root,"duplicate_small_file_sets":duplicate_sets[:150]}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("="*100);print("K01 REPO DEEP STRUCTURE AUDIT v2");print("="*100)
    for r in top:
        print(f"{r['directory']:18} files={r['files']:4} tracked={r['tracked']:4} untracked={r['untracked']:4} ext={r['extensions']}")
    print("-"*100);print("ROOT RESIDUAL FILES")
    for x in root:
        print(f"[{'T' if x['tracked'] else 'U'}] {x['name']:34} {x['size']:8} B | {x['snippet']}")
    print("-"*100);print("Duplicate small-file sets:",len(duplicate_sets))
    for x in duplicate_sets[:25]:print("[DUP]",x)
    print("Report:",OUT);return 0
if __name__=="__main__":raise SystemExit(main())
