from __future__ import annotations
import argparse
from pathlib import Path
from medtas_v16_common import load,dump,base_id

PROP_TYPE_TEXT=30
REPLACE_VALUE=1
SW_DOC_PART=1
SW_OPEN_SILENT=1


def latest_raw(root:Path):
    for n in ('K01_A001_SEMANTIC_RAW_API_v1_4.json','K01_A001_SEMANTIC_RAW_API_v1_2.json'):
        p=root/'reports/cad/current'/n
        if p.exists(): return p
    return None

def native_paths(raw):
    out={}
    for d in raw.get('documents',[]) or []:
        pid=base_id(d.get('title') or d.get('native_path'))
        p=d.get('native_path')
        if pid.startswith('K01-') and p: out[pid]=str(p)
    return out

def get_names(cpm):
    try:
        x=cpm.GetNames()
        if x is None:return []
        if isinstance(x,(list,tuple)):return [str(v) for v in x]
        return [str(x)]
    except Exception:return []

def get_value(cpm,name):
    try:
        r=cpm.Get6(name,False)
        if isinstance(r,(list,tuple)):
            ss=[str(x) for x in r if isinstance(x,str)]
            return ss[-1] if ss else ''
        return str(r or '')
    except Exception:
        try:
            r=cpm.Get2(name)
            if isinstance(r,(list,tuple)):
                ss=[str(x) for x in r if isinstance(x,str)];return ss[-1] if ss else ''
            return str(r or '')
        except Exception:return ''

def set_value(cpm,name,value):
    names={x.lower() for x in get_names(cpm)}
    if name.lower() in names:
        rc=cpm.Set2(name,str(value));return {'method':'Set2','rc':rc}
    rc=cpm.Add3(name,PROP_TYPE_TEXT,str(value),REPLACE_VALUE);return {'method':'Add3','rc':rc}

def get_open(sw,path):
    for candidate in (str(path),Path(path).name):
        try:
            x=sw.GetOpenDocumentByName(candidate)
            if x is not None:return x
        except Exception:pass
    return None

def open_part(sw,path):
    m=get_open(sw,path)
    if m is not None:return m,False
    try:m=sw.OpenDoc6(str(path),SW_DOC_PART,SW_OPEN_SILENT,'',0,0)
    except Exception:m=None
    if m is None:raise RuntimeError('Cannot open part through SOLIDWORKS: '+str(path))
    return m,True

def close_if_opened(sw,model,opened):
    if not opened:return
    try:sw.CloseDoc(model.GetTitle())
    except Exception:pass

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--apply',action='store_true');a=ap.parse_args();r=Path(a.repo_root).resolve()
    reg=load(r/'control/product/parts.json',{}) or {};out=r/'reports/bom/current/K01_PARTS_PROPERTY_PROJECTION_CURRENT.json';rawp=latest_raw(r)
    if rawp is None:
        payload={'schema':'k01.parts_property_projection.v2_0','status':'BLOCKED_RAW_CAD_SNAPSHOT_MISSING','apply':a.apply,'rows':[]};dump(out,payload);print('BLOCKED: raw CAD semantic snapshot missing');return 2
    raw=load(rawp,{}) or {};paths=native_paths(raw)
    try:
        import win32com.client
        sw=win32com.client.GetActiveObject('SldWorks.Application')
    except Exception as e:
        payload={'schema':'k01.parts_property_projection.v2_0','status':'BLOCKED_SOLIDWORKS','apply':a.apply,'error':str(e),'rows':[]};dump(out,payload);print('BLOCKED: active SOLIDWORKS not available');return 3
    rows=[];changes=0;errors=[];opened_count=0
    for pid,meta in sorted((reg.get('items') or {}).items()):
        path=paths.get(pid)
        if not path:
            rows.append({'part_number':pid,'status':'NOT_IN_CURRENT_A001','native_path':None,'changes':[]});continue
        p=Path(path)
        if not p.exists():
            errors.append(pid+':native path missing:'+path);rows.append({'part_number':pid,'status':'NATIVE_PATH_MISSING','native_path':path,'changes':[]});continue
        model=None;opened=False
        try:
            model,opened=open_part(sw,p);opened_count+=1 if opened else 0
            cpm=model.Extension.CustomPropertyManager('')
            desired={k:str(v) for k,v in (meta.get('cad_property_projection') or {}).items() if v not in (None,'')}
            diffs=[];write_results=[]
            for k,v in desired.items():
                cur=get_value(cpm,k)
                if str(cur)!=v:
                    diffs.append({'property':k,'current':cur,'desired':v})
                    if a.apply:
                        try:write_results.append({'property':k,**set_value(cpm,k,v)})
                        except Exception as e:errors.append(pid+':'+k+':'+str(e))
            changes+=len(diffs)
            if a.apply and diffs:
                try:
                    ok=model.Save()
                    if ok is False:errors.append(pid+':Save returned false')
                except Exception as e:errors.append(pid+':Save:'+str(e))
            rows.append({'part_number':pid,'native_path':path,'status':'APPLIED' if a.apply and diffs else 'DIFF' if diffs else 'IN_SYNC','changes':diffs,'write_results':write_results})
        except Exception as e:
            errors.append(pid+':'+str(e));rows.append({'part_number':pid,'native_path':path,'status':'ERROR','error':str(e),'changes':[]})
        finally:
            if model is not None:close_if_opened(sw,model,opened)
    status='HOLD' if errors else 'PASS_WITH_LIMITATIONS' if changes and not a.apply else 'PASS'
    payload={'schema':'k01.parts_property_projection.v2_0','status':status,'mode':'APPLY' if a.apply else 'DRY_RUN','authority':'control/product/parts.json -> SOLIDWORKS custom properties one-way projection. Native material assignment and geometry are not modified.','source_raw_snapshot':str(rawp.relative_to(r)).replace('\\','/'),'active_assembly_required':False,'rows':rows,'summary':{'registry_items':len(reg.get('items') or {}),'resolved_native_paths':len(paths),'documents_opened_silently':opened_count,'property_differences':changes,'errors':len(errors)},'errors':errors};dump(out,payload)
    print('Parts property projection',status,'mode=',payload['mode'],'differences=',changes,'errors=',len(errors),'active assembly required=NO');print('Report:',out)
    return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
