from __future__ import annotations
import argparse,os,subprocess,time,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();out=r/'reports/medtas/tests/K01_CENTER_ACTION_LAUNCH_SELFTEST_CURRENT.json';out.parent.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':
        payload={'schema':'k01.center_action_launch_selftest.v1_8','verdict':'PASS','status':'SKIPPED_NON_WINDOWS','issues':[]};out.write_text(json.dumps(payload,indent=2),encoding='utf-8');print('PASS Center action launch self-test (skipped non-Windows)');return 0
    probe=out.parent/'_K01_CENTER_ACTION_PROBE.cmd';marker=out.parent/'_K01_CENTER_ACTION_PROBE.marker'
    try:
        marker.unlink(missing_ok=True)
        probe.write_text('@echo off\r\necho PASS>"'+str(marker)+'"\r\nexit /b 0\r\n',encoding='utf-8')
        comspec=os.environ.get('COMSPEC') or 'cmd.exe';flags=getattr(subprocess,'CREATE_NEW_CONSOLE',0);cp=subprocess.Popen([comspec,'/d','/c',f'call "{str(probe)}"'],cwd=str(r),creationflags=flags,close_fds=False)
        cp.wait(timeout=15)
        ok=marker.exists() and marker.read_text(errors='ignore').strip()=='PASS';issues=[] if ok else ['CENTER-ACTION-PROBE-001: marker not created by controlled CMD launch']
        payload={'schema':'k01.center_action_launch_selftest.v1_8','verdict':'PASS' if ok else 'HOLD','return_code':cp.returncode,'issues':issues};out.write_text(json.dumps(payload,indent=2),encoding='utf-8');print(payload['verdict'],'Center controlled action launch self-test');return 0 if ok else 1
    except Exception as e:
        payload={'schema':'k01.center_action_launch_selftest.v1_8','verdict':'HOLD','issues':[repr(e)]};out.write_text(json.dumps(payload,indent=2),encoding='utf-8');print('HOLD Center action launch self-test',e);return 1
    finally:
        try:probe.unlink()
        except Exception:pass
        try:marker.unlink()
        except Exception:pass
if __name__=='__main__':raise SystemExit(main())
