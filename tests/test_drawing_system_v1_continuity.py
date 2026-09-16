import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_pointer_and_files_exist():
    p=ROOT/'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json'
    d=json.loads(p.read_text(encoding='utf-8'))
    assert d['schema']=='k01.drawing_system.current.v1'
    assert d['status'].startswith('GENERIC_SEMANTIC_CORE_VALIDATED')
    assert d['validation']['candidate_lifecycle']['placement_roundtrip']=='PASS'
    for rel in d['canonical_read_order']:
        if '<drawing_id>' not in rel: assert (ROOT/rel).exists(), rel
    for k,rel in d['implementation'].items():
        if k in ('placement_root','drawing_specs_root'): assert (ROOT/rel).is_dir(), rel
        else: assert (ROOT/rel).is_file(), rel

def test_handoff_requires_pointer():
    d=json.loads((ROOT/'control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json').read_text(encoding='utf-8'))
    assert 'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json' in d['required']
    assert 'docs/architecture/MARVILON_DRAWING_SYSTEM_V1.md' in d['required']

def test_ai_handoff_mentions_pointer():
    s=(ROOT/'tools/medtas/ai_handoff_v2_0.py').read_text(encoding='utf-8')
    assert 'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json' in s
    assert 'control/drawings/K01_DRAWING_REGISTRY_CURRENT.json' in s
    assert 'reports/control/K01_DRAWING_CONTROL_CURRENT.json' in s


def test_d003_view_strategy_and_datum_views():
    d=json.loads((ROOT/'control/drawings/spec/K01-D-003_P003_DRAWING_SPEC_v2.json').read_text(encoding='utf-8'))
    vs=d['view_strategy']
    assert vs['primary_representation']=='LONGITUDINAL_SECTION'
    required={x['view'] for x in vs['interface_end_views'] if x.get('required')}
    assert required=={'J1_END','J2_END'}
    views={x['id'] for x in d['view_definitions']}
    assert {'SECTION','J1_END','J2_END'} <= views
    assert all(x.get('view') in views for x in d['datum_features'])

def test_d006_generic_regression_spec_and_runner_present():
    spec_path=ROOT/'control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v1.json'
    assert spec_path.is_file()
    d=json.loads(spec_path.read_text(encoding='utf-8'))
    assert d['schema']=='k01.drawing_system_spec.v1'
    assert d['drawing_id']=='K01-D-006'
    assert d['part_id']=='K01-P-007'
    views={x['id'] for x in d['view_definitions']}
    assert views=={'SECTION','J2_END'}
    assert d['view_strategy']['primary_representation']=='LONGITUDINAL_SECTION'
    assert {x['id'] for x in d['datum_features']}=={'A','B'}
    anns={x['id']:x for x in d['annotations']}
    assert anns['D006-C01-FLATNESS']['zone_modifier']=='CZ'
    assert anns['D006-C04-POS']['zone_modifier']=='CZ'
    assert anns['D006-C04-POS']['material_modifier']=='M'
    assert anns['D006-C04-HOLES']['prefix']=='3× '
    assert anns['D006-C04-HOLES']['suffix']==' THRU'
    assert anns['D006-J2-RA08']['kind']=='SURFACE_FINISH'
    assert (ROOT/'RUN_K01_D006_DRAWING_SYSTEM_V1.cmd').is_file()


def test_pointer_records_d006_runtime_proof_and_control_plane_next():
    d=json.loads((ROOT/'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json').read_text(encoding='utf-8'))
    assert d['entry_points']['d006_build']=='RUN_K01_D006_DRAWING_SYSTEM_V1.cmd'
    assert d['validation']['D006']['generic_engine'].startswith('PASS')
    assert 'Do not rebuild K01-D-001' in d['next_validation']
    assert d['control_plane']['runtime_projection']=='reports/control/K01_DRAWING_CONTROL_CURRENT.json'
    assert 'historical capability evidence' in d['control_plane']['runtime_status_rule']
    assert d['control_plane']['auto_delete_candidates'] is False

def test_status_command_uses_runtime_control_not_d001_pointer_status():
    s=(ROOT/'tools/medtas/drawing_system_status_v1.py').read_text(encoding='utf-8')
    assert "CONTROL_REL='reports/control/K01_DRAWING_CONTROL_CURRENT.json'" in s
    assert "D001 GENERIC ENGINE:" not in s
    assert "runtime=" in s


def test_center_feed_exposes_registry_and_runtime_control():
    s=(ROOT/'tools/medtas/center_feed_v1_2.py').read_text(encoding='utf-8')
    assert "'drawing_registry':" in s
    assert "'drawing_control':" in s


def test_registry_declares_runtime_authority():
    d=json.loads((ROOT/'control/drawings/K01_DRAWING_REGISTRY_CURRENT.json').read_text(encoding='utf-8'))
    assert d['runtime_status_authority']=='reports/control/K01_DRAWING_CONTROL_CURRENT.json'
