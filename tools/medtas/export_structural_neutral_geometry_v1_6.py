from __future__ import annotations
import argparse,sys,traceback
from pathlib import Path
from canonical_hash_v1_5 import canonical_step_hash
from medtas_v16_common import load,dump,base_id,register_build,sha256_file

def binding(root):
    for n in ('K01_CAD_SEM_A001_BINDING_v1_6.json','K01_CAD_SEM_A001_BINDING_v1_5.json'):
        p=root/'control/medtas/v1/bindings'/n
        if p.exists():return load(p)
    raise FileNotFoundError('CAD binding missing')
def doc_paths(raw):
    out={}
    for d in raw.get('documents',[]) or []:
        pid=base_id(d.get('title') or d.get('native_path'))
        if pid:out[pid]=d.get('native_path')
    return out
def transforms(cad):
    out={}
    for i in cad.get('instances',[]) or []:
        pid=base_id(i.get('document_id'))
        if pid and not i.get('suppressed'):out.setdefault(pid,[]).append({'instance':i.get('instance'),'transform':i.get('transform')})
    return out
def export_step(sw,path,out):
    model=None
    try:model=sw.GetOpenDocumentByName(str(path))
    except Exception:pass
    if model is None:
        try:model=sw.OpenDoc6(str(path),1,1,'',0,0)
        except Exception:model=None
    if model is None:raise RuntimeError('Cannot open part '+str(path))
    out.parent.mkdir(parents=True,exist_ok=True)
    ok=False;errs=[]
    for fn,args in [('SaveAs3',(str(out),0,0)),('SaveAs2',(str(out),0,0,False,False)),('SaveAs',(str(out),))]:
        try:
            r=getattr(model,fn)(*args);ok=bool(r) or out.exists()
            if ok:break
        except Exception as e:errs.append(fn+':'+str(e))
    if not ok:
        try:
            ext=model.Extension;r=ext.SaveAs(str(out),0,1,None,0,0);ok=bool(r) or out.exists()
        except Exception as e:errs.append('Extension.SaveAs:'+str(e))
    if not ok or not out.exists():raise RuntimeError('STEP export failed: '+' | '.join(errs))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();b=binding(root)
    rawp=root/b['raw_api_output'];cadp=root/b['canonical_output'];dest=root/'reports/medtas/structural/current/neutral_geometry_p006';manifest=root/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_6.json'
    if not rawp.exists() or not cadp.exists():print('ERROR: CAD semantic evidence missing',file=sys.stderr);return 2
    raw=load(rawp);cad=load(cadp);paths=doc_paths(raw);trs=transforms(cad);parts=['K01-P-003','K01-P-007'];rows=[];limitations=[]
    try:
        import win32com.client
        sw=win32com.client.GetActiveObject('SldWorks.Application')
    except Exception as e:print('ERROR: cannot attach SOLIDWORKS:',e,file=sys.stderr);return 3
    for pid in parts:
        src=paths.get(pid)
        if not src or not Path(src).exists():limitations.append('NEUTRAL-PATH-MISSING:'+pid);continue
        out=dest/(pid+'.STEP')
        try:export_step(sw,Path(src),out)
        except Exception as e:limitations.append('NEUTRAL-EXPORT-FAILED:'+pid+':'+str(e));continue
        rows.append({'part_no':pid,'step_path':out.relative_to(root).as_posix(),'step_normalized_sha256':canonical_step_hash(out),'step_binary_sha256_diagnostic':sha256_file(out),'assembly_instances':trs.get(pid,[])})
    status='PASS' if len(rows)==2 and not limitations else 'HOLD'
    payload={'schema':'k01.structural_neutral_geometry.p006.v1_6','status':status,'source':'native SOLIDWORKS part documents from current CAD semantic raw snapshot','parts':rows,'limitations':limitations,'hash_policy':'normalized STEP hash strips volatile header and is artifact-stability evidence only; native CAD semantic state remains geometry authority'}
    dump(manifest,payload)
    if status=='PASS':register_build(root,'K01.STRUCT.NEUTRAL.GEOMETRY.P006',{'tool':'export_structural_neutral_geometry_v1_6.py','adapter':'SOLIDWORKS COM STEP export'})
    print(status,'neutral geometry:',manifest)
    for x in limitations:print(' -',x)
    return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
