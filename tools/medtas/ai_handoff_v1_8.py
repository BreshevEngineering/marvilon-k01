from __future__ import annotations
import argparse,hashlib,json,time,zipfile
from pathlib import Path

PATTERNS=[
  'reports/control/*.json','reports/medtas/pipeline/*.json','reports/medtas/cad/current/*.json','reports/medtas/mbd/current/*.json',
  'reports/medtas/product_definition/current/*.json','reports/medtas/tolerance/current/*.json','reports/medtas/structural/current/*.json',
  'reports/medtas/calculix/current/*.json','reports/medtas/drawing/current/*.json','reports/medtas/bom/current/*.json',
  'reports/drawing/current/*.json','reports/bom/current/*','reports/engineering/current/*.md','reports/engineering/current/*.docx',
  'reports/engineering/current/source/*','control/parameters/*.json','control/materials/*.json','control/drawings/*.json',
  'control/medtas/v1/graph/K01_engineering_build_graph_v1_8.json','control/medtas/v1/spec/*.json','control/medtas/v1/spec/*.md',
  'control/medtas/v1/bindings/*.json','docs/architecture/*.md','reports/medtas/logs/current/*.log','reports/medtas/tests/*.json'
]

def build_handoff(root:Path):
    root=Path(root).resolve();out=root/'reports/control/K01_AI_HANDOFF_CURRENT.zip';out.parent.mkdir(parents=True,exist_ok=True);include=[];seen=set()
    for pat in PATTERNS:
        for p in root.glob(pat):
            if not p.is_file() or p.resolve()==out.resolve():continue
            rel=p.relative_to(root).as_posix()
            if rel not in seen:seen.add(rel);include.append((rel,p))
    manifest=[]
    for rel,p in sorted(include):
        try:manifest.append({'path':rel,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        except Exception:pass
    meta={'schema':'k01.ai_handoff_manifest.v1_8','generated_local_time':time.strftime('%Y-%m-%d %H:%M:%S'),'project':'K01','file_count':len(manifest),'files':manifest,'note':'Current semantic/control/evidence handoff. Native CAD binaries are excluded by design; canonical CAD semantic snapshots and engineering evidence are included.'}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for rel,p in sorted(include):
            try:z.write(p,rel)
            except Exception:pass
        z.writestr('K01_AI_HANDOFF_MANIFEST.json',json.dumps(meta,ensure_ascii=False,indent=2))
    return {'ok':True,'id':'AI-HANDOFF-CURRENT','path':str(out),'size':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(manifest)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();res=build_handoff(Path(a.repo_root));print('AI handoff:',res['path']);print('files=',res['files'],'size=',res['size']);print('sha256=',res['sha256']);return 0
if __name__=='__main__':raise SystemExit(main())
