from __future__ import annotations
from pathlib import Path
import json,hashlib,datetime,sys

REPO=Path(r"D:\BreshevEngineering\marvilon-k01")
GOAL_CAND=[REPO/"control/project/K01_GOAL_LOCK_CURRENT.json",REPO/"control/project/K01_CURRENT_DELIVERABLE.json"]
FRONT=REPO/"control/state/K01_COMPLETION_FRONTIER_CURRENT.json"
OUT=REPO/"control/system/K01_OPERATOR_LOCK_CURRENT.json"

def rd(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    gp=next((p for p in GOAL_CAND if p.is_file()),None)
    if gp is None or not FRONT.is_file():
        print("HOLD: Goal Lock or Completion Frontier missing.");return 2
    f=rd(FRONT)
    goal=f.get("current_deliverable")
    obj=f.get("active_engineering_object")
    n=f.get("next_allowed_action") or {}
    wid=n.get("id")
    text=n.get("text")
    print("============================================================")
    print("K01 OPERATOR LOCK RC1")
    print("============================================================")
    print("GOAL LOCK:",goal)
    print("ACTIVE OBJECT:",obj)
    print("ACTIVE WORKPACK:",wid)
    print("NEXT:",text)
    print("")
    print("This confirmation means:")
    print("- the displayed Goal Lock is the work you intend K01 to pursue;")
    print("- this is the single active engineering workpack;")
    print("- other work remains parked/waiting/debt unless explicitly promoted.")
    print("")
    ans=input("Type CONFIRM to record the operator lock: ").strip()
    if ans!="CONFIRM":
        print("NO CHANGE: operator lock was not confirmed.");return 2
    rec={
      "schema":"k01.operator_lock.current.v1",
      "confirmed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "confirmed_goal_lock":goal,
      "confirmed_active_engineering_object":obj,
      "confirmed_active_workpack_id":wid,
      "confirmed_active_workpack_text":text,
      "goal_lock_source":gp.relative_to(REPO).as_posix(),
      "goal_lock_sha256":sha(gp),
      "frontier_source":FRONT.relative_to(REPO).as_posix(),
      "frontier_sha256":sha(FRONT),
      "rule":"Stale automatically when Goal Lock, Completion Frontier, ACTIVE workpack or source hashes change. Reconfirmation is then required."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS_OPERATOR_LOCK_CONFIRMED")
    print("OUT:",OUT)
    return 0
if __name__=="__main__":raise SystemExit(main())
