from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p,d=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return d
def dump(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    st=load(root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json')
    fm=load(root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json')
    if not st:
        print('CalculiX scaffold blocked: structural model missing');return 2
    confirmed=(fm or {}).get('confirmed_role_map',{}) or {}
    required=['FIXED_INTERFACE_FACE','SERVICE_FORCE_FACE','PRESSURE_FACES','CONTACT_PAIR']
    missing=[r for r in required if r not in confirmed]
    status='READY_FOR_NEUTRAL_MESH_EXPORT' if not missing and (fm or {}).get('status')=='PASS' else 'BLOCKED_FACE_ROLE_BINDING'
    p={'schema':'k01.calculix_case_scaffold.p006.v1_5','status':status,'source_structural_model':'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json','source_face_map':'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json','analysis':st.get('analysis'),'material':st.get('material'),'boundary_conditions':st.get('boundary_conditions'),'reference_solidworks_evidence':st.get('reference_solidworks_evidence'),'required_face_roles':required,'confirmed_face_roles':confirmed,'missing_face_roles':missing,'next_sequence':['export controlled neutral geometry for P003/P007 only','mesh with controlled mesher and named physical groups','generate CalculiX .inp from material + loads + role map','run ccx','parse .dat/.frd','reconcile sigma_vm_max / displacement / reaction balance against SolidWorks']}
    out=root/'reports/medtas/calculix/current/K01_CALCULIX_CASE_SCAFFOLD_P006_v1_5.json';dump(out,p);print('CalculiX case scaffold:',out);print('status=',status,'missing roles=',missing);return 0
if __name__=='__main__':raise SystemExit(main())
