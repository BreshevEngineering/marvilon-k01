from __future__ import annotations
import argparse, datetime as dt, hashlib, json, re
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
REPORT=Path("reports/control/K01_DECISION_IDENTITY_COHERENCE_CURRENT.json")

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default
def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def did(d,p):
    for k in ("decision_id","edr_id","id"):
        v=d.get(k)
        if isinstance(v,str) and re.fullmatch(r"EDR-\d+",v,re.I): return v.upper()
    m=re.match(r"(EDR-\d+)",p.name,re.I)
    return m.group(1).upper() if m else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root).resolve()
    issues=[]; rows=[]; by={}
    root=repo/"control/decisions"
    if not root.is_dir():
        print("HOLD_DECISION_IDENTITY_COHERENCE missing control/decisions");return 2
    # Active authorities are root-level EDR files only. history/** is provenance, not active authority.
    for p in sorted(root.glob("EDR-*.json")):
        d=rd(p,None); rel=p.relative_to(repo).as_posix()
        if not isinstance(d,dict):
            issues.append({"rule":"DEC-ID-JSON","path":rel});continue
        x=did(d,p)
        if not x:
            issues.append({"rule":"DEC-ID-MISSING","path":rel});continue
        rec={"decision_id":x,"path":rel,"sha256":sha(p),"status":d.get("status"),"subject":d.get("subject")}
        rows.append(rec);by.setdefault(x,[]).append(rec)
    for x,recs in by.items():
        if len(recs)>1:
            issues.append({"rule":"DEC-ID-DUPLICATE","decision_id":x,"paths":[r["path"] for r in recs],
                           "detail":"Exactly one active root decision file may own a decision_id."})
    disp=rd(repo/"control/decisions/K01_DECISION_AUTHORITY_DISPOSITION_EDR047.json",{}) or {}
    if disp:
        cp=repo/(disp.get("canonical_active_path") or "")
        hp=repo/(disp.get("superseded_history_path") or "")
        if not cp.is_file() or sha(cp)!=disp.get("canonical_sha256"):
            issues.append({"rule":"DEC-DISP-CANONICAL","detail":"EDR-047 canonical file missing/hash mismatch"})
        if not hp.is_file() or sha(hp)!=disp.get("superseded_sha256"):
            issues.append({"rule":"DEC-DISP-HISTORY","detail":"EDR-047 superseded history missing/hash mismatch"})
    status="PASS_DECISION_IDENTITY_COHERENCE" if not issues else "HOLD_DECISION_IDENTITY_COHERENCE"
    rep={"schema":"k01.decision_identity_coherence.current.v1","generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
         "status":status,"issues":issues,"active_decisions":rows,
         "rule":"One active root EDR file per decision_id; superseded variants live under history with explicit disposition."}
    wr(repo/REPORT,rep)
    print(status,"issues=",len(issues))
    for x in issues: print("HOLD:",json.dumps(x,ensure_ascii=False))
    print("REPORT:",repo/REPORT)
    return 0 if not issues else 2
if __name__=="__main__":raise SystemExit(main())
