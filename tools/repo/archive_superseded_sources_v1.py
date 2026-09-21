from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
from datetime import datetime, timezone

def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def tree_sig(p):
    files=sorted(x for x in p.rglob("*") if x.is_file()); h=hashlib.sha256()
    for f in files:
        rel=f.relative_to(p).as_posix(); h.update(rel.encode()); h.update(b"\0"); h.update(sha(f).encode()); h.update(b"\n")
    return len(files),h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default="."); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    reg=load(root/"control/repo/K01_SUPERSEDED_SOURCE_REGISTRY_CURRENT.json")
    rows=[]; issues=[]
    for u in reg.get("move_units",[]):
        src=root/u["source_path"]; dst=root/u["archive_path"]; kind=u["kind"]
        try:
            if src.exists() and dst.exists():
                if kind=="FILE":
                    if sha(src)!=sha(dst): raise RuntimeError("source+archive both exist with different hash")
                    src.unlink(); action="DEDUP_SOURCE_REMOVED"
                else:
                    sc,ss=tree_sig(src); dc,ds=tree_sig(dst)
                    if (sc,ss)!=(dc,ds): raise RuntimeError("source+archive both exist with different tree signature")
                    shutil.rmtree(src); action="DEDUP_SOURCE_TREE_REMOVED"
            elif src.exists():
                dst.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(src),str(dst)); action="MOVED_TO_ARCHIVE"
            elif dst.exists(): action="ALREADY_ARCHIVED"
            else: raise RuntimeError("neither source nor archive path exists")
            if src.exists(): raise RuntimeError("source remains after migration")
            if kind=="FILE":
                got=sha(dst); exp=u.get("source_sha256")
                if exp and got!=exp: raise RuntimeError(f"archive SHA mismatch expected={exp} got={got}")
                evidence={"sha256":got}
            else:
                cnt,sig=tree_sig(dst); expc=u.get("source_file_count"); exps=u.get("source_tree_sha256")
                if expc is not None and cnt!=expc: raise RuntimeError(f"archive count mismatch expected={expc} got={cnt}")
                if exps and sig!=exps: raise RuntimeError(f"archive tree hash mismatch expected={exps} got={sig}")
                evidence={"file_count":cnt,"tree_sha256":sig}
            rows.append({"source":u["source_path"],"archive":u["archive_path"],"action":action,**evidence})
        except Exception as e: issues.append({"source":u["source_path"],"archive":u["archive_path"],"error":repr(e)})
    status="PASS_ARCHIVE_MIGRATION" if not issues else "HOLD_ARCHIVE_MIGRATION"
    rep={"schema":"k01.archive_migration.current.v1","generated_utc":datetime.now(timezone.utc).isoformat(),"status":status,"items":rows,"issues":issues}
    out=root/"reports/control/K01_ARCHIVE_MIGRATION_CURRENT.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ARCHIVE_MIGRATION:",status,"items=",len(rows),"issues=",len(issues)); print("REPORT:",out)
    for x in issues: print("HOLD:",json.dumps(x,ensure_ascii=False))
    return 0 if not issues else 2
if __name__=="__main__": raise SystemExit(main())
