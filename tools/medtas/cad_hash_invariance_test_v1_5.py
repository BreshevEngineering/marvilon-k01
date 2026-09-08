from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, traceback
from pathlib import Path
from canonical_hash_v1_5 import canonical_json_hash

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def sha_file(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def assembly_from_raw(root):
    for name in ('K01_A001_SEMANTIC_RAW_API_v1_5.json','K01_A001_SEMANTIC_RAW_API_v1_4.json'):
        p=root/'reports/medtas/cad/current'/name
        if p.exists(): return Path(load(p)['assembly']['native_path'])
    raise FileNotFoundError('raw CAD semantic snapshot missing')
def run_export(root):
    cp=subprocess.run([sys.executable,str(root/'tools/medtas/run_cad_sem_a001.py'),'--repo-root',str(root)])
    if cp.returncode: raise RuntimeError('CAD semantic export failed rc='+str(cp.returncode))
    c=load(root/'reports/medtas/cad/current/K01_CAD_SEM_A001.json')
    d=load(root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json')['nodes']['K01.CAD.SEM.A001']
    asm=assembly_from_raw(root)
    return canonical_json_hash(c),d['state_hash'],sha_file(asm) if asm.exists() else None,asm

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    out=root/'reports/medtas/tests/K01_CAD_CANONICAL_HASH_INVARIANCE_CURRENT.json'
    print('K01 canonical hash invariance qualification v1.5')
    print('Rule: unchanged model save(s) must preserve canonical payload hash AND MEDTAS STATE_HASH.')
    print('Native SLDASM/SLDPRT binary SHA is diagnostic only.')
    try:
        h1,s1,b1,asm=run_export(root)
    except Exception as e:
        report={'schema':'k01.canonical_hash_invariance.v1_5','verdict':'BLOCKED_EXPORT','stage':'BASELINE_EXPORT','error':str(e),'traceback':traceback.format_exc(),'rule':'Exporter availability is separate from canonical invariance. No conclusion about canonicalization is permitted until two semantic exports succeed.'}
        dump(out,report); print('BLOCKED_EXPORT:',e); print('report=',out); return 2
    print('Baseline canonical payload hash:',h1);print('Baseline MEDTAS STATE_HASH:',s1);print('Baseline native binary SHA256:',b1);print('Assembly:',asm)
    print('\nIn SOLIDWORKS: do NOT change geometry, tolerances, MBD, suppression or mates.')
    print('Save the assembly twice (Ctrl+S, Ctrl+S), then return here.')
    input('Press ENTER after the two saves... ')
    try:
        h2,s2,b2,_=run_export(root)
    except Exception as e:
        report={'schema':'k01.canonical_hash_invariance.v1_5','verdict':'BLOCKED_EXPORT','stage':'SECOND_EXPORT','canonical_payload_hash_before':h1,'state_hash_before':s1,'binary_sha256_before':b1,'error':str(e),'traceback':traceback.format_exc()}
        dump(out,report); print('BLOCKED_EXPORT during second export:',e); print('report=',out); return 2
    verdict='PASS' if (h1==h2 and s1==s2) else 'HOLD_SEMANTIC_DRIFT'
    report={'schema':'k01.canonical_hash_invariance.v1_5','verdict':verdict,'canonical_payload_hash_before':h1,'canonical_payload_hash_after':h2,'state_hash_before':s1,'state_hash_after':s2,'binary_sha256_before':b1,'binary_sha256_after':b2,'binary_changed':b1!=b2,'canonical_equal':h1==h2,'state_equal':s1==s2,'rule':'PASS requires canonical payload hash and MEDTAS STATE_HASH equality. Native binary hash never controls engineering freshness.'}
    dump(out,report)
    print('\n'+verdict)
    print('canonical before=',h1);print('canonical after =',h2);print('STATE before=',s1);print('STATE after =',s2);print('native binary changed=',b1!=b2);print('report=',out)
    return 0 if verdict=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
