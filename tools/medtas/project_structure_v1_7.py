from __future__ import annotations
import argparse,json,re
from pathlib import Path
from medtas_v16_common import register_build,register_verify

ROOT_ENTRYPOINT_PATTERNS=[
    re.compile(r'^OPEN_K01_COMMAND_CENTER_V\d+(?:_REFERENCE)?\.cmd$',re.I),
    re.compile(r'^\d+[A-Z]?_.*\.cmd$',re.I),
    re.compile(r'^README_MEDTAS_.*\.md$',re.I),
    re.compile(r'^CHANGELOG_MEDTAS_.*\.md$',re.I),
    re.compile(r'^00_INSTALL_MEDTAS_.*\.md$',re.I),
    re.compile(r'^K01_MEDTAS_OVERLAY_MANIFEST_.*\.json$',re.I),
    re.compile(r'^K01_Command_Center_v\d+.*\.html$',re.I),
]

def load(p,default=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return default

def dump(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')

def cad_external_root(root:Path):
    for n in ('K01_CAD_SEM_A001_BINDING_v1_6.json','K01_CAD_SEM_A001_BINDING_v1_5.json'):
        b=load(root/'control/medtas/v1/bindings'/n,{}) or {};s=b.get('source_selection',{});rel=s.get('preferred_gate_verify');fld=s.get('preferred_gate_verify_field')
        if rel and fld:
            j=load(root/rel,{}) or {};cand=j.get(fld)
            if cand:
                p=Path(cand)
                # Current K01 CAD may live outside the repo. Stop at the directory named cad.
                for parent in [p.parent,*p.parents]:
                    if parent.name.lower()=='cad':return str(parent.resolve())
    # Fallback to canonical CAD semantic source assembly.
    c=load(root/'reports/medtas/cad/current/K01_CAD_SEM_A001.json',{}) or {};src=c.get('source_assembly') or c.get('assembly_path')
    if src:
        p=Path(src)
        for parent in [p.parent,*p.parents]:
            if parent.name.lower()=='cad':return str(parent.resolve())
    return None

def is_entrypoint(name):return any(rx.match(name) for rx in ROOT_ENTRYPOINT_PATTERNS)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--ensure-dirs',action='store_true');a=ap.parse_args();root=Path(a.repo_root).resolve();spec=load(root/'control/medtas/v1/spec/K01_PROJECT_LAYOUT_v1_7.json',{}) or {};rows=[]
    for z in spec.get('zones',[]):
        p=root/z['path']
        if a.ensure_dirs:p.mkdir(parents=True,exist_ok=True)
        count=0;size=0
        if p.exists():
            for f in p.rglob('*'):
                if f.is_file():
                    count+=1
                    try:size+=f.stat().st_size
                    except Exception:pass
        rows.append({**z,'exists':p.exists(),'file_count':count,'size_bytes':size,'resolved_path':str(p)})
    allowed_top={Path(z['path']).parts[0].lower() for z in spec.get('zones',[])}|{'.git','cad_api','__pycache__'}
    entrypoints=[];unclassified_root_files=[];unclassified_dirs=[]
    for p in sorted(root.iterdir(),key=lambda x:x.name.lower()):
        if p.name.lower() in allowed_top:continue
        if p.is_file():
            (entrypoints if is_entrypoint(p.name) else unclassified_root_files).append(p.name)
        elif p.is_dir():unclassified_dirs.append(p.name)
    ext=cad_external_root(root)
    payload={'schema':'k01.project_structure.current.v1_7','repo_root':str(root),'external_cad_root':ext,'zones':rows,'summary':{'zones':len(rows),'missing_zones':sum(1 for x in rows if not x['exists']),'controlled_root_entrypoints':len(entrypoints),'unclassified_root_files':len(unclassified_root_files),'unclassified_top_directories':len(unclassified_dirs)},'controlled_root_entrypoints':entrypoints,'unclassified_root_files':unclassified_root_files,'unclassified_top_directories':unclassified_dirs,'migration_policy':'NO_AUTOMATIC_MOVE. Canonical zones are created when requested; existing engineering files are never relocated or deleted automatically. Root launchers/manifests are classified as controlled entrypoints, not project-data authority.'}
    out=root/'reports/control/K01_PROJECT_STRUCTURE_CURRENT.json';dump(out,payload)
    actions=[]
    for f in unclassified_root_files:actions.append({'kind':'REVIEW_ROOT_FILE','source':f,'recommended_zone':'docs/ or control/ depending on authority','automatic':False})
    for d in unclassified_dirs:actions.append({'kind':'REVIEW_TOP_DIRECTORY','source':d,'recommended_zone':'classify before any move','automatic':False})
    migration={'schema':'k01.project_migration_plan.v1_7','status':'PASS' if not actions else 'REVIEW_REQUIRED','policy':'Review-only migration plan. No file move/delete/rename is performed by MEDTAS without an explicit approved change.','external_cad_root':ext,'controlled_entrypoints':entrypoints,'actions':actions}
    mout=root/'reports/control/K01_PROJECT_MIGRATION_PLAN_CURRENT.json';dump(mout,migration)
    lims=[] if not actions else ['PROJECT-STRUCTURE-REVIEW: '+str(len(actions))+' unclassified root object(s) require classification; no automatic move performed']
    register_build(root,'K01.PROJECT.STRUCTURE',{'tool':'project_structure_v1_7.py'},limitations=lims);register_verify(root,'K01.PROJECT.STRUCTURE','PASS' if not actions else 'PASS_WITH_LIMITATIONS',metrics=payload['summary'],limitations=lims)
    print('Project structure:',out);print(payload['summary']);print('Migration plan:',mout,migration['status']);return 0
if __name__=='__main__':raise SystemExit(main())
