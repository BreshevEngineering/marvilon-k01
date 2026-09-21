#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

def load_json(p,default=None):
    try: return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception: return default

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

VOLATILE_KEY_RE=re.compile(
    r"(?:^|_)(?:generated|captured|timestamp|mtime|modified|created|elapsed|duration|"
    r"sha(?:256)?|hash|fingerprint|bytes|size_bytes|source_digest|source_digests)(?:$|_)",
    re.I
)
VOLATILE_EXACT={
    "state_epoch","source_state_fingerprint","generated_utc","captured_utc",
    "captured_local_time","captured_unix","timestamp","source_fingerprints",
    "projection_observations"
}

def semantic_canonicalize(o):
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
    raw=json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def semantic_file_hash(p):
    if not p.is_file():
        return "MISSING"
    if p.suffix.lower()==".json":
        try:
            return canonical_hash(json.loads(p.read_text(encoding="utf-8-sig")))
        except Exception:
            pass
    try:
        txt=p.read_text(encoding="utf-8-sig",errors="strict").replace("\r\n","\n")
        kept=[]
        for line in txt.splitlines():
            if re.match(r"^\s*(Generated|Generated UTC|Captured|Timestamp|State epoch):",line,re.I):
                continue
            kept.append(line)
        return hashlib.sha256(("\n".join(kept)+"\n").encode("utf-8")).hexdigest()
    except Exception:
        return sha(p)

def resolve_fingerprint(root,path,mode,goal,frontier):
    # New v3 records declare the hashing contract explicitly. Legacy records are
    # resolved conservatively so an old epoch can still produce an intelligible HOLD.
    if mode=="semantic_object":
        if path=="goal": return canonical_hash(goal)
        if path=="frontier": return canonical_hash(frontier)
        return "UNRESOLVED_SEMANTIC_OBJECT"
    if mode=="semantic_file":
        return semantic_file_hash(root/path)
    if mode=="raw_file":
        p=root/path
        return sha(p) if p.is_file() else "MISSING"

    # Legacy fallback.
    if path=="goal": return canonical_hash(goal)
    if path=="frontier": return canonical_hash(frontier)
    p=root/path
    return sha(p) if p.is_file() else "MISSING"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",required=True); ap.add_argument("--write-report",action="store_true")
    a=ap.parse_args(); root=Path(a.repo_root).resolve(); issues=[]; checks=[]

    epoch_obj=load_json(root/"control/state/K01_STATE_EPOCH_CURRENT.json",{}) or {}
    epoch=epoch_obj.get("state_epoch")
    manifest=load_json(root/"control/project/K01_CURRENT_SESSION_MANIFEST.json",{}) or {}
    goal=load_json(root/"control/project/K01_GOAL_LOCK_CURRENT.json",{}) or {}
    nxt=load_json(root/"control/project/K01_NEXT_ACTIONS_CURRENT.json",{}) or {}
    rules=load_json(root/"control/project/K01_AI_SESSION_RULES_CURRENT.json",{}) or {}
    visual=load_json(root/"control/drawings/K01_D006_VISUAL_QA_CURRENT.json",{}) or {}
    resume=load_json(root/"reports/control/K01_RESUME_CURRENT.json",{}) or {}
    center_input=load_json(root/"control/center/K01_CENTER_INPUT_CURRENT.json",{}) or {}
    active_step=load_json(root/"control/project/K01_ACTIVE_STEP_GATE.json",{}) or {}
    frontier=load_json(root/"control/state/K01_COMPLETION_FRONTIER_CURRENT.json",{}) or {}
    drawing_control=load_json(root/"reports/control/K01_DRAWING_CONTROL_CURRENT.json",{}) or {}

    if not epoch: issues.append({"rule":"STATE_EPOCH_MISSING"})

    # Detect engineering/source changes that occurred after the last reducer run.
    # State Epoch sources are authority/control inputs only. Generated projections
    # are checked separately below and never define the epoch identity.
    stored_sources=epoch_obj.get("source_fingerprints") or []
    stored_paths=set()
    current_source_rows=[]
    for rec in stored_sources:
        path=rec.get("path"); exp=rec.get("sha256"); mode=rec.get("hash_mode")
        if not path: continue
        stored_paths.add(path)
        got=resolve_fingerprint(root,path,mode,goal,frontier)
        current_source_rows.append((path,got))
        if exp!=got:
            issues.append({"rule":"STATE_SOURCE_DRIFT","path":path,"hash_mode":mode or "legacy","expected":exp,"got":got})

    if stored_sources:
        current_fp=hashlib.sha256("\n".join(f"{path}\t{digest}" for path,digest in current_source_rows).encode()).hexdigest()
        expected_fp=epoch_obj.get("source_state_fingerprint")
        checks.append({"check":"source_state_fingerprint","expected":expected_fp,"got":current_fp})
        if expected_fp and current_fp!=expected_fp:
            issues.append({"rule":"STATE_FINGERPRINT_MISMATCH","expected":expected_fp,"got":current_fp})
        derived_epoch="K01-SE-"+current_fp[:16]
        checks.append({"check":"state_epoch_derivation","expected":epoch,"got":derived_epoch})
        if epoch and derived_epoch!=epoch:
            issues.append({"rule":"STATE_EPOCH_DERIVATION_MISMATCH","expected":epoch,"got":derived_epoch})

    # Projections are observations of the state. They may drift after the reducer,
    # which is a control-plane HOLD, but they do not feed back into State Epoch.
    for rec in epoch_obj.get("projection_observations") or []:
        path=rec.get("path"); exp=rec.get("sha256"); mode=rec.get("hash_mode") or "semantic_file"
        if not path: continue
        got=resolve_fingerprint(root,path,mode,goal,frontier)
        if exp!=got:
            issues.append({"rule":"PROJECTION_DRIFT_SINCE_REDUCE","path":path,"hash_mode":mode,"expected":exp,"got":got})

    current_edrs={p.relative_to(root).as_posix() for p in (root/"control/decisions").glob("EDR-*.json") if p.is_file()}
    stored_edrs={p for p in stored_paths if p.startswith("control/decisions/EDR-")}
    for path in sorted(current_edrs-stored_edrs):
        issues.append({"rule":"NEW_DECISION_NOT_REDUCED","path":path})
    for path in sorted(stored_edrs-current_edrs):
        issues.append({"rule":"DECISION_SOURCE_MISSING_AFTER_REDUCE","path":path})

    for name,obj in [("manifest",manifest),("goal_lock",goal),("next_actions",nxt),("ai_session_rules",rules),("visual_qa",visual),("resume",resume),("center_input",center_input),("active_step",active_step),("completion_frontier",frontier)]:
        got=obj.get("state_epoch")
        checks.append({"check":name+"_epoch","expected":epoch,"got":got})
        if epoch and got!=epoch: issues.append({"rule":"STATE_EPOCH_MISMATCH","artifact":name,"expected":epoch,"got":got})

    text_files=[
      ("start_here",root/"reports/control/K01_START_HERE.md"),
      ("session_close",root/"reports/control/K01_SESSION_CLOSE_CURRENT.md"),
      ("readme_current",root/"README_CURRENT.md")
    ]
    for name,p in text_files:
        text=p.read_text(encoding="utf-8",errors="replace") if p.is_file() else ""
        ok=bool(epoch and epoch in text)
        checks.append({"check":name+"_contains_epoch","ok":ok})
        if not ok: issues.append({"rule":"TEXT_STATE_EPOCH_MISSING","artifact":name})

    # Core semantic consistency
    delivery=goal.get("current_deliverable")
    if manifest.get("goal",{}).get("current_deliverable")!=delivery:
        issues.append({"rule":"DELIVERABLE_MISMATCH_MANIFEST_GOAL"})
    if nxt.get("current_deliverable")!=delivery:
        issues.append({"rule":"DELIVERABLE_MISMATCH_NEXT_GOAL"})
    dep=goal.get("active_dependency")
    if manifest.get("goal",{}).get("active_dependency")!=dep or nxt.get("active_dependency")!=dep:
        issues.append({"rule":"ACTIVE_DEPENDENCY_MISMATCH"})
    if delivery and dep and str(delivery).strip()==str(dep).strip():
        issues.append({"rule":"DEPENDENCY_REPLACED_DELIVERABLE"})

    # Current drawing identity
    goal_pdf=(goal.get("current_artifact") or {}).get("pdf")
    if visual.get("source_pdf")!=goal_pdf:
        issues.append({"rule":"VISUAL_QA_OLD_WORKSPACE","goal_pdf":goal_pdf,"visual_pdf":visual.get("source_pdf")})
    goal_draw=(goal.get("current_artifact") or {}).get("drawing")
    if manifest.get("active_artifact",{}).get("drawing")!=goal_draw:
        issues.append({"rule":"DRAWING_IDENTITY_MISMATCH"})

    # Drawing Control is the live runtime authority for the published D006.
    d006=(drawing_control.get("drawings") or {}).get("K01-D-006") or {}
    published=d006.get("current") or {}
    artifacts=published.get("artifacts") or {}
    dc_draw=(artifacts.get("drawing") or {}).get("path")
    dc_pdf=(artifacts.get("pdf") or {}).get("path")
    if published.get("status")=="PASS_CURRENT_PUBLISHED":
        if goal_draw!=dc_draw or goal_pdf!=dc_pdf:
            issues.append({"rule":"GOAL_ARTIFACT_NOT_DRAWING_CONTROL_CURRENT","goal_drawing":goal_draw,"drawing_control_drawing":dc_draw,"goal_pdf":goal_pdf,"drawing_control_pdf":dc_pdf})

    # Active Step Gate must be generated from the same state epoch / Next Action.
    if active_step.get("intent")!=nxt.get("next_action_id"):
        issues.append({"rule":"ACTIVE_STEP_NEXT_ACTION_MISMATCH","active_step_intent":active_step.get("intent"),"next_action_id":nxt.get("next_action_id")})
    fnext=(frontier.get("next_allowed_action") or {}).get("id")
    if fnext and nxt.get("next_action_id")!=fnext:
        issues.append({"rule":"FRONTIER_NEXT_ACTION_MISMATCH","frontier_next":fnext,"next_action_id":nxt.get("next_action_id")})
    if frontier.get("current_deliverable") and frontier.get("current_deliverable")!=delivery:
        issues.append({"rule":"FRONTIER_DELIVERABLE_MISMATCH","frontier":frontier.get("current_deliverable"),"goal":delivery})

    # First-read must begin with temporal state, not Center/legacy files.
    required_prefix=[
      "control/state/K01_STATE_EPOCH_CURRENT.json",
      "control/project/K01_CURRENT_SESSION_MANIFEST.json",
      "reports/control/K01_SESSION_CLOSE_CURRENT.md",
      "reports/control/K01_START_HERE.md"
    ]
    fro=rules.get("first_read_order") or []
    if fro[:len(required_prefix)]!=required_prefix:
        issues.append({"rule":"AI_FIRST_READ_TEMPORAL_PRECEDENCE_BROKEN","got":fro[:len(required_prefix)]})

    # PDS readiness freshness: its generated timestamp must exist and its text must acknowledge EDR-027 when EDR-027 exists.
    pds=root/"reports/pds/K01_P007_J2_READINESS_CURRENT.md"
    pds_txt=pds.read_text(encoding="utf-8",errors="replace") if pds.is_file() else ""
    if (root/"control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json").is_file() and "EDR-027" not in pds_txt:
        issues.append({"rule":"PDS_CURRENT_STALE_VS_EDR027"})

    # Old Stage3 README must not survive as CURRENT navigation.
    readme=(root/"README_CURRENT.md").read_text(encoding="utf-8",errors="replace") if (root/"README_CURRENT.md").is_file() else ""
    if "Stage3 Control V5" in readme:
        issues.append({"rule":"LEGACY_STAGE3_README_STILL_CURRENT"})

    # Known core old current artifact references.
    if visual.get("source_pdf") and "20260911" in str(visual.get("source_pdf")) and goal_pdf and "20260914" in str(goal_pdf):
        issues.append({"rule":"OLD_D006_CANDIDATE_MARKED_CURRENT"})

    status="PASS_TEMPORAL_COHERENCE" if not issues else "HOLD_TEMPORAL_COHERENCE"
    rep={
      "schema":"k01.temporal_coherence.current.v2_independent_guard",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":status,"state_epoch":epoch,"issues":issues,"checks":checks,
      "rule":"Temporal coherence validates primary project-state artifacts only. Semantic coherence is evaluated afterward by the independent semantic guard; guards must not depend on each other cyclically."
    }
    if a.write_report:
        p=root/"reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json"; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("REPORT:",p)
    print("TEMPORAL_COHERENCE:",status,"issues=",len(issues))
    for i in issues: print("HOLD:",json.dumps(i,ensure_ascii=False))
    return 0 if not issues else 2

if __name__=="__main__":
    raise SystemExit(main())
