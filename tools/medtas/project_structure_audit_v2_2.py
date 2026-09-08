from pathlib import Path
import argparse, os
from v22_common import save
ALLOWED={'00_admin','analysis','archive','bom','cad','cad_api','calc','control','docs','drawings','generated','master','purchased','release','reports','reverse_dxf','tools','tests','.github'}
TEMP_SUFFIX={'.CWR','.PC0','.SL3','.GEN','.MAS','.rsl'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
 dirs=[p.name for p in r.iterdir() if p.is_dir() and p.name!='.git']; unknown=sorted(set(dirs)-ALLOWED)
 temp=[]
 for p in r.rglob('*'):
  if p.is_file() and (p.name.startswith('~$') or p.suffix in TEMP_SUFFIX or '__pycache__' in p.parts): temp.append(str(p.relative_to(r)))
 legacy=[x for x in ['master/K01_master.json','control/K01_master_v2.json','bom/K01_BOM_master.csv','control/K01_PROJECT_CONTROL_v2.xlsx'] if (r/x).exists()]
 rep={'schema':'k01.project_structure_audit.v2_2','status':'PASS_WITH_LIMITATIONS' if (unknown or temp or legacy) else 'PASS','unknown_top_dirs':unknown,'runtime_temp_files':temp[:1000],'legacy_authority_sources_present':legacy,'release_r01_exists':(r/'release/R01').exists(),'release_r01_nonempty':any((r/'release/R01').iterdir()) if (r/'release/R01').exists() else False}
 p=save(r/'reports/control/K01_PROJECT_STRUCTURE_AUDIT_CURRENT.json',rep);print(rep['status'],'unknown=',len(unknown),'temp=',len(temp),'legacy=',len(legacy));print(p);return 0
if __name__=='__main__': raise SystemExit(main())
