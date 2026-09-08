from __future__ import annotations
import argparse,csv,json,hashlib
from pathlib import Path
from medtas_v16_common import load,dump,base_id,sha256_file,register_build,register_verify,graph


def can_register(root,nid):
    try:return nid in {n['node_id'] for n in graph(root).get('nodes',[])}
    except Exception:return False

def reg_build(root,nid,producer):
    if can_register(root,nid):
        try:register_build(root,nid,producer)
        except Exception as e:print('WARN register_build',nid,e)

def reg_verify(root,nid,verdict,metrics=None,limitations=None):
    if can_register(root,nid):
        try:register_verify(root,nid,verdict,metrics=metrics or {},limitations=limitations or [])
        except Exception as e:print('WARN register_verify',nid,e)

def doc_index(cad):
    return {base_id(d.get('document_id') or d.get('title')):d for d in cad.get('documents',[]) or []}

def occurrence_rows(cad):
    out=[]
    for i,x in enumerate(cad.get('instances',[]) or []):
        pid=base_id(x.get('document_id') or x.get('title') or x.get('component_name'))
        if not pid.startswith('K01-'):continue
        out.append({'index':i,'instance':x.get('component_name') or x.get('instance_name') or x.get('name') or f'instance-{i+1}','part_number':pid,'suppressed':bool(x.get('suppressed',False)),'referenced_configuration':x.get('referenced_configuration') or x.get('configuration')})
    return out

def make_row(pid,qty,meta,doc,source='CAD_MODELED'):
    mats=(doc or {}).get('materials',[]) or []
    native=mats[0] if len(mats)==1 else mats
    return {
      'registry_key':pid,'part_number':pid,'description':meta.get('description',''),'item_type':meta.get('item_type','OPEN'),'make_buy':meta.get('make_buy','OPEN'),'quantity':qty,'unit':meta.get('unit','ea'),
      'revision':meta.get('revision'),'revision_status':meta.get('revision_status','OPEN'),'material_authority':meta.get('material_authority','OPEN'),'material_status':meta.get('material_status','OPEN'),'cad_native_material':native,
      'supplier':meta.get('supplier'),'manufacturer_part_number':meta.get('manufacturer_part_number'),'standard_or_specification':meta.get('standard_or_specification'),'release_state':meta.get('release_state','HOLD'),'source':source
    }

def nonmodeled_row(x):
    return {'registry_key':x.get('registry_key'),'part_number':x.get('part_number'),'description':x.get('description'),'item_type':x.get('item_type'),'make_buy':'BUY' if 'PURCHASED' in str(x.get('item_type')) else 'PROCESS','quantity':x.get('quantity'),'unit':x.get('unit'),'revision':None,'revision_status':'N/A','material_authority':'OPEN' if x.get('status','').startswith('OPEN') else None,'material_status':x.get('status'),'cad_native_material':None,'supplier':None,'manufacturer_part_number':None,'standard_or_specification':None,'release_state':'HOLD' if x.get('release_blocker') else 'OPEN','source':'REGISTRY_NON_MODELED','parent':x.get('parent'),'note':x.get('note')}

def write_csv(path,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=['registry_key','part_number','description','item_type','make_buy','quantity','unit','revision','material_authority','material_status','cad_native_material','supplier','manufacturer_part_number','standard_or_specification','release_state','source','parent','note']
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(items)

def hash_payload(o):return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()

def build_view(root,cad,registry,policy,view):
    itemsreg=registry.get('items',{}) or {};docs=doc_index(cad);occs=occurrence_rows(cad);active=[x for x in occs if not x['suppressed']];supp=[x for x in occs if x['suppressed']]
    q={}
    for x in active:q[x['part_number']]=q.get(x['part_number'],0)+1
    items=[];issues=[];warnings=[]
    for pid in sorted(q):
        meta=itemsreg.get(pid)
        if not meta:
            meta={'description':'','item_type':'UNREGISTERED','make_buy':'OPEN','unit':'ea','material_authority':'OPEN','material_status':'OPEN','release_state':'HOLD'};issues.append('BOM-REGISTRY-MISSING:'+pid)
        items.append(make_row(pid,q[pid],meta,docs.get(pid)))
        if not docs.get(pid):warnings.append('BOM-CAD-DOCUMENT-SEMANTICS-MISSING:'+pid)
        if meta.get('revision') in (None,''):warnings.append('BOM-REVISION-OPEN:'+pid)
        if str(meta.get('material_status','')).upper().startswith('OPEN'):warnings.append('BOM-MATERIAL-OPEN:'+pid)
    # Suppressed components require explicit disposition and never vanish silently.
    dispositions=((registry.get('suppression_policy') or {}).get('dispositions') or {})
    suppressed_audit=[]
    for x in supp:
        disp=dispositions.get(x['instance']) or dispositions.get(x['part_number'])
        row={**x,'disposition':disp};suppressed_audit.append(row)
        if not disp:issues.append('BOM-SUPPRESSION-UNEXPLAINED:'+x['instance'])
    # Non-modeled items are explicit. OPEN entries appear in the BOM and therefore cannot be overlooked.
    for x in registry.get('non_modeled_inclusions',[]) or []:
        if view in (x.get('bom_views') or []):
            items.append(nonmodeled_row(x))
            if x.get('release_blocker'):issues.append(f"BOM-NONMODELED-OPEN:{x.get('registry_key')}")
    modeled_qty=sum(int(x.get('quantity') or 0) for x in items if x.get('source')=='CAD_MODELED')
    if modeled_qty!=len(active):issues.append(f'BOM-OCCURRENCE-PARITY:{modeled_qty}!={len(active)}')
    transformations=[]
    if view=='MBOM':
        for t in policy.get('manufacturing_transformations',[]) or []:
            transformations.append(t)
            if str(t.get('status','')).upper()!='RELEASED':issues.append('MBOM-TRANSFORMATION-OPEN:'+str(t.get('id')))
    status='PASS' if not issues and not warnings else 'PASS_WITH_LIMITATIONS' if not issues else 'HOLD'
    return {
      'schema':f'k01.{view.lower()}_model.a001.v1_9','view':view,'status':status,'authority':'CAD occurrence/quantity joined to control/product/parts.json metadata. No field is authored in both places.',
      'items':items,'item_count':len(items),'modeled_occurrence_total':len(active),'modeled_quantity_total':modeled_qty,'suppressed_occurrences':suppressed_audit,'suppressed_occurrence_count':len(supp),
      'manufacturing_transformations':transformations,'issues':sorted(set(issues)),'warnings':sorted(set(warnings)),'source_hashes':{'parts_registry':hash_payload(registry),'bom_policy':hash_payload(policy)},
      'principles':{'non_modeled_items':'explicit registry inclusions','suppression':'fail-closed unless disposition exists','ebom_mbom':'separate derived views'}
    }

def verify(viewmodel):
    issues=list(viewmodel.get('issues',[]) or []);warnings=list(viewmodel.get('warnings',[]) or [])
    verdict='PASS' if not issues else 'HOLD'
    # Warnings do not break structure parity but prevent a clean released metadata state.
    if verdict=='PASS' and warnings:verdict='PASS_WITH_LIMITATIONS'
    return {'schema':f'k01.{viewmodel.get("view","BOM").lower()}_verify.a001.v1_9','verdict':verdict,'issues':issues,'warnings':warnings,'metrics':{'items':viewmodel.get('item_count',0),'modeled_occurrences':viewmodel.get('modeled_occurrence_total',0),'suppressed_occurrences':viewmodel.get('suppressed_occurrence_count',0),'non_modeled_items':sum(1 for x in viewmodel.get('items',[]) if x.get('source')=='REGISTRY_NON_MODELED')}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    cadp=r/'reports/medtas/cad/current/K01_CAD_SEM_A001.json';regp=r/'control/product/parts.json';polp=r/'control/product/K01_BOM_POLICY_v1_9.json'
    if not cadp.exists():print('HOLD: canonical CAD semantic state missing');return 2
    cad=load(cadp);registry=load(regp);policy=load(polp)
    ebom=build_view(r,cad,registry,policy,'EBOM');mbom=build_view(r,cad,registry,policy,'MBOM');ev=verify(ebom);mv=verify(mbom)
    outdir=r/'reports/medtas/bom/current';artdir=r/'reports/bom/current';outdir.mkdir(parents=True,exist_ok=True);artdir.mkdir(parents=True,exist_ok=True)
    dump(outdir/'K01_EBOM_MODEL_A001_v1_9.json',ebom);dump(outdir/'K01_MBOM_MODEL_A001_v1_9.json',mbom);dump(outdir/'K01_EBOM_VERIFY_A001_v1_9.json',ev);dump(outdir/'K01_MBOM_VERIFY_A001_v1_9.json',mv)
    # compatibility aliases: old BOM node now means EBOM, not a parallel truth
    dump(outdir/'K01_BOM_MODEL_A001_v1.json',{**ebom,'schema':'k01.bom_model.a001.compat.v1_9','view':'EBOM','compatibility_alias':True,'limitations':ebom.get('warnings',[])+ebom.get('issues',[])})
    dump(outdir/'K01_BOM_VERIFY_A001_v1.json',{**ev,'schema':'k01.bom_verify.a001.compat.v1_9'})
    dump(artdir/'K01_EBOM_A001_CURRENT.json',ebom);dump(artdir/'K01_MBOM_A001_CURRENT.json',mbom)
    write_csv(artdir/'K01_EBOM_A001_CURRENT.csv',ebom['items']);write_csv(artdir/'K01_MBOM_A001_CURRENT.csv',mbom['items']);write_csv(artdir/'K01_BOM_A001_CURRENT.csv',ebom['items'])
    # Registration happens only after artifacts exist.
    reg_build(r,'K01.BOM.MODEL.A001',{'tool':'build_bom_v1_9.py','view':'EBOM'});reg_build(r,'K01.BOM.ARTIFACT.A001',{'tool':'build_bom_v1_9.py','view':'EBOM','formats':['json','csv']});reg_verify(r,'K01.BOM.VERIFY.A001',ev['verdict'],ev['metrics'],ev['issues']+ev['warnings'])
    reg_build(r,'K01.MBOM.MODEL.A001',{'tool':'build_bom_v1_9.py','view':'MBOM'});reg_build(r,'K01.MBOM.ARTIFACT.A001',{'tool':'build_bom_v1_9.py','view':'MBOM','formats':['json','csv']});reg_verify(r,'K01.MBOM.VERIFY.A001',mv['verdict'],mv['metrics'],mv['issues']+mv['warnings'])
    print('EBOM:',ev['verdict'],'items=',ebom['item_count'],'modeled_occ=',ebom['modeled_occurrence_total'],'suppressed=',ebom['suppressed_occurrence_count'])
    for x in ev['issues']:print(' -',x)
    print('MBOM:',mv['verdict'],'items=',mbom['item_count'])
    for x in mv['issues']:print(' -',x)
    print('Artifacts:',artdir/'K01_EBOM_A001_CURRENT.csv','|',artdir/'K01_MBOM_A001_CURRENT.csv')
    return 0
if __name__=='__main__':raise SystemExit(main())
