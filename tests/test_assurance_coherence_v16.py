from pathlib import Path
import json, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]

def put(root,rel,obj):
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj),encoding='utf-8');return p

def test_v16_guard_and_center_contract_present():
    for rel in [
        'RUN_K01_ASSURANCE_COHERENCE_V16.cmd',
        'tools/assurance/center_assurance_coherence.py',
        'control/center/K01_CENTER_ASSURANCE_INTEGRITY_CONTRACT.json',
        'docs/architecture/K01_CENTER_ASSURANCE_COHERENCE_TZ_v3.md']:
        assert (ROOT/rel).is_file(), rel

def test_coherent_fixture_passes():
    with tempfile.TemporaryDirectory() as d:
        r=Path(d)
        put(r,'reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json',{'d1_plan_sha256':'OLD'})
        put(r,'reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json',{'authoring_plan_sha256':'NEW','tasks':[{'claim_id':'C01.DATUM_A','annotation_view_role':'AV_J2_LONGITUDINAL'}]})
        put(r,'reports/drawing/current/K01-D-006_EXEMPLAR_REQUALIFICATION_CURRENT.json',{'status':'PASS_EXEMPLAR_REQUALIFIED_TO_CURRENT_D1_FROZEN_SCOPE','original_workspace_d1_pin':'OLD','current_d1_pin':'NEW'})
        put(r,'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json',{'characteristics':[{'id':'C01','solidworks_binding':{'binding_type':'COMPOSITE_COPLANAR_FACE_SET','entities':[{},{}]}}]})
        put(r,'control/drawings/K01_P007_D3_EXECUTION_CONTRACT_CURRENT.json',{'status':'ACTIVE','C01.DATUM_A':{'authority_binding_type':'COMPOSITE_COPLANAR_FACE_SET','authority_entity_count':2},'annotation_view_roles':{'AV_J2_LONGITUDINAL':{'status':'CONTROLLED_FOR_STANDARD_SW_VIEWS','allowed_standard_view_names':['*Front']}}})
        c=r/'tools/medtas/drawing_d3_verify_v17.py';c.parent.mkdir(parents=True,exist_ok=True);c.write_text('AUTHORITY_BINDING_CONTRACT_ENFORCED=True\nVIEW_ROLE_CONTRACT_ENFORCED=True\ndef c01_authority_member(): pass\ndef view_role_ok(): pass\n',encoding='utf-8')
        graph='control/medtas/v1/graph/K01_engineering_build_graph_v2_6.json'
        put(r,'control/project/K01_AUTHORITY_MAP_CURRENT.json',{'control_families':{'engineering_build_graph':{'authority':graph}}})
        nodes=[{'node_id':'K01.DRAWING.D006.D3.AUTHORING_VERIFY','contract':{'inputs':[]}}]
        put(r,graph,{'nodes':nodes})
        put(r,'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',{'nodes':{'K01.DRAWING.D006.D3.AUTHORING_VERIFY':{}}})
        put(r,'control/project/K01_DEPENDENCY_STATE.json',{'status':'LEGACY_QUARANTINED_DO_NOT_CONSUME_AS_CURRENT_AUTHORITY','authority':False,'nodes':{}})
        put(r,'control/center/K01_CENTER_INPUT_CURRENT.json',{'dependency_state':'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'})
        put(r,'reports/control/K01_P007_D3_AUTHORING_VERIFY_CURRENT.json',{'transition_contract':'FULL_D3_GATE_PASS_REQUIRED_FOR_D7','next':'L1/L2 alone never authorize D7. Run D7 only after PASS_D3_EXEMPLAR_*.'})
        put(r,'reports/drawing/current/K01-P-007_D3_AUTHORING_VERIFY_CURRENT.json',{})
        put(r,'K01_AI_HANDOFF_MANIFEST.json',{'files':[]})
        put(r,'reports/control/K01_HANDOFF_OMITTED_EVIDENCE_CURRENT.json',{'items':[]})
        cp=subprocess.run([sys.executable,str(ROOT/'tools/assurance/center_assurance_coherence.py'),'--repo-root',str(r),'--no-write'],capture_output=True,text=True)
        assert cp.returncode==0, cp.stdout+cp.stderr
        assert 'PASS_ASSURANCE_COHERENCE' in cp.stdout

def test_current_handoff_classes_are_detectable():
    cp=subprocess.run([sys.executable,str(ROOT/'tools/assurance/center_assurance_coherence.py'),'--repo-root',str(ROOT),'--no-write'],capture_output=True,text=True)
    assert cp.returncode in (0,3)
    # The guard must at least expose the named checks; their state evolves as defects are repaired.
    for ident in ['ACI-001_D1_WORKSPACE_PROVENANCE_PIN','ACI-002_AUTHORITY_EXECUTOR_BINDING_CONTRACT','ACI-004_GRAPH_DERIVED_STATE_PARITY','ACI-007_HANDOFF_RUNTIME_EVIDENCE_CLOSURE']:
        assert ident in cp.stdout
