from __future__ import annotations
from pathlib import Path
import argparse, json, hashlib, datetime, re, subprocess, zipfile
from k01_active_workpack_gate_rc1 import evaluate_active_workpack_gate

DEFAULT_REPO=Path(r"D:\BreshevEngineering\marvilon-k01")

CANDIDATES={
 "start_here":[Path("reports/control/K01_START_HERE.md"),Path("K01_START_HERE.md")],
 "control_panel":[Path("reports/control/K01_ENGINEERING_CONTROL_PANEL_CURRENT.md"),Path("K01_ENGINEERING_CONTROL_PANEL_CURRENT.md")],
 "checkpoint":[Path("control/project/K01_CHECKPOINT_CURRENT.json")],
 "authority_map":[Path("control/project/K01_AUTHORITY_MAP_CURRENT.json")],
 "goal_lock":[Path("control/project/K01_GOAL_LOCK_CURRENT.json"),Path("control/project/K01_CURRENT_DELIVERABLE.json")],
 "frontier":[Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")],
 "next_actions":[Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")],
 "p0p6":[Path("control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json")],
 "dependencies":[Path("reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json"),Path("control/project/K01_DEPENDENCY_STATE.json")],
 "domains":[Path("control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json")],
 "sources":[Path("control/evidence/K01_SOURCE_REGISTRY_v2.json")],
 "handoff_contract":[Path("control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json")],
 "git":[Path("reports/control/K01_GIT_GITHUB_STATUS_CURRENT.json"),Path("reports/git/K01_GITHUB_REMOTE_HEALTH_CURRENT.json")],
 "decision_identity":[Path("reports/control/K01_DECISION_IDENTITY_COHERENCE_CURRENT.json")],
 "value_coherence":[Path("reports/control/K01_ENGINEERING_VALUE_COHERENCE_CURRENT.json")],
 "temporal":[Path("reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json")],
 "semantic":[Path("reports/control/K01_SEMANTIC_COHERENCE_CURRENT.json")],
 "coverage":[Path("reports/control/K01_PROJECT_COVERAGE_COHERENCE_CURRENT.json"),Path("reports/control/K01_ENGINEERING_SYSTEM_COVERAGE_CURRENT.json")],
 "center":[Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json"),Path("reports/center/K01_CENTER_STATE_CURRENT.json")],
 "ai_handoff_completeness":[Path("reports/control/K01_AI_HANDOFF_COMPLETENESS_CURRENT.json")]
}

EXPECTED_DOMAINS=[
"REQ_ALLOC_DECISION","DERIVED_INPUTS","PRODUCT_DEFINITION","CAD_MBD_BINDING",
"DRAWING_D1_D9","TOLERANCE_VARIATION","STRUCTURAL_FEA","MAGNETIC_FEMM","FLOW_CFD",
"THERMAL","PRESSURE_VACUUM_CONTAINMENT","MATERIALS_JOINING_MANUFACTURING",
"EBOM","MBOM","INSPECTION_METROLOGY","CONFIGURATION_RELEASE_BASELINE","REPO_HANDOFF_TOOLCHAIN"
]

def rd_json(p):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return None
def find(repo,key):
    for rel in CANDIDATES[key]:
        p=repo/rel
        if p.is_file():return p
    return None
def rel(repo,p):
    try:return p.relative_to(repo).as_posix()
    except Exception:return str(p)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def recurse_values(o):
    if isinstance(o,dict):
        for k,v in o.items():
            yield (k,v)
            yield from recurse_values(v)
    elif isinstance(o,list):
        for v in o: yield from recurse_values(v)
def find_status(obj):
    if not isinstance(obj,dict):return None
    for k in ("status","state","result","gate_status"):
        v=obj.get(k)
        if isinstance(v,str):return v
    return None
def text_of(v):
    if v is None:return ""
    if isinstance(v,(str,int,float,bool)):return str(v)
    try:return json.dumps(v,ensure_ascii=False)
    except Exception:return str(v)

def frontier_state(repo):
    p=find(repo,"frontier")
    d=rd_json(p) if p else {}
    d=d or {}
    n=d.get("next_allowed_action") or {}
    b=d.get("active_blocker")
    if isinstance(b,dict):b=b.get("id") or b.get("name") or b.get("text")
    next_id=n.get("id") if isinstance(n,dict) else None
    next_text=n.get("text") if isinstance(n,dict) else text_of(n)
    return {
      "source":rel(repo,p) if p else None,
      "lifecycle":d.get("current_lifecycle_level"),
      "deliverable":d.get("current_deliverable"),
      "active_engineering_object":d.get("active_engineering_object"),
      "active_workpack_id":next_id,
      "active_workpack_text":next_text,
      "active_blocker":b,
      "next_id":next_id,
      "next_text":next_text,
      "raw_status":find_status(d)
    }

def domain_state(repo):
    p=find(repo,"domains")
    d=rd_json(p) if p else None
    found=[]
    if isinstance(d,dict):
        blob=json.dumps(d,ensure_ascii=False)
        for x in EXPECTED_DOMAINS:
            if x in blob:found.append(x)
    return {
      "source":rel(repo,p) if p else None,
      "expected_count":len(EXPECTED_DOMAINS),
      "found_count":len(found),
      "found":found,
      "missing":[x for x in EXPECTED_DOMAINS if x not in found]
    }

def duplicate_edrs(repo):
    root=repo/"control/decisions"
    by={}
    if root.is_dir():
        for p in sorted(root.glob("EDR-*.json")):
            d=rd_json(p)
            if not isinstance(d,dict):continue
            did=d.get("decision_id") or d.get("edr_id") or d.get("id")
            if not isinstance(did,str):
                m=re.match(r"(EDR-\d+)",p.name,re.I); did=m.group(1) if m else None
            if did:by.setdefault(did.upper(),[]).append(rel(repo,p))
    return {k:v for k,v in by.items() if len(v)>1}

def active_count(obj):
    """Diagnostic only. Canonical active workpack comes from Completion Frontier next_id."""
    hits=[]
    active_tokens={"ACTIVE_NOW","ACTIVE","EXECUTABLE_NOW"}
    def walk(v,path="$"):
        if isinstance(v,dict):
            for k,x in v.items():
                kp=f"{path}.{k}"
                if isinstance(x,str) and x.upper() in active_tokens:
                    hits.append(kp)
                walk(x,kp)
        elif isinstance(v,list):
            for i,x in enumerate(v):walk(x,f"{path}[{i}]")
    walk(obj)
    return hits

def file_sha_or_none(p):
    return sha(p) if p and p.is_file() else None

def operator_lock_state(repo,front):
    p=repo/"control/system/K01_OPERATOR_LOCK_CURRENT.json"
    if not p.is_file():
        return {"status":"MISSING","path":rel(repo,p)}
    d=rd_json(p)
    if not isinstance(d,dict):
        return {"status":"INVALID","path":rel(repo,p)}
    gp=find(repo,"goal_lock")
    fp=find(repo,"frontier")
    reasons=[]
    if d.get("confirmed_goal_lock")!=front.get("deliverable"):
        reasons.append("GOAL_LOCK_CHANGED")
    if d.get("confirmed_active_workpack_id")!=front.get("active_workpack_id"):
        reasons.append("ACTIVE_WORKPACK_CHANGED")
    if d.get("confirmed_active_engineering_object")!=front.get("active_engineering_object"):
        reasons.append("ACTIVE_OBJECT_CHANGED")
    if d.get("goal_lock_sha256")!=file_sha_or_none(gp):
        reasons.append("GOAL_LOCK_SOURCE_CHANGED")
    if d.get("frontier_sha256")!=file_sha_or_none(fp):
        reasons.append("FRONTIER_SOURCE_CHANGED")
    if reasons:
        return {"status":"STALE","path":rel(repo,p),"reasons":reasons,"record":d}
    return {"status":"CONFIRMED","path":rel(repo,p),"record":d}

def classify_holds(repo,frontier,objects,operator_lock):
    holds=[]
    def add(ht,id_,subject,reason,baw,ble,br,src,resume):
        holds.append({
          "type":ht,"id":id_,"subject":subject,"reason":reason,
          "blocks_active_workpack":bool(baw),"blocks_lifecycle_exit":bool(ble),"blocks_release":bool(br),
          "authority_or_evidence":src,"resume_trigger":resume
        })
    if operator_lock.get("status")!="CONFIRMED":
        add("CONTROL_SYSTEM_HOLD","OPERATOR-LOCK","Operator intent/authorization",
            "Operator Goal Lock / ACTIVE workpack confirmation is "+str(operator_lock.get("status")),
            True,False,False,operator_lock.get("path"),
            "Run SET_K01_OPERATOR_LOCK_RC1.cmd after reviewing Goal Lock and ACTIVE workpack.")
    if frontier.get("active_blocker"):
        holds.append({
          "type":"ENGINEERING_HOLD",
          "id":"ACTIVE-WORKPACK-TARGET",
          "subject":frontier.get("active_engineering_object"),
          "reason":text_of(frontier.get("active_blocker")),
          "role":"WORKPACK_TARGET",
          "blocks_active_workpack":False,
          "blocks_workpack_closure":True,
          "blocks_lifecycle_exit":True,
          "blocks_release":True,
          "authority_or_evidence":frontier.get("source"),
          "resume_trigger":frontier.get("next_text") or "Execute the ACTIVE workpack and close its target engineering gap."
        })
    mapping=[
      ("decision_identity","CONTROL_SYSTEM_HOLD","DECISION-IDENTITY"),
      ("value_coherence","CONTROL_SYSTEM_HOLD","ENGINEERING-VALUE-COHERENCE"),
      ("temporal","CONTROL_SYSTEM_HOLD","TEMPORAL-COHERENCE"),
      ("semantic","CONTROL_SYSTEM_HOLD","SEMANTIC-COHERENCE"),
      ("coverage","CONTROL_SYSTEM_HOLD","PROJECT-COVERAGE"),
      ("git","CONFIGURATION_HOLD","GIT-GITHUB"),
      ("center","PROJECTION_HOLD","CENTER-PROJECTION"),
    ]
    for key,ht,hid in mapping:
        p,obj=objects.get(key,(None,None))
        st=find_status(obj) if isinstance(obj,dict) else None
        if st and ("HOLD" in st.upper() or "FAIL" in st.upper() or "BLOCK" in st.upper()):
            # Decision/value incoherence can block engineering because input authority/value identity may be unsafe.
            baw = key in ("decision_identity","value_coherence")
            add(ht,hid,key,st,baw,baw, key!="center", rel(repo,p) if p else None,
                "Repair only this control defect; do not broaden scope.")
    # Release-only holds discovered from common status strings in P0/P6 / BOM projections are not engineering blockers by default.
    for key in ("p0p6",):
        p,obj=objects.get(key,(None,None))
        if isinstance(obj,dict):
            blob=json.dumps(obj,ensure_ascii=False)
            if re.search(r'"P6[^"]*"[^}]*HOLD|P6_RELEASE[^}]*HOLD',blob,re.I):
                add("RELEASE_HOLD","P6-RELEASE","Project release","P6 release remains HOLD",
                    False,False,True,rel(repo,p),"Close release criteria; does not automatically stop the current engineering workpack.")
    return holds

def handoff_integrity(repo, objects):
    checks=[]
    # Verify the canonical CURRENT handoff if it exists/referenced.
    candidates=[repo/"reports/control/K01_AI_HANDOFF_CURRENT.zip"]
    pcomp,obj=objects.get("ai_handoff_completeness",(None,None))
    if isinstance(obj,dict):
        for k,v in recurse_values(obj):
            if isinstance(v,str) and v.lower().endswith(".zip"):
                q=Path(v)
                if q.is_absolute(): candidates.append(q)
                else:candidates.append(repo/v)
    seen=set()
    for p in candidates:
        s=str(p).lower()
        if s in seen:continue
        seen.add(s)
        if not p.exists():
            checks.append({"path":str(p),"exists":False,"status":"HOLD_HANDOFF_ARTIFACT_MISSING"})
            continue
        rec={"path":str(p),"exists":True,"size_bytes":p.stat().st_size,"sha256":sha(p)}
        try:
            with zipfile.ZipFile(p,"r") as z:
                bad=z.testzip()
                names=z.namelist()
            rec["zip_integrity"]="PASS" if bad is None else f"FAIL:{bad}"
            rec["member_count"]=len(names)
            rec["required_member_signals"]={
              "start_here":any("START_HERE" in x.upper() for x in names),
              "control_panel":any("CONTROL_PANEL" in x.upper() for x in names),
            }
            rec["status"]="PASS_HANDOFF_ARTIFACT_VERIFIED" if bad is None else "HOLD_HANDOFF_ARCHIVE_CORRUPT"
        except Exception as e:
            rec["status"]="HOLD_HANDOFF_NOT_READABLE"
            rec["error"]=repr(e)
        checks.append(rec)
    return checks

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(DEFAULT_REPO))
    ap.add_argument("--mode",choices=["fast","deep"],default="fast")
    a=ap.parse_args()
    repo=Path(a.repo_root).resolve()
    out=repo/"reports/control"
    out.mkdir(parents=True,exist_ok=True)

    print("============================================================")
    print("K01 CONTROL SYSTEM RC1.3")
    print("MODE:",a.mode.upper())
    print("FAST_CONTROL IS READ-ONLY WITH RESPECT TO ENGINEERING STATE")
    print("============================================================")

    objects={}
    source_presence={}
    for k in CANDIDATES:
        p=find(repo,k)
        obj=rd_json(p) if p and p.suffix.lower()==".json" else None
        objects[k]=(p,obj)
        source_presence[k]={"path":rel(repo,p) if p else None,"exists":bool(p)}

    front=frontier_state(repo)
    domains=domain_state(repo)
    dups=duplicate_edrs(repo)
    next_obj=objects.get("next_actions",(None,None))[1]
    active_hits=active_count(next_obj) if next_obj else []
    op_lock=operator_lock_state(repo,front)
    holds=classify_holds(repo,front,objects,op_lock)
    handoff=handoff_integrity(repo,objects)

    execution_gate=evaluate_active_workpack_gate(
        repo,front,op_lock,typed_holds=holds,write_report=True,require_authorization=True
    )
    # Only technical/preflight failure is a control-system blocking HOLD.
    # Missing/stale human mutation authorization is an operator action gate, not a system defect.
    if execution_gate.get("preflight_status")!="PASS_ACTIVE_WORKPACK_PREFLIGHT":
        holds.append({
          "type":"CONTROL_SYSTEM_HOLD",
          "id":"ACTIVE-WORKPACK-PREFLIGHT",
          "subject":front.get("active_workpack_id"),
          "reason":execution_gate.get("preflight_status"),
          "blocks_active_workpack":True,
          "blocks_lifecycle_exit":False,
          "blocks_release":True,
          "authority_or_evidence":"reports/control/K01_ACTIVE_WORKPACK_GATE_CURRENT.json",
          "resume_trigger":"Resolve only the five-question preflight blockers; do not broaden scope."
        })

    engineering_blockers=[h for h in holds if h["blocks_active_workpack"]]
    control_holds=[h for h in holds if h["type"]=="CONTROL_SYSTEM_HOLD"]
    config_holds=[h for h in holds if h["type"]=="CONFIGURATION_HOLD"]
    projection_holds=[h for h in holds if h["type"]=="PROJECTION_HOLD"]
    release_holds=[h for h in holds if h["type"]=="RELEASE_HOLD"]

    source_p=find(repo,"sources")
    source_registry_present=bool(source_p)

    # System quality is separate from engineering readiness.
    rc1_issues=[]
    if domains["found_count"]!=17: rc1_issues.append("DOMAIN_COVERAGE_NOT_17")
    if dups: rc1_issues.append("DUPLICATE_ACTIVE_EDR_ID")
    if not source_registry_present: rc1_issues.append("SOURCE_REGISTRY_MISSING")
    if not front.get("deliverable"): rc1_issues.append("CURRENT_DELIVERABLE_MISSING")
    if not front.get("active_engineering_object"): rc1_issues.append("ACTIVE_ENGINEERING_OBJECT_MISSING")
    if not front.get("active_workpack_id"): rc1_issues.append("ACTIVE_WORKPACK_ID_MISSING")
    if active_hits and len(active_hits)!=1: rc1_issues.append(f"NEXT_ACTION_ACTIVE_MARKER_COUNT={len(active_hits)}")
    if op_lock.get("status")!="CONFIRMED": rc1_issues.append("OPERATOR_LOCK_"+op_lock.get("status","UNKNOWN"))
    if execution_gate.get("preflight_status")!="PASS_ACTIVE_WORKPACK_PREFLIGHT":
        rc1_issues.append("ACTIVE_WORKPACK_PREFLIGHT_HOLD")
    bad_handoff=[x for x in handoff if str(x.get("status","")).startswith("HOLD_")]
    # Handoff integrity is a control/handoff issue, not automatically an engineering blocker.
    if bad_handoff: rc1_issues.append("HANDOFF_INTEGRITY_HOLD")

    system_status="PASS_CONTROL_SYSTEM_RC1_FAST" if not rc1_issues else "HOLD_CONTROL_SYSTEM_RC1_FAST"
    engineering_status="HOLD_ACTIVE_ENGINEERING_WORKPACK" if engineering_blockers else "ENGINEERING_WORKPACK_NOT_BLOCKED_BY_CONTROL"
    if front.get("active_blocker") and not engineering_blockers:
        engineering_status="ENGINEERING_WORKPACK_HAS_CLOSURE_TARGET"
    if execution_gate.get("ready_for_operator_authorization"):
        engineering_status="ENGINEERING_WORKPACK_READY_FOR_MUTATION_AUTHORIZATION"
    if execution_gate.get("can_start_active_workpack"):
        engineering_status="ENGINEERING_WORKPACK_AUTHORIZED_TO_START"

    report={
      "schema":"k01.control_system_rc1.current.v1",
      "control_system_revision":"RC1.3",
      "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "mode":a.mode.upper(),
      "system_status":system_status,
      "engineering_status":engineering_status,
      "release_status":"HOLD_RELEASE" if release_holds else "RELEASE_STATUS_NOT_DERIVED_AS_PASS",
      "frontier":front,
      "domain_coverage":domains,
      "active_now_markers_diagnostic":active_hits,
      "active_workpack":{"id":front.get("active_workpack_id"),"text":front.get("active_workpack_text"),"source":front.get("source")},
      "operator_lock":op_lock,
      "execution_gate":execution_gate,
      "five_control_questions":execution_gate.get("five_control_questions"),
      "duplicate_active_edr_ids":dups,
      "source_registry":{"present":source_registry_present,"path":rel(repo,source_p) if source_p else None},
      "typed_holds":holds,
      "hold_summary":{
        "engineering_blocking":len(engineering_blockers),
        "control_system":len(control_holds),
        "configuration":len(config_holds),
        "projection":len(projection_holds),
        "release":len(release_holds)
      },
      "handoff_integrity":handoff,
      "source_presence":source_presence,
      "rc1_issues":rc1_issues,
      "operator_required":{
        "confirm_goal_lock":front.get("deliverable"),
        "confirm_active_workpack_id":front.get("active_workpack_id"),
        "confirm_active_engineering_object":front.get("active_engineering_object"),
        "operator_lock_status":op_lock.get("status"),
        "mutation_authorization_status":(execution_gate.get("authorization") or {}).get("status"),
        "ready_for_mutation_authorization":execution_gate.get("ready_for_operator_authorization"),
        "can_start_active_workpack":execution_gate.get("can_start_active_workpack"),
        "next_engineering_action":front.get("next_text"),
        "rule":"User controls intent, mutation authorization, acceptance and promotion; system controls coverage/coherence/freshness/bookkeeping."
      },
      "invariants":[
        "Center/reports/handoff/Git are projection/evidence, not engineering authority.",
        "A control/configuration/projection HOLD does not stop engineering unless blocks_active_workpack=true.",
        "WIP engineering = 1.",
        "PASS must always be scoped.",
        "FAST_CONTROL does not mutate engineering state.",
        "A workpack closure target is not a pre-execution blocker unless blocks_active_workpack=true.",
        "ENGINEERING_MUTATION / CONTROL_MUTATION / PROMOTION require explicit scope-bound human authorization."
      ]
    }

    json_path=out/"K01_CONTROL_SYSTEM_RC1_CURRENT.json"
    json_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    lines=[
      "# K01 CONTROL SYSTEM RC1 — CURRENT",
      "",
      f"- System: **{system_status}**",
      f"- Engineering: **{engineering_status}**",
      f"- Lifecycle: `{front.get('lifecycle')}`",
      f"- Deliverable: `{front.get('deliverable')}`",
      f"- Active object: `{front.get('active_engineering_object')}`",
      f"- Active workpack: `{front.get('active_workpack_id')}`",
      f"- Operator lock: `{op_lock.get('status')}`",
      f"- Action class: `{execution_gate.get('action_class')}`",
      f"- Active-workpack preflight: `{execution_gate.get('preflight_status')}`",
      f"- Mutation authorization: `{(execution_gate.get('authorization') or {}).get('status')}`",
      f"- Active-workpack execution gate: `{execution_gate.get('status')}`",
      f"- Can start ACTIVE workpack: `{execution_gate.get('can_start_active_workpack')}`",
      f"- Workpack closure target: `{front.get('active_blocker')}`",
      f"- Next engineering action: {front.get('next_text')}",
      f"- Domain coverage: `{domains['found_count']}/17`",
      f"- Duplicate active EDR IDs: `{len(dups)}`",
      f"- Source registry: `{'PRESENT' if source_registry_present else 'MISSING'}`",
      "",
      "## Typed holds"
    ]
    if holds:
        for h in holds:
            lines.append(f"- `{h['type']}` `{h['id']}` — blocks_active={h['blocks_active_workpack']} — {h['reason']}")
    else:
        lines.append("- none detected by FAST_CONTROL")
    lines += [
      "",
      "## Operator",
      f"- Confirm Goal Lock: `{front.get('deliverable')}`",
      f"- Confirm ACTIVE workpack: `{front.get('active_workpack_id')}` on `{front.get('active_engineering_object')}`",
      f"- Operator lock status: `{op_lock.get('status')}`",
      "- Do not treat CONTROL/CONFIGURATION/PROJECTION HOLD as engineering stop unless `blocks_active_workpack=true`.",
      "- Do not start a second executable engineering workpack.",
      "",
      "## RC1 issues"
    ]
    lines += [f"- {x}" for x in rc1_issues] or ["- none"]
    md_path=out/"K01_CONTROL_SYSTEM_RC1_CURRENT.md"
    md_path.write_text("\n".join(lines)+"\n",encoding="utf-8")

    print("SYSTEM:",system_status)
    print("ENGINEERING:",engineering_status)
    print("DOMAINS:",domains["found_count"],"/ 17")
    print("DELIVERABLE:",front.get("deliverable"))
    print("ACTIVE_OBJECT:",front.get("active_engineering_object"))
    print("ACTIVE_WORKPACK:",front.get("active_workpack_id"))
    print("OPERATOR_LOCK:",op_lock.get("status"))
    q=execution_gate.get("five_control_questions") or {}
    print("CONTROL_Q1_GOAL_LOCK_CONFIRMED:",q.get("1_goal_lock_operator_confirmed"))
    print("CONTROL_Q2_ACTIVE_WORKPACK_SINGLE:",q.get("2_active_workpack_single_and_operator_bound"))
    print("CONTROL_Q3_ENGINEERING_HOLD_BLOCKS_ACTIVE_PRESENT:",q.get("3_engineering_hold_blocks_active_workpack_present"))
    print("CONTROL_Q3_PASS_NO_BLOCKING_ENGINEERING_HOLD:",q.get("3_pass_no_blocking_engineering_hold"))
    print("CONTROL_Q4_INPUTS_UNAMBIGUOUS_AND_FRESH:",q.get("4_inputs_unambiguously_identified_and_fresh"))
    print("CONTROL_Q5_ACTION_CLASS:",q.get("5_action_class"))
    print("ACTIVE_WORKPACK_PREFLIGHT:",execution_gate.get("preflight_status"))
    print("MUTATION_AUTHORIZATION:",(execution_gate.get("authorization") or {}).get("status"))
    print("READY_FOR_OPERATOR_AUTHORIZATION:",execution_gate.get("ready_for_operator_authorization"))
    print("ACTIVE_WORKPACK_EXECUTION_GATE:",execution_gate.get("status"))
    print("CAN_START_ACTIVE_WORKPACK:",execution_gate.get("can_start_active_workpack"))
    print("NEXT:",front.get("next_text"))
    print("TYPED_HOLDS:",len(holds),"ENGINEERING_BLOCKING:",len(engineering_blockers))
    print("RC1_ISSUES:",len(rc1_issues))
    for x in rc1_issues: print("ISSUE:",x)
    print("REPORT:",json_path)
    print("MD:",md_path)
    return 0 if not rc1_issues else 2

if __name__=="__main__":
    raise SystemExit(main())
