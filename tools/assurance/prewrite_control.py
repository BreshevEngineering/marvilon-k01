from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

REPORT=Path('reports/control/K01_PREWRITE_CONTROL_CURRENT.json')

def run(root:Path,rel:str,*args):
    p=root/rel
    cp=subprocess.run([sys.executable,str(p),'--repo-root',str(root),*args],cwd=str(root),capture_output=True,text=True,errors='replace')
    return {'tool':rel,'args':list(args),'rc':cp.returncode,'stdout':cp.stdout.strip(),'stderr':cp.stderr.strip()}

def main():
    ap=argparse.ArgumentParser(description='K01 generic pre-write control refresh for the current active step.')
    ap.add_argument('--repo-root',default='.')
    a=ap.parse_args();root=Path(a.repo_root).resolve();runs=[]
    sequence=[
      ('tools/repo/control_namespace_guard.py',('--write-report',),True),
      ('tools/medtas/technical_filter_map_v2_2.py',(),True),
      ('tools/medtas/build_requirements_coverage_v1_9.py',(),True),
      ('tools/assurance/engineering_step_gate.py',(),True),
    ]
    failed=False
    for rel,args,blocking in sequence:
        row=run(root,rel,*args);runs.append(row)
        print(row['stdout'])
        if row['stderr']:print(row['stderr'])
        if row['rc']!=0 and blocking:
            failed=True;break

    step_status=None;mutation=False
    sg=root/'reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json'
    if sg.is_file():
        try:
            obj=json.loads(sg.read_text(encoding='utf-8-sig'));step_status=obj.get('status');mutation=bool(obj.get('mutation_authorized'))
        except Exception:pass

    rep={
      'schema':'k01.prewrite_control.current.v1',
      'generated_utc':datetime.now(timezone.utc).isoformat(),
      'status':'HOLD_PREWRITE_CONTROL' if failed else 'PASS_PREWRITE_CONTROL',
      'active_step_status':step_status,
      'mutation_authorized':mutation,
      'native_CAD_mutated':False,
      'runs':runs,
      'rule':'Refresh all generic control projections before an engineering write. The active step gate remains the final intent-specific authority.'
    }
    out=root/REPORT;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    # Build one final handoff after the step-gate evidence exists. Handoff is a
    # transport/resume product, not a prerequisite engineering authority.
    if not failed:
        row=run(root,'tools/medtas/ai_handoff_v2_0.py');runs.append(row)
        print(row['stdout'])
        if row['stderr']:print(row['stderr'])
        if row['rc']!=0:
            failed=True;rep['status']='HOLD_PREWRITE_CONTROL_FINAL_HANDOFF'
        rep['runs']=runs
        out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    print('prewrite_control:',rep['status'],'step=',step_status,'mutation_authorized=',mutation)
    print('REPORT:',out)
    return 0 if not failed else 2

if __name__=='__main__':raise SystemExit(main())
