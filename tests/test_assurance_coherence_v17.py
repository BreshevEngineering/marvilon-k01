from pathlib import Path
import json, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]

def put(root,rel,obj):
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj),encoding='utf-8');return p

def test_v17_files_present_and_graph_acyclic():
    for rel in [
      'RUN_K01_ASSURANCE_RECOVERY_V17.cmd','RUN_K01_D3_VERIFY_P007_V17.cmd',
      'tools/assurance/d006_exemplar_requalify_v17.py','tools/assurance/assurance_recovery_v17.py',
      'tools/medtas/drawing_d3_verify_v17.py','control/drawings/K01_P007_D3_EXECUTION_CONTRACT_CURRENT.json',
      'control/medtas/v1/graph/K01_engineering_build_graph_v2_6.json']:
        assert (ROOT/rel).is_file(), rel
    g=json.loads((ROOT/'control/medtas/v1/graph/K01_engineering_build_graph_v2_6.json').read_text(encoding='utf-8-sig'))
    nodes={n['node_id']:n for n in g['nodes']}
    assert 'K01.DRAWING.D006.EXEMPLAR.REQUALIFICATION' in nodes
    assert 'K01.DRAWING.D006.D3.EXECUTION.CONTRACT' in nodes
    d3=nodes['K01.DRAWING.D006.D3.AUTHORING_VERIFY']
    assert d3['producer']['implementation'].endswith('drawing_d3_verify_v17.py')
    deps={x['node_id'] for x in d3['contract']['inputs']}
    assert {'K01.DRAWING.D006.EXEMPLAR.REQUALIFICATION','K01.DRAWING.D006.D3.EXECUTION.CONTRACT'} <= deps
    indeg={k:0 for k in nodes}; out={k:[] for k in nodes}
    for k,n in nodes.items():
        for inp in n.get('contract',{}).get('inputs',[]):
            src=inp['node_id']; assert src in nodes,(k,src); indeg[k]+=1; out[src].append(k)
    q=[k for k,v in indeg.items() if v==0]; seen=0
    while q:
        x=q.pop(); seen+=1
        for y in out[x]:
            indeg[y]-=1
            if indeg[y]==0:q.append(y)
    assert seen==len(nodes)

def test_authority_map_points_v26_and_program_chain_not_lost():
    a=json.loads((ROOT/'control/project/K01_AUTHORITY_MAP_CURRENT.json').read_text(encoding='utf-8-sig'))
    assert a['control_families']['engineering_build_graph']['authority'].endswith('K01_engineering_build_graph_v2_6.json')
    n=json.loads((ROOT/'control/project/K01_NEXT_ACTIONS_CURRENT.json').read_text(encoding='utf-8-sig'))
    assert n['current_stage']=='K01_ASSURANCE_RECOVERY_V17_THEN_D3'
    assert n['drawing_assurance_v17']['d3_command']=='RUN_K01_D3_VERIFY_P007_V17.cmd'
    seq=n['program_sequence_after_exemplar']
    assert 'bom' in seq and 'engineering_domains' in seq and 'assembly_release' in seq
    assert any('D8' in x for x in seq['drawing'])
    assert any('EBOM' in x for x in seq['bom'])
    assert any('FEMM' in x for x in seq['engineering_domains'])

def test_explicit_requalification_fixture_passes_without_cad_write():
    with tempfile.TemporaryDirectory() as d:
        r=Path(d)
        put(r,'reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json',{'part':'K01-P-007','drawing':'K01-D-006','d1_plan_sha256':'OLD','d2_authorizable_claim_ids':['C01.DATUM_A','C02.DIAMETER_FIT','C09.MATERIAL']})
        put(r,'reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json',{'authoring_plan_sha256':'NEW','d2_authorizable_claim_ids':['C01.DATUM_A','C02.DIAMETER_FIT','C09.MATERIAL'],'tasks':[
          {'claim_id':'C01.DATUM_A','annotation_view_role':'AV_J2_LONGITUDINAL','resolved_claim_values':{'nominal_or_requirement.datum':'A'}},
          {'claim_id':'C02.DIAMETER_FIT','resolved_claim_values':{'nominal_or_requirement.diameter_mm':14.1,'variation_semantics.diameter_fit':'H7'}},
          {'claim_id':'C09.MATERIAL','resolved_claim_values':{'nominal_or_requirement.material':'AISI 316L / EN 1.4404'}}]})
        put(r,'control/drawings/K01_D006_EXEMPLAR_POLICY_CURRENT.json',{'d2_authoring_scope':{'expected_now':['C01.DATUM_A','C02.DIAMETER_FIT','C09.MATERIAL']}})
        put(r,'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json',{})
        cp=subprocess.run([sys.executable,str(ROOT/'tools/assurance/d006_exemplar_requalify_v17.py'),'--repo-root',str(r)],capture_output=True,text=True)
        assert cp.returncode==0,cp.stdout+cp.stderr
        out=json.loads((r/'reports/drawing/current/K01-D-006_EXEMPLAR_REQUALIFICATION_CURRENT.json').read_text())
        assert out['status'].startswith('PASS_EXEMPLAR_REQUALIFIED')
        assert out['cad_mutated'] is False
        assert out['original_workspace_d1_pin']=='OLD' and out['current_d1_pin']=='NEW'
