from __future__ import annotations
import json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/medtas'))
import medtas_state_engine_v1_1 as eng

def node(nid,kind='artifact',mode='derived',inputs=None,out=None,payload=None,verification=False):
    return {'schema_version':'MEDTAS-NODE-1.1','node_id':nid,'project':'TEST','kind':kind,'title':nid,'producer':{'mode':mode},'lifecycle':{'criticality':'advisory','superseded_by':None},'contract':{'inputs':inputs or [],'semantic_payload':payload or {},'toolchain':[],'outputs':([] if out is None else [{'output_id':'o','path':out,'required':True,'hash_mode':'file'}]),'verification_policy':'VP' if verification else None,'hash_policy':{'algorithm':'sha256','canonicalization':'TEST','include_toolchain_identity':True,'float_policy':'x'}}}

def edge(up,consume='state'): return {'node_id':up,'role':'up','consume':consume,'required':True}
def check(got,want,label):
    if got!=want: raise AssertionError(f'{label}: got {got}, want {want}')

def main():
  with tempfile.TemporaryDirectory() as td:
    r=Path(td);(r/'out').mkdir();(r/'out/a.txt').write_text('A');(r/'out/v.txt').write_text('V')
    g={'schema_version':'X','project':'TEST','nodes':[node('S',kind='parameter_set',mode='source',payload={'x':1}),node('A',inputs=[edge('S')],out='out/a.txt'),node('V',kind='verification',inputs=[edge('A','both')],out='out/v.txt',verification=True)]}
    d0=eng.evaluate_graph(g,r,{},{});check(d0['S']['state'],'PASS','source');check(d0['A']['state'],'MISSING','missing build');check(d0['V']['state'],'BLOCKED','blocked downstream')
    # Fresh A build.
    brA={'node_id':'A','built_state_hash':d0['A']['state_hash'],'artifact_hash':d0['A']['artifact_hash']};d1=eng.evaluate_graph(g,r,{'A':brA},{});check(d1['A']['state'],'PASS','fresh build');check(d1['V']['state'],'MISSING','verification artifact no build')
    # Drift: bytes change with same state.
    (r/'out/a.txt').write_text('A2');d2=eng.evaluate_graph(g,r,{'A':brA},{});check(d2['A']['state'],'DRIFT','artifact drift')
    # Restore artifact and change upstream semantics => STALE.
    (r/'out/a.txt').write_text('A');g2=json.loads(json.dumps(g));g2['nodes'][0]['contract']['semantic_payload']={'x':2};d3=eng.evaluate_graph(g2,r,{'A':brA},{});check(d3['A']['state'],'STALE','upstream semantic stale')
    # Verification record bound to wrong hash => FRESH_UNVERIFIED.
    d4a=eng.evaluate_graph(g,r,{'A':brA},{})
    brV={'node_id':'V','built_state_hash':d4a['V']['state_hash'],'artifact_hash':d4a['V']['artifact_hash']}
    d4b=eng.evaluate_graph(g,r,{'A':brA,'V':brV},{'V':{'node_id':'V','verified_state_hash':'bad','verified_artifact_hash':'bad','verdict':'PASS'}});check(d4b['V']['state'],'FRESH_UNVERIFIED','old verification hashes')
    # Current verification PASS.
    vr={'node_id':'V','verified_state_hash':d4b['V']['state_hash'],'verified_artifact_hash':d4b['V']['artifact_hash'],'verdict':'PASS'}
    d5=eng.evaluate_graph(g,r,{'A':brA,'V':brV},{'V':vr});check(d5['V']['state'],'PASS','current verification')
  print('PASS MEDTAS state reducer fixtures: missing/blocking, drift, stale propagation, verification freshness')
  return 0
if __name__=='__main__':raise SystemExit(main())
