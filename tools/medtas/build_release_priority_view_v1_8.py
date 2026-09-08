from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p,d=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return d

def dump(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    pol=load(r/'control/medtas/v1/spec/K01_RELEASE_PRIORITY_POLICY_v1_8.json',{}) or {};der=load(r/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',{}) or {};nodes=der.get('nodes',{})
    st=load(r/'reports/control/K01_CURRENT_STATE.json',{}) or load(r/'control/state/K01_CURRENT_STATE.json',{}) or {};reqrows={x.get('id'):x for x in (st.get('requirements',{}) or {}).get('rows',[]) or []}
    bands=[]
    for b in pol.get('priority_bands',[]) or []:
        items=[]
        for nid in b.get('nodes',[]) or []:
            n=nodes.get(nid,{}) or {};items.append({'type':'node','id':nid,'title':n.get('title') or nid,'state':n.get('state','MISSING'),'reasons':n.get('reasons',[])})
        for rid in b.get('requirement_ids',[]) or []:
            q=reqrows.get(rid,{}) or {};items.append({'type':'requirement','id':rid,'title':q.get('title') or rid,'state':q.get('requirement_status','MISSING'),'release_blocker':q.get('release_blocker',False),'verification_method':q.get('verification_method')})
        open_items=[x for x in items if str(x.get('state','')).upper() not in ('PASS','RELEASED','CURRENT','FROZEN','PASS_WITH_LIMITATIONS','PASS_WITH_LIMIT')]
        bands.append({**b,'items':items,'open_count':len(open_items)})
    # Current mechanical design conclusion is deliberately separated from product-release conclusion.
    cad=nodes.get('K01.CAD.SEM.A001',{}).get('state');sw=nodes.get('K01.STRUCT.SWSIM.P006',{}).get('state');assembly_gate=next((x for x in (st.get('gates',{}) or {}).get('rows',[]) or [] if x.get('gate')=='assembly'),{})
    mechanical_ready = cad=='PASS' and sw=='PASS' and str(assembly_gate.get('status','')).startswith('PASS')
    drawing=load(r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json',{}) or {};bomv=load(r/'reports/medtas/bom/current/K01_BOM_VERIFY_A001_v1.json',{}) or {};prod=load(r/'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json',{}) or {}
    conclusions={
      'mechanical_geometry':'FROZEN_READY_TO_PROTECT' if mechanical_ready else 'NOT_YET_FROZEN',
      'mechanical_geometry_ready':mechanical_ready,
      'production_definition':'PASS' if drawing.get('verdict')=='PASS' and bomv.get('verdict')=='PASS' else 'HOLD',
      'production_release':'HOLD' if (st.get('requirements',{}) or {}).get('blockers',0) or not (drawing.get('verdict')=='PASS' and bomv.get('verdict')=='PASS') else 'REVIEW',
      'calculix_role':pol.get('calculix_current_role','DEFERRED_ASSURANCE'),
      'product_definition_summary':prod.get('summary',{})
    }
    # Do-now is intentionally the first non-deferred band with open work.
    do_now=[];do_next=[];deferred=[]
    for b in bands:
        target=deferred if b.get('priority')=='P4' else (do_now if not do_now and b.get('open_count',0)>0 else do_next)
        if b.get('open_count',0)>0:target.append({'priority':b.get('priority'),'title':b.get('title'),'open_count':b.get('open_count'),'items':[x for x in b['items'] if str(x.get('state','')).upper() not in ('PASS','RELEASED','CURRENT','FROZEN','PASS_WITH_LIMITATIONS','PASS_WITH_LIMIT')]})
    payload={'schema':'k01.release_priority.current.v1_8','policy':pol,'conclusions':conclusions,'bands':bands,'do_now':do_now,'do_next':do_next,'deferred':deferred,'decision':'Do not spend current project time on CalculiX unless the deferred-assurance reopen condition is met. Primary effort is production technical definition, then unresolved release requirements.'}
    out=r/'reports/control/K01_RELEASE_PRIORITY_CURRENT.json';dump(out,payload);print('Release priority:',out);print('conclusions=',conclusions);return 0
if __name__=='__main__':raise SystemExit(main())
