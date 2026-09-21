from __future__ import annotations
import argparse,hashlib,subprocess,sys,traceback
from pathlib import Path
from control_authority import require_control_family
from canonical_hash_v1_5 import canonical_json_hash
from medtas_v16_common import load,dump,register_build,register_verify

def sha_file(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def binding(root):
    return load(require_control_family(root,'cad_sem_a001_binding'),{}) or {}

def assembly_from_raw(root,b):
    p=root/b['raw_api_output']
    if not p.exists():raise FileNotFoundError('raw CAD semantic snapshot missing: '+str(p))
    r=load(p);q=r.get('assembly',{}).get('native_path')
    if not q:raise KeyError('raw snapshot assembly.native_path missing')
    return Path(q)

def run_export(root,b):
    cp=subprocess.run([sys.executable,str(root/'tools/medtas/run_cad_sem_a001.py'),'--repo-root',str(root)])
    if cp.returncode:raise RuntimeError('CAD semantic export failed rc='+str(cp.returncode))
    c=load(root/b['canonical_output'])
    d=load(root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json')['nodes']['K01.CAD.SEM.A001']
    asm=assembly_from_raw(root,b)
    return {'canonical_hash':canonical_json_hash(c),'state_hash':d['state_hash'],'artifact_hash':d['artifact_hash'],'binary_sha256':sha_file(asm) if asm.exists() else None,'assembly':str(asm)}

def eq(a,b):return a['canonical_hash']==b['canonical_hash'] and a['state_hash']==b['state_hash']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();b=binding(root)
    out=root/'reports/medtas/tests/K01_CAD_CANONICAL_HASH_INVARIANCE_CURRENT.json'
    print('K01 canonical hash invariance qualification v1.6')
    print('PASS requires: export#1 == export#2, then export#2 == export#3 after two no-change native saves.')
    print('Native SLDASM/SLDPRT SHA is diagnostic only and never controls engineering freshness.')
    runs=[]
    try:
        runs.append(run_export(root,b));runs.append(run_export(root,b))
    except Exception as e:
        report={'schema':'k01.canonical_hash_invariance.v1_6','verdict':'BLOCKED_EXPORT','stage':'DETERMINISTIC_REPEAT_EXPORT','error':str(e),'traceback':traceback.format_exc(),'runs':runs}
        dump(out,report);print('BLOCKED_EXPORT:',e);return 2
    deterministic=eq(runs[0],runs[1])
    print('Repeat-export canonical equal=',runs[0]['canonical_hash']==runs[1]['canonical_hash'],'STATE equal=',runs[0]['state_hash']==runs[1]['state_hash'])
    if not deterministic:
        report={'schema':'k01.canonical_hash_invariance.v1_6','verdict':'HOLD_SEMANTIC_DRIFT','stage':'DETERMINISTIC_REPEAT_EXPORT','runs':runs,'rule':'Two API exports without a CAD save must be semantically identical before save-invariance can be tested.'}
        dump(out,report);register_build(root,'K01.CAD.HASH.QUAL.A001',{'tool':'cad_hash_invariance_test_v1_6.py'});register_verify(root,'K01.CAD.HASH.QUAL.A001','HOLD',limitations=['CAD-HASH-001: repeated semantic export changed without a CAD write'])
        print('HOLD_SEMANTIC_DRIFT before save test.');return 1
    print('\nIn SOLIDWORKS do NOT change geometry, MBD/tolerances, configuration, suppression or mates.')
    print('Save the assembly twice (Ctrl+S, Ctrl+S), then return here.')
    input('Press ENTER after the two no-change saves... ')
    try:runs.append(run_export(root,b))
    except Exception as e:
        report={'schema':'k01.canonical_hash_invariance.v1_6','verdict':'BLOCKED_EXPORT','stage':'POST_SAVE_EXPORT','error':str(e),'traceback':traceback.format_exc(),'runs':runs}
        dump(out,report);print('BLOCKED_EXPORT after saves:',e);return 2
    save_equal=eq(runs[1],runs[2]);verdict='PASS' if save_equal else 'HOLD_SEMANTIC_DRIFT'
    report={'schema':'k01.canonical_hash_invariance.v1_6','verdict':verdict,'deterministic_repeat_equal':deterministic,'post_save_equal':save_equal,'runs':runs,'native_binary_changed_repeat':runs[0]['binary_sha256']!=runs[1]['binary_sha256'],'native_binary_changed_after_saves':runs[1]['binary_sha256']!=runs[2]['binary_sha256'],'rule':'Canonical payload hash and MEDTAS STATE_HASH must remain equal. Native binary SHA is diagnostic only.'}
    dump(out,report);register_build(root,'K01.CAD.HASH.QUAL.A001',{'tool':'cad_hash_invariance_test_v1_6.py'});register_verify(root,'K01.CAD.HASH.QUAL.A001',verdict,metrics={'deterministic_repeat_equal':deterministic,'post_save_equal':save_equal,'native_binary_changed_after_saves':report['native_binary_changed_after_saves']},limitations=[] if verdict=='PASS' else ['CAD-HASH-002: no-change native save changed semantic hash'])
    subprocess.call([sys.executable,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)])
    print('\n'+verdict);print('report=',out)
    for i,r in enumerate(runs,1):print('run',i,'canonical=',r['canonical_hash'],'STATE=',r['state_hash'],'native=',r['binary_sha256'])
    return 0 if verdict=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
