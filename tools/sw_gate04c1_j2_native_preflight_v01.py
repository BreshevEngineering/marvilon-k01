"""
K01 Gate04C1 — J2 NATIVE PREFLIGHT / READ-ONLY
==============================================
Audits CURRENT STABLE native CAD before Gate04C write operations.
No SOLIDWORKS document is saved or modified.
"""
from __future__ import annotations
import json, os, traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    import pythoncom
    from win32com.client import dynamic
except Exception as exc:
    raise SystemExit("pywin32 is required: py -m pip install pywin32") from exc

SW_DOC_PART=1; SW_DOC_ASM=2; SW_OPEN_SILENT=1; SW_BODY_SOLID=0
STABLE_ASM=r"D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM"
P003_STABLE=r"D:\Marvilon\K01\cad\parts\K01-P-003_Cartridge_Body.SLDPRT"
P007_STABLE=r"D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT"
P003_TOKEN="K01-P-003_Cartridge_Body"; P007_TOKEN="K01-P-007_Hermetic_Magnetic_Can"
EXPECTED={
 "P003_material":"AISI 316L / EN 1.4404","P007_material":"AISI 316L / EN 1.4404",
 "P003_rear_OD_mm_current":16.0,"P003_rear_zone_L_mm_current":5.0,
 "P007_OAL_mm":35.0,"P007_root_ID_mm":14.1,"P007_thin_OD_mm":10.0,
 "P007_thin_ID_mm":9.4,"P007_thin_wall_mm":0.3,
 "J2_target_flange_OD_mm":36.0,"J2_target_PCD_mm":28.0,
 "J2_target_M3_clearance_D_mm":3.4,"J2_target_pilot_nominal_D_mm":14.10,
 "J2_target_pilot_male_L_mm":1.50,"J2_target_pilot_female_depth_mm":1.70,
 "J2_target_seal_size":"16x1.5 mm","J2_target_gland_ID_mm":16.00,
 "J2_target_gland_width_mm":2.10,"J2_target_gland_depth_mm":1.10,
 "J2_target_gland_OD_nom_mm":20.20,"J2_target_gland_OD_design_max_mm":20.60,
}
TOL_D=0.03

def utc_now(): return datetime.now(timezone.utc).isoformat()
def norm(p): return os.path.normcase(os.path.abspath(p))

def find_repo_root():
    here=Path(__file__).resolve()
    for p in [here.parent]+list(here.parents):
        if (p/'master').exists() and ((p/'reports').exists() or (p/'control').exists()): return p
    return here.parent

def out_path():
    root=find_repo_root(); p=root/'reports'/'cad'/'current'
    try:
        p.mkdir(parents=True,exist_ok=True); return p/'K01_GATE04C1_J2_NATIVE_PREFLIGHT.json'
    except Exception:
        return Path(__file__).resolve().with_name('K01_GATE04C1_J2_NATIVE_PREFLIGHT.json')

def connect_sw():
    pythoncom.CoInitialize(); sw=dynamic.Dispatch('SldWorks.Application'); sw.Visible=True
    try: sw.UserControl=True
    except Exception: pass
    return sw

def sw_revision(sw):
    try: return str(sw.RevisionNumber())
    except Exception: return 'UNKNOWN'

def open_or_activate_asm(sw):
    active=sw.ActiveDoc
    if active is not None:
        try:
            if int(active.GetType())==SW_DOC_ASM and norm(active.GetPathName())==norm(STABLE_ASM):
                return active,'already_active'
        except Exception: pass
    if not os.path.exists(STABLE_ASM): raise RuntimeError('Stable assembly not found: '+STABLE_ASM)
    try:
        title=os.path.basename(STABLE_ASM); act=sw.ActivateDoc3(title,True,0,0)
        if act is not None and norm(act.GetPathName())==norm(STABLE_ASM): return act,'activated_existing'
    except Exception: pass
    try: doc=sw.OpenDoc6(STABLE_ASM,SW_DOC_ASM,SW_OPEN_SILENT,'',0,0)
    except Exception: doc=sw.OpenDoc(STABLE_ASM,SW_DOC_ASM)
    if doc is None: raise RuntimeError('Could not open stable assembly: '+STABLE_ASM)
    return doc,'opened_stable'

def walk_components(root):
    q=[]
    try:
        ch=root.GetChildren(); q.extend(list(ch) if ch else [])
    except Exception: pass
    while q:
        c=q.pop(0); yield c
        try:
            ch=c.GetChildren(); q.extend(list(ch) if ch else [])
        except Exception: pass

def comp_name(c):
    try: return str(c.Name2)
    except Exception: return ''
def comp_path(c):
    try: return str(c.GetPathName())
    except Exception: return ''

def find_component(asm,token,expected_path):
    root=asm.GetRootComponent3(True)
    if root is None: raise RuntimeError('Assembly root component unavailable')
    exact=[]; token_hits=[]
    for c in walk_components(root):
        p=comp_path(c); n=comp_name(c)
        if p and norm(p)==norm(expected_path): exact.append(c)
        if token.lower() in n.lower() or (p and token.lower() in os.path.basename(p).lower()): token_hits.append(c)
    hits=exact or token_hits
    if not hits: raise RuntimeError('Component not found: '+token)
    for c in hits:
        try:
            if c.GetModelDoc2() is not None: return c
        except Exception: pass
    return hits[0]

def safe_arr(v):
    if v is None: return None
    try: return [float(x) for x in list(v)]
    except Exception: return None

def surface_info(face):
    d={"area_mm2":None,"kind":"other","params_raw_SI":None,"plane_normal":None,
       "plane_point_mm":None,"cyl_axis_origin_mm":None,"cyl_axis_direction":None,"diameter_mm":None}
    try: d['area_mm2']=float(face.GetArea())*1e6
    except Exception: pass
    try: s=face.GetSurface()
    except Exception: s=None
    if s is None: return d
    try:
        if bool(s.IsPlane()):
            d['kind']='plane'; a=safe_arr(s.PlaneParams); d['params_raw_SI']=a
            if a and len(a)>=6:
                d['plane_normal']=a[:3]; d['plane_point_mm']=[1000*q for q in a[3:6]]
            return d
    except Exception: pass
    try:
        if bool(s.IsCylinder()):
            d['kind']='cylinder'; a=safe_arr(s.CylinderParams); d['params_raw_SI']=a
            if a and len(a)>=7:
                d['cyl_axis_origin_mm']=[1000*q for q in a[:3]]; d['cyl_axis_direction']=a[3:6]
                d['diameter_mm']=2000*float(a[6])
            return d
    except Exception: pass
    try:
        if bool(s.IsCone()): d['kind']='cone'; d['params_raw_SI']=safe_arr(s.ConeParams); return d
    except Exception: pass
    try:
        if bool(s.IsSphere()): d['kind']='sphere'; d['params_raw_SI']=safe_arr(s.SphereParams); return d
    except Exception: pass
    return d

def body_audit(model):
    out=[]
    try:
        bodies=model.GetBodies2(SW_BODY_SOLID,True); bodies=list(bodies) if bodies else []
    except Exception: bodies=[]
    for bi,body in enumerate(bodies):
        b={'index':bi,'bbox_mm':None,'faces':[]}
        try:
            bb=safe_arr(body.GetBodyBox()); b['bbox_mm']=[1000*q for q in bb[:6]] if bb and len(bb)>=6 else None
        except Exception: pass
        try:
            faces=body.GetFaces(); faces=list(faces) if faces else []
        except Exception: faces=[]
        for fi,face in enumerate(faces):
            x={'index':fi}; x.update(surface_info(face)); b['faces'].append(x)
        out.append(b)
    return out

def feature_tree(model):
    rows=[]
    def add_feature(f,depth,parent):
        while f is not None:
            try: name=str(f.Name)
            except Exception: name=''
            try: typ=str(f.GetTypeName2())
            except Exception: typ=''
            try: sup=bool(f.IsSuppressed())
            except Exception: sup=None
            rows.append({'depth':depth,'name':name,'type':typ,'parent':parent,'suppressed':sup})
            try: sf=f.GetFirstSubFeature()
            except Exception: sf=None
            if sf is not None: add_feature(sf,depth+1,name)
            try: f=f.GetNextFeature()
            except Exception: f=None
    try: first=model.FirstFeature()
    except Exception: first=None
    add_feature(first,0,None); return rows

def custom_props(model):
    keys=['PartNo','Description','Material','MaterialSpec','Revision','Status','Process','Note']; out={}
    try: mgr=model.Extension.CustomPropertyManager('')
    except Exception: return out
    for k in keys:
        val=''
        try:
            r=mgr.Get6(k,False,'','',False,False)
            if isinstance(r,tuple):
                ss=[x for x in r if isinstance(x,str)]; val=ss[-1] if ss else ''
            elif r is not None: val=str(r)
        except Exception:
            try:
                r=mgr.Get2(k,'','')
                if isinstance(r,tuple):
                    ss=[x for x in r if isinstance(x,str)]; val=ss[-1] if ss else ''
                elif r is not None: val=str(r)
            except Exception: pass
        out[k]=val
    return out

def material_name(model):
    for cfg in ('','Default'):
        try:
            r=model.GetMaterialPropertyName2(cfg,'')
            if isinstance(r,tuple):
                ss=[x for x in r if isinstance(x,str) and x.strip()]
                if ss: return ss[-1]
            elif isinstance(r,str) and r.strip(): return r
        except Exception: pass
    return ''

def component_transform(c):
    try:
        t=c.Transform2; return safe_arr(t.ArrayData) if t is not None else None
    except Exception: return None

def component_box(c):
    try:
        bb=safe_arr(c.GetBox()); return [1000*q for q in bb[:6]] if bb and len(bb)>=6 else None
    except Exception: return None

def model_summary(c,tag):
    model=c.GetModelDoc2()
    if model is None: raise RuntimeError(tag+' unresolved/model unavailable')
    try: mt=int(model.GetType())
    except Exception: mt=None
    return {'tag':tag,'component_name':comp_name(c),'component_path':comp_path(c),'model_title':str(model.GetTitle()),
            'model_type':mt,'component_transform_raw':component_transform(c),'component_box_assembly_mm':component_box(c),
            'custom_properties':custom_props(model),'solidworks_material_name_diagnostic':material_name(model),
            'feature_tree':feature_tree(model),'bodies':body_audit(model)}

def all_faces(part):
    out=[]
    for b in part['bodies']:
        for f in b['faces']:
            x=dict(f); x['body_index']=b['index']; out.append(x)
    return out

def axial_plane_faces(part):
    out=[]
    for f in all_faces(part):
        if f.get('kind')!='plane': continue
        n=f.get('plane_normal'); p=f.get('plane_point_mm')
        if n and p and abs(abs(n[0])-1)<1e-4 and abs(n[1])<1e-4 and abs(n[2])<1e-4: out.append(f)
    out.sort(key=lambda r:r['plane_point_mm'][0]); return out

def axial_cylinders(part):
    out=[]
    for f in all_faces(part):
        if f.get('kind')!='cylinder': continue
        a=f.get('cyl_axis_direction')
        if a and abs(abs(a[0])-1)<1e-4 and abs(a[1])<1e-4 and abs(a[2])<1e-4: out.append(f)
    out.sort(key=lambda r:(r.get('diameter_mm') or 0,-(r.get('area_mm2') or 0))); return out

def detect(p3,p7):
    d={'P003':{},'P007':{},'J2_write_readiness':{}}
    p3p=axial_plane_faces(p3); p7p=axial_plane_faces(p7); p3c=axial_cylinders(p3); p7c=axial_cylinders(p7)
    if p3p:
        d['P003']['axial_plane_x_mm']=[f['plane_point_mm'][0] for f in p3p]; d['P003']['rear_plane_candidate']=p3p[-1]
    if p7p:
        d['P007']['axial_plane_x_mm']=[f['plane_point_mm'][0] for f in p7p]; d['P007']['front_plane_candidate']=p7p[0]; d['P007']['rear_plane_candidate']=p7p[-1]
        d['P007']['plane_span_mm']=p7p[-1]['plane_point_mm'][0]-p7p[0]['plane_point_mm'][0]
    def near(cyls,target): return [f for f in cyls if f.get('diameter_mm') is not None and abs(f['diameter_mm']-target)<=TOL_D]
    d['P003']['cylinders_D16']=near(p3c,16.0); d['P007']['cylinders_D14p1']=near(p7c,14.1)
    d['P007']['cylinders_D10']=near(p7c,10.0); d['P007']['cylinders_D9p4']=near(p7c,9.4)
    def interesting(part):
        rr=[]
        for f in part['feature_tree']:
            typ=(f.get('type') or ''); name=(f.get('name') or '')
            if any(k in typ.lower() for k in ('boss','extrusion','cut','hole','pattern','revolve','fillet','chamfer','sketch','refplane','refaxis')) or any(k in name.upper() for k in ('J1','J2','P007','P003','GATE03','DATUM')): rr.append(f)
        return rr
    d['P003']['interesting_features']=interesting(p3); d['P007']['interesting_features']=interesting(p7)
    checks=[
      {'check':'P003 stable rear Ø16 exists','pass':len(d['P003']['cylinders_D16'])>=1,'observed_count':len(d['P003']['cylinders_D16'])},
      {'check':'P007 stable Ø14.10 root exists','pass':len(d['P007']['cylinders_D14p1'])>=1,'observed_count':len(d['P007']['cylinders_D14p1'])},
    ]
    oal=d['P007'].get('plane_span_mm')
    checks.append({'check':'P007 axial plane span approximately 35 mm','pass':oal is not None and abs(oal-35.0)<=0.10,'observed_mm':oal,'note':'Diagnostic; BREP/body data is also recorded.'})
    d['J2_write_readiness']['checks']=checks
    d['J2_write_readiness']['status']='PASS_PREFLIGHT' if all(x['pass'] for x in checks) else 'HOLD_REVIEW_REPORT'
    d['J2_write_readiness']['planned_native_operations_after_review']=[
      'P003: enlarge existing rear Ø16 x 5 mm zone to Ø36 without changing rear station/OAL.',
      'P003: create Ø14.10 g6 x 1.50 male pilot using actual native topology.',
      'P003: create axial O-ring gland ID16.00, width2.10, depth1.10.',
      'P003: create one M3 tapped seed at PCD28 + native 3x120 circular pattern.',
      'P007: create Ø36 x 3.00 front flange inside existing L35 envelope.',
      'P007: preserve/use existing Ø14.10 root as H7 locating bore if topology permits.',
      'P007: create one Ø3.40 THRU seed at PCD28 + native 3x120 circular pattern.',
      'Build candidate-only verification assembly; stable P003/P007 remain untouched until promotion.'
    ]
    return d

def main():
    report={'schema':'k01_gate04c1_j2_native_preflight_v1','status':'RUNNING','created_utc':utc_now(),'read_only':True,
            'stable_assembly':STABLE_ASM,'expected':EXPECTED}
    sw=connect_sw(); report['solidworks_revision']=sw_revision(sw)
    asm,activation=open_or_activate_asm(sw); report['stable_A001_activation']=activation
    print('[INFO] Stable A001 activation:',activation)
    p3c=find_component(asm,P003_TOKEN,P003_STABLE); p7c=find_component(asm,P007_TOKEN,P007_STABLE)
    report['parts']={'P003':model_summary(p3c,'P003'),'P007':model_summary(p7c,'P007')}
    report['derived']=detect(report['parts']['P003'],report['parts']['P007']); report['status']=report['derived']['J2_write_readiness']['status']
    p=out_path(); p.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('='*92); print('K01 Gate04C1 — J2 NATIVE PREFLIGHT / READ-ONLY'); print('='*92)
    print('SOLIDWORKS:',report['solidworks_revision']); print('P003:',report['parts']['P003']['component_name']); print('P007:',report['parts']['P007']['component_name'])
    d=report['derived']; print('[P003] Ø16 axial cylinders:',len(d['P003'].get('cylinders_D16',[])))
    print('[P007] Ø14.10 axial cylinders:',len(d['P007'].get('cylinders_D14p1',[]))); print('[P007] axial plane span [mm]:',d['P007'].get('plane_span_mm'))
    print('-'*92)
    for c in d['J2_write_readiness']['checks']:
        print(('[PASS] ' if c['pass'] else '[HOLD] ')+c['check'],c.get('observed_mm',c.get('observed_count','')))
    print('-'*92); print('STATUS:',report['status']); print('Report:',str(p)); print('No CAD was modified or saved.')
    return 0 if report['status']=='PASS_PREFLIGHT' else 2

if __name__=='__main__':
    try: raise SystemExit(main())
    except SystemExit: raise
    except Exception as exc:
        print('FAIL: Gate04C1'); traceback.print_exc()
        try:
            p=out_path(); p.write_text(json.dumps({'schema':'k01_gate04c1_j2_native_preflight_v1','status':'FAIL_EXCEPTION','created_utc':utc_now(),'read_only':True,'error':repr(exc),'traceback':traceback.format_exc()},indent=2,ensure_ascii=False),encoding='utf-8')
            print('Failure report:',str(p))
        except Exception: pass
        raise
