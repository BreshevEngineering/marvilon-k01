"""BOM from the actual v1.4 instances + v1.9 items contract. Never release stale CAD."""
from pathlib import Path
import argparse,csv,re
from v22_common import load,save,sha256_file

def partno_from_name(s):
    m=re.search(r'(K01-(?:P|B)-\d{3})',s or '',re.I)
    return m.group(1).upper() if m else None

def components(raw):
    for key in ('instances','components','component_instances'):
        if isinstance(raw.get(key),list): return raw[key]
    return []

def build(raw,reg):
    issues=[]; qty={}; suppressed=[]
    records=reg.get('items',reg.get('parts',{}))
    if isinstance(records,list): records={x.get('part_number') or x.get('part_no'):x for x in records}
    if not isinstance(records,dict): records={}; issues.append('REGISTRY_SCHEMA_INVALID')
    occurrences=components(raw)
    if raw.get('status') not in ('OK','PASS'): issues.append('CAD_EXPORT_NOT_OK')
    if not occurrences: issues.append('CAD_OCCURRENCES_MISSING')
    expected=(raw.get('assembly') or {}).get('component_count')
    if expected is None or expected!=len(occurrences): issues.append('CAD_COMPONENT_COUNT_UNVERIFIED')
    for c in occurrences:
        pn=partno_from_name(str(c.get('path') or c.get('native_path') or c.get('name') or ''))
        if not pn: issues.append('UNIDENTIFIED_OCCURRENCE:'+str(c.get('name'))); continue
        if c.get('suppressed') is not False:
            suppressed.append(c); issues.append('SUPPRESSION_REQUIRES_DISPOSITION:'+str(c.get('name'))); continue
        qty[pn]=qty.get(pn,0)+1
    def row(pn,q,d):
        result={'PartNo':pn,'Description':d.get('description') or 'OPEN','Qty':q,'Type':d.get('item_type') or d.get('type') or 'OPEN','MakeBuy':d.get('make_buy') or 'OPEN','Material':d.get('material_authority') or d.get('material') or 'OPEN','MaterialStatus':d.get('material_status') or 'OPEN','Revision':d.get('revision') or 'OPEN','Supplier':d.get('supplier') or 'OPEN','Status':d.get('release_state') or d.get('status') or 'OPEN'}
        for key in ('Description','MakeBuy','Material','Revision'):
            if result[key]=='OPEN': issues.append(key.upper()+'_OPEN:'+pn)
        if result['MaterialStatus']!='CONTROLLED': issues.append('MATERIAL_REVIEW:'+pn)
        if result['Status']!='PASS': issues.append('ITEM_NOT_RELEASED:'+pn)
        return result
    rows=[]
    for pn,q in sorted(qty.items()):
        if pn not in records: issues.append('REGISTRY_MISSING:'+pn)
        rows.append(row(pn,q,records.get(pn,{})))
    for item in reg.get('non_modeled_inclusions',[]):
        if 'EBOM' not in item.get('bom_views',[]): continue
        pn=item.get('part_number') or item.get('registry_key') or 'OPEN'
        rows.append(row(pn,item.get('quantity'),item))
        if not item.get('part_number') or item.get('release_blocker'): issues.append('NON_MODELED_SPEC_OPEN:'+pn)
    # An archived export without a native hash/config binding is useful inventory, not release evidence.
    issues.append('FRESH_FINAL_CAD_BINDING_REQUIRED')
    return {'schema':'k01.ebom.v2_2_repair1','status':'HOLD','rows':rows,'suppressed':suppressed,'issues':sorted(set(issues)),'source_component_count':sum(qty.values()),'source_assembly':raw.get('assembly',{}),'usage':'RECONSTRUCTED_SNAPSHOT_BOM_NOT_RELEASED'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    binding=load(r/'control/medtas/v1/bindings/K01_CAD_SEM_A001_BINDING_v1_6.json',{}) or {}
    rawp=r/binding.get('raw_api_output','reports/cad/current/K01_A001_SEMANTIC_RAW_API_v1_4.json')
    regp=r/'control/product/parts.json'; reg=load(regp,{}) or {}; eb=build(load(rawp,{}) or {},reg)
    eb['input_hashes']={str(p.relative_to(r)):sha256_file(p) for p in (rawp,regp) if p.is_file()}
    out=r/'reports/bom/current';out.mkdir(parents=True,exist_ok=True)
    for view in ('EBOM','MBOM'):
        result=dict(eb)
        if view=='MBOM':
            result['schema']='k01.mbom.v2_2_repair1';result['issues']=eb['issues']+['P007_MANUFACTURING_DECOMPOSITION_OPEN']
            result['process_inclusions']=[x for x in reg.get('non_modeled_inclusions',[]) if 'MBOM' in x.get('bom_views',[]) and 'EBOM' not in x.get('bom_views',[])]
        save(out/('K01_'+view+'_A001_CURRENT.json'),result)
        with (out/('K01_'+view+'_A001_CURRENT.csv')).open('w',newline='',encoding='utf-8-sig') as f:
            fields=list(eb['rows'][0]) if eb['rows'] else ['PartNo','Qty']
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(eb['rows'])
    save(out/'K01_SYSTEM_BOM_CURRENT.json',{'schema':'k01.system_bom.v2_2_repair1','status':'HOLD','issues':['SYSTEM_BOUNDARY_AND_QUANTITIES_NOT_VERIFIED'],'rows':eb['rows']})
    print('HOLD: snapshot BOM reconstructed, CAD occurrences=',eb['source_component_count'],'rows=',len(eb['rows']))
    return 2
if __name__=='__main__': raise SystemExit(main())
