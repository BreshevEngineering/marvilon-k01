#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import medtas_state_engine_v1_1 as eng

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,o): p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sig(part,f):
    d={'part':part,'body':f.get('body'),'surface_type':f.get('surface_type'),'area_m2':f.get('area_m2'),'box_m':f.get('box_m'),'normal':f.get('normal'),'edge_count':f.get('edge_count')}
    return hashlib.sha256(canon(d).encode()).hexdigest()
def fl(x):
    try:return float(x)
    except:return None

def axis_from_faces(fs):
    mins=[None,None,None]; maxs=[None,None,None]
    for f in fs:
        b=f.get('box_m') or []
        if len(b)!=6: continue
        vals=[fl(v) for v in b]
        if any(v is None for v in vals): continue
        for i in range(3):
            mins[i]=vals[i] if mins[i] is None else min(mins[i],vals[i])
            maxs[i]=vals[i+3] if maxs[i] is None else max(maxs[i],vals[i+3])
    spans=[(maxs[i]-mins[i]) if mins[i] is not None else -1 for i in range(3)]
    return max(range(3),key=lambda i:spans[i]) if max(spans)>=0 else None, spans

def centroid_axis(f,axis):
    b=f.get('box_m') or []
    if axis is None or len(b)!=6:return None
    try:return (float(b[axis])+float(b[axis+3]))/2
    except:return None

def normal_axis(f,axis):
    n=f.get('normal') or []
    if axis is None or len(n)<3:return None
    try:return abs(float(n[axis]))
    except:return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    structp=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json'
    if not structp.exists(): print('ERROR structural model missing',file=sys.stderr); return 61
    st=load(structp); faces=st.get('geometry',{}).get('face_candidates',{}) or {}
    outparts={}; review=[]
    for part,fs in faces.items():
        axis,spans=axis_from_faces(fs)
        rows=[]
        for f in fs:
            r=dict(f); r['face_signature']=sig(part,f); r['major_axis']=axis; r['centroid_on_major_axis_m']=centroid_axis(f,axis); r['normal_alignment_to_major_axis']=normal_axis(f,axis); r['candidate_roles']=[]
            if f.get('surface_type')=='plane' and (r['normal_alignment_to_major_axis'] or 0)>=0.98:
                r['candidate_roles']=['FIXED_INTERFACE_FACE','SERVICE_FORCE_FACE','AXIAL_CONTACT_FACE']
            elif f.get('surface_type') in ('cylinder','cone'):
                r['candidate_roles']=['PRESSURE_FACE','CONTACT_FACE']
            else:
                r['candidate_roles']=['PRESSURE_FACE','CONTACT_FACE','OTHER']
            rows.append(r)
        rows.sort(key=lambda r:(str(r.get('surface_type')),r.get('centroid_on_major_axis_m') if r.get('centroid_on_major_axis_m') is not None else 1e99,str(r.get('face_signature'))))
        axial=[r for r in rows if 'FIXED_INTERFACE_FACE' in r['candidate_roles'] and r.get('centroid_on_major_axis_m') is not None]
        suggestions=[]
        if axial:
            suggestions.append({'role_hint':'AXIAL_END_MIN','face_signature':min(axial,key=lambda r:r['centroid_on_major_axis_m'])['face_signature'],'status':'REVIEW_REQUIRED'})
            suggestions.append({'role_hint':'AXIAL_END_MAX','face_signature':max(axial,key=lambda r:r['centroid_on_major_axis_m'])['face_signature'],'status':'REVIEW_REQUIRED'})
        outparts[part]={'major_axis_index':axis,'estimated_spans_m':spans,'faces':rows,'suggestions':suggestions}
        if not rows: review.append('FACE-MAP-NO-FACES:'+part)
    required={'FIXED_INTERFACE_FACE':1,'SERVICE_FORCE_FACE':1,'PRESSURE_FACES':5,'CONTACT_PAIR':'surface-to-surface'}
    review += ['FACE-MAP-ROLE-001: exact FIXED_INTERFACE_FACE must be confirmed against the SolidWorks study selection',
               'FACE-MAP-ROLE-002: exact SERVICE_FORCE_FACE must be confirmed against the SolidWorks study selection',
               'FACE-MAP-ROLE-003: the five PRESSURE_FACES must be confirmed against the SolidWorks study selection',
               'FACE-MAP-ROLE-004: CONTACT_PAIR must be mapped to persistent surface signatures before CCX input generation']
    payload={'schema':'k01.structural_face_map.p006.v1','method':'topology-independent geometric face signatures; runtime face indices are non-authoritative','required_roles':required,'parts':outparts,'confirmed_role_map':{},'status':'REVIEW_REQUIRED','limitations':review,'next_action':'Bind exact SolidWorks study selections to face_signature values, then verify this node PASS before generating CalculiX input.'}
    out=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json'; dump(out,payload)
    # register build against current graph state
    gp=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_5.json'
    if not gp.exists(): gp=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_4.json'
    if not gp.exists(): gp=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_3.json'
    graph=load(gp)
    records=eng.load_record_store(root/'reports/medtas/records/current'); verifs=eng.load_record_store(root/'reports/medtas/verifications/current')
    d=eng.evaluate_graph(graph,root,records,verifs)['K01.STRUCT.FACE_MAP.P006']
    if not d.get('artifact_hash'): print('ERROR face-map artifact hash missing',file=sys.stderr); return 62
    br={'schema':'medtas.build_record.v1','node_id':'K01.STRUCT.FACE_MAP.P006','built_state_hash':d['state_hash'],'artifact_hash':d['artifact_hash'],'producer':{'tool':'build_face_map_candidate_v1_3.py'},'limitations':review}
    dump(root/'reports/medtas/records/current/K01.STRUCT.FACE_MAP.P006.build.json',br)
    # re-evaluate with build record, then create fail-closed verification record bound to exact hashes
    records=eng.load_record_store(root/'reports/medtas/records/current'); d=eng.evaluate_graph(graph,root,records,verifs)['K01.STRUCT.FACE_MAP.P006']
    vr={'schema':'medtas.verification_record.v1','node_id':'K01.STRUCT.FACE_MAP.P006','verified_state_hash':d['state_hash'],'verified_artifact_hash':d['artifact_hash'],'verdict':'HOLD','metrics':{'parts':len(outparts),'faces':sum(len(x['faces']) for x in outparts.values()),'confirmed_roles':0},'limitations':review,'notes':'Candidate geometric signatures are available, but exact SW study selections are not yet bound. This intentionally blocks CalculiX.'}
    dump(root/'reports/medtas/verifications/current/K01.STRUCT.FACE_MAP.P006.verify.json',vr)
    print('K01.STRUCT.FACE_MAP.P006 candidate generated: HOLD until exact role binding is confirmed')
    print(out)
    return 0
if __name__=='__main__': raise SystemExit(main())
