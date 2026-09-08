"""Read native files only; create a compact, reproducible recovery evidence bundle."""
from pathlib import Path
import argparse,json,subprocess,sys,zipfile,datetime,os
from v22_common import load,save,sha256_file

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--cad-root',action='append',default=[]);ap.add_argument('--compile-adapter',action='store_true');a=ap.parse_args();r=Path(a.repo_root).resolve()
 out=r/'reports/recovery';out.mkdir(parents=True,exist_ok=True)
 cfg=load(r/'control/configuration/K01_LOCAL_PATHS.json',{}) or {}
 roots=[r]+[Path(x).resolve() for x in a.cad_root]
 if cfg.get('cad_workspace_root'):roots.append(Path(cfg['cad_workspace_root']).resolve())
 if os.name=='nt':roots += [Path('D:/Marvilon/K01'),Path('D:/BreshevEngineering/K01')]
 roots=list(dict.fromkeys(roots)); native=[]; locks=[]
 for root in roots:
  if not root.is_dir():continue
  for p in sorted((root/'cad').rglob('*')):
   if not p.is_file() or p.suffix.lower() not in ('.sldprt','.sldasm','.slddrw'):continue
   if p.name.startswith('~$'):locks.append(str(p));continue
   native.append({'path':str(p),'root':str(root),'relative':str(p.relative_to(root)),'size':p.stat().st_size,'sha256':sha256_file(p)})
 base=load(r/'control/baseline/K01_FINAL_ASSEMBLY_BASELINE_v2_2.json',{}) or {}
 expected=[{'path':str(root/base['source']),'exists':(root/base['source']).is_file()} for root in roots] if base.get('source') else []
 groups={}
 for p in native:
  if p['path'].lower().endswith('.sldasm'):groups.setdefault(p['sha256'],[]).append(p['path'])
 status_reports=[]
 for folder in ['reports/control','reports/drawing/current','reports/inspection/current','reports/bom/current']:
  for p in sorted((r/folder).glob('*.json')):
   d=load(p,{}) or {}
   if not isinstance(d,dict):continue
   status_reports.append({'path':str(p.relative_to(r)),'sha256':sha256_file(p),'schema':d.get('schema'),'reported_status':d.get('status',d.get('verdict')),'evidence_freshness':'NOT_REQUALIFIED'})
 git={}
 for name,args in [('head',['rev-parse','HEAD']),('branch',['branch','--show-current']),('status',['status','--porcelain=v1','-uall']),('local_tracking',['rev-list','--left-right','--count','HEAD...origin/main'])]:
  try:
   cp=subprocess.run(['git']+args,cwd=r,capture_output=True,text=True,timeout=30);git[name]={'rc':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}
  except Exception as e:git[name]={'error':str(e)}
 git['remote_verification']='NOT_PERFORMED: local tracking refs do not establish server state'
 runs=[]
 commands=[['tests/medtas/test_recovery_contracts.py'],['tools/medtas/build_bom_v2_2.py','--repo-root',str(r)]]
 if a.compile_adapter and os.name=='nt':commands.append(['tools/medtas/compile_packandgo_v2_2.py','--repo-root',str(r)])
 for command in commands:
  try:
   cp=subprocess.run([sys.executable,str(r/command[0])]+command[1:],cwd=r,text=True,capture_output=True,timeout=120)
   runs.append({'command':command,'rc':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
  except Exception as e:runs.append({'command':command,'error':str(e)})
 report={'schema':'k01.recovery_audit.1','status':'HOLD_SOURCE_REQUALIFICATION_REQUIRED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'roots':[str(x) for x in roots],'expected_source':expected,'native_files':native,'locks_not_documents':locks,'identical_assemblies':[v for v in groups.values() if len(v)>1],'reported_states_not_requalified':status_reports,'git':git,'runs':runs,'cad_writes':False,'scope':'File inventory, hashes, offline contract tests and optional C# compilation. No SolidWorks execution, geometry or mate verification.'}
 save(out/'K01_RECOVERY_CURRENT.json',report)
 bundle=out/'K01_RECOVERY_RESULT.zip'
 with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
  z.write(out/'K01_RECOVERY_CURRENT.json','K01_RECOVERY_CURRENT.json')
  for p in (r/'reports/bom/current').glob('K01_*A001_CURRENT.*'):z.write(p,'bom/'+p.name)
 print(report['status']);print('Native files:',len(native),'Lock files excluded:',len(locks));print('Source present:',any(x['exists'] for x in expected));print('Result:',bundle)
 # 0 means diagnostic completed, not engineering release.
 return 1 if any('error' in x or (x.get('rc') not in (0,2)) for x in runs) else 0
if __name__=='__main__':raise SystemExit(main())
