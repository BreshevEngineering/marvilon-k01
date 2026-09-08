from pathlib import Path
import argparse,re
from v22_common import load,save

def latest_raw(root):
 d=root/'reports/cad/current'
 fs=sorted(d.glob('K01_A001_SEMANTIC_RAW_API*.json')) if d.exists() else []
 return fs[-1] if fs else None

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();b=load(r/'control/baseline/K01_FINAL_ASSEMBLY_BASELINE_v2_2.json',{}) or {}; rp=r/'reports/control/K01_FINAL_ASSEMBLY_SEMANTIC_VERIFY_CURRENT.json'
 rawp=latest_raw(r); rep={'schema':'k01.final_assembly_semantic_verify.v2_2','status':'HOLD','raw_snapshot':str(rawp) if rawp else None,'checks':[]}
 if not rawp: save(rp,rep);print('HOLD raw semantic snapshot missing; run CAD semantic extraction on promoted assembly');return 2
 raw=load(rawp,{}) or {}; comps=raw.get('components') or raw.get('component_instances') or []; mates=raw.get('mates') or []
 rep['checks'].append({'id':'SEM-COMP-001','status':'PASS' if len(comps)==b.get('expected_component_count') else 'FAIL','actual':len(comps),'expected':b.get('expected_component_count')})
 rep['checks'].append({'id':'SEM-MATE-001','status':'PASS' if len(mates)==b.get('expected_mate_count') else 'FAIL','actual':len(mates),'expected':b.get('expected_mate_count')})
 bad=[]
 for c in comps:
  s=str(c.get('native_path') or c.get('path') or c.get('name') or '')
  n=Path(s).name.upper()
  if any(t in n for t in ['GATE','CANDIDATE','VERIFY','REFERENCE']): bad.append(n)
 rep['checks'].append({'id':'SEM-ID-001','status':'PASS' if not bad else 'FAIL','bad_names':bad})
 # P007 current live geometry, if materialized, must match selected baseline nominals
 geo=load(r/'reports/drawing/current/K01-D-006_P007_LIVE_GEOMETRY_CURRENT.json',{}) or {}
 vals=geo.get('values_mm') or geo.get('geometry_mm') or geo.get('critical_geometry_mm') or {}
 expected={'flange_OD':33.0,'flange_thickness':3.0,'locator_OD':14.10,'locator_length':2.0,'thin_OD':10.0,'thin_ID':9.4,'overall_length':35.0,'fastener_PCD':26.5}
 if vals:
  misses=[]
  for k,v in expected.items():
   av=vals.get(k)
   if av is None: continue
   if abs(float(av)-v)>1e-6: misses.append({'key':k,'actual':av,'expected':v})
  rep['checks'].append({'id':'SEM-P007-001','status':'PASS' if not misses else 'FAIL','mismatches':misses})
 else:
  rep['checks'].append({'id':'SEM-P007-001','status':'HOLD','detail':'P007 live geometry report not present; run P007 live-geometry extraction'})
 hardfail=any(x['status']=='FAIL' for x in rep['checks']); hold=any(x['status']=='HOLD' for x in rep['checks'])
 rep['status']='FAIL' if hardfail else ('PASS_WITH_LIMITATIONS' if hold else 'PASS')
 save(rp,rep);print(rep['status']);[print(x) for x in rep['checks'] if x['status']!='PASS'];return 0 if rep['status'].startswith('PASS') else 3
if __name__=='__main__': raise SystemExit(main())
