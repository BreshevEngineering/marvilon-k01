from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def add(checks, ident, ok, severity='HOLD', **details):
    checks.append({'id':ident,'pass':bool(ok),'severity':severity if not ok else 'INFO',**details})


def main():
    ap=argparse.ArgumentParser(description='Read-only coherence guard for authority -> executor -> evidence -> graph -> handoff.')
    ap.add_argument('--repo-root',required=True)
    ap.add_argument('--no-write',action='store_true')
    a=ap.parse_args()
    root=Path(a.repo_root.strip().strip('"')).resolve()
    checks=[]

    # 1. D1 provenance pinning for the current exemplar.
    ws_path=root/'reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json'
    d1_path=root/'reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json'
    ws=load_json(ws_path) or {}; d1=load_json(d1_path) or {}
    ws_sha=ws.get('d1_plan_sha256'); d1_sha=d1.get('authoring_plan_sha256')
    rq=load_json(root/'reports/drawing/current/K01-D-006_EXEMPLAR_REQUALIFICATION_CURRENT.json') or {}
    exact_pin=bool(ws_sha and d1_sha and ws_sha==d1_sha)
    explicit_requal=bool(rq.get('status')=='PASS_EXEMPLAR_REQUALIFIED_TO_CURRENT_D1_FROZEN_SCOPE' and rq.get('original_workspace_d1_pin')==ws_sha and rq.get('current_d1_pin')==d1_sha)
    add(checks,'ACI-001_D1_WORKSPACE_PROVENANCE_PIN', exact_pin or explicit_requal,
        workspace_pin=ws_sha,current_d1_semantic_sha=d1_sha,exact_pin=exact_pin,explicit_requalification=explicit_requal,
        requalification_report='reports/drawing/current/K01-D-006_EXEMPLAR_REQUALIFICATION_CURRENT.json' if rq else None,
        rule='The active exemplar must use its original D1 pin or an explicit fail-closed requalification that preserves the frozen D2 claim scope; silent reinterpretation by a newer CURRENT plan is forbidden.')

    # 2. C01 authority semantics versus the active V17 acceptance layer.
    pd_path=root/'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json'
    pd=load_json(pd_path) or {}
    c01=next((x for x in pd.get('characteristics',[]) if isinstance(x,dict) and x.get('id')=='C01'),{})
    binding=c01.get('solidworks_binding',{}) if isinstance(c01,dict) else {}
    btype=binding.get('binding_type') or (pd.get('datum_A') or {}).get('binding_mode')
    expected_count=len(binding.get('entities',[]) or [])
    exec_path=root/'control/drawings/K01_P007_D3_EXECUTION_CONTRACT_CURRENT.json'
    exec_contract=load_json(exec_path) or {}
    d3_py=root/'tools/medtas/drawing_d3_verify_v17.py'
    d3_text=d3_py.read_text(encoding='utf-8-sig',errors='replace') if d3_py.is_file() else ''
    ec01=exec_contract.get('C01.DATUM_A') or {}
    contract_matches=(exec_contract.get('status')=='ACTIVE' and ec01.get('authority_binding_type')==btype and ec01.get('authority_entity_count')==expected_count)
    wrapper_enforces=('AUTHORITY_BINDING_CONTRACT_ENFORCED=True' in d3_text and 'c01_authority_member' in d3_text and "S2_C01_GEOM" not in d3_text.split('c01_authority_member',1)[0][-800:])
    semantic_ok=bool(btype=='COMPOSITE_COPLANAR_FACE_SET' and expected_count==2 and contract_matches and wrapper_enforces)
    add(checks,'ACI-002_AUTHORITY_EXECUTOR_BINDING_CONTRACT', semantic_ok,
        authority_binding_type=btype,authority_entity_count=expected_count,execution_contract=str(exec_path.relative_to(root)),
        contract_matches_authority=contract_matches,active_wrapper='tools/medtas/drawing_d3_verify_v17.py',wrapper_enforces_authority_contract=wrapper_enforces,
        rule='The active D3 acceptance layer must consume the controlled composite datum semantics. The SW2018 helper may act as a sensor, but its legacy positional heuristic may not decide C01 acceptance.')

    # 3. Annotation-view role must be an explicit machine contract, even when a current exemplar violates it.
    role=None
    try:
        role=next((x.get('annotation_view_role') for x in d1.get('tasks',[]) if x.get('claim_id')=='C01.DATUM_A'),None)
    except Exception:
        pass
    if role is None:
        txt=json.dumps(d1,ensure_ascii=False)
        m=re.search(r'AV_J2_LONGITUDINAL',txt)
        role='AV_J2_LONGITUDINAL' if m else None
    role_rec=((exec_contract.get('annotation_view_roles') or {}).get(role) or {}) if role else {}
    view_contract=bool(role and role_rec.get('status') and role_rec.get('allowed_standard_view_names') and 'VIEW_ROLE_CONTRACT_ENFORCED=True' in d3_text and 'view_role_ok' in d3_text)
    add(checks,'ACI-003_ANNOTATION_VIEW_ROLE_CONTRACT', bool((not role) or view_contract),
        required_role=role,execution_contract=str(exec_path.relative_to(root)),role_status=role_rec.get('status'),
        allowed_standard_view_names=role_rec.get('allowed_standard_view_names'),verifier_has_role_contract=view_contract,
        rule='A non-empty SOLIDWORKS view name is insufficient. D1 normalized role must map through an explicit execution contract; a current drawing may still fail that role without creating a meta-coherence defect.')

    # 4. Graph authority and materialized derived-state parity.
    auth=load_json(root/'control/project/K01_AUTHORITY_MAP_CURRENT.json') or {}
    graph_rel=(((auth.get('control_families') or {}).get('engineering_build_graph') or {}).get('authority'))
    graph_path=root/graph_rel if graph_rel else root/'control/project/__MISSING_ENGINEERING_BUILD_GRAPH_AUTHORITY__.json'
    graph=load_json(graph_path) or {}
    graph_nodes={n.get('node_id') for n in graph.get('nodes',[]) if isinstance(n,dict) and n.get('node_id')}
    derived=load_json(root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json') or {}
    derived_nodes=set((derived.get('nodes') or {}).keys()) if isinstance(derived.get('nodes'),dict) else set()
    missing=sorted(graph_nodes-derived_nodes)
    add(checks,'ACI-004_GRAPH_DERIVED_STATE_PARITY', len(missing)==0,
        graph=str(graph_path.relative_to(root)) if graph_path.is_relative_to(root) else str(graph_path),
        graph_node_count=len(graph_nodes),derived_node_count=len(derived_nodes),missing_nodes=missing[:50],missing_count=len(missing),
        rule='Center/automation may not present a graph version whose authoritative nodes are absent from materialized derived state.')

    # 5. Legacy dependency state must not masquerade as current authority.
    dep=load_json(root/'control/project/K01_DEPENDENCY_STATE.json') or {}
    dep_generated=dep.get('generated_utc')
    graph_generated=graph.get('generated_utc') or graph.get('generated_local_time')
    legacy_nodes=set((dep.get('nodes') or {}).keys()) if isinstance(dep.get('nodes'),dict) else set()
    d3node='K01.DRAWING.D006.D3.AUTHORING_VERIFY'
    center_input=load_json(root/'control/center/K01_CENTER_INPUT_CURRENT.json') or {}
    quarantined='legacy_quarantined' in str(dep.get('status','')).lower() and dep.get('authority') is False
    center_uses_current=center_input.get('dependency_state')=='reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'
    dep_current = bool(quarantined and center_uses_current)
    add(checks,'ACI-005_LEGACY_DEPENDENCY_STATE_QUARANTINE', dep_current,
        dependency_generated_utc=dep_generated,graph_generated=graph_generated,dependency_node_count=len(legacy_nodes),legacy_status=dep.get('status'),
        center_dependency_state=center_input.get('dependency_state'),quarantined=quarantined,center_uses_current_medtas=center_uses_current,
        rule='Legacy dependency snapshots may remain for history only when explicitly quarantined and no Center current-state source consumes them.')

    # 6. Stage sequencing language must agree with executable gate condition.
    gate=load_json(root/'reports/control/K01_P007_D3_AUTHORING_VERIFY_CURRENT.json') or {}
    nxt=str(gate.get('next',''))
    transition=gate.get('transition_contract')
    sequence_ok=(transition=='FULL_D3_GATE_PASS_REQUIRED_FOR_D7' and 'L1/L2 alone never authorize D7' in nxt)
    add(checks,'ACI-006_STAGE_TRANSITION_CONTRACT', sequence_ok,
        declared_next=nxt,transition_contract=transition,
        rule='D7 is authorized by full D3 gate PASS, not by a subset such as L1/L2.')

    # 7. Runtime evidence referenced by D3 must be transportable or explicitly omitted/hash indexed.
    d3=load_json(root/'reports/drawing/current/K01-P-007_D3_AUTHORING_VERIFY_CURRENT.json') or {}
    referenced=[]
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if isinstance(v,str) and (v.endswith(('.txt','.log','.json')) and ('reports/' in v.replace('\\','/'))):
                    referenced.append(v.replace('\\','/'))
                else: walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(d3)
    manifest=load_json(root/'K01_AI_HANDOFF_MANIFEST.json') or {}
    packed=set()
    for item in manifest.get('files',manifest.get('items',[])) if isinstance(manifest,dict) else []:
        if isinstance(item,dict) and item.get('path'): packed.add(str(item['path']).replace('\\','/'))
    omitted=load_json(root/'reports/control/K01_HANDOFF_OMITTED_EVIDENCE_CURRENT.json') or {}
    omitted_paths={str(x.get('path','')).replace('\\','/') for x in omitted.get('items',[]) if isinstance(x,dict)}
    missing_evidence=[]
    for rel in sorted(set(referenced)):
        # A current gate reference must resolve in the transport package, or be explicitly
        # declared as omitted/hash-indexed. A dangling path is itself a closure defect.
        if rel not in packed and rel not in omitted_paths:
            missing_evidence.append(rel)
    add(checks,'ACI-007_HANDOFF_RUNTIME_EVIDENCE_CLOSURE', len(missing_evidence)==0,
        referenced_runtime_evidence=sorted(set(referenced)),unpacked_unindexed=missing_evidence,
        rule='Evidence referenced by a current gate must be packed in the handoff or explicitly hash-indexed as omitted evidence.')

    blockers=[c for c in checks if not c['pass'] and c['severity']=='HOLD']
    status='PASS_ASSURANCE_COHERENCE' if not blockers else 'HOLD_ASSURANCE_COHERENCE'
    report={
        'schema':'k01.assurance_coherence.current.v17',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'status':status,
        'blocking_count':len(blockers),
        'checks':checks,
        'scope':'Read-only meta-assurance. This report does not decide engineering acceptance; it verifies coherence between controlled authority, executors, evidence, graph state and handoff.',
        'next':'Resolve every ACI HOLD before using downstream stage actions in Center.' if blockers else 'Meta-assurance coherent; downstream engineering gates remain authoritative.'
    }
    if not a.no_write:
        out=root/'reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json'
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        print('REPORT:',out)
    print('STATUS:',status)
    for c in checks:
        print(('PASS' if c['pass'] else 'HOLD'),c['id'])
    return 0 if not blockers else 3

if __name__=='__main__':
    raise SystemExit(main())
