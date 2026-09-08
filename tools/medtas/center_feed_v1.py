#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); ap.add_argument('--derived',required=True); ap.add_argument('--graph',required=True); ap.add_argument('--registry',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); root=Path(a.repo_root); d=load(a.derived); g=load(a.graph); reg=load(a.registry)
    byid={n['node_id']:n for n in g['nodes']}; states=d['nodes']
    counts={}
    for x in states.values(): counts[x['state']]=counts.get(x['state'],0)+1
    nodes=[]
    for nid in [n['node_id'] for n in g['nodes']]:
        s=states[nid]
        nodes.append({
            'node_id':nid,'title':byid[nid].get('title'),'kind':byid[nid].get('kind'),'state':s['state'],
            'state_hash':s.get('state_hash'),'artifact_hash':s.get('artifact_hash'),'reasons':s.get('reasons',[]),
            'criticality':byid[nid].get('lifecycle',{}).get('criticality')
        })
    evidence=[]
    for item in reg.get('items',[]):
        files=[]
        for rel in item.get('files',[]):
            p=root/rel; files.append({'path':rel.replace('\\','/'),'exists':p.exists()})
        e=dict(item); e['files']=files; evidence.append(e)
    cad=states.get('K01.CAD.SEM.A001',{})
    payload={
        'schema':'k01.command_center.medtas_feed.v1','project':'K01','summary':{'counts':counts},
        'cad_semantic':{'state':cad.get('state'),'state_hash':cad.get('state_hash'),'artifact_hash':cad.get('artifact_hash')},
        'nodes':nodes,'evidence':evidence,
        'principle':'Command Center consumes this generated feed; it does not infer engineering truth from filenames.'
    }
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
