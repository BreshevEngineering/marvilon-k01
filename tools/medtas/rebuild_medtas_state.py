#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import medtas_state_engine_v1_1 as eng

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v2_0.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_9.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_8.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_7.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_6.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_5.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_4.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_3.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_2.json'
    if not graph_path.exists(): graph_path=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_1.json'
    graph=load(graph_path)
    records=eng.load_record_store(root/'reports/medtas/records/current')
    verifs=eng.load_record_store(root/'reports/medtas/verifications/current')
    derived=eng.evaluate_graph(graph,root,records,verifs)
    out=root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'
    dump(out,{'schema_version':'MEDTAS-DERIVED-STATE-1.2','project':'K01','nodes':derived})
    registry=root/'control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1_2.json'
    if not registry.exists(): registry=root/'control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1.json'
    feed=root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json'
    subprocess.check_call([sys.executable,str(root/'tools/medtas/center_feed_v1_2.py'),'--repo-root',str(root),'--derived',str(out),'--graph',str(graph_path),'--registry',str(registry),'--out',str(feed)])
    subprocess.check_call([sys.executable,str(root/'tools/medtas/render_center_html_v1_2.py'),'--repo-root',str(root),'--feed',str(feed),'--out',str(root/'reports/control/K01_MEDTAS_CENTER_CURRENT.html')])
    print('Derived state:',out)
    print('Center feed  :',feed)
    print('Center HTML  :',root/'reports/control/K01_MEDTAS_CENTER_CURRENT.html')
if __name__=='__main__': main()
