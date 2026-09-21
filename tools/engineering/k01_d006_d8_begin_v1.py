from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
QA=Path("reports/drawing/current/K01-D-006_V2_SEMANTIC_NATIVE_QA_CURRENT.json")
D8=Path("control/drawings/K01_D006_D8_WORKPACK_CURRENT.json")
LEASE=Path("control/state/K01_NATIVE_MUTATION_LEASE_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")

def rd(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def now():return dt.datetime.now(dt.timezone.utc).isoformat()

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));ap.add_argument("--owner",default=os.environ.get("USERNAME","K01_USER"));a=ap.parse_args();repo=Path(a.repo_root)
 for rel in (QA,D8,NEXT):
  if not (repo/rel).exists():raise SystemExit("HOLD: missing "+str(rel))
 qa=rd(repo/QA);wp=rd(repo/D8);n=rd(repo/NEXT)
 if qa.get("status")!="PASS_D006_SEMANTIC_NATIVE_QA__READY_FOR_D8":raise SystemExit("HOLD: semantic/native QA not PASS.")
 if n.get("next_action_id")!="K01-NA-D006-D8-VISUAL-QA":raise SystemExit("HOLD: frontier is not D8.")
 cand=Path(wp.get("candidate",""))
 if not cand.is_file():raise SystemExit("HOLD: D8 candidate missing.")
 lease={"schema":"k01.native_mutation_lease.current.v1","lease_id":"K01-D006-D8-"+dt.datetime.now().strftime("%Y%m%d_%H%M%S"),"status":"ACTIVE","owner_session":a.owner,"artifact_id":"K01-D-006-V2-D8-CANDIDATE","native_path":str(cand),"baseline_candidate_sha256":sha(cand),"allowed_operation":"PRESENTATION_ONLY_D8: move annotations/views/leaders; update title/status wording; regenerate candidate PDF/BMP. NO ENGINEERING VALUE CHANGES. NO CURRENT OVERWRITE.","start_utc":now(),"rollback_reference":"Candidate baseline SHA is recorded; current/ and source P007 are outside mutation scope."}
 wr(repo/LEASE,lease)
 print("LEASE ACTIVE:",lease["lease_id"])
 print("CANDIDATE:",cand)
 print("WORKPACK:",repo/D8)
 print("ALLOWED: presentation-only D8 changes.")
 print("FORBIDDEN: engineering values, P007 source, current D006.")
 print("After save/close, do NOT publish current yet; run automated/human D8 closeout.")
 return 0
if __name__=="__main__":raise SystemExit(main())
