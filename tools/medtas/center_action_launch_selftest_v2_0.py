from __future__ import annotations
import argparse,subprocess,sys,time,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();out=r/'reports/medtas/tests/K01_CENTER_ACTION_LAUNCH_SELFTEST_CURRENT.json';out.parent.mkdir(parents=True,exist_ok=True)
    marker=out.parent/'_K01_CENTER_ACTION_PY.marker'
    try:
        marker.unlink(missing_ok=True)
        code="from pathlib import Path; Path(r'"+str(marker).replace("'","''")+"').write_text('PASS',encoding='utf-8')"
        flags=getattr(subprocess,'CREATE_NEW_CONSOLE',0) if sys.platform.startswith('win') else 0
        cp=subprocess.Popen([sys.executable,'-c',code],cwd=str(r),creationflags=flags,close_fds=False);cp.wait(timeout=15)
        ok=marker.exists() and marker.read_text(encoding='utf-8',errors='ignore').strip()=='PASS'
        issues=[] if ok else ['CENTER-ACTION-PROBE-001: direct Python marker was not created']
        payload={'schema':'k01.center_action_launch_selftest.v2_0','verdict':'PASS' if ok else 'HOLD','return_code':cp.returncode,'launcher':'DIRECT_PYTHON_ARGV','issues':issues};out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(payload['verdict'],'Center direct action launch self-test');return 0 if ok else 1
    except Exception as e:
        payload={'schema':'k01.center_action_launch_selftest.v2_0','verdict':'HOLD','issues':[repr(e)]};out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print('HOLD Center direct action launch self-test',e);return 1
    finally:
        try:marker.unlink()
        except Exception:pass
if __name__=='__main__':raise SystemExit(main())
