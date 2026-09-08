from __future__ import annotations
import argparse,json,subprocess,time
from pathlib import Path
from medtas_v16_common import load,dump,evaluate,register_build,register_verify,sha256_file,tool_path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();d=evaluate(root);work=root/'reports/medtas/calculix/current/K01_CCX_P006';deck=work/'K01_P006.inp';ccx=tool_path(root,'calculix_executable',['ccx.exe','ccx']);blocking=[]
    if d.get('K01.STRUCT.CCX.INPUT.P006',{}).get('state')!='PASS':blocking.append('K01.STRUCT.CCX.INPUT.P006:'+str(d.get('K01.STRUCT.CCX.INPUT.P006',{}).get('state')))
    if not deck.exists():blocking.append('CCX-RUN-DECK-001: controlled K01_P006.inp missing')
    if not ccx:blocking.append('CCX-EXE-001: CalculiX executable not found/bound')
    if blocking:
        print('BLOCKED CalculiX run');[print(' -',x) for x in blocking];return 1
    work.mkdir(parents=True,exist_ok=True)
    # Remove solver outputs from the previous run, but never the controlled input deck.
    for ext in ('.dat','.frd','.sta','.cvg','.12d','.eig','.rout','.log'):
        p=work/('K01_P006'+ext)
        if p.exists():
            try:p.unlink()
            except Exception:pass
    t=time.time();cp=subprocess.run([str(ccx),'K01_P006'],cwd=str(work),text=True,capture_output=True,timeout=3600);dur=round(time.time()-t,3)
    (work/'K01_P006.stdout.log').write_text(cp.stdout or '',encoding='utf-8',errors='replace');(work/'K01_P006.stderr.log').write_text(cp.stderr or '',encoding='utf-8',errors='replace')
    artifacts=[]
    for p in sorted(work.glob('K01_P006.*')):
        if p.is_file():artifacts.append({'path':p.relative_to(root).as_posix(),'size':p.stat().st_size,'sha256':sha256_file(p)})
    result_files=[p for p in (work/'K01_P006.dat',work/'K01_P006.frd') if p.exists() and p.stat().st_size>0]
    verdict='PASS' if cp.returncode==0 and result_files else 'HOLD';payload={'schema':'k01.calculix_run.p006.v1_7','verdict':verdict,'return_code':cp.returncode,'duration_s':dur,'executable':str(ccx),'job':'K01_P006','artifacts':artifacts,'result_files':[p.relative_to(root).as_posix() for p in result_files],'limitations':[] if verdict=='PASS' else ['CCX-RUN-001: solver did not return zero with non-empty .dat/.frd evidence']}
    out=work/'K01_CALCULIX_RUN_P006_v1_7.json';dump(out,payload)
    # The graph hashes the whole work directory; register only after all logs/result files exist.
    register_build(root,'K01.STRUCT.CCX.P006',{'tool':'run_calculix_p006_v1_7.py','executable':str(ccx),'job':'K01_P006'},limitations=payload['limitations']);register_verify(root,'K01.STRUCT.CCX.P006',verdict,metrics={'return_code':cp.returncode,'duration_s':dur,'result_file_count':len(result_files)},limitations=payload['limitations'])
    print(verdict,'CalculiX K01_P006 rc=',cp.returncode,'duration=',dur,'s');print('Evidence:',out);return 0 if verdict=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
