from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify
from face_identity_v1_7 import signature,base_id

def index_faces(fm):
    by={}
    for part,x in (fm.get('parts') or {}).items():
        for f in x.get('faces',[]):by.setdefault(f.get('face_signature'),[]).append({'part_no':part,**f})
    return by

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();fm_p=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json';bind_p=root/'control/medtas/v1/bindings/K01_SWSIM_STUDY_BINDING_v1_7.json';raw_p=root/'reports/medtas/structural/current/K01_SWSIM_STUDY_SELECTIONS_RAW_v1_7.json'
    if not fm_p.exists():print('HOLD: face-map candidate missing; run pipeline first');return 2
    fm=load(fm_p);binding=load(bind_p);exe=root/'cad_api/medtas/bin/K01SimulationStudySelections.exe'
    if not exe.exists():print('HOLD: Simulation selection exporter missing; rerun adapter compile stage');return 3
    cp=subprocess.run([str(exe),'--out',str(raw_p),'--study',binding['study_name']],cwd=str(root),text=True,capture_output=True,timeout=180)
    if cp.stdout:print(cp.stdout,end='')
    if cp.stderr:print(cp.stderr,end='',file=sys.stderr)
    if cp.returncode or not raw_p.exists():print('HOLD: Simulation API extraction failed rc=',cp.returncode);return 4
    raw=load(raw_p);idx=index_faces(fm);issues=[];roles={};rows={str(x.get('name')):x for x in raw.get('loads_and_restraints',[])}
    for role,spec in binding['loads'].items():
        item=rows.get(spec['name'])
        if not item:issues.append(f'SWSIM-ROLE-MISSING:{role}:{spec["name"]}');continue
        ents=item.get('entities',[]) or []
        if len(ents)!=int(spec['expected_entity_count']):issues.append(f'SWSIM-ROLE-COUNT:{role}:{len(ents)}!={spec["expected_entity_count"]}');continue
        mapped=[]
        for e in ents:
            face=e.get('face') if e.get('entity_kind')=='FACE' else None
            if not face:issues.append(f'SWSIM-ROLE-NONFACE:{role}:select_type={e.get("select_type")}');continue
            part=base_id(face.get('part_no'));sg=signature(part,face);matches=idx.get(sg,[])
            if len(matches)!=1:
                issues.append(f'SWSIM-ROLE-AMBIG:{role}:{part}:{sg}:matches={len(matches)}');continue
            m=matches[0];mapped.append({'part_no':m['part_no'],'face_signature':sg,'surface_type':m.get('surface_type'),'area_m2':m.get('area_m2'),'source_load_name':spec['name']})
        if len(mapped)==int(spec['expected_entity_count']):roles[role]=mapped
    cs=int((raw.get('contact_summary') or {}).get('contact_set_count') or 0)
    if cs==0:
        roles['CONTACT']={'mode':'GLOBAL_NO_PENETRATION_BODY_PAIR','body_pair':binding['contact']['body_pair'],'authority':'controlled SW report + Simulation study has no explicit contact set; no arbitrary face pair is invented'}
    else:
        issues.append('SWSIM-CONTACT-001: explicit contact set(s) exist; v1.7 requires explicit source/target extraction before PASS')
    expected=set(binding['loads']);complete=expected.issubset(roles) and 'CONTACT' in roles and not issues
    if complete:
        fm['confirmed_role_map']=roles;fm['status']='PASS';fm['limitations']=[];fm['binding_authority']='automatic SolidWorks Simulation study extraction by exact load names/entities; ambiguity fail-closed'
    else:
        fm['status']='REVIEW_REQUIRED';fm['limitations']=sorted(set((fm.get('limitations') or [])+issues))
    dump(fm_p,fm);register_build(root,'K01.STRUCT.FACE_MAP.P006',{'tool':'auto_bind_structural_face_roles_v1_7.py','study':binding['study_name'],'mode':'automatic exact Simulation entity extraction'},limitations=fm.get('limitations',[]));register_verify(root,'K01.STRUCT.FACE_MAP.P006','PASS' if complete else 'HOLD',metrics={'roles_bound':sorted(roles),'issues':len(issues),'simulation_items':len(raw.get('loads_and_restraints',[]))},limitations=issues,notes='No human click selection. Exact Simulation load entities are mapped to unique persistent semantic face identities. Global contact remains body-pair semantics when no explicit contact set exists.')
    print(('PASS' if complete else 'HOLD'),'automatic Simulation face-role binding');[print(' -',x) for x in issues];return 0 if complete else 1
if __name__=='__main__':raise SystemExit(main())
