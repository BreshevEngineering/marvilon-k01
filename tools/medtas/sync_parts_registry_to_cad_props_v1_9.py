from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
from medtas_v16_common import load,dump,base_id

PROP_TYPE_TEXT=30
REPLACE_VALUE=1


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
            # resolved value is normally one of the string outputs; prefer the last non-empty string
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

def walk_components(asm):
    try:comps=asm.GetComponents(False) or []
    except Exception:comps=[]
    if not isinstance(comps,(list,tuple)):comps=[comps]
    docs={}
    for c in comps:
        try:
            if bool(c.IsSuppressed()):continue
        except Exception:pass
        try:doc=c.GetModelDoc2()
        except Exception:doc=None
        if doc is None:continue
        try:title=doc.GetTitle()
        except Exception:title=''
        pid=base_id(title)
        if pid.startswith('K01-'):docs[pid]=doc
    return docs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--apply',action='store_true');a=ap.parse_args();r=Path(a.repo_root).resolve();reg=load(r/'control/product/parts.json',{}) or {};out=r/'reports/bom/current/K01_PARTS_PROPERTY_PROJECTION_CURRENT.json'
    try:
        import win32com.client
        sw=win32com.client.GetActiveObject('SldWorks.Application')
    except Exception as e:
        payload={'schema':'k01.parts_property_projection.v1_9','status':'BLOCKED_SOLIDWORKS','apply':a.apply,'error':str(e),'rows':[]};dump(out,payload);print('BLOCKED: active SOLIDWORKS not available');return 2
    try:doc=sw.ActiveDoc
    except Exception:doc=None
    if doc is None:
        payload={'schema':'k01.parts_property_projection.v1_9','status':'BLOCKED_NO_ACTIVE_DOC','apply':a.apply,'rows':[]};dump(out,payload);print('BLOCKED: no active SOLIDWORKS document');return 3
    try:
        dtype=int(doc.GetType())
    except Exception:dtype=0
    if dtype!=2:
        # Try to find an open assembly by title from available documents is intentionally not guessed here.
        payload={'schema':'k01.parts_property_projection.v1_9','status':'BLOCKED_ACTIVE_DOC_NOT_ASSEMBLY','apply':a.apply,'rows':[]};dump(out,payload);print('BLOCKED: activate the current K01 A001 assembly and rerun');return 4
    try:doc.ResolveAllLightWeightComponents(True)
    except Exception:pass
    docs=walk_components(doc);rows=[];changes=0;missing=[];errors=[]
    for pid,meta in sorted((reg.get('items') or {}).items()):
        md=docs.get(pid)
        if md is None:
            # Registry may contain items not in the active assembly; report but do not treat as an error.
            rows.append({'part_number':pid,'status':'NOT_IN_ACTIVE_ASSEMBLY','changes':[]});continue
        try:cpm=md.Extension.CustomPropertyManager('')
        except Exception as e:
            errors.append(pid+':CustomPropertyManager:'+str(e));rows.append({'part_number':pid,'status':'ERROR','error':str(e)});continue
        desired={k:str(v) for k,v in (meta.get('cad_property_projection') or {}).items() if v not in (None,'')}
        diffs=[];write_results=[]
        for k,v in desired.items():
            cur=get_value(cpm,k)
            if str(cur)!=v:
                diffs.append({'property':k,'current':cur,'desired':v})
                if a.apply:
                    try:write_results.append({'property':k,**set_value(cpm,k,v)})
                    except Exception as e:errors.append(pid+':'+k+':'+str(e))
        if diffs:changes+=len(diffs)
        if a.apply and diffs:
            try:md.Save()
            except Exception as e:errors.append(pid+':Save:'+str(e))
        rows.append({'part_number':pid,'status':'APPLIED' if a.apply and diffs else 'DIFF' if diffs else 'IN_SYNC','changes':diffs,'write_results':write_results})
    status='HOLD' if errors else 'PASS_WITH_LIMITATIONS' if changes and not a.apply else 'PASS'
    payload={'schema':'k01.parts_property_projection.v1_9','status':status,'mode':'APPLY' if a.apply else 'DRY_RUN','authority':'control/product/parts.json -> SOLIDWORKS custom properties one-way projection. Native material assignment is not overwritten by this command.','rows':rows,'summary':{'registry_items':len(reg.get('items') or {}),'active_documents':len(docs),'property_differences':changes,'errors':len(errors)},'errors':errors};dump(out,payload)
    print('Parts property projection',status,'mode=',payload['mode'],'differences=',changes,'errors=',len(errors));print('Report:',out)
    return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
