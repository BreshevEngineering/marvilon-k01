from __future__ import annotations
import argparse, datetime as dt, hashlib, json, re
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
P={
 "epoch":Path("control/state/K01_STATE_EPOCH_CURRENT.json"),
 "manifest":Path("control/project/K01_CURRENT_SESSION_MANIFEST.json"),
 "goal":Path("control/project/K01_GOAL_LOCK_CURRENT.json"),
 "next":Path("control/project/K01_NEXT_ACTIONS_CURRENT.json"),
 "gate":Path("control/project/K01_ACTIVE_STEP_GATE.json"),
 "frontier":Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json"),
 "rules":Path("control/project/K01_AI_SESSION_RULES_CURRENT.json"),
 "visual":Path("control/drawings/K01_D006_VISUAL_QA_CURRENT.json"),
 "resume":Path("reports/control/K01_RESUME_CURRENT.json"),
 "center":Path("control/center/K01_CENTER_INPUT_CURRENT.json"),
 "center_master":Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")
}

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

VOLATILE_KEY_RE=re.compile(
    r"(?:^|_)(?:generated|captured|timestamp|mtime|modified|created|elapsed|duration|"
    r"sha(?:256)?|hash|fingerprint|bytes|size_bytes|source_digest|source_digests)(?:$|_)",
    re.I
)
VOLATILE_EXACT={
    "state_epoch","source_state_fingerprint","generated_utc","captured_utc",
    "captured_local_time","captured_unix","timestamp","source_fingerprints"
}

def semantic_canonicalize(o):
    """Remove regeneration/provenance noise while preserving engineering state."""
    if isinstance(o,dict):
        out={}
        for k,v in o.items():
            ks=str(k)
            if ks in VOLATILE_EXACT or VOLATILE_KEY_RE.search(ks):
                continue
            out[ks]=semantic_canonicalize(v)
        return out
    if isinstance(o,list):
        return [semantic_canonicalize(v) for v in o]
    return o

def canonical_hash(o):
    x=semantic_canonicalize(json.loads(json.dumps(o)))
    return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()

def semantic_file_hash(p):
    """Stable semantic digest for generated JSON/text reports used by the State Epoch."""
    if not p.is_file():
        return "MISSING"
    if p.suffix.lower()==".json":
        try:
            return canonical_hash(json.loads(p.read_text(encoding="utf-8-sig")))
        except Exception:
            pass
    try:
        txt=p.read_text(encoding="utf-8-sig",errors="strict").replace("\r\n","\n")
        # Strip only common generated-at lines from Markdown/text summaries.
        kept=[]
        for line in txt.splitlines():
            if re.match(r"^\s*(Generated|Generated UTC|Captured|Timestamp|State epoch):",line,re.I):
                continue
            kept.append(line)
        return hashlib.sha256(("\n".join(kept)+"\n").encode("utf-8")).hexdigest()
    except Exception:
        return sha(p)

def edr_num(s):
    m=re.search(r"EDR-(\d+)",str(s or ""),re.I)
    return int(m.group(1)) if m else -1

def decision_id(d,p):
    return d.get("decision_id") or d.get("id") or (re.match(r"(EDR-\d+)",p.name,re.I).group(1) if re.match(r"(EDR-\d+)",p.name,re.I) else p.stem)

def candidate_status(s):
    u=str(s or "").upper()
    return "CANDIDATE" in u or ("CONDITIONAL" in u and "RELEASE_DEFINITION" not in u)

def closed_status(s):
    u=str(s or "").upper()
    if any(x in u for x in ("REJECT","OPEN","HOLD")):return False
    if candidate_status(u):return False
    return any(x in u for x in ("ACCEPTED","PASS_DECISION","DECIDED","CONTROLLED_SCOPE_DECISION"))

def summary(d):
    return d.get("title") or d.get("subject") or d.get("problem") or ""

def source_rows(repo,goal,front,active):
    """Return engineering/control authorities that DEFINE the State Epoch.

    Generated CURRENT reports are deliberately excluded from this set. They are
    observations/projections of the state, not inputs to the state identity.
    This prevents a self-referential loop where regenerating a report changes the
    State Epoch that the report is supposed to describe.
    """
    rows=[
      {"path":"goal","sha256":canonical_hash(goal),"hash_mode":"semantic_object"},
      {"path":"frontier","sha256":canonical_hash(front),"hash_mode":"semantic_object"}
    ]

    # Active decisions and explicit engineering authorities are exact content
    # authorities: any byte-level change must move the State Epoch.
    for p in sorted((repo/"control/decisions").glob("EDR-*.json")):
        rows.append({"path":p.relative_to(repo).as_posix(),"sha256":sha(p),"hash_mode":"raw_file"})

    authority_files=[
      "control/project/K01_CHECKPOINT_CURRENT.json",
      "control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json",
      "control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json",
      "control/decisions/K01_DECISION_AUTHORITY_DISPOSITION_EDR047.json",
      "control/product_definition/K01_CONTROLLED_CHARACTERISTIC_REGISTRY_CURRENT.json",
      "control/engineering/K01_ENGINEERING_REFERENCE_REGISTRY_CURRENT.json",
      "cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_OPERATING_STANDARD_CURRENT.txt"]
    for rel in authority_files:
        p=repo/rel
        rows.append({"path":rel,"sha256":sha(p) if p.is_file() else "MISSING","hash_mode":"raw_file"})

    dynamic=[]
    if active=="K01-P-004":
        dynamic=[
          ("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json","authority"),
          ("reports/product_definition/K01-P-004_READINESS_CURRENT.json","derived"),
          ("reports/engineering/K01_P004_THERMAL_TOLERANCE_SCREEN_CURRENT.json","derived"),
          ("reports/inspection/K01-P-004_INSPECTION_PLAN_CURRENT.json","derived")]
    elif active=="K01-P-007" or "D-006" in str(goal.get("current_deliverable","")):
        dynamic=[
          ("control/product_definition/K01_P007_PRODUCT_DEFINITION_RELEASE_CURRENT.json","authority"),
          ("reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json","derived"),
          ("control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json","authority")]
    for rel,kind in dynamic:
        if kind!="authority":
            continue
        p=repo/rel
        rows.append({"path":rel,"sha256":sha(p) if p.is_file() else "MISSING","hash_mode":"raw_file"})
    return rows

def projection_rows(repo,goal,active):
    """Return derived projections observed at reducer time.

    These digests are checked by the temporal guard for drift between projection
    generation and guard execution, but they DO NOT participate in the State Epoch
    fingerprint.
    """
    derived_reports=[
      "reports/control/K01_DRAWING_CONTROL_CURRENT.json",
      "reports/control/K01_BOM_RELEASE_STATUS_CURRENT.json",
      "reports/control/K01_ANALYSIS_REGISTER_CURRENT.json",
      "reports/control/K01_ENGINEERING_SYSTEM_COVERAGE_CURRENT.json",
      "reports/control/K01_GIT_GITHUB_STATUS_CURRENT.json",
      "reports/control/K01_DECISION_IDENTITY_COHERENCE_CURRENT.json",
      "reports/control/K01_ENGINEERING_VALUE_COHERENCE_CURRENT.json",
      "reports/control/K01_PROJECT_CONTROL_SPINE_CURRENT.json"]
    rows=[
      {"path":rel,"sha256":semantic_file_hash(repo/rel),"hash_mode":"semantic_file"}
      for rel in derived_reports
    ]

    dynamic=[]
    if active=="K01-P-004":
        dynamic=[
          "reports/product_definition/K01-P-004_READINESS_CURRENT.json",
          "reports/engineering/K01_P004_THERMAL_TOLERANCE_SCREEN_CURRENT.json",
          "reports/inspection/K01-P-004_INSPECTION_PLAN_CURRENT.json"]
    elif active=="K01-P-007" or "D-006" in str(goal.get("current_deliverable","")):
        dynamic=["reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json"]
    for rel in dynamic:
        rows.append({"path":rel,"sha256":semantic_file_hash(repo/rel),"hash_mode":"semantic_file"})
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(R))
    a=ap.parse_args()
    repo=Path(a.repo_root).resolve()
    now=dt.datetime.now(dt.timezone.utc).isoformat()

    for k in ("goal","next","gate","frontier"):
        if not (repo/P[k]).is_file():
            raise SystemExit("HOLD: missing "+str(P[k]))

    goal=rd(repo/P["goal"],{}) or {}
    front=rd(repo/P["frontier"],{}) or {}
    n0=rd(repo/P["next"],{}) or {}
    gate=rd(repo/P["gate"],{}) or {}

    deliver=goal.get("current_deliverable")
    fdel=front.get("current_deliverable")
    active=front.get("active_engineering_object")
    level=front.get("current_lifecycle_level")
    if not deliver or deliver!=fdel:
        raise SystemExit(f"HOLD: Goal/Frontier deliverable mismatch: {deliver!r} != {fdel!r}")
    if not active or not level:
        raise SystemExit("HOLD: Completion Frontier missing active engineering object/lifecycle level.")

    timing=front.get("timing") or {}
    if len(timing.get("ACTIVE_NOW") or [])!=1:
        raise SystemExit("HOLD: exactly one ACTIVE_NOW required before reconciliation.")

    na=front.get("next_allowed_action") or {}
    nid=na.get("id")
    ntxt=na.get("text")
    exp=na.get("expected_closure")
    blocker=(front.get("active_blocker") or {}).get("id") if isinstance(front.get("active_blocker"),dict) else front.get("active_blocker")
    if not nid or not ntxt or not exp or not blocker:
        raise SystemExit("HOLD: Completion Frontier blocker/NEXT/expected closure is incomplete.")

    # Completion Frontier is the canonical execution-navigation source.
    # Reconcile Goal Lock navigation BEFORE computing the State Epoch fingerprint,
    # otherwise stale local NEXT fields can survive in Goal Lock and create a
    # self-changing epoch on the next sync.
    active_dep=front.get("active_dependency") or goal.get("active_dependency")
    execution_mode=na.get("execution_mode") or goal.get("current_execution_mode")
    state_semantics=dict(goal.get("state_semantics") or {})
    state_semantics.update({
      "CURRENT_DELIVERABLE":fdel,
      "CURRENT_LIFECYCLE_LEVEL":level,
      "ACTIVE_ENGINEERING_OBJECT":active,
      "ACTIVE_DEPENDENCY":active_dep,
      "ACTIVE_BLOCKER":blocker,
      "NEXT_ACTION_ID":nid,
      "EXPECTED_CLOSURE":exp,
      "rule":"Global execution navigation is reduced from Completion Frontier; local parked branches cannot overwrite Global NEXT."
    })
    anti_loop=dict(goal.get("anti_loop") or {})
    anti_loop["current_application"]=(
      f"Keep WIP=1 on {blocker}. WAITING_EXTERNAL/WAITING_DEPENDENCY work remains visible "
      "in project coverage but does not own Global NEXT while another lifecycle-critical workpack is executable."
    )
    goal.update({
      "current_deliverable":fdel,
      "current_lifecycle_level":level,
      "active_engineering_object":active,
      "active_dependency":active_dep,
      "current_execution_mode":execution_mode,
      "next_action_id":nid,
      "next_action":ntxt,
      "expected_closure":exp,
      "state_semantics":state_semantics,
      "anti_loop":anti_loop
    })

    decisions=[]
    for p in sorted((repo/"control/decisions").glob("EDR-*.json")):
        d=rd(p,{}) or {}
        did=decision_id(d,p)
        st=d.get("status") or d.get("decision") or ""
        decisions.append({"id":did,"n":edr_num(did),"status":st,"summary":summary(d),"path":p.relative_to(repo).as_posix(),"sha256":sha(p)})
    decisions.sort(key=lambda x:x["n"])
    closed=[x for x in decisions if closed_status(x["status"])]
    candidates=[x for x in decisions if candidate_status(x["status"])]
    last_closed=max(closed,key=lambda x:x["n"]) if closed else None
    latest=max(decisions,key=lambda x:x["n"]) if decisions else None
    latest_cand=max(candidates,key=lambda x:x["n"]) if candidates else None

    rows=source_rows(repo,goal,front,active)
    projections=projection_rows(repo,goal,active)
    fp=hashlib.sha256("\n".join(f"{r['path']}\t{r['sha256']}" for r in rows).encode()).hexdigest()
    epoch="K01-SE-"+fp[:16]
    checkpoint=rd(repo/"control/project/K01_CHECKPOINT_CURRENT.json",{}) or {}

    wr(repo/P["epoch"],{
      "schema":"k01.state_epoch.current.v2_lifecycle",
      "state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp,
      "goal_lock":deliver,"current_lifecycle_level":level,"active_engineering_object":active,
      "checkpoint":checkpoint.get("checkpoint_id") or checkpoint.get("id"),
      "last_closed_decision":last_closed,"latest_engineering_activity":latest,
      "source_fingerprints":rows,
      "projection_observations":projections,
      "fingerprint_policy":{
        "state_epoch_inputs":"authority/control sources only",
        "projection_rule":"generated CURRENT projections are observed and guarded but do not define State Epoch"
      }})

    goal.update({"state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp})
    wr(repo/P["goal"],goal)

    front.update({"state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp})
    wr(repo/P["frontier"],front)

    n=dict(n0)
    n.update({
      "state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp,
      "current_lifecycle_level":level,"current_deliverable":deliver,
      "deliverable_class":goal.get("deliverable_class"),"wip_limit":1,
      "active_engineering_object":active,
      "active_dependency":front.get("active_dependency") or goal.get("active_dependency"),
      "active_blocker":blocker,"current_blocker":blocker+":OPEN",
      "next_1":ntxt,"next_action_id":nid,"expected_closure":exp,
      "current_stage":f"{level} {front.get('lifecycle_name','')} / {active}",
      "execution_mode":na.get("execution_mode") or n.get("execution_mode")})
    wr(repo/P["next"],n)

    gate.update({"state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp,
                 "current_lifecycle_level":level,"active_blocker":blocker,
                 "step_id":"K01-STEP-"+re.sub(r"[^A-Z0-9]+","-",str(blocker).upper()).strip("-"),
                 "active_line":front.get("active_dependency") or goal.get("active_dependency"),
                 "intent":nid,"intent_text":ntxt,"expected_closure":exp})
    wr(repo/P["gate"],gate)

    art=goal.get("current_artifact") or {}
    manifest={
      "schema":"k01.current_session_manifest.v2_lifecycle",
      "state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp,
      "project":goal.get("project","K01 / MARVILON"),"checkpoint":checkpoint,
      "goal":{"current_lifecycle_level":level,"current_deliverable":deliver,
              "deliverable_class":goal.get("deliverable_class"),"wip_limit":1,
              "active_engineering_object":active,"active_dependency":goal.get("active_dependency"),
              "execution_mode":goal.get("current_execution_mode")},
      "active_artifact":{"drawing":art.get("drawing"),"pdf":art.get("pdf"),"status":art.get("status")},
      "engineering_state":{"last_closed":last_closed,"latest_activity":latest,"latest_candidate":latest_cand,
                           "closed_do_not_restart":[x["id"] for x in closed if x["n"]>=25],
                           "candidate_not_release":[x["id"] for x in candidates if x["n"]>=25]},
      "completion_frontier":{"active_blocker":blocker,"next_action_id":nid,"expected_closure":exp,"timing":timing},
      "next_allowed_action":{"id":nid,"text":ntxt,"expected_closure":exp,"authority_set":na.get("authority_set") or []},
      "authority_rule":"Manifest controls current-session navigation only; engineering values remain in domain authorities.",
      "center_mode":"PROJECTION_ONLY"}
    wr(repo/P["manifest"],manifest)

    resume=rd(repo/P["resume"],{}) or {}
    resume.update({"schema":"k01.resume.current.v4_lifecycle","state_epoch":epoch,"generated_utc":now,"project":"K01"})
    resume["active_work"]={"current_lifecycle_level":level,"current_deliverable":deliver,
                           "active_engineering_object":active,"active_dependency":goal.get("active_dependency"),
                           "active_blocker":blocker,"next_1":ntxt,"expected_closure":exp,
                           "waiting_external":timing.get("WAITING_EXTERNAL") or []}
    wr(repo/P["resume"],resume)

    waiting=timing.get("WAITING_EXTERNAL") or []
    start_lines=[
      "# K01 START HERE","",
      "> AUTO-GENERATED STATE_CURRENT. Do not hand-edit.",
      f"> State epoch: `{epoch}`","",
      "## Main engineering front",
      f"- Lifecycle: **{level} — {front.get('lifecycle_name','')}**",
      f"- Deliverable: **{deliver}**",
      f"- Active engineering object: **{active}**",
      f"- Active dependency: **{goal.get('active_dependency')}**",
      f"- Active blocker: **{blocker}**",
      "- WIP: **1**","",
      "## Waiting external / downstream",
    ]
    start_lines += [f"- {x}" for x in waiting] if waiting else ["- None"]
    start_lines += [
      "","## Last engineering activity",
      f"- Last closed: **{last_closed['id'] if last_closed else 'OPEN'}** — {last_closed['summary'] if last_closed else ''}",
      f"- Latest activity: **{latest['id'] if latest else 'OPEN'}** — {latest['status'] if latest else ''}",
      "","## Exact next allowed action",f"**{ntxt}**","",f"Expected closure: `{exp}`","",
      "## Mandatory read order",
      "1. `control/state/K01_STATE_EPOCH_CURRENT.json`",
      "2. `control/project/K01_CURRENT_SESSION_MANIFEST.json`",
      "3. `reports/control/K01_SESSION_CLOSE_CURRENT.md`",
      "4. `reports/control/K01_START_HERE.md`",
      "5. `control/project/K01_GOAL_LOCK_CURRENT.json`",
      "6. `control/state/K01_COMPLETION_FRONTIER_CURRENT.json`",
      "7. active authority set from the Completion Frontier","",
      "## Non-negotiable",
      "- Product > Evidence > Automation.",
      "- OPEN/PARTIAL remains OPEN/PARTIAL.",
      "- Screening/analytical PASS is not physical qualification or release PASS.",
      "- Drawing candidates do not replace Drawing Control authority."]
    (repo/"reports/control/K01_START_HERE.md").write_text("\n".join(start_lines)+"\n",encoding="utf-8")

    session_lines=[
      "# K01 SESSION CLOSE / CURRENT RESUME AUTHORITY","",
      f"State epoch: `{epoch}`",f"Generated: `{now}`","",
      "## Current lifecycle",f"- Level: **{level}**",f"- Deliverable: **{deliver}**",
      f"- Active object: **{active}**",f"- Active blocker: **{blocker}**","",
      "## Exact NEXT",f"**{ntxt}**",f"Expected closure: `{exp}`","",
      "## Waiting external"]
    session_lines += [f"- {x}" for x in waiting] if waiting else ["- None"]
    session_lines += ["","## Authority rule",
                      "Navigation is reduced from Goal Lock + Completion Frontier + current engineering authorities.",
                      "Native CAD/drawing authority is not changed by this state reducer."]
    (repo/"reports/control/K01_SESSION_CLOSE_CURRENT.md").write_text("\n".join(session_lines)+"\n",encoding="utf-8")

    readme_lines=[
      "# K01 CURRENT ENTRY POINT","",f"> AUTO-GENERATED. State epoch: `{epoch}`","",
      f"Current lifecycle: **{level}**",f"Current deliverable: **{deliver}**",
      f"Active object: **{active}**",f"Active blocker: **{blocker}**",f"NEXT: **{ntxt}**","",
      "Read State Epoch -> Session Manifest -> Session Close -> START HERE -> Goal Lock -> Completion Frontier -> authority set."]
    (repo/"README_CURRENT.md").write_text("\n".join(readme_lines)+"\n",encoding="utf-8")

    visual=rd(repo/P["visual"],{}) or {}
    visual["state_epoch"]=epoch
    visual["generated_utc"]=now
    if art.get("drawing"):visual["source_drawing"]=art.get("drawing")
    if art.get("pdf"):visual["source_pdf"]=art.get("pdf")
    if visual:wr(repo/P["visual"],visual)

    rules=rd(repo/P["rules"],{}) or {}
    rules.update({"state_epoch":epoch,"generated_utc":now,"startup_mode":"TARGETED_STATE_RECONCILIATION"})
    authority=[x for x in (na.get("authority_set") or []) if isinstance(x,str)]
    rules["first_read_order"]=[
      "control/state/K01_STATE_EPOCH_CURRENT.json",
      "control/project/K01_CURRENT_SESSION_MANIFEST.json",
      "reports/control/K01_SESSION_CLOSE_CURRENT.md",
      "reports/control/K01_START_HERE.md",
      "control/project/K01_GOAL_LOCK_CURRENT.json",
      "control/state/K01_COMPLETION_FRONTIER_CURRENT.json"]+authority
    wr(repo/P["rules"],rules)

    center=rd(repo/P["center"],{}) or {}
    center.update({"state_epoch":epoch,"generated_utc":now,
                   "current_session_manifest":str(P["manifest"]).replace("\\","/"),
                   "state_epoch_source":str(P["epoch"]).replace("\\","/"),
                   "goal_lock":str(P["goal"]).replace("\\","/"),
                   "completion_frontier":str(P["frontier"]).replace("\\","/"),
                   "policy":"Center is projection only."})
    wr(repo/P["center"],center)

    cm=rd(repo/P["center_master"],{}) or {}
    if cm:
        cm.update({"state_epoch":epoch,"generated_utc":now,"current_lifecycle_level":level,
                   "current_deliverable":deliver,"active_engineering_object":active,
                   "active_blocker":blocker,"next_action_id":nid})
        wr(repo/P["center_master"],cm)

    wr(repo/"reports/control/K01_TZ_EXECUTION_STATE_CURRENT.json",{
      "schema":"k01.tz.execution_state.current.v3_lifecycle","state_epoch":epoch,
      "generated_utc":now,"status":"PASS_LIFECYCLE_STATE_REDUCED",
      "current_lifecycle_level":level,"current_deliverable":deliver,
      "active_engineering_object":active,"active_blocker":blocker,"next_action":ntxt})
    wr(repo/"control/state/K01_CURRENT_INDEX_CURRENT.json",{
      "schema":"k01.current_index.current.v2_lifecycle","state_epoch":epoch,"generated_utc":now,
      "state_current":[str(P[x]).replace("\\","/") for x in ("epoch","manifest","goal","frontier","next","gate")],
      "domain_current_rule":"Domain CURRENT cannot override global state; engineering values remain in domain authorities."})

    print("STATE_SYNC: PASS_LIFECYCLE_REDUCER_V2")
    print("STATE_EPOCH:",epoch)
    print("LIFECYCLE:",level)
    print("DELIVERABLE:",deliver)
    print("ACTIVE_OBJECT:",active)
    print("BLOCKER:",blocker)
    print("LAST_CLOSED:",last_closed["id"] if last_closed else "OPEN")
    print("NEXT:",ntxt)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
