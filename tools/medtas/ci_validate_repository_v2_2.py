from pathlib import Path
import argparse,json,sys

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--json-only',action='store_true');a=ap.parse_args();r=Path(a.repo_root);errs=[];count=0
 for p in r.rglob('*.json'):
  if '.git' in p.parts: continue
  try: json.loads(p.read_text(encoding='utf-8-sig'));count+=1
  except Exception as e: errs.append(str(p)+': '+str(e))
 print('JSON',count,'errors',len(errs)); [print(x) for x in errs]
 if a.json_only: return 1 if errs else 0
 # critical files
 for rel in ['control/project/K01_AUTHORITY_MAP_v2_2.json','control/decision_system/K01_TECHNICAL_FILTER_24_v2_2.json','control/git/K01_GIT_POLICY_v2_2.json']:
  if not (r/rel).exists(): errs.append('missing '+rel)
 return 1 if errs else 0
if __name__=='__main__': raise SystemExit(main())
