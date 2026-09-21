#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def load_json(p:Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return default

def write_json(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def sha(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def canonical_json_hash(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()

def normalize_goal_for_fingerprint(goal):
    g=json.loads(json.dumps(goal))
    for k in ("state_epoch","generated_utc","source_state_fingerprint","captured_unix"):
        g.pop(k,None)
    return g

def edr_number(x):
    m=re.search(r"EDR-(\d+)",str(x or ""),re.I)
    return int(m.group(1)) if m else -1

def decision_id(d,p):
    return d.get("decision_id") or d.get("id") or re.match(r"(EDR-\d+)",p.name,re.I).group(1)

def is_candidate(status):
    s=str(status or "").upper()
    return "CANDIDATE" in s or ("CONDITIONAL" in s and "RELEASE_DEFINITION" not in s)

def is_closed(status):
    s=str(status or "").upper()
    if any(x in s for x in ("REJECT","OPEN","HOLD")): return False
    if is_candidate(s): return False
    return any(x in s for x in ("ACCEPTED_RELEASE_DEFINITION","PASS_DECISION","DECIDED","CONTROLLED_SCOPE_DECISION","ACCEPTED_ENGINEERING_SCREEN","ACCEPTED"))

def decision_summary(d):
    return d.get("title") or d.get("subject") or d.get("problem") or ""

def source_fingerprint(root, goal):
    rels=[
      "control/project/K01_CHECKPOINT_CURRENT.json",
      "reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json",
      "control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json",
      "control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json",
      "control/workpacks/K01_T04_SEAL_BASELINE_CURRENT.json",
      "control/drawings/K01_D006_API_AUTHORING_METHOD_CURRENT.md",
      "reports/control/K01_DRAWING_CONTROL_CURRENT.json",
    ]
    rows=[("goal",canonical_json_hash(normalize_goal_for_fingerprint(goal)))]
    for p in sorted((root/"control/decisions").glob("EDR-*.json")):
        rows.append((p.relative_to(root).as_posix(),sha(p)))
    for rel in rels:
        p=root/rel
        rows.append((rel,sha(p) if p.is_file() else "MISSING"))
    raw="\n".join(f"{a}\t{b}" for a,b in rows).encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), rows

def refresh_pds(root):
    p=root/"tools/pds/k01_pds.py"
    if not p.is_file(): return {"status":"SKIP_PDS_TOOL_MISSING"}
    cp=subprocess.run([sys.executable,str(p),"--repo-root",str(root),"report"],cwd=str(root),capture_output=True,text=True,errors="replace")
    return {"status":"PASS" if cp.returncode==0 else "HOLD","returncode":cp.returncode,"stdout":cp.stdout[-2000:],"stderr":cp.stderr[-2000:]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",required=True)
    a=ap.parse_args(); root=Path(a.repo_root).resolve()
    now=datetime.now(timezone.utc).isoformat()

    pds_refresh=refresh_pds(root)

    goal_p=root/"control/project/K01_GOAL_LOCK_CURRENT.json"
    goal=load_json(goal_p,{}) or {}
    if not goal.get("current_deliverable"):
        print("HOLD: Goal Lock missing/invalid"); return 2

    # Resolve the live drawing artifact from Drawing Control before the state
    # fingerprint is calculated. Goal Lock remains the session goal authority,
    # but it must not retain a superseded candidate when Drawing Control has
    # explicitly published a CURRENT drawing.
    drawing_control=load_json(root/"reports/control/K01_DRAWING_CONTROL_CURRENT.json",{}) or {}
    active_art=(goal.get("current_artifact") or {})
    current_drawing=active_art.get("drawing")
    current_pdf=active_art.get("pdf")
    if "K01-D-006" in str(goal.get("current_deliverable") or ""):
        d006=(drawing_control.get("drawings") or {}).get("K01-D-006") or {}
        published=d006.get("current") or {}
        artifacts=published.get("artifacts") or {}
        draw_rec=artifacts.get("drawing") or {}
        pdf_rec=artifacts.get("pdf") or {}
        if (published.get("status")=="PASS_CURRENT_PUBLISHED" and
            draw_rec.get("exists") and pdf_rec.get("exists") and
            draw_rec.get("path") and pdf_rec.get("path")):
            current_drawing=draw_rec.get("path")
            current_pdf=pdf_rec.get("path")
            active_art={
              "drawing":current_drawing,
              "pdf":current_pdf,
              "status":d006.get("semantic_status") or published.get("status"),
              "source_authority":"reports/control/K01_DRAWING_CONTROL_CURRENT.json",
              "drawing_control_generated_utc":drawing_control.get("generated_utc")
            }
            goal["current_artifact"]=active_art

    readiness=load_json(root/"reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json",{}) or {}
    gaps=load_json(root/"control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json",{}) or {}
    req=load_json(root/"control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json",{}) or {}
    checkpoint=load_json(root/"control/project/K01_CHECKPOINT_CURRENT.json",{}) or {}

    decisions=[]
    for p in sorted((root/"control/decisions").glob("EDR-*.json")):
        d=load_json(p,{}) or {}
        did=decision_id(d,p); status=d.get("status") or d.get("decision") or ""
        decisions.append({"id":did,"n":edr_number(did),"status":status,"summary":decision_summary(d),"path":p.relative_to(root).as_posix(),"sha256":sha(p)})
    decisions.sort(key=lambda x:x["n"])
    closed=[x for x in decisions if is_closed(x["status"])]
    candidates=[x for x in decisions if is_candidate(x["status"])]
    last_closed=max(closed,key=lambda x:x["n"]) if closed else None
    latest_activity=max(decisions,key=lambda x:x["n"]) if decisions else None
    latest_candidate=max(candidates,key=lambda x:x["n"]) if candidates else None

    fp, fp_rows=source_fingerprint(root,goal)
    epoch="K01-SE-"+fp[:16]

    blockers=readiness.get("release_blockers") or []
    blocker_ids=[str(x.get("id")) for x in blockers if isinstance(x,dict)]
    requirements=req.get("requirements") or {}
    media=(requirements.get("REQ-K01-MEDIA-001") or {}).get("requirement_status")
    seal=(requirements.get("REQ-K01-SEAL-001") or {}).get("requirement_status")
    leak=(requirements.get("REQ-K01-LEAK-001") or {}).get("requirement_status")
    if "C12" in blocker_ids or str(media).upper()!="RELEASED" or str(leak).upper()!="RELEASED":
        next_action="Close J2 media/seal/C12 acceptance basis first: bound media/cleaning envelope, exact seal product/compound status, quantitative leak acceptance and verification method. Do not invent missing values."
        next_id="K01-NA-C12-MEDIA-SEAL-LEAK"
        current_stage="P007 Product Definition Closure — media/seal/leak/C12 release basis"
    elif blockers:
        b=blockers[0]
        next_action=f"Close next Product Definition release blocker {b.get('id')}: {b.get('role') or b.get('class')}. Preserve WIP=1."
        next_id="K01-NA-"+str(b.get("id"))
        current_stage="P007 Product Definition Closure — release blocker closure"
    else:
        next_action="Run final D006 Product Definition/drawing release readiness review; do not broaden scope."
        next_id="K01-NA-D006-RELEASE-READINESS"
        current_stage="D006 release-readiness closure"

    # active_art/current_drawing/current_pdf were resolved above, before
    # fingerprinting, so all STATE_CURRENT projections share the same identity.

    state_epoch={
      "schema":"k01.state_epoch.current.v1",
      "state_epoch":epoch,
      "generated_utc":now,
      "source_state_fingerprint":fp,
      "goal_lock":goal.get("current_deliverable"),
      "checkpoint":checkpoint.get("checkpoint_id") or checkpoint.get("id"),
      "last_closed_decision":last_closed,
      "latest_engineering_activity":latest_activity,
      "source_fingerprints":[{"path":a,"sha256":b} for a,b in fp_rows]
    }
    write_json(root/"control/state/K01_STATE_EPOCH_CURRENT.json",state_epoch)

    goal["state_epoch"]=epoch; goal["generated_utc"]=now; goal["source_state_fingerprint"]=fp
    write_json(goal_p,goal)

    manifest={
      "schema":"k01.current_session_manifest.v1",
      "state_epoch":epoch,
      "generated_utc":now,
      "source_state_fingerprint":fp,
      "project":goal.get("project","K01 / MARVILON"),
      "checkpoint":checkpoint,
      "goal":{
        "current_deliverable":goal.get("current_deliverable"),
        "deliverable_class":goal.get("deliverable_class"),
        "wip_limit":goal.get("wip_limit",1),
        "active_dependency":goal.get("active_dependency"),
        "execution_mode":goal.get("current_execution_mode")
      },
      "active_artifact":{
        "drawing":current_drawing,"pdf":current_pdf,"status":active_art.get("status"),
        "drawing_method_baseline":"TWO_VIEW_V2" if current_drawing and "TWO_VIEW_V2" in current_drawing.upper() else "CONTROLLED_CURRENT"
      },
      "engineering_state":{
        "last_closed":last_closed,
        "latest_activity":latest_activity,
        "latest_candidate":latest_candidate,
        "closed_do_not_restart":[x["id"] for x in closed if x["n"]>=25],
        "candidate_not_release":[x["id"] for x in candidates if x["n"]>=25]
      },
      "release_readiness":{
        "status":readiness.get("status"),"release_blockers":blockers,
        "active_engineering_gaps":gaps.get("active_engineering_gaps") or []
      },
      "next_allowed_action":{"id":next_id,"text":next_action},
      "temporal_policy":"docs/architecture/K01_TEMPORAL_AUTHORITY_POLICY_v1.md",
      "authority_rule":"Manifest controls current session navigation, not engineering values. Engineering values remain in declared domain authorities.",
      "center_mode":"FROZEN_MAINTENANCE_ONLY",
      "non_active_work":goal.get("non_active_work") or {}
    }
    write_json(root/"control/project/K01_CURRENT_SESSION_MANIFEST.json",manifest)

    next_obj={
      "schema":"k01.next_actions.current.v19",
      "state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp,
      "current_deliverable":goal.get("current_deliverable"),
      "deliverable_class":goal.get("deliverable_class"),
      "wip_limit":goal.get("wip_limit",1),
      "active_dependency":goal.get("active_dependency"),
      "active_line":goal.get("active_dependency"),
      "current_stage":current_stage,
      "last_completed": (last_closed["id"]+" — "+last_closed["summary"]) if last_closed else "OPEN",
      "latest_engineering_activity": (latest_activity["id"]+" — "+latest_activity["summary"]+" ["+str(latest_activity["status"])+"]") if latest_activity else "OPEN",
      "candidate_not_release": (latest_candidate["id"] if latest_candidate else None),
      "current_blocker":"; ".join(f"{x.get('id')}:{x.get('state')}" for x in blockers) if blockers else "None",
      "next_1":next_action,
      "next_action_id":next_id,
      "execution_mode":goal.get("current_execution_mode"),
      "current_drawing_candidate":current_drawing,
      "current_drawing_pdf":current_pdf,
      "do_not_do":[
        "Do not replace the D006 deliverable with its P007 dependency.",
        "Do not restart closed EDR decisions without an explicit stale trigger.",
        "Do not create a new D006 from zero while the controlled TWO_VIEW_V2 candidate exists.",
        "Do not redesign Center or launch general Git cleanup as the active front.",
        "Do not invent OPEN media, seal, leak, service-life or supplier values."
      ],
      "authority":[x["path"] for x in decisions if x["n"]>=25],
      "release_blockers":blockers
    }
    write_json(root/"control/project/K01_NEXT_ACTIONS_CURRENT.json",next_obj)

    # Active Step Gate is STATE_CURRENT navigation. Generate it from the same
    # reducer so an old step (for example T07A) cannot survive a newer epoch.
    if next_id=="K01-NA-C12-MEDIA-SEAL-LEAK":
        active_step={
          "schema":"k01.active_step_gate.v3",
          "state_epoch":epoch,
          "generated_utc":now,
          "step_id":"K01-STEP-P007-PD-CLOSURE-C12-MEDIA-SEAL-LEAK",
          "active_line":"K01-P007-PRODUCT-DEFINITION-CLOSURE",
          "checkpoint_id":checkpoint.get("checkpoint_id") or checkpoint.get("id"),
          "intent":next_id,
          "intent_text":next_action,
          "mutation_authorized":False,
          "mutation_scope":"READ_ONLY_REQUIREMENT_RECONCILIATION; NO CAD/DRAWING/BOM MUTATION",
          "result_on_pass":"PASS_READ_ONLY_STEP_READY__EXTERNAL_INPUTS_MAY_REMAIN",
          "required_files":[
            "control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json",
            "control/workpacks/K01_T04_SEAL_BASELINE_CURRENT.json",
            "control/decisions/EDR-021_J2_DIFFERENTIAL_PRESSURE_ENVELOPE.json",
            "control/decisions/EDR-022_J2_CFD_TEMPERATURE_BASIS.json",
            "reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json",
            "control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json"
          ],
          "impact_declarations":{
            "requirements":"MEDIA/SEAL/LEAK remain OPEN/PARTIAL until controlled evidence exists.",
            "materials":"No material family or exact supplier compound is promoted by this step.",
            "bom":"No BOM mutation is authorized.",
            "dimxpert_drawings":"No CAD/PMI/drawing mutation is authorized.",
            "inspection":"C12 verification method may be evaluated; no numeric acceptance is invented.",
            "dependencies":"D006 remains the deliverable; P007 Product Definition closure remains the dependency.",
            "technical_filter":"Existing accepted geometry/pressure/temperature decisions remain closed unless stale-triggered.",
            "rollback":"State projections are regenerated from authorities; no native CAD mutation occurs.",
            "evidence":"Use current requirements, EDR-021/022, T04 seal baseline and product documentation; external gaps remain explicit."
          }
        }
    else:
        active_step={
          "schema":"k01.active_step_gate.v3",
          "state_epoch":epoch,
          "generated_utc":now,
          "step_id":"K01-STEP-"+next_id.replace("K01-NA-",""),
          "active_line":goal.get("active_dependency"),
          "checkpoint_id":checkpoint.get("checkpoint_id") or checkpoint.get("id"),
          "intent":next_id,
          "intent_text":next_action,
          "mutation_authorized":False,
          "mutation_scope":"READ_ONLY_UNTIL_EXPLICIT_PREFLIGHT",
          "result_on_pass":"PASS_STEP_IDENTIFIED__MUTATION_NOT_AUTHORIZED",
          "required_files":[],
          "impact_declarations":{k:"Reassess before mutation." for k in ("requirements","materials","bom","dimxpert_drawings","inspection","dependencies","technical_filter","rollback","evidence")}
        }
    write_json(root/"control/project/K01_ACTIVE_STEP_GATE.json",active_step)

    # RESUME is also STATE_CURRENT. Keep it coherent before handoff; the handoff
    # builder may enrich it later but must preserve this epoch.
    resume_p=root/"reports/control/K01_RESUME_CURRENT.json"
    resume=load_json(resume_p,{}) or {}
    resume["schema"]="k01.resume.current.v3"
    resume["state_epoch"]=epoch
    resume["generated_utc"]=now
    resume["project"]="K01"
    aw=resume.setdefault("active_work",{})
    aw.update({
      "state_epoch":epoch,
      "current_deliverable":goal.get("current_deliverable"),
      "deliverable_class":goal.get("deliverable_class"),
      "wip_limit":goal.get("wip_limit",1),
      "active_dependency":goal.get("active_dependency"),
      "current_stage":current_stage,
      "last_completed":next_obj["last_completed"],
      "latest_engineering_activity":next_obj["latest_engineering_activity"],
      "current_blocker":next_obj["current_blocker"],
      "next_1":next_action,
      "current_execution_mode":goal.get("current_execution_mode"),
      "current_drawing_candidate":current_drawing,
      "current_drawing_pdf":current_pdf
    })
    write_json(resume_p,resume)

    start=f"""# K01 START HERE

> AUTO-GENERATED STATE_CURRENT. Do not hand-edit.
> State epoch: `{epoch}`

## Goal Lock
- **CURRENT DELIVERABLE:** `{goal.get('current_deliverable')}`
- **CLASS:** `{goal.get('deliverable_class')}`
- **WIP LIMIT:** `{goal.get('wip_limit',1)}`
- **ACTIVE DEPENDENCY:** `{goal.get('active_dependency')}`
- **EXECUTION MODE:** `{goal.get('current_execution_mode')}`

## Current configuration
- Checkpoint: `{checkpoint.get('checkpoint_id') or checkpoint.get('id') or 'OPEN'}`
- Drawing: `{current_drawing or 'OPEN'}`
- PDF: `{current_pdf or 'OPEN'}`

## Engineering state
- Last CLOSED decision: **{last_closed['id'] if last_closed else 'OPEN'}** — {last_closed['summary'] if last_closed else ''}
- Latest engineering activity: **{latest_activity['id'] if latest_activity else 'OPEN'}** — `{latest_activity['status'] if latest_activity else 'OPEN'}`
- Candidate / NOT release authority: **{latest_candidate['id'] if latest_candidate else 'None'}**

## Release readiness
- Product Definition: **{readiness.get('status','OPEN')}**
- Blockers: {", ".join(blocker_ids) if blocker_ids else "None"}

## Exact next allowed action
**{next_action}**

## Mandatory read order
1. `control/state/K01_STATE_EPOCH_CURRENT.json`
2. `control/project/K01_CURRENT_SESSION_MANIFEST.json`
3. `reports/control/K01_SESSION_CLOSE_CURRENT.md`
4. `reports/control/K01_START_HERE.md`
5. active engineering authorities listed by the Session Manifest / Authority Map

## Non-negotiable
- `CURRENT` filename alone is not global authority.
- Domain/current reports do not override this state epoch.
- Technical values come from EDR/CAD/requirements/evidence authorities, not this summary.
- OPEN/PARTIAL stays OPEN/PARTIAL.
- Screening PASS is not release PASS.
"""
    sp=root/"reports/control/K01_START_HERE.md"; sp.parent.mkdir(parents=True,exist_ok=True); sp.write_text(start,encoding="utf-8")

    session=f"""# K01 SESSION CLOSE / CURRENT RESUME AUTHORITY

State epoch: `{epoch}`
Generated: `{now}`

## Goal
- CURRENT DELIVERABLE: **{goal.get('current_deliverable')}**
- CLASS: **{goal.get('deliverable_class')}**
- WIP: **{goal.get('wip_limit',1)}**
- ACTIVE DEPENDENCY: **{goal.get('active_dependency')}**

## Active D006 workspace
- Drawing: `{current_drawing}`
- PDF: `{current_pdf}`
- Rule: **do not create a new D006 from zero**.

## Closed decisions — do not restart
{chr(10).join("- "+x["id"]+" — "+x["summary"] for x in closed if x["n"]>=25) or "- None"}

## Candidate / conditional — NOT release authority
{chr(10).join("- "+x["id"]+" — "+x["summary"]+" — "+str(x["status"]) for x in candidates if x["n"]>=25) or "- None"}

## Current release blockers
{chr(10).join("- "+str(x.get("id"))+" — "+str(x.get("state"))+" — "+str(x.get("role") or x.get("class")) for x in blockers) or "- None"}

## Exact next allowed action
**{next_action}**

## Scope control
Center = `FROZEN_MAINTENANCE_ONLY`.
General Git cleanup / BOM overhaul / new drawing framework are not active WIP.

## Authority rule
This file controls current-session navigation only. Engineering values remain in the domain authorities.
Older `*_CURRENT` navigation with a different/missing state epoch is `STALE_CONTEXT`.
"""
    sc=root/"reports/control/K01_SESSION_CLOSE_CURRENT.md"; sc.write_text(session,encoding="utf-8")

    readme=f"""# K01 CURRENT ENTRY POINT

> AUTO-GENERATED. State epoch: `{epoch}`

This file is only a project entry pointer. It is not engineering authority.

Read in order:
1. `control/state/K01_STATE_EPOCH_CURRENT.json`
2. `control/project/K01_CURRENT_SESSION_MANIFEST.json`
3. `reports/control/K01_SESSION_CLOSE_CURRENT.md`
4. `reports/control/K01_START_HERE.md`
5. domain engineering authorities required by the exact next action

Current deliverable: **{goal.get('current_deliverable')}**
Active dependency: **{goal.get('active_dependency')}**
Exact next action: **{next_action}**

Historical Stage3 README content was superseded by the temporal-authority policy and belongs in archive/history, not current navigation.
"""
    (root/"README_CURRENT.md").write_text(readme,encoding="utf-8")

    # Artifact-bound visual QA CURRENT: point only to the current workspace, do not inherit old candidate.
    visual={
      "schema":"k01.d006.visual_qa.current.v3",
      "state_epoch":epoch,"generated_utc":now,"source_state_fingerprint":fp,
      "status":"PENDING_VISUAL_QA_CURRENT_WORKSPACE",
      "source_drawing":current_drawing,"source_pdf":current_pdf,"source_bmp":None,
      "automated_prechecks":"NOT_REASSERTED_BY_STATE_REDUCER",
      "required_visual_checks":[
        "views readable and non-overlapping",
        "section exposes thin can and blind end",
        "native datum/GD&T/surface-finish semantics remain correct",
        "title/status block is release-quality",
        "OPEN/CANDIDATE requirements are not shown as released"
      ],
      "release_boundary":"ENGINEERING REVIEW CANDIDATE ONLY until drawing release gates close.",
      "rule":"This CURRENT file is bound to Goal Lock current_artifact; an older PDF path is temporal incoherence."
    }
    write_json(root/"control/drawings/K01_D006_VISUAL_QA_CURRENT.json",visual)

    # AI session rules: concise targeted first-read; preserve permanent rules.
    rules_p=root/"control/project/K01_AI_SESSION_RULES_CURRENT.json"
    rules=load_json(rules_p,{}) or {}
    rules["state_epoch"]=epoch; rules["generated_utc"]=now
    rules["startup_mode"]="TARGETED_STATE_RECONCILIATION"
    rules["first_read_order"]=[
      "control/state/K01_STATE_EPOCH_CURRENT.json",
      "control/project/K01_CURRENT_SESSION_MANIFEST.json",
      "reports/control/K01_SESSION_CLOSE_CURRENT.md",
      "reports/control/K01_START_HERE.md",
      "control/project/K01_GOAL_LOCK_CURRENT.json",
      "reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json",
      "control/project/K01_AUTHORITY_MAP_CURRENT.json",
      "reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json",
      "control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json",
      "control/drawings/K01_D006_API_AUTHORING_METHOD_CURRENT.md"
    ]
    pr=rules.setdefault("permanent_rules",[])
    if not any(str(x.get("id"))=="R55" for x in pr if isinstance(x,dict)):
        pr.append({"id":"R55","rule":"TEMPORAL PRECEDENCE: filename CURRENT is not global authority. Global STATE_CURRENT files must share K01_STATE_EPOCH_CURRENT; handoff must fail closed on temporal-coherence HOLD. Domain CURRENT files cannot override the Current Session Manifest."})
    write_json(rules_p,rules)

    tz={
      "schema":"k01.tz.execution_state.current.v2","state_epoch":epoch,"generated_utc":now,
      "status":"PASS_GOAL_LOCK_WIP1_AND_TEMPORAL_STATE_REDUCED",
      "current_deliverable":goal.get("current_deliverable"),"active_dependency":goal.get("active_dependency"),
      "wip_limit":goal.get("wip_limit",1),"current_drawing":current_drawing,"current_pdf":current_pdf,
      "last_closed_decision":last_closed,"latest_activity":latest_activity,"next_action":next_action,
      "pds_refresh":pds_refresh
    }
    write_json(root/"reports/control/K01_TZ_EXECUTION_STATE_CURRENT.json",tz)

    current_index={
      "schema":"k01.current_index.current.v1","state_epoch":epoch,"generated_utc":now,
      "state_current":[
        "control/state/K01_STATE_EPOCH_CURRENT.json","control/project/K01_CURRENT_SESSION_MANIFEST.json",
        "control/project/K01_GOAL_LOCK_CURRENT.json","control/project/K01_NEXT_ACTIONS_CURRENT.json",
        "reports/control/K01_START_HERE.md","reports/control/K01_SESSION_CLOSE_CURRENT.md","README_CURRENT.md"
      ],
      "artifact_bound_current":["control/drawings/K01_D006_VISUAL_QA_CURRENT.json"],
      "domain_current_rule":"Domain CURRENT is current only inside its declared domain and cannot override global state.",
      "legacy_current_rule":"Any global navigation CURRENT without this epoch is STALE_CONTEXT."
    }
    write_json(root/"control/state/K01_CURRENT_INDEX_CURRENT.json",current_index)

    # Bind Center projection input to the same global state epoch without making
    # Center an authority.
    center_p=root/"control/center/K01_CENTER_INPUT_CURRENT.json"
    center=load_json(center_p,{}) or {}
    center["state_epoch"]=epoch
    center["generated_utc"]=now
    center["current_session_manifest"]="control/project/K01_CURRENT_SESSION_MANIFEST.json"
    center["state_epoch_source"]="control/state/K01_STATE_EPOCH_CURRENT.json"
    center["temporal_coherence"]="reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json"
    center["goal_lock"]="control/project/K01_GOAL_LOCK_CURRENT.json"
    center["policy"]="Center is projection only; global state comes from Current Session Manifest / state epoch. Domain reports remain domain-scoped."
    write_json(center_p,center)

    print("STATE_SYNC: PASS")
    print("STATE_EPOCH:",epoch)
    print("LAST_CLOSED:",last_closed["id"] if last_closed else "OPEN")
    print("LATEST_ACTIVITY:",latest_activity["id"] if latest_activity else "OPEN")
    print("NEXT:",next_action)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
