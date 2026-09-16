import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_presentation_policy_shape():
    p=json.loads((ROOT/'control/drawings/presentation/K01_DRAWING_PRESENTATION_POLICY_V1.json').read_text(encoding='utf-8'))
    assert p['schema']=='k01.drawing_presentation_policy.v1'
    assert p['sheet']['width_m']>0 and p['sheet']['height_m']>0
    assert p['reserved_regions']

def test_pointer_names_presentation_layer():
    p=json.loads((ROOT/'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json').read_text(encoding='utf-8'))
    i=p['implementation']
    for k in ('presentation_audit','presentation_capture','presentation_policy'):
        assert (ROOT/i[k]).exists(), (k,i[k])
    assert p['validation']['D006']['generic_engine'].startswith('PASS')

def test_handoff_contains_presentation_layer():
    p=json.loads((ROOT/'control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json').read_text(encoding='utf-8'))
    r=set(p['required'])
    assert 'docs/architecture/MARVILON_DRAWING_PRESENTATION_ENGINE_V1.md' in r
    assert 'tools/medtas/drawing_presentation_audit_v1.py' in r


def test_section_view_identity_and_backward_match_are_locked():
    engine=(ROOT/'cad_api/solidworks_2018_proven/current/K01_DRAWING_SYSTEM_V1/K01DrawingSystemV1.cs').read_text(encoding='utf-8')
    audit=(ROOT/'cad_api/solidworks_2018_proven/current/K01_DRAWING_PRESENTATION_V1/K01DrawingPresentationAuditV1.cs').read_text(encoding='utf-8')
    assert 'sec.SetName2(AName("VIEW_"+s.id))' in engine
    assert 'Backward-compatible recovery for candidates generated before section views were semantically named.' in audit
    assert 'Dist2(p[0],p[1],s.x_m,s.y_m)' in audit

def test_presentation_runner_reaps_owned_solidworks():
    src=(ROOT/'tools/medtas/drawing_presentation_audit_v1.py').read_text(encoding='utf-8')
    assert 'def cleanup_owned_solidworks()' in src
    assert 'taskkill' in src and 'SLDWORKS.exe' in src
    assert 'finally:' in src and 'cleanup_owned_solidworks()' in src
