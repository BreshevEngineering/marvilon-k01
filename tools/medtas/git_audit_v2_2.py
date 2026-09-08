from pathlib import Path
import argparse, subprocess, json, os
from v22_common import save

def cmd(r,args):
 p=subprocess.run(['git']+args,cwd=r,text=True,capture_output=True); return p.returncode,p.stdout.strip(),p.stderr.strip()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
 rep={'schema':'k01.git_audit.v2_2','repo_root':str(r),'status':'HOLD','checks':[]}
 if not (r/'.git').exists():
  rep['checks'].append({'id':'GIT-001','status':'FAIL','detail':'.git directory missing in this working root'}); save(r/'reports/control/K01_GIT_AUDIT_CURRENT.json',rep); print('HOLD: not a git working tree'); return 2
 rc,remote,err=cmd(r,['remote','-v']); rc2,branch,err2=cmd(r,['branch','--show-current']); rc3,status,err3=cmd(r,['status','--porcelain=v1']);
 rep['remote_v']=remote; rep['branch']=branch; rep['dirty_count']=len([x for x in status.splitlines() if x.strip()]); rep['status_lines']=status.splitlines()[:500]
 rep['checks'].append({'id':'GIT-REMOTE','status':'PASS' if remote else 'HOLD','detail':remote or 'no remote configured'})
 rep['checks'].append({'id':'GIT-BRANCH','status':'PASS' if branch=='main' else 'HOLD','detail':branch})
 rep['checks'].append({'id':'GIT-IGNORE','status':'PASS' if (r/'.gitignore').exists() else 'HOLD'})
 rep['status']='PASS_WITH_LIMITATIONS' if remote else 'HOLD'
 p=save(r/'reports/control/K01_GIT_AUDIT_CURRENT.json',rep); print(rep['status'],'branch=',branch,'dirty=',rep['dirty_count']); print(p); return 0
if __name__=='__main__': raise SystemExit(main())
