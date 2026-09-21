#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import medtas_state_engine_v1_1 as eng
from v22_common import authority_path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    graph_path=authority_path(root,'engineering_build_graph')
    if graph_path is None: raise RuntimeError('Declared engineering build graph authority missing')
    graph=load(graph_path)
    records=eng.load_record_store(root/'reports/medtas/records/current')
    verifs=eng.load_record_store(root/'reports/medtas/verifications/current')
    derived=eng.evaluate_graph(graph,root,records,verifs)
    out=root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'
    dump(out,{'schema_version':'MEDTAS-DERIVED-STATE-1.2','project':'K01','nodes':derived})
    registry=authority_path(root,'evidence_registry')
    if registry is None: raise RuntimeError('Declared evidence registry authority missing')
    feed=root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json'
    subprocess.check_call([sys.executable,str(root/'tools/medtas/center_feed_v1_2.py'),'--repo-root',str(root),'--derived',str(out),'--graph',str(graph_path),'--registry',str(registry),'--out',str(feed)])
    subprocess.check_call([sys.executable,str(root/'tools/medtas/render_center_html_v1_2.py'),'--repo-root',str(root),'--feed',str(feed),'--out',str(root/'reports/control/K01_MEDTAS_CENTER_CURRENT.html')])
    print('Derived state:',out)
    print('Center feed  :',feed)
    print('Center HTML  :',root/'reports/control/K01_MEDTAS_CENTER_CURRENT.html')
if __name__=='__main__': main()
