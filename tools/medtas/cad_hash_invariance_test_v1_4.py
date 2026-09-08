from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from canonical_hash_v1_4 import canonical_json_hash

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha_file(p):
    h=hashlib.sha256();
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def assembly_from_raw(root):
    raw=load(root/'reports/medtas/cad/current/K01_A001_SEMANTIC_RAW_API_v1_4.json')
    return Path(raw['assembly']['native_path'])
def run_export(root):
    cp=subprocess.run([sys.executable,str(root/'tools/medtas/run_cad_sem_a001.py'),'--repo-root',str(root)])
    if cp.returncode: raise RuntimeError('CAD semantic export failed rc='+str(cp.returncode))
    c=load(root/'reports/medtas/cad/current/K01_CAD_SEM_A001.json')
    d=load(root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json')['nodes']['K01.CAD.SEM.A001']
    a=assembly_from_raw(root)
    return canonical_json_hash(c), d['state_hash'], sha_file(a) if a.exists() else None, a

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    print('K01 canonical hash invariance test — NO CAD writes are performed by this script.')
    h1,s1,b1,asm=run_export(root)
    print('Baseline canonical payload hash:',h1);print('Baseline MEDTAS STATE_HASH:',s1);print('Baseline native binary SHA256:',b1);print('Assembly:',asm)
    print('\nIn SOLIDWORKS: do NOT change geometry/tolerances/mates. Press Ctrl+S twice, then return here.')
    input('Press ENTER after the two saves... ')
    h2,s2,b2,_=run_export(root)
    verdict='PASS' if (h1==h2 and s1==s2) else 'HOLD'
    report={'schema':'k01.canonical_hash_invariance.v1_4','verdict':verdict,'canonical_payload_hash_before':h1,'canonical_payload_hash_after':h2,'state_hash_before':s1,'state_hash_after':s2,'binary_sha256_before':b1,'binary_sha256_after':b2,'binary_changed':b1!=b2,'rule':'PASS requires both canonical payload hash and MEDTAS STATE_HASH equality. Native SLDASM binary hash is diagnostic only and never controls engineering freshness.'}
    out=root/'reports/medtas/tests/K01_CAD_CANONICAL_HASH_INVARIANCE_CURRENT.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('\n'+verdict,'semantic hash invariance')
    print('canonical before=',h1);print('canonical after =',h2);print('STATE before=',s1);print('STATE after =',s2);print('native binary changed=',b1!=b2);print('report=',out)
    return 0 if verdict=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
