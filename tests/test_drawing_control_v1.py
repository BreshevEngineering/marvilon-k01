from __future__ import annotations
import json, sys, pytest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'medtas'))
import drawing_control_v1 as dc
import drawing_system_v1 as ds


def test_d001_spec_preflight_holds_until_product_definition_ready():
    with pytest.raises(RuntimeError, match='HOLD_PRODUCT_DEFINITION'):
        ds.preflight(ROOT, ROOT/'control/drawings/spec/K01-D-001_P001_DRAWING_SPEC_v1.json', 'review')


def test_registry_and_control_plane_contract():
    reg=json.loads((ROOT/'control/drawings/K01_DRAWING_REGISTRY_CURRENT.json').read_text(encoding='utf-8'))
    assert set(['K01-D-001','K01-D-003','K01-D-006']).issubset(reg['drawings'])
    assert reg['current_root'].endswith(r'cad\drawings\current')
    retention=json.loads((ROOT/'control/drawings/K01_DRAWING_CANDIDATE_RETENTION_POLICY_CURRENT.json').read_text(encoding='utf-8'))
    assert retention['policy']['auto_delete'] is False


def test_publish_current_prefers_manual_finish(tmp_path: Path):
    drawings=tmp_path/'drawings'; out=drawings/'candidates'/'K01-D-X'; cand=out/'drawing_system_v1_1'
    gen=cand/'generated'; man=cand/'manual_finish'; gen.mkdir(parents=True);man.mkdir()
    (gen/'K01-D-X.SLDDRW').write_bytes(b'generated')
    (gen/'K01-D-X.PDF').write_bytes(b'generated-pdf')
    (man/'K01-D-X_ISO_FINISH.SLDDRW').write_bytes(b'manual')
    (man/'K01-D-X_ISO_FINISH.PDF').write_bytes(b'manual-pdf')
    manifest={'paths':{'generated':str(gen),'manual_finish':str(man)},'source_model':{'sha256':'abc'},'spec':{'sha256':'def'}}
    (cand/'candidate_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    spec={'output_root':str(out),'drawing_id':'K01-D-X','part_id':'K01-P-X','title':'X','model_path':'x.SLDPRT','release_blockers':['open']}
    pub=dc.publish_current('K01-D-X',spec,cand,manifest)
    assert pub['status']=='PASS_CURRENT_PUBLISHED'
    current=drawings/'current'/'K01-D-X'
    assert (current/'K01-D-X.SLDDRW').read_bytes()==b'manual'
    assert (current/'K01-D-X.PDF').read_bytes()==b'manual-pdf'
    pointer=json.loads((current/'CURRENT.json').read_text(encoding='utf-8'))
    assert pointer['preferred_stage']=='MANUAL_FINISH'
