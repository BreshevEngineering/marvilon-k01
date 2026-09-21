from __future__ import annotations
import argparse, datetime as dt, json, subprocess
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
OUT=Path("reports/control/K01_GIT_GITHUB_STATUS_CURRENT.json")

def run_git(repo:Path,*args):
    cp=subprocess.run(["git",*args],cwd=repo,text=True,capture_output=True,errors="replace")
    return cp.returncode,cp.stdout.strip(),cp.stderr.strip()

def wr(p:Path,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def classify_dirty(lines):
    runtime_prefixes=("reports/","handoff/","Downloads/",".local_archive/","review_upload/")
    source=[]; runtime=[]; unknown=[]
    for line in lines:
        s=line[3:] if len(line)>=4 else line
        s=s.strip().strip('"')
        if any(s.startswith(p) for p in runtime_prefixes): runtime.append(line)
        elif s.startswith(("control/","tools/","tests/","docs/","cad_api/",".github/")) or s in {".gitattributes",".gitignore","README_CURRENT.md","run.cmd"}: source.append(line)
        else: unknown.append(line)
    return source,runtime,unknown

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default=str(R)); a=ap.parse_args(); repo=Path(a.repo_root).resolve()
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    issues=[]
    if not (repo/".git").exists():
        o={"schema":"k01.git_github_status.current.v1","generated_utc":now,"status":"HOLD_NOT_GIT_WORKTREE","issues":[".git missing"]}
        wr(repo/OUT,o); print(o["status"]); return 2
    rc,branch,e=run_git(repo,"branch","--show-current")
    rc2,head,e2=run_git(repo,"rev-parse","HEAD")
    rc3,origin,e3=run_git(repo,"rev-parse","origin/main")
    rc4,ab,e4=run_git(repo,"rev-list","--left-right","--count","origin/main...HEAD")
    rc5,status,e5=run_git(repo,"status","--porcelain=v1")
    ahead=behind=None
    if rc4==0:
        parts=ab.split()
        if len(parts)==2:
            behind=int(parts[0]); ahead=int(parts[1])
    dirty=[x for x in status.splitlines() if x.strip()] if rc5==0 else []
    source,runtime,unknown=classify_dirty(dirty)
    remote_state="UNKNOWN"
    if ahead is not None and behind is not None:
        remote_state="SYNCED" if ahead==0 and behind==0 else ("DIVERGED" if ahead>0 and behind>0 else ("AHEAD" if ahead>0 else "BEHIND"))
    if rc or rc2 or rc3 or rc4 or rc5: issues.append("git command failure")
    if remote_state in {"BEHIND","DIVERGED"}: issues.append("remote divergence requires reconciliation before mutation")
    if unknown: issues.append("unclassified dirty paths present")
    status_name="PASS_GIT_GITHUB_STATUS" if not issues else "HOLD_GIT_GITHUB_STATUS"
    o={
      "schema":"k01.git_github_status.current.v1","generated_utc":now,"status":status_name,
      "branch":branch or None,"local_head":head or None,"origin_main_head":origin or None,
      "ahead":ahead,"behind":behind,"remote_state":remote_state,
      "dirty_count":len(dirty),"dirty_classification":{
          "ACTIVE_SOURCE_OR_CONTROLLED_CHANGES":len(source),
          "RUNTIME_GENERATED":len(runtime),
          "UNCLASSIFIED":len(unknown)},
      "source_or_controlled_changes":source[:500],"runtime_generated":runtime[:500],"unclassified":unknown[:500],
      "issues":issues,
      "rule":"Git/GitHub is configuration evidence, not engineering-value authority. Dirty != engineering HOLD unless identity or reproducibility is unsafe."
    }
    wr(repo/OUT,o)
    print(status_name,"branch=",branch,"ahead=",ahead,"behind=",behind,"dirty=",len(dirty),"unknown=",len(unknown))
    return 0 if remote_state not in {"BEHIND","DIVERGED"} else 2

if __name__=="__main__": raise SystemExit(main())
