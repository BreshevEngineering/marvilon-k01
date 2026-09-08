from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p,d=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return d

def dump(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')

def open_state(s):return str(s or '').upper() not in ('PASS','RELEASED','CURRENT','FROZEN','PASS_WITH_LIMITATIONS','PASS_WITH_LIMIT','READY_FOR_EXEMPLAR_DRAWING')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();pol=load(r/'control/medtas/v1/spec/K01_RELEASE_PRIORITY_POLICY_v1_9.json',{}) or {};der=load(r/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',{}) or {};nodes=der.get('nodes',{});st=load(r/'reports/control/K01_CURRENT_STATE.json',{}) or load(r/'control/state/K01_CURRENT_STATE.json',{}) or {};reqrows={x.get('id'):x for x in (st.get('requirements',{}) or {}).get('rows',[]) or []};bands=[]
    for b in pol.get('priority_bands',[]) or []:
        items=[]
        for nid in b.get('nodes',[]) or []:
            n=nodes.get(nid,{}) or {};items.append({'type':'node','id':nid,'title':n.get('title') or nid,'state':n.get('state','MISSING'),'reasons':n.get('reasons',[])})
        for rid in b.get('requirement_ids',[]) or []:
            q=reqrows.get(rid,{}) or {};items.append({'type':'requirement','id':rid,'title':q.get('title') or rid,'state':q.get('requirement_status','MISSING'),'release_blocker':q.get('release_blocker',False),'verification_method':q.get('verification_method')})
        bands.append({**b,'items':items,'open_count':sum(1 for x in items if open_state(x.get('state')))})
    p007=load(r/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json',{}) or {};eb=load(r/'reports/medtas/bom/current/K01_EBOM_VERIFY_A001_v1_9.json',{}) or {};mb=load(r/'reports/medtas/bom/current/K01_MBOM_VERIFY_A001_v1_9.json',{}) or {};draw=load(r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json',{}) or {}
    geom_ok=nodes.get('K01.CAD.SEM.A001',{}).get('state')=='PASS' and nodes.get('K01.STRUCT.SWSIM.P006',{}).get('state')=='PASS'
    pd=load(r/'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json',{}) or {}
    conclusions={'mechanical_geometry':'FROZEN_READY_TO_PROTECT' if geom_ok else 'REVIEW','mechanical_geometry_ready':geom_ok,'production_definition':pd.get('status','MISSING'),'p007_exemplar':p007.get('status','MISSING'),'ebom':eb.get('verdict','MISSING'),'mbom':mb.get('verdict','MISSING'),'drawing_pack_definition':draw.get('verdict','MISSING'),'production_release':'HOLD' if (st.get('requirements',{}) or {}).get('blockers',0) or draw.get('verdict')!='PASS' or eb.get('verdict')!='PASS' else 'REVIEW','calculix_role':'DEFERRED_ASSURANCE'}
    openbands=[b for b in bands if b.get('open_count')]
    do_now=[{'priority':b['priority'],'title':b['title'],'open_count':b['open_count'],'items':[x for x in b['items'] if open_state(x.get('state'))]} for b in openbands if b['priority'] in ('P1A','P1B')]
    do_next=[{'priority':b['priority'],'title':b['title'],'open_count':b['open_count'],'items':[x for x in b['items'] if open_state(x.get('state'))]} for b in openbands if b['priority'] in ('P1C','P2','P3')]
    deferred=[{'priority':b['priority'],'title':b['title'],'open_count':b['open_count'],'items':[x for x in b['items'] if open_state(x.get('state'))]} for b in openbands if b['priority']=='P4']
    payload={'schema':'k01.release_priority.current.v1_9','policy':pol,'conclusions':conclusions,'bands':bands,'do_now':do_now,'do_next':do_next,'deferred':deferred,'decision':'DO NOW: P007 exemplar PMI/drawing + parts registry/EBOM. THEN: remaining drawings/MBOM and product requirements. CalculiX remains deferred assurance.'};out=r/'reports/control/K01_RELEASE_PRIORITY_CURRENT.json';dump(out,payload);print('Release priority:',out);print('conclusions=',conclusions);return 0
if __name__=='__main__':raise SystemExit(main())
