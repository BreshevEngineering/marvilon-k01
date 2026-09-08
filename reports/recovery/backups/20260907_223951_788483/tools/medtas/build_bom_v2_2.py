from pathlib import Path
import argparse,csv,re
from v22_common import load,save,sha256_file

def partno_from_name(s):
 m=re.search(r'(K01-(?:P|B)-\d{3})',s or '',re.I); return m.group(1).upper() if m else None

def raw_snapshot(root):
 cand=list((root/'reports/cad/current').glob('K01_A001_SEMANTIC_RAW_API*.json')) if (root/'reports/cad/current').exists() else []
 return load(sorted(cand)[-1],{}) if cand else {}
def components(raw):
 for key in ('components','component_instances'):
  if isinstance(raw.get(key),list): return raw[key]
 return []
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve(); reg=load(r/'control/product/parts.json',{}) or {}; records=reg.get('parts',reg if isinstance(reg,list) else [])
 if isinstance(records,dict): records=[{'part_no':k,**(v if isinstance(v,dict) else {})} for k,v in records.items()]
 idx={str(x.get('part_no') or x.get('PartNo') or x.get('id','')).upper():x for x in records}
 raw=raw_snapshot(r); qty={}; suppressed=[]
 for c in components(raw):
  pn=partno_from_name(str(c.get('name') or c.get('component_name') or c.get('native_path') or c.get('path') or ''))
  if not pn: continue
  sup=bool(c.get('suppressed',False));
  if sup: suppressed.append({'part_no':pn,'component':c.get('name'),'disposition':'OPEN'})
  else: qty[pn]=qty.get(pn,0)+1
 nonmode=[('NM-J2-SEAL',1),('NM-J2-CLAMP-SCREW',3)]
 rows=[]; issues=[]
 for pn,q in sorted(qty.items()):
  d=idx.get(pn); 
  if not d: issues.append('REGISTRY_MISSING:'+pn); d={}
  rows.append({'PartNo':pn,'Description':d.get('description','OPEN'),'Qty':q,'Type':d.get('type','OPEN'),'MakeBuy':d.get('make_buy',d.get('makeBuy','OPEN')),'Material':d.get('material','OPEN'),'Revision':d.get('revision','OPEN'),'Supplier':d.get('supplier','OPEN')})
 for pn,q in nonmode:
  d=idx.get(pn,{}); rows.append({'PartNo':pn,'Description':d.get('description','OPEN'),'Qty':q,'Type':d.get('type','NON_MODELED'),'MakeBuy':d.get('make_buy','OPEN'),'Material':d.get('material','OPEN'),'Revision':d.get('revision','OPEN'),'Supplier':d.get('supplier','OPEN')});
  if not d: issues.append('REGISTRY_MISSING:'+pn)
 if suppressed: issues.append('SUPPRESSED_OCCURRENCES_REQUIRE_DISPOSITION')
 outdir=r/'reports/bom/current';outdir.mkdir(parents=True,exist_ok=True)
 eb={'schema':'k01.ebom.v2_2','status':'PASS' if not issues else 'HOLD','rows':rows,'suppressed':suppressed,'issues':issues,'source_component_count':sum(qty.values())}
 ep=save(outdir/'K01_EBOM_A001_CURRENT.json',eb)
 with open(outdir/'K01_EBOM_A001_CURRENT.csv','w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['PartNo','Description','Qty','Type','MakeBuy','Material','Revision','Supplier']);w.writeheader();w.writerows(rows)
 # MBOM preserves EBOM but marks P007 transformation open until released process decomposition
 mb_issues=list(issues)+['P007_MANUFACTURING_DECOMPOSITION_OPEN','P007_WELD_PROCESS_OPEN']
 mb={'schema':'k01.mbom.v2_2','status':'HOLD' if mb_issues else 'PASS','rows':rows,'manufacturing_transformations':[{'parent':'K01-P-007','status':'OPEN_SUBCOMPONENT_IDENTITIES'}],'issues':mb_issues}
 save(outdir/'K01_MBOM_A001_CURRENT.json',mb)
 with open(outdir/'K01_MBOM_A001_CURRENT.csv','w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['PartNo','Description','Qty','Type','MakeBuy','Material','Revision','Supplier']);w.writeheader();w.writerows(rows)
 # system BOM adds B007-B010 if registry knows them
 sysrows=list(rows)
 for pn in ['K01-B-007','K01-B-008','K01-B-009','K01-B-010']:
  d=idx.get(pn,{})
  if d: sysrows.append({'PartNo':pn,'Description':d.get('description','OPEN'),'Qty':1,'Type':d.get('type','BUY'),'MakeBuy':d.get('make_buy','BUY'),'Material':d.get('material','OPEN'),'Revision':d.get('revision','OPEN'),'Supplier':d.get('supplier','OPEN')})
 save(outdir/'K01_SYSTEM_BOM_CURRENT.json',{'schema':'k01.system_bom.v2_2','status':'PASS_WITH_LIMITATIONS','rows':sysrows})
 print('EBOM',eb['status'],'rows=',len(rows),'issues=',len(issues));print('MBOM',mb['status'],'issues=',len(mb_issues));return 0
if __name__=='__main__': raise SystemExit(main())
