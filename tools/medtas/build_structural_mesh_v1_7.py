from __future__ import annotations
import argparse,math,sys,traceback
from pathlib import Path
from medtas_v16_common import load,dump,base_id,register_build,register_verify,tool_path,sha256_file

def f(x):
    try:return float(x)
    except:return None
def stype(t):
    s=str(t or '').lower()
    if 'plane' in s:return 'plane'
    if 'cylinder' in s:return 'cylinder'
    if 'cone' in s:return 'cone'
    if 'sphere' in s:return 'sphere'
    if 'torus' in s:return 'torus'
    return 'other'
def role_entries(fm):
    out=[]
    for role,val in (fm.get('confirmed_role_map') or {}).items():
        if role=='CONTACT': continue
        for x in val or []: out.append((role,x))
    return out
def transform_matrix(tr):
    vals=[f(x) for x in (tr or [])]
    if len(vals)<13 or any(x is None for x in vals[:13]):return None
    s=vals[12] or 1.0;r=vals[:9];t=vals[9:12]
    return [s*r[0],s*r[1],s*r[2],t[0],s*r[3],s*r[4],s*r[5],t[1],s*r[6],s*r[7],s*r[8],t[2],0,0,0,1]
def descriptor(gmsh,tag):
    bb=gmsh.model.getBoundingBox(2,tag);area=gmsh.model.occ.getMass(2,tag);typ=stype(gmsh.model.getType(2,tag));edges=gmsh.model.getBoundary([(2,tag)],combined=False,oriented=False,recursive=False)
    return {'tag':tag,'surface_type':typ,'area_m2':float(area),'box_m':[float(x) for x in bb],'edge_count':len([x for x in edges if x[0]==1])}
def score(c,g):
    if c.get('surface_type') and c.get('surface_type')!=g.get('surface_type'):return 1e9
    s=0.0
    ca=f(c.get('area_m2'));ga=f(g.get('area_m2'))
    if ca is not None and ga is not None:s+=abs(ca-ga)/max(abs(ca),1e-12)
    cb=c.get('box_m') or [];gb=g.get('box_m') or []
    if len(cb)==6 and len(gb)==6:s+=max(abs(float(cb[i])-float(gb[i])) for i in range(6))/1e-6
    if c.get('edge_count') is not None and int(c['edge_count'])!=int(g.get('edge_count') or -1):s+=100
    return s
def match(candidates,geom):
    cand=sorted(((score(c,g),g) for c in candidates for g in geom if c.get('face_signature')),key=lambda x:x[0])
    # caller matches one candidate at a time; this helper unused
    return cand
def find_one(c,geom):
    arr=sorted(((score(c,g),g) for g in geom),key=lambda x:x[0])
    if not arr or arr[0][0]>0.05:raise RuntimeError('No unique STEP-surface match for '+str(c.get('face_signature'))+' best='+str(arr[0][0] if arr else None))
    if len(arr)>1 and abs(arr[1][0]-arr[0][0])<1e-9:raise RuntimeError('Ambiguous STEP-surface match for '+str(c.get('face_signature')))
    return arr[0][1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();fm_p=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json';fq_p=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_QUAL_P006_v1_7.json';ng_p=root/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_7.json';out=root/'reports/medtas/calculix/current/K01_STRUCTURAL_MESH_P006_v1_7.json';msh=root/'reports/medtas/calculix/current/K01_P006_NEUTRAL_MESH.msh';base_inp=root/'reports/medtas/calculix/current/K01_P006_MESH_BASE.inp'
    if not fm_p.exists() or not ng_p.exists():print('ERROR: face map or neutral geometry missing',file=sys.stderr);return 2
    fm=load(fm_p);ng=load(ng_p);fq=load(fq_p) if fq_p.exists() else {};lims=[]
    if fm.get('status')!='PASS':lims.append('CCX-FACE-002: face map is not PASS')
    if fq.get('verdict')!='PASS':lims.append('CCX-FACE-QUAL-001: face-map qualification is not PASS')
    if ng.get('status')!='PASS':lims.append('CCX-GEO-002: neutral geometry is not PASS')
    try:import gmsh
    except Exception as e:
        lims.append('CCX-MESH-API-001: Python gmsh module unavailable. Install the matching Gmsh Python API or bind an equivalent controlled mesher.')
        dump(out,{'schema':'k01.structural_mesh.p006.v1_7','status':'HOLD','limitations':lims,'gmsh_executable':tool_path(root,'gmsh_executable',['gmsh.exe','gmsh'])});print('HOLD mesh:',*lims,sep='\n - ');return 1
    if lims:dump(out,{'schema':'k01.structural_mesh.p006.v1_7','status':'HOLD','limitations':lims});return 1
    # index persistent CAD faces by signature and part
    cad={}
    for part,x in fm.get('parts',{}).items():
        for r in x.get('faces',[]) or []:cad[(base_id(part),r['face_signature'])]=r
    parts={x['part_no']:x for x in ng.get('parts',[]) or []};roles=role_entries(fm);contact=(fm.get('confirmed_role_map') or {}).get('CONTACT') or {};tag_by_sig={};volumes_by_part={};surfaces_by_part={}
    try:
        gmsh.initialize();gmsh.model.add('K01_P006_STRUCTURAL')
        for pid in ('K01-P-003','K01-P-007'):
            rec=parts.get(pid)
            if not rec:raise RuntimeError('Neutral geometry manifest missing '+pid)
            before=set(gmsh.model.getEntities())
            gmsh.model.occ.importShapes(str(root/rec['step_path']));gmsh.model.occ.synchronize()
            after=set(gmsh.model.getEntities());new=after-before
            surfs=[t for d,t in new if d==2];vols=[t for d,t in new if d==3]
            if not vols:raise RuntimeError(pid+' STEP import produced no volume')
            geom=[descriptor(gmsh,t) for t in surfs]
            wanted=[(role,x) for role,x in roles if base_id(x.get('part_no'))==pid]
            for role,x in wanted:
                c=cad.get((pid,x['face_signature']))
                if not c:raise RuntimeError('CAD face signature absent '+x['face_signature'])
                g=find_one(c,geom);tag_by_sig[x['face_signature']]=g['tag']
            tr=(rec.get('assembly_instances') or [{}])[0].get('transform');mat=transform_matrix(tr)
            if mat:gmsh.model.occ.affineTransform([(3,t) for t in vols],mat);gmsh.model.occ.synchronize()
            else:lims.append('CCX-TRANSFORM-001: no usable assembly transform for '+pid)
            volumes_by_part[pid]=vols;surfaces_by_part[pid]=surfs
        # Physical groups after transforms; entity tags persist.
        role_tags={}
        for role,x in roles:role_tags.setdefault(role,[]).append(tag_by_sig[x['face_signature']])
        for name,tags in sorted(role_tags.items()):
            pg=gmsh.model.addPhysicalGroup(2,sorted(set(tags)));gmsh.model.setPhysicalName(2,pg,name)
        if contact.get('mode')=='GLOBAL_NO_PENETRATION_BODY_PAIR':
            pair=[base_id(x) for x in contact.get('body_pair',[])]
            if len(pair)!=2: raise RuntimeError('Global contact body_pair must contain exactly two parts')
            for name,pid in [('CONTACT_A',pair[0]),('CONTACT_B',pair[1])]:
                tags=surfaces_by_part.get(pid,[])
                if not tags: raise RuntimeError('No imported surfaces for global contact part '+pid)
                pg=gmsh.model.addPhysicalGroup(2,sorted(set(tags)));gmsh.model.setPhysicalName(2,pg,name)
        else: raise RuntimeError('Unsupported/undefined contact semantics for mesh: '+str(contact))
        for pid,vols in volumes_by_part.items():
            pg=gmsh.model.addPhysicalGroup(3,vols);gmsh.model.setPhysicalName(3,pg,pid.replace('-','_'))
        bind=load(root/'control/medtas/v1/bindings/K01_TOOLCHAIN_BINDING_v1_6.json');mc=bind.get('mesh',{})
        gmsh.option.setNumber('Mesh.ElementOrder',int(mc.get('element_order',2)));gmsh.option.setNumber('Mesh.CharacteristicLengthMin',float(mc.get('characteristic_length_mm',1.0))/1000.0);gmsh.option.setNumber('Mesh.CharacteristicLengthMax',float(mc.get('characteristic_length_mm',1.0))/1000.0);gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.option.setNumber('Mesh.SaveAll',1)
        try:gmsh.option.setNumber('Mesh.Algorithm3D',int(mc.get('algorithm_3d',10)))
        except Exception:pass
        gmsh.model.mesh.generate(3);gmsh.model.mesh.setOrder(2);msh.parent.mkdir(parents=True,exist_ok=True);gmsh.write(str(msh)); gmsh.write(str(base_inp))
        # count tet10
        types,tags,nodes=gmsh.model.mesh.getElements(3);counts={int(t):len(tags[i]) for i,t in enumerate(types)}
        tet10=counts.get(11,0)
        if tet10<=0:lims.append('CCX-MESH-002: no Gmsh type-11 (10-node tetra) elements found')
    except Exception as e:
        lims.append('CCX-MESH-BUILD-001:'+str(e));
        try:traceback.print_exc()
        except Exception:pass
    finally:
        try:gmsh.finalize()
        except Exception:pass
    status='PASS' if msh.exists() and not lims else 'HOLD';payload={'schema':'k01.structural_mesh.p006.v1_7','status':status,'mesh_path':msh.relative_to(root).as_posix() if msh.exists() else None,'mesh_sha256':sha256_file(msh) if msh.exists() else None,'base_inp_path':base_inp.relative_to(root).as_posix() if base_inp.exists() else None,'base_inp_sha256':sha256_file(base_inp) if base_inp.exists() else None,'element_family':'quadratic tetra / C3D10-compatible','physical_groups':sorted(set([r for r,_ in roles]+['CONTACT_A','CONTACT_B'])),'limitations':lims}
    dump(out,payload)
    if msh.exists():
        register_build(root,'K01.STRUCT.MESH.P006',{'tool':'build_structural_mesh_v1_7.py','mesher':'Gmsh Python API'},limitations=lims);register_verify(root,'K01.STRUCT.MESH.P006','PASS' if status=='PASS' else 'HOLD',metrics={'mesh_exists':True,'physical_group_count':len(payload['physical_groups'])},limitations=lims)
    print(status,'mesh:',msh if msh.exists() else 'not generated');
    for x in lims:print(' -',x)
    return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
