"""Install presentation assets without replacing unknown project dispatchers."""
import argparse,hashlib,json,shutil,sys,time
from pathlib import Path
SRC=Path(__file__).resolve().parent

def install(root):
 root=Path(root).resolve()
 if not root.is_dir():raise ValueError('Repository root does not exist')
 target=root/'center/panel';stamp=time.strftime('%Y%m%d_%H%M%S');backup=root/'archive/center_panel'/stamp
 if target.exists():
  backup.mkdir(parents=True,exist_ok=False);shutil.copytree(target,backup/'panel')
 target.mkdir(parents=True,exist_ok=True)
 for p in (SRC/'center/panel').iterdir():
  if p.is_file():shutil.copy2(p,target/p.name)
 cfg=target/'config.json'
 if not cfg.exists():
  verdict='evidence/verdict.json'
  if not (root/verdict).exists() and (root/'evidence/current/K01_CENTER_VIEW.json').exists():verdict='evidence/current/K01_CENTER_VIEW.json'
  cfg.write_text(json.dumps({'verdict':verdict,'cad_root':None,'commands':{'verdict':['verdict'],'audit':['audit'],'selftest':['selftest']}},indent=2),encoding='utf-8')
 script=root/'tools/run.py';launcher=root/'run.cmd';expected=(SRC/'integration/source_sha256.txt').read_text().strip();integrated=False
 if script.is_file() and hashlib.sha256(script.read_bytes()).hexdigest()==expected:
  backup.mkdir(parents=True,exist_ok=True);shutil.copy2(script,backup/'run.py');shutil.copy2(SRC/'integration/run.py',script);integrated=True
 elif not script.exists() and not launcher.exists() and not (root/'tools/cli/k01_cli.py').exists():
  script.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/'integration/run.py',script);shutil.copy2(SRC/'integration/run.cmd',launcher);integrated=True
 print('Installed:',target)
 print('Configuration:',cfg)
 print('Canonical integration:', 'run.cmd center' if integrated else 'Existing dispatcher preserved; use the direct command below or add center route.')
 print('Direct launch:')
 print('py -3 "'+str(target/'server.py')+'" --repo-root "'+str(root)+'"')
 print('No CAD/BOM/requirements/verdict/Git changes were made.')
 return 0
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--repo-root',required=True);o=a.parse_args()
 try:raise SystemExit(install(o.repo_root))
 except (OSError,ValueError) as e:print('INSTALL ERROR:',e);raise SystemExit(2)
