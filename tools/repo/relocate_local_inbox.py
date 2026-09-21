from __future__ import annotations
import argparse, shutil
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(
        description="Relocate untracked local _inbox only to an explicitly supplied target."
    )
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--target",default=None)
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    src=root/"_inbox"

    if not src.exists():
        print("PASS: repository _inbox absent")
        return 0

    files=[p for p in src.rglob("*") if p.is_file()]
    print("SOURCE:",src)
    print("FILES:",len(files))

    if not a.target:
        print("HOLD: explicit --target is required. No default destination is allowed.")
        print("No files moved.")
        return 2

    target=Path(a.target).expanduser().resolve()
    print("TARGET:",target)
    print("STATUS:","PASS_READY_TO_APPLY" if not a.apply else "APPLYING")

    if not a.apply:
        return 0

    target.mkdir(parents=True,exist_ok=True)
    for p in files:
        rel=p.relative_to(src)
        dst=target/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            i=1
            while True:
                alt=dst.with_name(dst.stem+"_moved%d"%i+dst.suffix)
                if not alt.exists():
                    dst=alt
                    break
                i+=1
        shutil.move(str(p),str(dst))

    for d in sorted([p for p in src.rglob("*") if p.is_dir()],reverse=True):
        try:d.rmdir()
        except OSError:pass
    try:src.rmdir()
    except OSError:pass

    print("PASS_APPLIED:",target)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
