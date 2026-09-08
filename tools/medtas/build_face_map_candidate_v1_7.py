from __future__ import annotations
import argparse,collections,sys
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify,base_id
from face_identity_v1_7 import signature,semantic_descriptor

def all_faces(parts):
    for part,x in parts.items():
        for f in x.get('faces',[]):yield part,f

def role_entries(m):
    for k,v in (m or {}).items():
        if k=='CONTACT':continue
        if isinstance(v,list):
            for x in v:
                if isinstance(x,dict):yield k,x

def complete(m):
    return len((m or {}).get('FIXED_INTERFACE_FACE',[]))==1 and len((m or {}).get('SERVICE_FORCE_FACE',[]))==1 and len((m or {}).get('PRESSURE_FACES',[]))==5 and ((m or {}).get('CONTACT') or {}).get('mode') in ('GLOBAL_NO_PENETRATION_BODY_PAIR','EXPLICIT_CONTACT_SET')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();sp=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json';out=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json'
    if not sp.exists():print('ERROR structural model missing',file=sys.stderr);return 61
    st=load(sp);faces=st.get('geometry',{}).get('face_candidates',{}) or {};old=load(out) if out.exists() else {};parts={};sig_counts=collections.Counter()
    for part,fs in faces.items():
        rows=[]
        for f in fs:
            r=dict(f);r['face_signature']=signature(part,f);r['semantic_descriptor']=semantic_descriptor(part,f);rows.append(r);sig_counts[r['face_signature']]+=1
        rows.sort(key=lambda x:(x.get('surface_type',''),x.get('face_signature','')));parts[base_id(part)]={'faces':rows}
    ambiguous=sorted(k for k,v in sig_counts.items() if v>1)
    confirmed=old.get('confirmed_role_map',{}) or {};valid={f['face_signature'] for _,f in all_faces(parts)};lost=[];amb_used=[]
    for role,x in role_entries(confirmed):
        s=x.get('face_signature');
        if s not in valid:lost.append(s)
        if s in ambiguous:amb_used.append(s)
    if lost or amb_used:confirmed={}
    limits=[]
    if ambiguous:limits.append(f'FACE-MAP-AMBIG-001: {len(ambiguous)} duplicate semantic face signature(s) exist; any role resolving to one is HOLD')
    if lost:limits.append('FACE-MAP-STALE-001: previously confirmed semantic face(s) disappeared')
    if amb_used:limits.append('FACE-MAP-AMBIG-002: previously confirmed role became ambiguous')
    if not complete(confirmed):limits.append('FACE-MAP-ROLE-001: automatic SolidWorks Simulation study role extraction/confirmation is required')
    payload={'schema':'k01.structural_face_map.p006.v1_7','method':'canonical primitive face descriptors + unique semantic signatures; runtime face IDs are non-authoritative','parts':parts,'signature_ambiguities':ambiguous,'confirmed_role_map':confirmed,'status':'PASS' if complete(confirmed) and not amb_used else 'REVIEW_REQUIRED','limitations':limits,'persistence':'Bindings persist only while every role resolves uniquely to the same semantic face identity. Ambiguity is fail-closed.'}
    dump(out,payload);register_build(root,'K01.STRUCT.FACE_MAP.P006',{'tool':'build_face_map_candidate_v1_7.py'},limitations=limits);register_verify(root,'K01.STRUCT.FACE_MAP.P006','PASS' if payload['status']=='PASS' else 'HOLD',metrics={'faces':sum(len(x['faces']) for x in parts.values()),'ambiguous_signatures':len(ambiguous),'roles_complete':complete(confirmed)},limitations=limits)
    print('K01.STRUCT.FACE_MAP.P006',payload['status'],'ambiguities=',len(ambiguous));return 0
if __name__=='__main__':raise SystemExit(main())
