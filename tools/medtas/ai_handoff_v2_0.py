from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile
from datetime import datetime
from pathlib import Path

try:
    from medtas_v16_common import register_build
except Exception:
    register_build=None

REPORT_PATTERNS=[
  'reports/control/*.json','reports/control/*.md',
  'reports/medtas/pipeline/*.json','reports/medtas/cad/current/*.json','reports/cad/current/*.json',
  'reports/cad/identity_freeze/*','reports/cad/assembly_approval/*','reports/cad/gate04e_snapshot/*',
  'reports/medtas/mbd/current/*.json','reports/medtas/product_definition/current/*.json','reports/medtas/tolerance/current/*.json',
  'reports/medtas/structural/current/*.json','reports/medtas/calculix/current/*.json','reports/medtas/drawing/current/*.json',
  'reports/medtas/bom/current/*.json','reports/drawing/current/*','reports/inspection/current/*','reports/bom/current/*',
  'reports/engineering/*.json','reports/engineering/*.md','reports/engineering/current/*.md','reports/engineering/current/*.docx','reports/engineering/current/source/*',
  'reports/medtas/logs/current/*.log','reports/medtas/tests/*.json','reports/pds/*.md','reports/pds/*.json'
]

# Controlled semantic/config/source trees. Binary build output and native CAD are excluded below.
TREE_ROOTS=['control','docs','spec','tools','scripts','cad_api','tests','.github','.githooks']
ROOT_PATTERNS=['*.cmd','*.ps1','*.md','*.json','.gitignore','.gitattributes']
ALLOWED_TREE_SUFFIXES={
  '.json','.jsonl','.md','.txt','.csv','.yaml','.yml','.toml','.ini','.cfg',
  '.py','.cs','.cmd','.bat','.ps1','.sln','.csproj','.props','.targets','.xml'
}
EXCLUDED_DIR_NAMES={'.git','__pycache__','bin','obj','_inbox','.local_archive','archive','history','Downloads'}
EXCLUDED_FILE_PREFIXES=('~$','.~')
NATIVE_EXCLUDED_SUFFIXES={'.sldprt','.sldasm','.slddrw','.exe','.dll','.pdb','.pyc'}
CAD_SUFFIXES={'.sldprt','.sldasm','.slddrw','.step','.stp','.iges','.igs','.pdf','.dxf','.dwg'}

MANDATORY_CONTEXT=[
  'control/state/K01_STATE_EPOCH_CURRENT.json',
  'control/state/K01_CURRENT_INDEX_CURRENT.json',
  'control/project/K01_CURRENT_SESSION_MANIFEST.json',
  'reports/control/K01_SESSION_CLOSE_CURRENT.md',
  'reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json',
  'docs/architecture/K01_TEMPORAL_AUTHORITY_POLICY_v1.md',
  'control/project/K01_NEXT_ACTIONS_CURRENT.json',
  'control/project/K01_AI_SESSION_RULES_CURRENT.json',
  'docs/architecture/K01_AI_ENGINEERING_WORKING_PROTOCOL_v1.md',
  'cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_RULES_v1.md',
  'cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json',
  'reports/control/K01_SOLIDWORKS_PROVEN_MANIFEST_CURRENT.json',
  'reports/control/K01_P007_PMI_PROVEN_CURRENT.json',
  'reports/control/K01_P007_PMI_PROVEN_CORE_MANIFEST_CURRENT.json',
  'reports/drawing/current/K01-D-006_P007_PHASE_B_WORKPACK_CURRENT.json',
  'control/project/K01_AUTHORITY_MAP_CURRENT.json',
  'control/project/K01_ENGINEERING_STRATEGY_CURRENT.json',
  'control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json',
  'control/project/K01_TECHNICAL_FILTER_POLICY.json',
  'docs/architecture/K01_ENGINEERING_LIFECYCLE_P0_P6_v1.md',
  'docs/architecture/K01_TECHNICAL_FILTER_POLICY_v1.md',
  'docs/architecture/K01_DIMXPERT_DRAWING_PIPELINE_v1.md',
  'control/drawings/K01_TPD_DRAWING_ASSURANCE_STANDARD_v1.json',
  'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json',
  'control/drawings/K01_DRAWING_REGISTRY_CURRENT.json',
  'docs/architecture/MARVILON_DRAWING_CONTROL_PLANE_V1.md',
  'reports/control/K01_DRAWING_CONTROL_CURRENT.json',
  'control/drawings/K01_DRAWING_CANDIDATE_RETENTION_POLICY_CURRENT.json',
  'control/drawings/spec/K01-D-001_P001_DRAWING_SPEC_v1.json',
  'control/drawings/trace/K01-D-001_TRACE_CURRENT.json',
  'docs/architecture/MARVILON_DRAWING_SYSTEM_V1.md',
  'docs/architecture/MARVILON_DRAWING_CANDIDATE_LIFECYCLE_V1.md',
  'control/medtas/v1/spec/K01_PRODUCT_DEFINITION_POLICY_v1_8.json',
  'reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json',
  'reports/cad/current/K01_GATE04B_DATUM_C_BUILD.json',
  'reports/cad/current/K01_GATE04B_DATUM_C_ASSEMBLY_QA.json',
  'control/decisions/EDR-023_DATUM_C_KINEMATIC_BASELINE.json',
  'control/project/K01_CHECKPOINT_CURRENT.json',
  'control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json',
  'control/project/K01_CONTROL_NAMESPACE_POLICY.json',
  'control/project/K01_ACTIVE_STEP_GATE.json',
  'reports/control/K01_CONTROL_NAMESPACE_GUARD_CURRENT.json',
  'reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json',
  'reports/control/K01_BASELINE_02C_PROMOTION_PREFLIGHT_CURRENT.json',
  'reports/control/K01_PROMOTION_TOOLCHAIN_REVIEW_CURRENT.json',
  'control/requirements/K01_REQUIREMENTS_EVIDENCE_POLICY.json',
  'control/project/K01_BASELINE_02C_PROMOTION_TRANSACTION_CURRENT.json',
  'control/product/parts.json',
  'reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json',
  'reports/pds/K01_P007_J2_READINESS_CURRENT.md',
  'control/pds/K01_P007_J2_LIFECYCLE.json',
  'control/pds/K01_WORK_QUEUE.json',
  'control/repo/K01_SUPERSEDED_SOURCE_REGISTRY_CURRENT.json',
  'reports/control/K01_SOURCE_HYGIENE_CURRENT.json',
  'control/decisions/EDR-025_P007_MONOLITHIC_REMOVABLE_J2_BASELINE.json',
  'control/decisions/EDR-026_T07_PRESSURE_ONLY_SCOPE.json'
]

MANDATORY_SOURCE=[
  'tools/medtas/ai_handoff_v2_0.py',
  'tools/medtas/p007_pmi_proven_step13_current_v1.py',
  'cad_api/solidworks_2018_proven/RUN_P007_PMI_PROVEN_CURRENT.cmd',
  'cad_api/solidworks_2018_proven/current/P007_DIMXPERT_WRITE_C02_C05/K01P007PmiStep13_PROVEN_FROZEN.cs',
  'cad_api/solidworks_2018_proven/current/P007_DIMXPERT_WRITE_C02_C05/run_p007_pmi_step13_PROVEN_FROZEN.py',
  'tools/cli/k01_cli.py',
  'run.cmd',
  'tools/repo/control_namespace_guard.py',
  'tools/assurance/engineering_step_gate.py',
  'tools/medtas/control_authority.py',
  'tools/repo/root_cleanup.py',
  'tools/assurance/prewrite_control.py'
]

MAX_INLINE_REPORT_BYTES=5*1024*1024

def sha256_file(path:Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def sha256_bytes(data:bytes):
    return hashlib.sha256(data).hexdigest()

def load_json(path:Path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:
        return None

def git_snapshot(root:Path):
    def run(*args):
        try:
            cp=subprocess.run(['git',*args],cwd=str(root),capture_output=True,text=True,errors='replace',timeout=20)
            return cp.returncode,cp.stdout.strip(),cp.stderr.strip()
        except Exception as e:
            return 99,'',repr(e)
    _,branch,_=run('branch','--show-current')
    _,head,_=run('rev-parse','HEAD')
    _,remote,_=run('remote','get-url','origin')
    _,status,_=run('status','--short')
    rows=[x for x in status.splitlines() if x.strip()]
    return {
      'captured_local_time':time.strftime('%Y-%m-%d %H:%M:%S'),
      'branch':branch or None,'head':head or None,'origin':remote or None,
      'dirty_count':len(rows),'dirty_sample':rows[:100],'dirty_truncated':len(rows)>100
    }

def is_lock_name(name:str):
    low=name.lower()
    return any(low.startswith(x.lower()) for x in EXCLUDED_FILE_PREFIXES)

def cad_asset_index(cad_root:Path,repo_root:Path):
    assets=[]
    if cad_root.exists():
        for p in cad_root.rglob('*'):
            if not p.is_file() or p.suffix.lower() not in CAD_SUFFIXES or is_lock_name(p.name):
                continue
            try:
                st=p.stat()
                rel=p.relative_to(cad_root).as_posix()
                assets.append({'scope':'native_cad','path':str(p),'relative':rel,'suffix':p.suffix.lower(),'size':st.st_size,'mtime_ns':st.st_mtime_ns})
            except Exception:
                pass
    ref=repo_root/'reference'
    if ref.exists():
        for p in ref.rglob('*'):
            if not p.is_file() or is_lock_name(p.name): continue
            try:
                st=p.stat()
                assets.append({'scope':'repo_reference','path':str(p),'relative':p.relative_to(repo_root).as_posix(),'suffix':p.suffix.lower(),'size':st.st_size,'mtime_ns':st.st_mtime_ns})
            except Exception:
                pass
    assets.sort(key=lambda x:(x['scope'],x['relative'].lower()))
    latest_any={}; stable={}; candidate={}
    for a in assets:
        m=re.search(r'(K01-(?:A|P|B)-\d{3})',Path(a['relative']).name,re.I)
        if not m: continue
        pid=m.group(1).upper()
        def newer(bucket):
            cur=bucket.get(pid)
            if cur is None or a['mtime_ns']>cur['mtime_ns']: bucket[pid]=a
        newer(latest_any)
        rel='/'+a['relative'].replace('\\','/').lower()+'/'
        if '/parts/' in rel or '/assemblies/' in rel: newer(stable)
        if '/candidates/' in rel: newer(candidate)
    return {
      'schema':'k01.asset_index.v2',
      'cad_root':str(cad_root),'cad_root_exists':cad_root.exists(),
      'asset_count':len(assets),'assets':assets,
      'latest_by_identity_non_authoritative':latest_any,
      'stable_by_identity':stable,
      'latest_candidate_by_identity':candidate,
      'note':'mtime is inventory/navigation only; canonical authority comes from baseline/snapshot/hash evidence.'
    }

def current_checkpoint(root:Path):
    ptr=load_json(root/'control/project/K01_CHECKPOINT_CURRENT.json') or {}
    rel=ptr.get('path')
    cp=load_json(root/rel) if rel and (root/rel).is_file() else {}
    if not cp and ptr.get('checkpoint_id'):
        cp=ptr
    return ptr,cp

def dynamic_required_sources(root:Path):
    cfg=load_json(root/'control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json') or {}
    rows=[]
    for x in cfg.get('required',[]) or []:
        if isinstance(x,str) and x.strip(): rows.append(x.strip().replace('\\','/'))
    return list(dict.fromkeys(rows))


def dynamic_runtime_evidence_sources(root:Path):
    """Collect runtime evidence referenced by the *active assurance path* only.

    Do not crawl every historical ``*CURRENT*.json`` report: many current-named reports
    are intentionally retained as historical/parallel engineering evidence and must not
    silently become transport blockers for an unrelated active gate. The active source
    list is derived from K01_NEXT_ACTIONS_CURRENT plus the current D3 control gate.

    A referenced repo-relative report path is returned even when missing on disk so the
    handoff completeness gate fails closed rather than dropping the evidence edge.
    """
    rows=[]
    seen=set()
    next_actions=load_json(root/'control/project/K01_NEXT_ACTIONS_CURRENT.json') or {}
    a17=next_actions.get('drawing_assurance_v17') or {}
    a15=next_actions.get('drawing_assurance_v15') or {}

    candidate_rel=[]
    # V17 is authoritative when present; V15 D7 remains the current downstream QA.
    for key in ('d3_report','requalification_report'):
        rel=a17.get(key)
        if isinstance(rel,str) and rel.strip(): candidate_rel.append(rel.strip().replace('\\','/'))
    rel=a17.get('d7_report') or a15.get('d7_report')
    if isinstance(rel,str) and rel.strip():
        rel=rel.strip().replace('\\','/')
        # D7 is downstream of D3 and may legitimately not exist yet. It becomes
        # runtime evidence only after an actual D7 report has been produced.
        if (root/rel).is_file(): candidate_rel.append(rel)
    # Current transition gate is part of the active D3 -> D7 contract.
    candidate_rel.append('reports/control/K01_P007_D3_AUTHORING_VERIFY_CURRENT.json')
    # Meta-assurance report is active while V17 recovery is the current stage.
    candidate_rel.append('reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json')

    def add_rel(rel):
        rel=rel.replace('\\','/').strip()
        if rel.startswith('reports/') and rel.lower().endswith(('.txt','.log','.json','.md','.csv')) and rel not in seen:
            seen.add(rel); rows.append(rel)

    def walk(x):
        if isinstance(x,dict):
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
        elif isinstance(x,str):
            add_rel(x)

    for rel in candidate_rel:
        add_rel(rel)
        pth=root/rel
        if pth.is_file():
            obj=load_json(pth)
            if obj is not None: walk(obj)
    return rows


def dynamic_authority_sources(root:Path):
    """Pack every declared critical control-family authority; never hard-code a graph/binding version here."""
    amap=load_json(root/'control/project/K01_AUTHORITY_MAP_CURRENT.json') or {}
    rows=[]
    for rec in (amap.get('control_families') or {}).values():
        if isinstance(rec,dict):
            rel=rec.get('authority')
            if isinstance(rel,str) and rel.strip(): rows.append(rel.strip().replace('\\','/'))
    for key in ('engineering_baseline','requirements','product_metadata','requirements_evidence_policy'):
        rel=(amap.get('authorities') or {}).get(key)
        if isinstance(rel,str) and rel.strip() and not any(x in rel for x in (' + ','->','→',';','::')):
            rows.append(rel.strip().replace('\\','/'))
    return list(dict.fromkeys(rows))

def current_resume(root:Path,cad_root:Path):
    next_actions=load_json(root/'control/project/K01_NEXT_ACTIONS_CURRENT.json') or {}
    identity=load_json(root/'reports/cad/identity_freeze/K01_IDENTITY_FREEZE_VERIFY_CURRENT.json') or {}
    producer=load_json(root/'reports/cad/current/K01_GATE04B_DATUM_C_BUILD.json') or {}
    qa=load_json(root/'reports/cad/current/K01_GATE04B_DATUM_C_ASSEMBLY_QA.json') or {}
    checkpoint_ptr,checkpoint=current_checkpoint(root)
    gates=load_json(root/'control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json') or {}
    tech=load_json(root/'reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json') or {}
    p007=load_json(root/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json') or {}
    drawing_system=load_json(root/'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json') or {}
    drawing_registry=load_json(root/'control/drawings/K01_DRAWING_REGISTRY_CURRENT.json') or {}
    drawing_control=load_json(root/'reports/control/K01_DRAWING_CONTROL_CURRENT.json') or {}
    mbd=load_json(root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json') or {}
    ebom=load_json(root/'reports/bom/current/K01_EBOM_A001_CURRENT.json') or {}
    mbom=load_json(root/'reports/bom/current/K01_MBOM_A001_CURRENT.json') or {}
    namespace=load_json(root/'reports/control/K01_CONTROL_NAMESPACE_GUARD_CURRENT.json') or {}
    reqcov=load_json(root/'reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json') or {}
    stepgate_report=load_json(root/'reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json') or {}
    stepgate_contract=load_json(root/'control/project/K01_ACTIVE_STEP_GATE.json') or {}
    stepgate_match=(stepgate_report.get('step_id')==stepgate_contract.get('step_id')) if stepgate_report else False
    stepgate={
      'status': stepgate_report.get('status') if stepgate_match else 'STALE_OR_MISSING_REPORT__ACTIVE_CONTRACT_CURRENT',
      'mutation_authorized': stepgate_report.get('mutation_authorized') if stepgate_match else stepgate_contract.get('mutation_authorized',False),
      'step_id': stepgate_contract.get('step_id'),
      'report_step_id': stepgate_report.get('step_id'),
      'report_matches_contract': stepgate_match
    }
    canonical=identity.get('canonical_assembly') or {}
    reqsum=reqcov.get('summary') or {}
    manifest=load_json(root/'control/project/K01_CURRENT_SESSION_MANIFEST.json') or {}
    return {
      'schema':'k01.resume.current.v3','state_epoch':manifest.get('state_epoch') or next_actions.get('state_epoch'),
      'project':'K01','git':git_snapshot(root),
      'checkpoint':{'id':checkpoint.get('checkpoint_id') or checkpoint_ptr.get('checkpoint_id'),'path':checkpoint_ptr.get('path'),'status':checkpoint.get('status') or checkpoint_ptr.get('status'),'authority':checkpoint.get('authority')},
      'canonical_assembly':canonical,'identity_status':identity.get('status'),
      'datum_c':{
        'producer_status':producer.get('status'),
        'producer_release_status':producer.get('release_status'),
        'assembly_qa_status':qa.get('status'),
        'assembly_qa_release_status':qa.get('release_status'),
        'verification_sha256':qa.get('verification_sha256'),
        'component_count':qa.get('component_count'),
        'unexpected_interference_total':qa.get('unexpected_interference_total'),
        'P003_candidate':qa.get('p003_candidate') or ((producer.get('P003') or {}).get('native')),
        'P016_candidate':qa.get('p016_candidate') or ((producer.get('P016') or {}).get('native')),
        'P017_candidate':qa.get('p017_candidate') or ((producer.get('P017') or {}).get('native'))
      },
      'p0_p6_status':{k:(v or {}).get('status') for k,v in (gates.get('gates') or {}).items()},
      'technical_filter':{'status':tech.get('status'),'unmapped':tech.get('unmapped',[])},
      'drawing':{'P007_D006_status':p007.get('status'),'policy':'DimXpert/PMI-first; drawing derived; no AutoDimension release dump'},
      'drawing_system':{'status':drawing_system.get('status'),'pointer':'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json','validation':drawing_system.get('validation') or {}},
      'drawing_registry':{'pointer':'control/drawings/K01_DRAWING_REGISTRY_CURRENT.json','drawing_ids':sorted((drawing_registry.get('drawings') or {}).keys())},
      'drawing_control':{'status':drawing_control.get('status'),'pointer':'reports/control/K01_DRAWING_CONTROL_CURRENT.json','summary':drawing_control.get('summary') or {},'drawings':{k:{'status':v.get('status'),'semantic_status':v.get('semantic_status'),'latest_candidate':v.get('latest_candidate')} for k,v in (drawing_control.get('drawings') or {}).items()}},
      'mbd':{'status':mbd.get('status'),'issues':mbd.get('issues',[])},
      'bom':{'EBOM_status':ebom.get('status'),'MBOM_status':mbom.get('status')},
      'control_namespace':{'status':namespace.get('status'),'violations':len(namespace.get('violations') or []),'legacy_debt':namespace.get('declared_legacy_sibling_debt')},
      'requirements_coverage':{'status':reqcov.get('status'),'total':reqsum.get('total'),'evidence_linked':reqsum.get('registered_evidence_linked'),'release_blockers_without_registered_evidence':reqsum.get('release_blockers_without_registered_evidence')},
      'step_gate':{'status':stepgate.get('status'),'mutation_authorized':stepgate.get('mutation_authorized')},
      'active_work':next_actions,
      'exact_resume_rule':'Read K01_STATE_EPOCH_CURRENT -> K01_CURRENT_SESSION_MANIFEST -> K01_SESSION_CLOSE_CURRENT -> K01_START_HERE first. Continue only the exact next action after engineering-authority review. CURRENT filename alone is not temporal authority.',
      'cad_root':str(cad_root)
    }

def render_state(resume:dict):
    aw=resume.get('active_work') or {}; d=resume.get('datum_c') or {}; cp=resume.get('checkpoint') or {}
    return '\n'.join([
      '# K01 current state','',
      '> AUTO-GENERATED by the controlled AI handoff builder. Do not hand-edit.','',
      f"- Checkpoint: **{cp.get('id','OPEN')} / {cp.get('status','OPEN')}**",
      f"- Active line: **{aw.get('active_line','OPEN')}**",
      f"- Stage: **{aw.get('current_stage','OPEN')}**",
      f"- Last completed: **{aw.get('last_completed','OPEN')}**",
      f"- Current blocker: **{aw.get('current_blocker','OPEN')}**",
      f"- Next action: **{aw.get('next_1','OPEN')}**",'',
      '## Datum C',
      f"- Producer: **{d.get('producer_status','OPEN')}**",
      f"- Assembly QA: **{d.get('assembly_qa_status','OPEN')}**",
      f"- Candidate authority transition: **{d.get('assembly_qa_release_status','OPEN')}**",
      f"- Verification SHA-256: `{d.get('verification_sha256','OPEN')}`",'',
      '## Control',
      f"- Technical filter map: **{(resume.get('technical_filter') or {}).get('status','OPEN')}**",
      f"- P007/D006 drawing exemplar: **{(resume.get('drawing') or {}).get('P007_D006_status','OPEN')}**",
      f"- Drawing System capability: **{(resume.get('drawing_system') or {}).get('status','OPEN')}** — `control/drawings/K01_DRAWING_SYSTEM_CURRENT.json`",
      f"- Drawing runtime control: **{(resume.get('drawing_control') or {}).get('status','OPEN')}**; holds `{((resume.get('drawing_control') or {}).get('summary') or {}).get('holds',[])}` — `reports/control/K01_DRAWING_CONTROL_CURRENT.json`",
      f"- EBOM / MBOM: **{(resume.get('bom') or {}).get('EBOM_status','OPEN')} / {(resume.get('bom') or {}).get('MBOM_status','OPEN')}**",'',
      '## Rule',
      'Checkpoint -> authority -> dependency/freshness -> technical filter -> material/BOM/DimXpert/drawing impact -> evidence/rollback -> one active mutation -> verification -> promotion.'
    ])+'\n'

def render_start(resume:dict,assets:dict):
    aw=resume.get('active_work') or {}; g=resume.get('git') or {}; d=resume.get('datum_c') or {}; cp=resume.get('checkpoint') or {}
    return '\n'.join([
      '# K01 START HERE','',
      'Mandatory first read for a new K01 engineering session.','',
      f"**Checkpoint:** {cp.get('id','OPEN')} / {cp.get('status','OPEN')}",
      f"**Active line:** {aw.get('active_line','OPEN')}",
      f"**Stage:** {aw.get('current_stage','OPEN')}",
      f"**Last completed:** {aw.get('last_completed','OPEN')}",
      f"**Current blocker:** {aw.get('current_blocker','OPEN')}",
      f"**Exact next action:** {aw.get('next_1','OPEN')}",'',
      '## Current anchors',
      f"- Datum C producer / integration: {d.get('producer_status','OPEN')} / {d.get('assembly_qa_status','OPEN')}",
      f"- Verification SHA-256: `{d.get('verification_sha256','OPEN')}`",
      f"- Native CAD assets indexed: {assets.get('asset_count',0)}",
      f"- Git snapshot: branch `{g.get('branch')}`, HEAD `{g.get('head')}`, dirty {g.get('dirty_count')}",'',
      '## Read next',
      '1. `reports/control/K01_ENGINEERING_CONTROL_PANEL_CURRENT.md`',
      '2. `control/project/K01_CHECKPOINT_CURRENT.json`',
      '3. `control/project/K01_AUTHORITY_MAP_CURRENT.json`',
      '4. `control/project/K01_ENGINEERING_STRATEGY_CURRENT.json`',
      '5. `control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json`',
      '6. `docs/architecture/K01_ENGINEERING_LIFECYCLE_P0_P6_v1.md`',
      '7. `docs/architecture/K01_TECHNICAL_FILTER_POLICY_v1.md`',
      '8. `docs/architecture/K01_DIMXPERT_DRAWING_PIPELINE_v1.md`',
      '9. `control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json`',
      '10. `control/drawings/K01_DRAWING_SYSTEM_CURRENT.json` for Drawing System capabilities',
      '11. `control/drawings/K01_DRAWING_REGISTRY_CURRENT.json` for drawing↔part/spec/trace identity',
      '12. `reports/control/K01_DRAWING_CONTROL_CURRENT.json` for live drawing PASS/HOLD/current artifacts',
      '13. active EDR/change/evidence/source files','',
      '## Non-negotiable',
      'Before mutation: checkpoint + authority + dependency/freshness + technical filter + material + BOM/DimXpert/drawing/inspection impact + rollback/evidence.',
      'Search the included source tree before creating a new tool. Reuse/patch existing implementation.'
    ])+'\n'

def render_control_panel(resume:dict):
    aw=resume.get('active_work') or {}; cp=resume.get('checkpoint') or {}; tf=resume.get('technical_filter') or {}; dw=resume.get('drawing') or {}; bom=resume.get('bom') or {}; ns=resume.get('control_namespace') or {}; rq=resume.get('requirements_coverage') or {}; sg=resume.get('step_gate') or {}
    gate_lines=[]
    for k,v in (resume.get('p0_p6_status') or {}).items():
        gate_lines.append(f"- {k}: **{v or 'OPEN'}**")
    return '\n'.join([
      '# K01 engineering control panel','',
      '> AUTO-GENERATED navigation/summary. Not an engineering authority.','',
      f"**Checkpoint:** `{cp.get('id','OPEN')}` — {cp.get('status','OPEN')}",
      f"**Active line:** `{aw.get('active_line','OPEN')}`",
      f"**Next:** {aw.get('next_1','OPEN')}",'',
      '## P0-P6',*gate_lines,'',
      '## Control integrity / step gate',
      f"- Control namespace: **{ns.get('status','OPEN')}**; violations `{ns.get('violations','OPEN')}`; declared migration debt `{ns.get('legacy_debt','OPEN')}`",
      f"- Active step contract: **{sg.get('step_id','OPEN')}**; mutation authorized `{sg.get('mutation_authorized',False)}`",
      f"- Step-gate verification report: **{sg.get('status','OPEN')}**; report matches active contract `{sg.get('report_matches_contract',False)}`",
      '- Namespace authority: `control/project/K01_AUTHORITY_MAP_CURRENT.json::control_families`','',
      '## Requirements / evidence',
      f"- Coverage: **{rq.get('status','OPEN')}**; total `{rq.get('total','OPEN')}`; registered-evidence-linked `{rq.get('evidence_linked','OPEN')}`; release blockers without registered evidence `{rq.get('release_blockers_without_registered_evidence','OPEN')}`",
      '- Evidence link presence does not equal release verification; method/supporting evidence must not clear a numeric/bench requirement.',
      '- Policy: `control/requirements/K01_REQUIREMENTS_EVIDENCE_POLICY.json`','',
      '## Technical filter',
      f"- Current derived map: **{tf.get('status','OPEN')}**",
      f"- Unmapped nodes: `{len(tf.get('unmapped') or [])}`",
      '- Policy: `control/project/K01_TECHNICAL_FILTER_POLICY.json`',
      '- Derived map: `reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json`','',
      '## Drawings / DimXpert',
      f"- P007 / K01-D-006 exemplar: **{dw.get('P007_D006_status','OPEN')}**",
      '- Pipeline: Product Characteristic -> native CAD semantic feature -> DimXpert/PMI -> tolerance analysis -> SLDDRW/PDF -> lint/visual QA -> inspection traceability.',
      '- Policy: `docs/architecture/K01_DIMXPERT_DRAWING_PIPELINE_v1.md`',
      '- Assurance: `control/drawings/K01_TPD_DRAWING_ASSURANCE_STANDARD_v1.json`',
      f"- Drawing System v1: **{(resume.get('drawing_system') or {}).get('status','OPEN')}**",
      '- Drawing System pointer: `control/drawings/K01_DRAWING_SYSTEM_CURRENT.json`','',
      '## BOM',
      f"- EBOM: **{bom.get('EBOM_status','OPEN')}**",
      f"- MBOM: **{bom.get('MBOM_status','OPEN')}**",
      '- Authority: CAD occurrence tree + parts registry + manufacturing process definitions. Generated BOM is never hand-edited authority.','',
      '## Easy-access authorities',
      '- Strategy: `control/project/K01_ENGINEERING_STRATEGY_CURRENT.json`',
      '- Authority map: `control/project/K01_AUTHORITY_MAP_CURRENT.json`',
      '- Current checkpoint pointer: `control/project/K01_CHECKPOINT_CURRENT.json`',
      '- Immutable checkpoints: `control/checkpoints/`',
      '- P0-P6: `control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json`',
      '- Active change: `control/change/K01_CHANGE_CURRENT.json`',
      '- Decisions: `docs/DECISION_LOG.md`',
      '- Dependency graph authority: `control/project/K01_AUTHORITY_MAP_CURRENT.json::control_families.engineering_build_graph`',
      '- Dependency state: `reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json` (legacy snapshot quarantined at `control/project/K01_DEPENDENCY_STATE.json`)',
      '- Project structure audit: `reports/control/K01_PROJECT_STRUCTURE_CURRENT.json`',
      '- Product registry: `control/product/parts.json`',
      '- Handoff source contract: `control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json`','',
      '## Step discipline',
      'Every engineering action must be checked against the current checkpoint and technical filter before a write. Screening PASS is not release PASS.'
    ])+'\n'

def tree_file_allowed(root:Path,p:Path):
    if not p.is_file() or is_lock_name(p.name): return False
    try: rel=p.relative_to(root)
    except Exception: return False
    if any(part in EXCLUDED_DIR_NAMES for part in rel.parts): return False
    if p.suffix.lower() in NATIVE_EXCLUDED_SUFFIXES: return False
    if p.suffix.lower() not in ALLOWED_TREE_SUFFIXES and p.name not in ('.gitignore','.gitattributes'): return False
    return True

def collect_files(root:Path,out:Path,generated_paths:list[Path],required_rel:set[str]|None=None):
    include=[]; seen=set(); omitted=[]; required_rel=required_rel or set()
    def add(p,report_candidate=False):
        try:
            if not p.is_file() or p.resolve()==out.resolve() or is_lock_name(p.name): return
            rel=p.relative_to(root).as_posix()
        except Exception: return
        if rel=='K01_AI_HANDOFF_MANIFEST.json' or rel in seen: return
        if report_candidate and p.stat().st_size>MAX_INLINE_REPORT_BYTES and rel not in required_rel:
            omitted.append({'path':rel,'size':p.stat().st_size,'sha256':sha256_file(p),'reason':f'oversized report > {MAX_INLINE_REPORT_BYTES} bytes; kept on disk and indexed, omitted from transport ZIP'})
            seen.add(rel); return
        seen.add(rel); include.append((rel,p))
    # Add explicitly required/runtime-referenced evidence first; this covers report
    # subdirectories not represented by broad REPORT_PATTERNS (for example D3 raw TXT).
    for rel in sorted(required_rel):
        p=root/rel
        if p.is_file(): add(p, p.parts[0]=='reports')
    for pat in REPORT_PATTERNS:
        for p in root.glob(pat):
            if p.is_file() and p.suffix.lower() not in NATIVE_EXCLUDED_SUFFIXES: add(p,True)
    for d in TREE_ROOTS:
        base=root/d
        if not base.exists(): continue
        for p in base.rglob('*'):
            if tree_file_allowed(root,p): add(p,False)
    for pat in ROOT_PATTERNS:
        for p in root.glob(pat):
            if tree_file_allowed(root,p): add(p,False)
    for p in generated_paths: add(p,False)
    return sorted(include,key=lambda x:x[0].lower()),sorted(omitted,key=lambda x:x['path'].lower())

def completeness(root:Path,include:list[tuple[str,Path]]):
    included={rel for rel,_ in include}
    required=MANDATORY_CONTEXT+MANDATORY_SOURCE+dynamic_required_sources(root)+dynamic_authority_sources(root)+dynamic_runtime_evidence_sources(root)
    required=list(dict.fromkeys(required))
    missing_disk=[x for x in required if not (root/x).is_file()]
    missing_archive=[x for x in required if x not in included]
    temporal=load_json(root/'reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json') or {}
    temporal_pass=temporal.get('status')=='PASS_TEMPORAL_COHERENCE'
    base_ok=not missing_disk and not missing_archive
    status='PASS_COMPLETE_FOR_RESUME_AND_SOURCE_REVIEW' if base_ok and temporal_pass else ('HOLD_TEMPORAL_INCOHERENCE' if base_ok else 'HOLD_MISSING_REQUIRED_CONTEXT_OR_SOURCE')
    return {
      'schema':'k01.ai_handoff_completeness.v4',
      'generated_local_time':time.strftime('%Y-%m-%d %H:%M:%S'),
      'status':status,
      'required_count':len(required),
      'missing_on_disk':missing_disk,
      'missing_from_archive':missing_archive,
      'temporal_coherence_status':temporal.get('status'),
      'state_epoch':temporal.get('state_epoch'),
      'source_policy':'Active implementation source and proven API rules/core are part of the handoff. Native SOLIDWORKS binaries are indexed, not packed.',
      'notes':[
        'The archive is a transport/resume checkpoint, not product authority.',
        'File presence is insufficient: temporal coherence must PASS before handoff completeness can PASS.',
        'Archive source coverage includes tools/scripts/cad_api/tests text sources to prevent parallel reinvention in later AI sessions.',
        'SOLIDWORKS ~$ lock files are excluded from asset indexing and latest-by-identity selection.'
      ]
    }

def validate_zip(path:Path,manifest:dict):
    errors=[]
    with zipfile.ZipFile(path,'r') as z:
        names=set(z.namelist())
        if 'K01_AI_HANDOFF_MANIFEST.json' not in names: errors.append('MANIFEST_MISSING')
        for item in manifest.get('files',[]):
            rel=item['path']
            if rel not in names:
                errors.append('MISSING:'+rel); continue
            if sha256_bytes(z.read(rel))!=item['sha256']: errors.append('HASH:'+rel)
    return errors

def build_handoff(root:Path,cad_root:Path|None=None):
    root=Path(root).resolve()

    # Temporal precedence preflight. Direct invocation of this builder must be as
    # safe as `run.cmd handoff`; no bypass around the centralized state reducer.
    sync=root/'tools/state/k01_state_sync_v3.py'
    temporal=root/'tools/state/k01_temporal_coherence_guard_v1.py'
    semantic=root/'tools/state/k01_semantic_coherence_guard_v1.py'
    coverage=root/'tools/state/k01_project_control_guard_v1.py'
    if not all(p.is_file() for p in (sync,temporal,semantic,coverage)):
        raise RuntimeError('Global project-control tools missing; refusing to build handoff')
    cp=subprocess.run([sys.executable,str(sync),'--repo-root',str(root)],cwd=str(root))
    if cp.returncode!=0:
        raise RuntimeError(f'Global project state sync failed rc={cp.returncode}')
    for tool,args,label in [
        (temporal,['--write-report'],'Temporal coherence'),
        (semantic,['--write-report'],'Semantic coherence'),
        (coverage,[],'Project coverage coherence')]:
        cp=subprocess.run([sys.executable,str(tool),'--repo-root',str(root),*args],cwd=str(root))
        if cp.returncode!=0:
            raise RuntimeError(f'{label} HOLD rc={cp.returncode}; refusing handoff')

    if cad_root is None:
        default=Path(r'D:\Marvilon\K01\cad')
        cad_root=default if default.exists() else root/'cad'
    else:
        cad_root=Path(cad_root)

    control_dir=root/'reports/control'; control_dir.mkdir(parents=True,exist_ok=True)
    history_dir=control_dir/'handoff_history'; history_dir.mkdir(parents=True,exist_ok=True)
    out=control_dir/'K01_AI_HANDOFF_CURRENT.zip'

    # Build registration first so any graph/build record it changes is eligible for this archive.
    record_warning=None
    if register_build is not None:
        try: register_build(root,'K01.AI.HANDOFF.CURRENT',{'tool':'ai_handoff_v2_0.py','resume_contract':'v2','source_included':True,'native_cad_binaries_excluded':True})
        except Exception as e: record_warning=repr(e)

    assets=cad_asset_index(cad_root,root)
    resume=current_resume(root,cad_root)
    state=render_state(resume)
    panel=render_control_panel(resume)

    start_path=control_dir/'K01_START_HERE.md'
    if not start_path.is_file():
        raise RuntimeError('Centralized START_HERE missing after state reducer')
    start=start_path.read_text(encoding='utf-8',errors='replace')
    resume_path=control_dir/'K01_RESUME_CURRENT.json'
    assets_path=control_dir/'K01_ASSET_INDEX_CURRENT.json'
    state_path=root/'docs/STATE.md'
    panel_path=control_dir/'K01_ENGINEERING_CONTROL_PANEL_CURRENT.md'
    complete_path=control_dir/'K01_AI_HANDOFF_COMPLETENESS_CURRENT.json'
    omitted_path=control_dir/'K01_HANDOFF_OMITTED_EVIDENCE_CURRENT.json'

    # START_HERE is owned exclusively by the centralized state reducer.
    # Handoff may package it but must never regenerate it independently.
    resume_path.write_text(json.dumps(resume,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assets_path.write_text(json.dumps(assets,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    state_path.parent.mkdir(parents=True,exist_ok=True); state_path.write_text(state,encoding='utf-8')
    panel_path.write_text(panel,encoding='utf-8')

    # Handoff itself writes RESUME / derived navigation. Re-run temporal guard
    # after these writes so the archive cannot PASS using a pre-write guard result.
    cp=subprocess.run([sys.executable,str(temporal),'--repo-root',str(root),'--write-report'],cwd=str(root))
    if cp.returncode!=0:
        raise RuntimeError(f'Temporal coherence changed during handoff generation rc={cp.returncode}; refusing archive')

    generated=[start_path,resume_path,assets_path,state_path,panel_path]
    required_rel=set(MANDATORY_CONTEXT+MANDATORY_SOURCE+dynamic_required_sources(root)+dynamic_authority_sources(root)+dynamic_runtime_evidence_sources(root))
    include,omitted=collect_files(root,out,generated,required_rel)
    omitted_rep={'schema':'k01.handoff_omitted_evidence.v1','generated_local_time':time.strftime('%Y-%m-%d %H:%M:%S'),'threshold_bytes':MAX_INLINE_REPORT_BYTES,'omitted_count':len(omitted),'omitted_bytes':sum(x['size'] for x in omitted),'items':omitted,'rule':'Oversized non-mandatory reports remain on disk and are hash-indexed here; they are not duplicated inside the AI transport ZIP.'}
    omitted_path.write_text(json.dumps(omitted_rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    comp=completeness(root,include)
    if record_warning: comp['build_registration_warning']=record_warning
    complete_path.write_text(json.dumps(comp,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    include,_=collect_files(root,out,generated+[complete_path,omitted_path],required_rel)
    manifest=[]
    for rel,p in include:
        manifest.append({'path':rel,'size':p.stat().st_size,'sha256':sha256_file(p)})

    meta={
      'schema':'k01.ai_handoff_manifest.v3',
      'generated_local_time':time.strftime('%Y-%m-%d %H:%M:%S'),
      'project':'K01',
      'checkpoint':resume.get('checkpoint'),
      'active_line':(resume.get('active_work') or {}).get('active_line'),
      'git':resume.get('git'),
      'file_count':len(manifest),
      'completeness_status':comp['status'],
      'files':manifest,
      'mandatory_first_read':[
        'control/state/K01_STATE_EPOCH_CURRENT.json',
        'control/project/K01_CURRENT_SESSION_MANIFEST.json',
        'reports/control/K01_SESSION_CLOSE_CURRENT.md',
        'reports/control/K01_START_HERE.md',
        'reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json',
        'control/project/K01_AI_SESSION_RULES_CURRENT.json',
        'docs/architecture/K01_AI_ENGINEERING_WORKING_PROTOCOL_v1.md',
        'cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_RULES_v1.md',
        'cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json',
        'reports/control/K01_P007_PMI_PROVEN_CURRENT.json',
        'reports/drawing/current/K01-D-006_P007_PHASE_B_WORKPACK_CURRENT.json',
        'reports/control/K01_START_HERE.md',
        'reports/control/K01_ENGINEERING_CONTROL_PANEL_CURRENT.md',
        'reports/control/K01_RESUME_CURRENT.json',
        'control/project/K01_CHECKPOINT_CURRENT.json',
        'control/project/K01_AUTHORITY_MAP_CURRENT.json',
        'control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json',
        'control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json',
  'control/project/K01_CONTROL_NAMESPACE_POLICY.json',
  'control/project/K01_ACTIVE_STEP_GATE.json',
  'reports/control/K01_CONTROL_NAMESPACE_GUARD_CURRENT.json',
  'reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json',
  'control/requirements/K01_REQUIREMENTS_EVIDENCE_POLICY.json',
        'docs/architecture/K01_ENGINEERING_LIFECYCLE_P0_P6_v1.md',
        'docs/architecture/K01_TECHNICAL_FILTER_POLICY_v1.md',
        'docs/architecture/K01_DIMXPERT_DRAWING_PIPELINE_v1.md'
      ],
      'omitted_oversized_reports':{'count':len(omitted),'bytes':sum(x['size'] for x in omitted),'index':'reports/control/K01_HANDOFF_OMITTED_EVIDENCE_CURRENT.json'},
      'note':'Current semantic/control/evidence/source handoff. Native SOLIDWORKS binaries are excluded and indexed separately; oversized non-mandatory reports are hash-indexed, not duplicated.'
    }

    # Persist the same manifest beside the repo so coherence checks and Center never
    # inspect a stale manifest left from a previous transport checkpoint.
    manifest_path=root/'K01_AI_HANDOFF_MANIFEST.json'
    manifest_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    tmp=out.with_suffix('.tmp.zip')
    if tmp.exists(): tmp.unlink()
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for rel,p in include: z.write(p,rel)
        z.writestr('K01_AI_HANDOFF_MANIFEST.json',json.dumps(meta,ensure_ascii=False,indent=2).encode('utf-8'))
    errors=validate_zip(tmp,meta)
    if errors:
        tmp.unlink(missing_ok=True)
        raise RuntimeError('AI handoff self-validation failed: '+'; '.join(errors[:20]))
    os.replace(tmp,out)

    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    hist=history_dir/f'K01_AI_HANDOFF_{stamp}.zip'
    shutil.copy2(out,hist)

    result={
      'ok':comp['status'].startswith('PASS'),
      'status':comp['status'],
      'id':'AI-HANDOFF-CURRENT',
      'path':str(out),'history_path':str(hist),
      'size':out.stat().st_size,'sha256':sha256_file(out),'files':len(manifest),
      'start_here':str(start_path),'control_panel':str(panel_path),
      'resume':str(resume_path),'asset_index':str(assets_path),'completeness':str(complete_path),'omitted_evidence':str(omitted_path),'manifest':str(manifest_path)
    }
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',required=True)
    ap.add_argument('--cad-root',default=None)
    a=ap.parse_args()
    res=build_handoff(Path(a.repo_root),Path(a.cad_root) if a.cad_root else None)
    print('AI handoff status:',res['status'])
    print('AI handoff built:',res['files'],'files, SHA-256',res['sha256'])
    print('CURRENT:',res['path'])
    print('HISTORY:',res['history_path'])
    print('START HERE:',res['start_here'])
    print('CONTROL PANEL:',res['control_panel'])
    print('COMPLETENESS:',res['completeness'])
    return 0 if res['ok'] else 2

if __name__=='__main__':
    raise SystemExit(main())
