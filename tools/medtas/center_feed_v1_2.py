#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
PASSISH={'PASS','PASS_WITH_LIMITATIONS','DRIFT','FRESH_UNVERIFIED'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); ap.add_argument('--derived',required=True); ap.add_argument('--graph',required=True); ap.add_argument('--registry',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    root=Path(a.repo_root); d=load(a.derived); g=load(a.graph); reg=load(a.registry); byid={n['node_id']:n for n in g['nodes']}; states=d['nodes']
    counts={}
    for x in states.values(): counts[x['state']]=counts.get(x['state'],0)+1
    nodes=[]; frontier=[]
    for nid in [n['node_id'] for n in g['nodes']]:
        s=states[nid]; n=byid[nid]
        inputs=n.get('contract',{}).get('inputs',[])
        required=[e['node_id'] for e in inputs if e.get('required',True)]
        upstream_ready=all(states.get(x,{}).get('state') in PASSISH for x in required)
        if s['state'] in ('MISSING','FRESH_UNVERIFIED') and upstream_ready:
            frontier.append({'node_id':nid,'title':n.get('title'),'state':s['state'],'next_action':'build/verify this node','reasons':s.get('reasons',[])})
        nodes.append({'node_id':nid,'title':n.get('title'),'kind':n.get('kind'),'state':s['state'],'state_hash':s.get('state_hash'),'artifact_hash':s.get('artifact_hash'),'reasons':s.get('reasons',[]),'criticality':n.get('lifecycle',{}).get('criticality'),'outputs':n.get('contract',{}).get('outputs',[])})
    evidence=[]
    for item in reg.get('items',[]):
        files=[]
        for rel in item.get('files',[]):
            p=root/rel; files.append({'path':rel.replace('\\','/'),'exists':p.exists(),'size':p.stat().st_size if p.exists() and p.is_file() else None})
        e=dict(item); e['files']=files; evidence.append(e)
    failure_path=root/'reports/control/K01_MEDTAS_LAST_FAILURE.json'; failure=load(failure_path) if failure_path.exists() else None
    cad=states.get('K01.CAD.SEM.A001',{})
    payload={'schema':'k01.command_center.medtas_feed.v1_2','project':'K01','summary':{'counts':counts,'frontier_count':len(frontier)},'cad_semantic':{'state':cad.get('state'),'state_hash':cad.get('state_hash'),'artifact_hash':cad.get('artifact_hash')},'frontier':frontier,'nodes':nodes,'evidence':evidence,'last_failure':failure,'principle':'Command Center consumes generated state/evidence. Filenames and timestamps are not engineering truth.'}
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
