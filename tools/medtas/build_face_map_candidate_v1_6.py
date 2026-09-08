from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify,base_id

def canon(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sig(part,f):
    d={'part':base_id(part),'body':f.get('body'),'surface_type':f.get('surface_type'),'area_m2':f.get('area_m2'),'box_m':f.get('box_m'),'normal':f.get('normal'),'edge_count':f.get('edge_count')}
    return hashlib.sha256(canon(d).encode()).hexdigest()
def fl(x):
    try:return float(x)
    except:return None
def axis_from_faces(fs):
    mins=[None]*3;maxs=[None]*3
    for f in fs:
        b=f.get('box_m') or []
        if len(b)!=6:continue
        vals=[fl(v) for v in b]
        if any(v is None for v in vals):continue
        for i in range(3):mins[i]=vals[i] if mins[i] is None else min(mins[i],vals[i]);maxs[i]=vals[i+3] if maxs[i] is None else max(maxs[i],vals[i+3])
    spans=[(maxs[i]-mins[i]) if mins[i] is not None else -1 for i in range(3)]
    return (max(range(3),key=lambda i:spans[i]) if max(spans)>=0 else None),spans
def centroid(f,axis):
    b=f.get('box_m') or []
    try:return (float(b[axis])+float(b[axis+3]))/2 if axis is not None and len(b)==6 else None
    except:return None
def nalign(f,axis):
    n=f.get('normal') or []
    try:return abs(float(n[axis])) if axis is not None and len(n)>=3 else None
    except:return None

def flatten_sigs(parts):return {r['face_signature'] for p in parts.values() for r in p.get('faces',[])}
def map_sigs(m):
    out=[]
    for k,v in (m or {}).items():
        if isinstance(v,list):out += [x.get('face_signature') if isinstance(x,dict) else x for x in v]
        elif isinstance(v,dict):
            for vv in v.values():
                if isinstance(vv,list):out += [x.get('face_signature') if isinstance(x,dict) else x for x in vv]
                elif isinstance(vv,dict):out.append(vv.get('face_signature'))
                elif isinstance(vv,str):out.append(vv)
        elif isinstance(v,str):out.append(v)
    return [x for x in out if x]
def complete(m):
    return len((m or {}).get('FIXED_INTERFACE_FACE',[]))==1 and len((m or {}).get('SERVICE_FORCE_FACE',[]))==1 and len((m or {}).get('PRESSURE_FACES',[]))==5 and len(((m or {}).get('CONTACT_PAIR') or {}).get('A',[]))>=1 and len(((m or {}).get('CONTACT_PAIR') or {}).get('B',[]))>=1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();structp=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json';out=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json'
    if not structp.exists():print('ERROR structural model missing',file=sys.stderr);return 61
    st=load(structp);faces=st.get('geometry',{}).get('face_candidates',{}) or {};old=load(out) if out.exists() else {};outparts={};review=[]
    for part,fs in faces.items():
        axis,spans=axis_from_faces(fs);rows=[]
        for f in fs:
            r=dict(f);r['face_signature']=sig(part,f);r['major_axis']=axis;r['centroid_on_major_axis_m']=centroid(f,axis);r['normal_alignment_to_major_axis']=nalign(f,axis);r['candidate_roles']=[]
            if f.get('surface_type')=='plane' and (r['normal_alignment_to_major_axis'] or 0)>=0.98:r['candidate_roles']=['FIXED_INTERFACE_FACE','SERVICE_FORCE_FACE','AXIAL_CONTACT_FACE']
            elif f.get('surface_type') in ('cylinder','cone'):r['candidate_roles']=['PRESSURE_FACE','CONTACT_FACE']
            else:r['candidate_roles']=['PRESSURE_FACE','CONTACT_FACE','OTHER']
            rows.append(r)
        rows.sort(key=lambda r:(str(r.get('surface_type')),r.get('centroid_on_major_axis_m') if r.get('centroid_on_major_axis_m') is not None else 1e99,str(r.get('face_signature'))))
        outparts[base_id(part)]={'major_axis_index':axis,'estimated_spans_m':spans,'faces':rows}
        if not rows:review.append('FACE-MAP-NO-FACES:'+base_id(part))
    valid=flatten_sigs(outparts);confirmed=old.get('confirmed_role_map',{}) if old.get('confirmed_role_map') else {}
    lost=[s for s in map_sigs(confirmed) if s not in valid]
    if lost:confirmed={};review.append('FACE-MAP-STALE-001: previously confirmed face signature(s) disappeared after CAD change')
    is_complete=complete(confirmed)
    if not is_complete:review += ['FACE-MAP-ROLE-001: bind exact Fixed-1 face','FACE-MAP-ROLE-002: bind exact Force-1 face','FACE-MAP-ROLE-003: bind exact five Pressure-1 faces','FACE-MAP-ROLE-004: bind both sides of the no-penetration contact pair']
    payload={'schema':'k01.structural_face_map.p006.v1_6','method':'persistent geometric face signatures; runtime face IDs are non-authoritative','required_roles':{'FIXED_INTERFACE_FACE':1,'SERVICE_FORCE_FACE':1,'PRESSURE_FACES':5,'CONTACT_PAIR':{'A':1,'B':1}},'parts':outparts,'confirmed_role_map':confirmed,'status':'PASS' if is_complete else 'REVIEW_REQUIRED','limitations':review,'persistence':'Confirmed role bindings survive pipeline rebuilds while every stored signature still exists. Missing signatures reopen the node.'}
    dump(out,payload);register_build(root,'K01.STRUCT.FACE_MAP.P006',{'tool':'build_face_map_candidate_v1_6.py'},limitations=review)
    register_verify(root,'K01.STRUCT.FACE_MAP.P006','PASS' if is_complete else 'HOLD',metrics={'parts':len(outparts),'faces':sum(len(x['faces']) for x in outparts.values()),'confirmed_roles_complete':is_complete,'lost_signatures':len(lost)},limitations=review,notes='Exact study selections are bound by 10_BIND_STRUCTURAL_FACE_ROLES.cmd. Candidate generation never invents a role.')
    print('K01.STRUCT.FACE_MAP.P006',payload['status']);print(out);return 0
if __name__=='__main__':raise SystemExit(main())
