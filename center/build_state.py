from __future__ import annotations
import json, hashlib, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_BASELINE_NAME='K01-A-001_GATE04E_P006_SERVICE_VERIFY.SLDASM'
EXPECTED_BASELINE_SHA='8059423b4fe1cb0bc384c5f7164eb92a7ad800bc0c79b2de7339f68e1d7489d4'
EXPECTED_COMPONENTS=13

def win_basename(value):
    return str(value or '').replace('\\','/').split('/')[-1]


def load(path:Path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:
        return default

def sha256_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def git(repo:Path,*args):
    try:
        cp=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,errors='replace')
        return cp.returncode,cp.stdout.strip(),cp.stderr.strip()
    except Exception as e:
        return 127,'',repr(e)

def count_characteristics(reg):
    rows=[]
    if isinstance(reg,dict):
        for d in reg.get('drawings',[]) or []:
            for c in d.get('characteristics',[]) or []:
                rows.append({'drawing_no':d.get('drawing_no'),'model':d.get('model'),'title':d.get('title'),**c})
    counts={}
    for c in rows: counts[c.get('status','UNKNOWN')]=counts.get(c.get('status','UNKNOWN'),0)+1
    return rows,counts

def parse_bom(j):
    if not isinstance(j,dict): return {'status':'MISSING','rows':[],'release_open_items':[]}
    rows=j.get('rows',[]) or []
    return {
      'schema':j.get('schema'),'status':j.get('status','MISSING'),
      'structure_status':j.get('structure_status'), 'release_status':j.get('release_status',j.get('status')),
      'modeled_instances':j.get('source_component_count',j.get('modeled_instances')),
      'expected_component_count':j.get('expected_component_count'),
      'row_count':len(rows),'rows':rows,
      'issues':j.get('issues',[]) or [],'release_open_items':j.get('release_open_items',[]) or [],
      'source_raw_snapshot':j.get('source_raw_snapshot')
    }

def normalize_release_open(ebom):
    items=[]
    for x in ebom.get('release_open_items',[]) or []:
        text=str(x); pn=text.split(':',1)[0]; reason=text.split(':',1)[1] if ':' in text else text
        items.append({'part_number':pn,'reason':reason,'raw':text})
    return items

def build(repo:Path):
    foundation=load(repo/'reports/foundation/K01_FOUNDATION_AUDIT_CURRENT.json',{}) or {}
    norm=load(repo/'reports/foundation/K01_REPOSITORY_NORMALIZATION_PLAN_CURRENT.json',{}) or {}
    promo=load(repo/'reports/control/K01_FINAL_ASSEMBLY_PROMOTION_CURRENT.json',{}) or {}
    git_audit=load(repo/'reports/control/K01_GIT_AUDIT_CURRENT.json',{}) or {}
    gate=load(repo/'reports/cad/current/K01_GATE04E_P006_SERVICE_VERIFY.json',{}) or {}
    calc=load(repo/'reports/control/K01_CALCULATION_EVIDENCE_INDEX_CURRENT.json',{}) or {}
    parts=load(repo/'control/product/parts.json',{}) or {}
    chars_reg=load(repo/'control/drawings/K01_DRAWING_CHARACTERISTICS_v1_7.json',{}) or {}
    draw_plan=load(repo/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json',{}) or {}
    release_chars=load(repo/'reports/inspection/current/K01_RELEASE_CHARACTERISTICS_CURRENT.json',{}) or {}
    eb=parse_bom(load(repo/'reports/bom/current/K01_EBOM_A001_CURRENT.json',{}))
    mb=parse_bom(load(repo/'reports/bom/current/K01_MBOM_A001_CURRENT.json',{}))
    sysbom=parse_bom(load(repo/'reports/bom/current/K01_SYSTEM_BOM_CURRENT.json',{}))
    authority=load(repo/'control/project/K01_AUTHORITY_MAP_CURRENT.json',{}) or load(repo/'control/project/K01_AUTHORITY_MAP_v2_2.json',{}) or {}
    req=load(repo/'control/requirements/requirements.json',{}) or {}

    fb=foundation.get('engineering_baseline',{}) if isinstance(foundation,dict) else {}
    baseline_source=fb.get('source') or promo.get('source') or gate.get('verify_assembly')
    baseline_sha=fb.get('source_sha256')
    if baseline_source and not baseline_sha:
        p=Path(str(baseline_source))
        if p.exists(): baseline_sha=sha256_file(p)
    sim=fb.get('simulation_evidence',[]) or []
    latest=fb.get('latest_simulation_report')
    baseline_status='PASS' if baseline_source and win_basename(baseline_source)==EXPECTED_BASELINE_NAME and baseline_sha==EXPECTED_BASELINE_SHA else 'HOLD'

    chars, char_counts=count_characteristics(chars_reg)
    drawings=[]
    for d in chars_reg.get('drawings',[]) if isinstance(chars_reg,dict) else []:
        rr=[x for x in chars if x.get('drawing_no')==d.get('drawing_no')]
        drawings.append({'drawing_no':d.get('drawing_no'),'model':d.get('model'),'title':d.get('title'),
                         'counts':{k:sum(1 for x in rr if x.get('status')==k) for k in sorted(set(x.get('status','UNKNOWN') for x in rr))},
                         'characteristics':rr})

    product_items=[]
    if isinstance(parts.get('items'),dict):
        for pn,d in sorted(parts['items'].items()):
            product_items.append({'part_number':pn,'description':d.get('description'),'item_type':d.get('item_type'),
                                  'material':d.get('material_authority'),'material_status':d.get('material_status'),
                                  'release_state':d.get('release_state'),'make_buy':d.get('make_buy'),'supplier':d.get('supplier')})
    product_open=[x for x in product_items if str(x.get('release_state','')).upper() not in ('PASS','RELEASED')]

    evidence=[]
    for x in calc.get('items',[]) if isinstance(calc,dict) else []:
        evidence.append({'id':x.get('id'),'kind':x.get('kind'),'path':x.get('path'),'sha256':x.get('sha256'),'size':x.get('size')})
    struct=[x for x in evidence if x.get('kind')=='STRUCTURAL']
    magnetic=[x for x in evidence if x.get('kind')=='MAGNETIC']

    rc,bout,_=git(repo,'branch','--show-current'); rc2,head,_=git(repo,'rev-parse','HEAD')
    git_state={'status':git_audit.get('status','UNKNOWN'),'dirty_count':git_audit.get('dirty_count'),
               'source_control_dirty_count':git_audit.get('source_control_dirty_count'),
               'runtime_generated_dirty_count':git_audit.get('runtime_generated_dirty_count'),
               'unclassified_dirty_count':git_audit.get('unclassified_dirty_count'),
               'branch':git_audit.get('branch') or bout,'head':head if rc2==0 else None,
               'normalization_plan_status':norm.get('apply_readiness') or norm.get('status'),
               'normalization_classes':norm.get('classes') or norm.get('class_counts')}

    req_rows=req.get('requirements',req.get('items',[])) if isinstance(req,dict) else []
    if isinstance(req_rows,dict): req_rows=list(req_rows.values())
    req_open=[]
    for x in req_rows or []:
        if isinstance(x,dict):
            st=str(x.get('status') or x.get('requirement_status') or '').upper()
            if st and st not in ('PASS','RELEASED','CLOSED'): req_open.append({'id':x.get('id'),'title':x.get('title'),'status':st})

    state={
      'schema':'k01.center_state.v1_0','generated_utc':datetime.now(timezone.utc).isoformat(),
      'project':'K01','mode':'READ_ONLY_CENTER_1_0',
      'baseline':{'status':baseline_status,'authority':'CURRENT_DESIGN_AND_ANALYSIS_BASELINE','assembly':baseline_source,
                  'sha256':baseline_sha,'expected_name':EXPECTED_BASELINE_NAME,'expected_sha256':EXPECTED_BASELINE_SHA,
                  'component_count':gate.get('top_level_component_count') or EXPECTED_COMPONENTS,
                  'simulation_evidence_count':fb.get('simulation_evidence_count',len(sim)),'simulation_evidence':sim,'latest_simulation_report':latest,
                  'promotion_status':promo.get('status'),'promotion_mode':promo.get('mode'),'r01_target':promo.get('target'),
                  'r01_is_authority':False},
      'bom':{'ebom':eb,'mbom':mb,'system':sysbom,'release_open':normalize_release_open(eb),
             'structural_verdict':'PASS' if eb.get('modeled_instances')==EXPECTED_COMPONENTS and (eb.get('structure_status') in (None,'PASS')) else 'HOLD'},
      'product_definition':{'characteristic_count':len(chars),'status_counts':char_counts,'drawings':drawings,
                            'blocking_items':draw_plan.get('blocking_items',[]) if isinstance(draw_plan,dict) else [],
                            'drawing_plan_status':draw_plan.get('status') if isinstance(draw_plan,dict) else None,
                            'release_characteristics_summary':release_chars.get('summary') if isinstance(release_chars,dict) else None,
                            'release_characteristics':release_chars.get('characteristics',[]) if isinstance(release_chars,dict) else []},
      'product_registry':{'count':len(product_items),'open_count':len(product_open),'items':product_items,'open_items':product_open},
      'analysis':{'evidence_count':len(evidence),'structural':struct,'magnetic':magnetic,'all':evidence},
      'repository':git_state,
      'authority_map':authority,
      'requirements':{'count':len(req_rows or []),'open_count':len(req_open),'open_items':req_open},
      'foundation':{'status':foundation.get('status'),'center_prior_status':(foundation.get('structure_center') or {}).get('center_status'),
                    'normalization_plan_status':norm.get('apply_readiness') or norm.get('status')},
      'release_readiness':{'status':'HOLD','reasons':[]}
    }
    reasons=[]
    if baseline_status!='PASS': reasons.append('ENGINEERING_BASELINE_NOT_CONFIRMED')
    if eb.get('status')!='PASS': reasons.append('EBOM_RELEASE_HOLD')
    if mb.get('status')!='PASS': reasons.append('MBOM_RELEASE_HOLD')
    if char_counts.get('NEEDS_MBD_BIND',0): reasons.append(f"MBD_BIND_OPEN:{char_counts.get('NEEDS_MBD_BIND')}")
    if char_counts.get('OPEN_SPEC',0): reasons.append(f"PRODUCT_SPEC_OPEN:{char_counts.get('OPEN_SPEC')}")
    if git_state.get('source_control_dirty_count') not in (None,0): reasons.append('SOURCE_CONTROL_NOT_CLEAN')
    state['release_readiness']['reasons']=reasons
    if not reasons: state['release_readiness']['status']='PASS'
    return state

def main():
    repo=Path(sys.argv[1] if len(sys.argv)>1 else os.getenv('K01_REPO_ROOT',r'D:\BreshevEngineering\marvilon-k01')).resolve()
    if not (repo/'.git').exists(): raise SystemExit('HOLD: repo root not found: '+str(repo))
    state=build(repo)
    out=repo/'reports/center/K01_CENTER_STATE_CURRENT.json'; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Center state:',out)
    print('baseline=',state['baseline']['status'],'bom=',state['bom']['ebom']['status'],'chars=',state['product_definition']['status_counts'],'release=',state['release_readiness']['status'])
    return 0
if __name__=='__main__': raise SystemExit(main())
