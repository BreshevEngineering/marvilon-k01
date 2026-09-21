from pathlib import Path
import argparse, re
from v22_common import load, save, latest_graph
from control_authority import require_control_family

def get_nodes(g):
 n=g.get('nodes',[])
 if isinstance(n,dict): return [{'node_id':k,**(v if isinstance(v,dict) else {})} for k,v in n.items()]
 return n

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); r=Path(a.repo_root)
 gp=latest_graph(r); rulesp=require_control_family(r,'technical_filter_rules'); catsp=require_control_family(r,'technical_filter_categories'); rules=load(rulesp,{}) or {}; cats=load(catsp,{}) or {}
 valid_ids={str(x.get('id')) for x in (cats.get('categories') or []) if isinstance(x,dict) and x.get('id')}; rep={'schema':'k01.node_technical_filter_map.v2_2','graph':str(gp) if gp else None,'rules_authority':str(rulesp),'categories_authority':str(catsp),'nodes':[],'status':'HOLD'}
 if not gp: save(r/'reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json',rep); print('HOLD graph missing'); return 2
 g=load(gp,{}) or {}
 for node in get_nodes(g):
  nid=node.get('node_id') or node.get('id') or '' ; title=node.get('title','')
  hay=(nid+' '+title).upper(); cs=[]; rats=[]
  exact=[rr for rr in rules.get('rules',[]) if rr.get('match')=='EXACT_NODE_ID' and any(nid.upper()==p.upper() for p in rr.get('pattern',[]))]
  selected=exact if exact else [rr for rr in rules.get('rules',[]) if rr.get('match')!='EXACT_NODE_ID' and any(p.upper() in hay for p in rr.get('pattern',[]))]
  for rr in selected:
   cs+=rr.get('categories',[]); rats.append(rr.get('rationale',''))
  cs=sorted(set(cs),key=lambda x:int(x))
  unknown=sorted(set(cs)-valid_ids)
  if unknown: raise RuntimeError(f'Technical-filter rule mapped unknown category id(s) {unknown} for {nid}')
  rep['nodes'].append({'node_id':nid,'categories':cs,'rationale':' '.join(dict.fromkeys(rats)),'status':'MAPPED' if cs else 'UNMAPPED'})
 unm=[x['node_id'] for x in rep['nodes'] if not x['categories']]
 rep['unmapped']=unm; rep['status']='PASS' if not unm else 'HOLD'
 p=save(r/'reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json',rep); print(rep['status'],'nodes=',len(rep['nodes']),'unmapped=',len(unm)); print(p); return 0 if not unm else 3
if __name__=='__main__': raise SystemExit(main())
