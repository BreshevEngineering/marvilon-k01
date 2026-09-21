from __future__ import annotations
import argparse,sys
from pathlib import Path
from control_authority import require_control_family
from medtas_v16_common import load,dump,evaluate,register_build,register_verify,sha256_file

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    out=root/'reports/medtas/calculix/current/K01_CALCULIX_INPUT_P006_v1_7.json';deck=root/'reports/medtas/calculix/current/K01_CCX_P006/K01_P006.inp';base=root/'reports/medtas/calculix/current/K01_P006_MESH_BASE.inp';bp=require_control_family(root,'bolt_equiv_p006_binding')
    d=evaluate(root);blocking=[]
    for nid in ('K01.STRUCT.FACE_MAP.P006','K01.STRUCT.FACE_MAP.QUAL.P006','K01.STRUCT.MESH.P006','K01.STRUCT.BOLT_EQUIV.P006'):
        st=d.get(nid,{}).get('state')
        if st!='PASS':blocking.append(nid+':'+str(st))
    b=load(bp) if bp.exists() else {};frag=str((b.get('calculix_representation') or {}).get('approved_ccx_tail_fragment') or '').strip();fragp=(root/frag).resolve() if frag else None
    if not base.exists():blocking.append('CCX-INPUT-BASE-001: Gmsh/Abaqus base mesh input missing')
    if not frag:blocking.append('CCX-INPUT-EQUIV-001: approved_ccx_tail_fragment is not bound in declared bolt-equivalence binding authority')
    elif not fragp.exists():blocking.append('CCX-INPUT-EQUIV-002: approved tail fragment file missing: '+str(fragp))
    if blocking:
        if deck.exists():deck.unlink()
        payload={'schema':'k01.calculix_input.p006.v1_7','status':'BLOCKED','deck':None,'blocking':blocking,'policy':'No CalculiX deck is emitted while qualified face roles, quadratic mesh, or reviewed bolt/preload/contact/load-path equivalence is open.','next_action':'Close K01.STRUCT.BOLT_EQUIV.P006 with a reviewed CCX tail fragment, then rerun.'};dump(out,payload);print('BLOCKED CalculiX input');[print(' -',x) for x in blocking];return 1
    deck.parent.mkdir(parents=True,exist_ok=True);base_txt=base.read_text(encoding='utf-8',errors='replace');tail=fragp.read_text(encoding='utf-8',errors='replace')
    hdr='** K01 MEDTAS v1.7 controlled CalculiX deck\n** Base mesh: '+base.relative_to(root).as_posix()+'\n** Reviewed engineering tail: '+fragp.relative_to(root).as_posix()+'\n'
    deck.write_text(hdr+base_txt.rstrip()+'\n'+tail.strip()+'\n',encoding='utf-8')
    payload={'schema':'k01.calculix_input.p006.v1_7','status':'PASS','deck':deck.relative_to(root).as_posix(),'deck_sha256':sha256_file(deck),'base_mesh_input':base.relative_to(root).as_posix(),'approved_tail_fragment':fragp.relative_to(root).as_posix(),'policy':'Deterministic composition of controlled C3D10-compatible mesh export and reviewed solver-equivalence tail.'};dump(out,payload)
    register_build(root,'K01.STRUCT.CCX.INPUT.P006',{'tool':'build_calculix_input_v1_7.py','mode':'deterministic base+approved-tail composition'});register_verify(root,'K01.STRUCT.CCX.INPUT.P006','PASS',metrics={'deck_sha256':payload['deck_sha256']},notes='Input provenance/composition PASS; solver-result correctness is evaluated downstream.')
    print('PASS CalculiX input:',deck);return 0
if __name__=='__main__':raise SystemExit(main())
