from __future__ import annotations
import argparse, json, sys, traceback
from pathlib import Path
from datetime import datetime

# This adapter is deliberately independent of generated makepy wrappers. It uses the
# same COM route that already proved viable in earlier K01 Gate01 probes. It is a
# runtime fallback, not a second semantic model: output is normalized by the same
# canonicalizer used for the C# adapter.

def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def logger(path):
    p=Path(path) if path else None
    def log(stage,msg):
        line=f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | PYWIN32:{stage} | {msg}"
        print(line,flush=True)
        if p:
            p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('a',encoding='utf-8') as f: f.write(line+'\n')
    return log

def arr(v):
    if v is None: return []
    if isinstance(v,(tuple,list)): return list(v)
    try: return list(v)
    except Exception: return []

def call(obj,name,*args):
    fn=getattr(obj,name)
    return fn(*args)

def prop(obj,name,default=None):
    try: return getattr(obj,name)
    except Exception: return default

def safe_call(obj,name,*args,default=None):
    try: return call(obj,name,*args)
    except Exception: return default

def suppressed_feature(f):
    try: return bool(call(f,'IsSuppressed'))
    except Exception: return False

def suppressed_component(c):
    try: return int(call(c,'GetSuppression'))==0  # swComponentSuppressed
    except Exception: return False

def feature_dimensions(feat,path,warnings):
    out=[]
    try: dd=call(feat,'GetFirstDisplayDimension')
    except Exception: dd=None
    guard=0
    while dd is not None and guard<500:
        guard+=1
        try:
            dim=call(dd,'GetDimension2',0)
            if dim is not None:
                name=str(prop(dim,'Name','') or '')
                full=str(prop(dim,'FullName','') or (path+'/'+name))
                sv=prop(dim,'SystemValue',None)
                if callable(sv):
                    try: sv=sv()
                    except Exception: sv=None
                try: sv=float(sv) if sv is not None else None
                except Exception: sv=None
                out.append({'name':name,'full_name':full,'system_value_SI':sv})
        except Exception as e: warnings.append('dimension:'+path+':'+str(e))
        try: dd=call(feat,'GetNextDisplayDimension',dd)
        except Exception: dd=None
    return out

def walk_features(first,parent,warnings,depth=0):
    out=[]
    if first is None or depth>16: return out
    f=first; guard=0
    while f is not None and guard<5000:
        guard+=1
        try: name=str(prop(f,'Name','') or '')
        except Exception: name=''
        try: typ=str(call(f,'GetTypeName2') or '')
        except Exception: typ=''
        path=name if not parent else parent+'/'+name
        out.append({'path':path,'name':name,'type':typ,'suppressed':suppressed_feature(f),'dimensions':feature_dimensions(f,path,warnings)})
        try:
            sub=call(f,'GetFirstSubFeature')
            if sub is not None: out.extend(walk_features(sub,path,warnings,depth+1))
        except Exception as e: warnings.append('subfeature:'+path+':'+str(e))
        try: f=call(f,'GetNextFeature') if depth==0 else call(f,'GetNextSubFeature')
        except Exception: f=None
    return out

def read_material(model,config,warnings):
    # Prefer the native PartDoc method when win32com can marshal its out argument;
    # otherwise the canonicalizer still recovers MaterialFolder from the feature tree.
    try:
        r=call(model,'GetMaterialPropertyName2',config or '')
        if isinstance(r,(tuple,list)):
            vals=[str(x or '') for x in r]
            return (vals[0] if vals else ''),(vals[1] if len(vals)>1 else '')
        return str(r or ''),''
    except Exception as e:
        warnings.append('material_api:'+str(e)); return '',''

def surface_type(face,warnings):
    try:
        s=call(face,'IGetSurface')
        for m,n in [('IsPlane','plane'),('IsCylinder','cylinder'),('IsCone','cone'),('IsSphere','sphere'),('IsTorus','torus')]:
            try:
                if call(s,m): return n
            except Exception: pass
        return 'other'
    except Exception as e:
        warnings.append('surface:'+str(e)); return 'unknown'

def face_inventory(model,warnings):
    out=[]
    try: bodies=call(model,'GetBodies2',0,True)  # swSolidBody = 0
    except Exception:
        try: bodies=call(model,'GetBodies2',0,1)
        except Exception as e: warnings.append('bodies:'+str(e)); return out
    for bi,b in enumerate(arr(bodies),1):
        try: bname=str(prop(b,'Name','') or f'BODY_{bi}')
        except Exception: bname=f'BODY_{bi}'
        try: fs=call(b,'GetFaces')
        except Exception as e: warnings.append('faces:'+bname+':'+str(e)); continue
        for fi,f in enumerate(arr(fs),1):
            d={'body':bname,'face_index_runtime':fi}
            try: d['area_m2']=float(call(f,'GetArea'))
            except Exception: d['area_m2']=None
            try: d['box_m']=[float(x) for x in arr(call(f,'GetBox'))]
            except Exception: d['box_m']=[]
            try:
                n=prop(f,'Normal',None)
                if callable(n): n=n()
                d['normal']=[float(x) for x in arr(n)]
            except Exception: d['normal']=[]
            d['surface_type']=surface_type(f,warnings)
            try: d['edge_count']=len(arr(call(f,'GetEdges')))
            except Exception: d['edge_count']=None
            out.append(d)
    return out

def read_document(model,path,config,warnings):
    try: title=str(call(model,'GetTitle') or '')
    except Exception: title=Path(path).name
    mat,db=read_material(model,config,warnings)
    try: first=call(model,'FirstFeature')
    except Exception: first=None
    features=walk_features(first,'',warnings)
    try: bodies=call(model,'GetBodies2',0,True); body_count=len(arr(bodies))
    except Exception: body_count=None
    return {'title':title,'native_path':path,'configuration':config or '','material_name':mat,'material_database':db,'solid_body_count':body_count,'features':features,'faces':face_inventory(model,warnings)}

def find_open_document(sw,path):
    want=str(Path(path)).lower()
    try:
        docs=call(sw,'GetDocuments')
        for d in arr(docs):
            try:
                p=str(call(d,'GetPathName') or '').lower()
                if p==want: return d
            except Exception: pass
    except Exception: pass
    try:
        a=prop(sw,'ActiveDoc',None)
        if a is not None:
            p=str(call(a,'GetPathName') or '').lower()
            if p==want: return a
    except Exception: pass
    return None

def open_assembly(sw,path,warnings):
    m=find_open_document(sw,path)
    if m is not None: return m,True
    attempts=[]
    for name,args in [
        ('OpenDoc6',(path,2,1,'',0,0)),
        ('OpenDoc6',(path,2,0,'',0,0)),
        ('OpenDoc',(path,2)),
    ]:
        try:
            m=call(sw,name,*args)
            if isinstance(m,(tuple,list)): m=m[0] if m else None
            if m is not None: return m,False
        except Exception as e: attempts.append(name+':'+str(e))
    warnings.extend('open_attempt:'+x for x in attempts)
    return None,False

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--assembly',required=True); ap.add_argument('--out',required=True); ap.add_argument('--log'); a=ap.parse_args()
    log=logger(a.log); warnings=[]; stage='BOOT'
    try:
        import pythoncom, win32com.client
        pythoncom.CoInitialize()
        stage='ATTACH'; log(stage,'starting pywin32 semantic extraction v1.5')
        try: sw=win32com.client.GetActiveObject('SldWorks.Application')
        except Exception: sw=win32com.client.Dispatch('SldWorks.Application'); setattr(sw,'Visible',True)
        stage='OPEN_ASSEMBLY'; model,already=open_assembly(sw,a.assembly,warnings)
        if model is None: raise RuntimeError('Cannot obtain target assembly. Open it manually in SOLIDWORKS and retry. '+ '; '.join(warnings[-3:]))
        try: dtype=int(call(model,'GetType'))
        except Exception: dtype=-1
        if dtype!=2: raise RuntimeError('Target document is not assembly, swDocType='+str(dtype))
        log(stage,('using already open' if already else 'opened')+' assembly')
        try: call(model,'ResolveAllLightWeightComponents',True)
        except Exception as e: warnings.append('resolve:'+str(e))
        stage='READ_COMPONENTS'
        cfg=''
        try: cfg=str(prop(prop(model,'ConfigurationManager'),'ActiveConfiguration').Name)
        except Exception: pass
        try: comps=call(model,'GetComponents',False)
        except Exception as e: raise RuntimeError('GetComponents failed: '+str(e))
        instances=[]; documents=[]; seen=set()
        for i,c in enumerate(arr(comps),1):
            try: name=str(prop(c,'Name2','') or '')
            except Exception: name=''
            try: path=str(call(c,'GetPathName') or '')
            except Exception: path=''
            try: rcfg=str(prop(c,'ReferencedConfiguration','') or '')
            except Exception: rcfg=''
            sup=suppressed_component(c)
            tr=[]
            try:
                t=prop(c,'Transform2',None)
                ad=prop(t,'ArrayData',None) if t is not None else None
                if callable(ad): ad=ad()
                tr=[float(x) for x in arr(ad)]
            except Exception as e: warnings.append('transform:'+name+':'+str(e))
            instances.append({'name':name,'path':path,'referenced_configuration':rcfg,'suppressed':sup,'transform':tr})
            if (not sup) and path:
                key=(path.lower(),rcfg)
                if key not in seen:
                    seen.add(key)
                    try: cm=call(c,'GetModelDoc2')
                    except Exception: cm=None
                    if cm is not None: documents.append(read_document(cm,path,rcfg,warnings))
                    else: warnings.append('GetModelDoc2:null:'+name)
        stage='READ_MATES'; mates=[]
        try: f=call(model,'FirstFeature')
        except Exception: f=None
        guard=0
        while f is not None and guard<10000:
            guard+=1
            try: typ=str(call(f,'GetTypeName2') or '')
            except Exception: typ=''
            try: name=str(prop(f,'Name','') or '')
            except Exception: name=''
            if 'mate' in typ.lower(): mates.append({'name':name,'type':typ,'suppressed':suppressed_feature(f)})
            try: f=call(f,'GetNextFeature')
            except Exception: f=None
        stage='WRITE'
        title=''
        try: title=str(call(model,'GetTitle') or '')
        except Exception: title=Path(a.assembly).name
        root={'schema':'k01_sw_semantic_raw_a001_v1_5_pywin32','status':'OK','adapter':'pywin32','assembly':{'title':title,'native_path':a.assembly,'configuration':cfg,'component_count':len(instances)},'instances':instances,'documents':documents,'mates':mates,'errors':warnings}
        dump(a.out,root); log(stage,f'PASS components={len(instances)} documents={len(documents)} mates={len(mates)} warnings={len(warnings)}')
        return 0
    except Exception as e:
        err={'schema':'k01_sw_semantic_raw_a001_error_v1_5','status':'ERROR','stage':stage,'assembly':a.assembly,'error':str(e),'stack_trace':traceback.format_exc(),'errors':warnings}
        try: dump(a.out,err)
        except Exception: pass
        log(stage,'ERROR '+str(e)); print(traceback.format_exc(),file=sys.stderr); return 1
    finally:
        try:
            import pythoncom; pythoncom.CoUninitialize()
        except Exception: pass
if __name__=='__main__': raise SystemExit(main())
