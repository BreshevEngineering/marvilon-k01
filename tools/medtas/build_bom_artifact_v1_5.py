from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import medtas_state_engine_v1_1 as eng

def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def graph_path(root):
    for n in ('K01_engineering_build_graph_v1_5.json','K01_engineering_build_graph_v1_4.json'):
        p=root/'control/medtas/v1/graph'/n
        if p.exists():return p
    raise FileNotFoundError('MEDTAS graph missing')
def eval_node(root,nid):
    g=load(graph_path(root));r=eng.load_record_store(root/'reports/medtas/records/current');v=eng.load_record_store(root/'reports/medtas/verifications/current');return eng.evaluate_graph(g,root,r,v)[nid]
def register_build(root,nid,producer):
    d=eval_node(root,nid)
    if not d.get('artifact_hash'):raise RuntimeError(nid+' artifact hash missing')
    dump(root/'reports/medtas/records/current'/f'{nid}.build.json',{'schema':'medtas.build_record.v1','node_id':nid,'built_state_hash':d['state_hash'],'artifact_hash':d['artifact_hash'],'producer':producer})
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    modelp=root/'reports/medtas/bom/current/K01_BOM_MODEL_A001_v1.json'
    if not modelp.exists():print('BOM ARTIFACT BLOCKED: canonical BOM model missing');return 2
    model=load(modelp);items=model.get('items',[]) or []
    outdir=root/'reports/bom/current';outdir.mkdir(parents=True,exist_ok=True);csvp=outdir/'K01_BOM_A001_CURRENT.csv'
    fields=['item_id','part_number','description','quantity','material','make_buy','source_node']
    with csvp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for row in items:
            r=dict(row);mat=r.get('material')
            if isinstance(mat,list):r['material']='; '.join(str(x) for x in mat)
            w.writerow(r)
    register_build(root,'K01.BOM.ARTIFACT.A001',{'tool':'build_bom_artifact_v1_5.py','format':'CSV UTF-8 BOM','source':'K01.BOM.MODEL.A001'})
    # Verify semantic parity against what was just exported.
    rows=[]
    with csvp.open('r',encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    issues=[]
    if len(rows)!=len(items):issues.append(f'BOM-ROW-COUNT:{len(rows)}!={len(items)}')
    by={r.get('part_number'):r for r in rows}
    for i in items:
        p=i.get('part_number');r=by.get(p)
        if not r:issues.append('BOM-MISSING:'+str(p));continue
        if str(r.get('quantity'))!=str(i.get('quantity')):issues.append('BOM-QTY:'+str(p))
        exp=i.get('material');exp='; '.join(str(x) for x in exp) if isinstance(exp,list) else str(exp or '')
        if str(r.get('material') or '')!=exp:issues.append('BOM-MATERIAL:'+str(p))
    verify={'schema':'k01.bom_verify.a001.v1_5','source_model':'reports/medtas/bom/current/K01_BOM_MODEL_A001_v1.json','artifact':'reports/bom/current/K01_BOM_A001_CURRENT.csv','model_item_count':len(items),'artifact_row_count':len(rows),'issues':issues,'limitations':model.get('limitations',[]),'verdict':'PASS' if not issues else 'HOLD'}
    vp=root/'reports/medtas/bom/current/K01_BOM_VERIFY_A001_v1.json';dump(vp,verify);register_build(root,'K01.BOM.VERIFY.A001',{'tool':'build_bom_artifact_v1_5.py','stage':'semantic_parity'})
    d=eval_node(root,'K01.BOM.VERIFY.A001')
    dump(root/'reports/medtas/verifications/current/K01.BOM.VERIFY.A001.verify.json',{'schema':'medtas.verification_record.v1','node_id':'K01.BOM.VERIFY.A001','verified_state_hash':d['state_hash'],'verified_artifact_hash':d['artifact_hash'],'verdict':'PASS' if not issues else 'HOLD','metrics':{'model_items':len(items),'artifact_rows':len(rows)},'limitations':model.get('limitations',[])+issues,'notes':'CSV is a derived presentation of the canonical BOM model; it is not a second source of truth.'})
    print('BOM artifact:',csvp);print('BOM verify:',verify['verdict'],'issues=',len(issues),'model limitations=',len(model.get('limitations',[])))
    return 0 if not issues else 1
if __name__=='__main__':raise SystemExit(main())
