from pathlib import Path
import argparse
from v22_common import save,sha256_file
PATTERNS=['*.docx','*.csv','*.txt','*.jpg','*.png','*.json']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve(); items=[]
 roots=[r/'cad/candidates/gate04e_p006_service/verification',r/'reports',r/'reports/engineering/current',r/'reports/medtas']
 seen=set()
 for d in roots:
  if not d.exists(): continue
  for pat in PATTERNS:
   for p in d.rglob(pat):
    if p in seen or p.name.startswith('~$'): continue
    seen.add(p); n=p.name.lower(); kind='OTHER'
    if 'static' in n or 'stress' in n or 'strain' in n or 'displacement' in n: kind='STRUCTURAL'
    elif 'femm' in n or 'coil' in n: kind='MAGNETIC'
    elif 'flow' in n or 'cfd' in n: kind='FLOW'
    elif 'dimension' in n or 'tolerance' in n: kind='TOLERANCE'
    items.append({'id':f'CALC-{len(items)+1:04d}','kind':kind,'path':str(p.relative_to(r)),'sha256':sha256_file(p),'size':p.stat().st_size})
 rep={'schema':'k01.calculation_evidence_index.v2_2','status':'PASS' if items else 'HOLD','items':items}
 p=save(r/'reports/control/K01_CALCULATION_EVIDENCE_INDEX_CURRENT.json',rep); print(rep['status'],'items=',len(items));print(p);return 0
if __name__=='__main__': raise SystemExit(main())
