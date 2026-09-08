from __future__ import annotations
import argparse,math,sys,time
from pathlib import Path
from medtas_v16_common import load,dump,base_id,register_build,register_verify

def seq(x):
    if x is None:return []
    try:return list(x)
    except Exception:return []
def surface_type(s):
    for name,label in [('IsPlane','plane'),('IsCylinder','cylinder'),('IsCone','cone'),('IsSphere','sphere'),('IsTorus','torus')]:
        try:
            if bool(getattr(s,name)()):return label
        except Exception:pass
    return 'other'
def selected_descriptor(face,comp):
    part=base_id(comp.GetPathName() if comp else '')
    body=''
    try:body=face.GetBody().Name
    except Exception:pass
    try:area=float(face.GetArea())
    except Exception:area=None
    try:box=[float(x) for x in seq(face.GetBox())]
    except Exception:box=[]
    try:normal=[float(x) for x in seq(face.Normal)]
    except Exception:normal=[]
    try:ec=len(seq(face.GetEdges()))
    except Exception:ec=None
    try:st=surface_type(face.GetSurface())
    except Exception:st='unknown'
    return {'part':part,'body':body,'surface_type':st,'area_m2':area,'box_m':box,'normal':normal,'edge_count':ec}
def err(desc,row):
    if desc['part'] and base_id(row.get('_part'))!=desc['part']:return 1e9
    if desc['surface_type']!='unknown' and row.get('surface_type')!=desc['surface_type']:return 1e8
    score=0.0
    try:score += abs(float(row.get('area_m2'))-desc['area_m2'])/max(abs(desc['area_m2']),1e-12)
    except Exception:score+=1
    rb=row.get('box_m') or [];db=desc.get('box_m') or []
    if len(rb)==6 and len(db)==6:score += max(abs(float(rb[i])-float(db[i])) for i in range(6))/1e-6
    else:score+=1
    if row.get('edge_count') is not None and desc.get('edge_count') is not None and int(row['edge_count'])!=int(desc['edge_count']):score+=100
    return score
def match(desc,rows):
    cand=sorted(((err(desc,r),r) for r in rows),key=lambda x:x[0])
    if not cand or cand[0][0]>0.05:raise RuntimeError('Selected face does not match a persistent CAD signature closely enough; best score='+str(cand[0][0] if cand else None))
    if len(cand)>1 and abs(cand[1][0]-cand[0][0])<1e-8:raise RuntimeError('Selected face match is ambiguous')
    return cand[0][1]
def read_selected(sw,rows,expected,label):
    model=sw.ActiveDoc
    if model is None:raise RuntimeError('No active SOLIDWORKS document')
    input(f'In SOLIDWORKS select exactly {expected} face(s) for {label}, then press ENTER here... ')
    sm=model.SelectionManager;count=int(sm.GetSelectedObjectCount2(-1))
    if count!=expected:raise RuntimeError(f'{label}: expected {expected} selected objects, got {count}')
    out=[]
    for i in range(1,count+1):
        face=sm.GetSelectedObject6(i,-1);comp=sm.GetSelectedObjectsComponent4(i,-1)
        if face is None:raise RuntimeError(label+': selection '+str(i)+' is not a face')
        d=selected_descriptor(face,comp);r=match(d,rows);out.append({'part_no':base_id(r.get('_part')),'face_signature':r['face_signature'],'surface_type':r.get('surface_type'),'area_m2':r.get('area_m2')})
    try:model.ClearSelection2(True)
    except Exception:pass
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();p=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json'
    if not p.exists():raise SystemExit('ERROR: face map candidate missing; run pipeline first')
    fm=load(p);rows=[]
    for part,x in fm.get('parts',{}).items():
        for r in x.get('faces',[]):q=dict(r);q['_part']=part;rows.append(q)
    try:
        import win32com.client
        sw=win32com.client.GetActiveObject('SldWorks.Application')
        print('Attached to SOLIDWORKS. This command changes selection only; it does not write CAD geometry.')
        fixed=read_selected(sw,rows,1,'FIXED_INTERFACE_FACE / SolidWorks Fixed-1')
        force=read_selected(sw,rows,1,'SERVICE_FORCE_FACE / SolidWorks Force-1')
        pressure=read_selected(sw,rows,5,'PRESSURE_FACES / SolidWorks Pressure-1')
        contact=read_selected(sw,rows,2,'CONTACT_PAIR / choose one face from each contacting side')
    except Exception as e:
        print('ERROR:',e,file=sys.stderr);return 2
    fm['confirmed_role_map']={'FIXED_INTERFACE_FACE':fixed,'SERVICE_FORCE_FACE':force,'PRESSURE_FACES':pressure,'CONTACT_PAIR':{'A':[contact[0]],'B':[contact[1]]}}
    fm['status']='PASS';fm['limitations']=[];fm['binding_authority']='human-confirmed actual SolidWorks study selections mapped to persistent geometric signatures';dump(p,fm)
    register_build(root,'K01.STRUCT.FACE_MAP.P006',{'tool':'bind_structural_face_roles_v1_6.py','mode':'human-confirmed SolidWorks selection binding'})
    register_verify(root,'K01.STRUCT.FACE_MAP.P006','PASS',metrics={'fixed_faces':1,'force_faces':1,'pressure_faces':5,'contact_sides':2},notes='Role binding is persistent by geometric signature. Rebuild reopens only if a required signature disappears.')
    print('PASS structural face roles bound:',p);return 0
if __name__=='__main__':raise SystemExit(main())
