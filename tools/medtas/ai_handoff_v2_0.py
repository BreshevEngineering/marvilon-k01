from __future__ import annotations
import argparse,hashlib,json,time,zipfile
from pathlib import Path
from medtas_v16_common import register_build

PATTERNS=[
  'reports/control/*.json','reports/medtas/pipeline/*.json','reports/medtas/cad/current/*.json','reports/cad/current/*.json',
  'reports/medtas/mbd/current/*.json','reports/medtas/product_definition/current/*.json','reports/medtas/tolerance/current/*.json',
  'reports/medtas/structural/current/*.json','reports/medtas/calculix/current/*.json','reports/medtas/drawing/current/*.json',
  'reports/medtas/bom/current/*.json','reports/drawing/current/*','reports/inspection/current/*','reports/bom/current/*',
  'reports/engineering/current/*.md','reports/engineering/current/*.docx','reports/engineering/current/source/*',
  'control/parameters/*.json','control/materials/*.json','control/drawings/*.json','control/product/*.json','control/revisions/*.json','control/requirements/*.json','control/identity/*.json','control/inspection/*.json',
  'control/medtas/v1/graph/K01_engineering_build_graph_v2_0.json','control/medtas/v1/graph/K01_engineering_build_graph_v1_9.json','control/medtas/v1/spec/*.json','control/medtas/v1/spec/*.md',
  'control/medtas/v1/bindings/*.json','docs/architecture/*.md','docs/automation/*.md','reports/medtas/logs/current/*.log','reports/medtas/tests/*.json','tests/medtas/*.py'
]

def build_handoff(root:Path):
    root=Path(root).resolve();out=root/'reports/control/K01_AI_HANDOFF_CURRENT.zip';out.parent.mkdir(parents=True,exist_ok=True);include=[];seen=set()
    for pat in PATTERNS:
        for p in root.glob(pat):
            if not p.is_file() or p.resolve()==out.resolve():continue
            rel=p.relative_to(root).as_posix()
            # Native CAD binaries and executable/script build outputs are intentionally excluded.
            if p.suffix.lower() in {'.sldprt','.sldasm','.slddrw','.exe','.dll','.pdb'}:continue
            if rel not in seen:seen.add(rel);include.append((rel,p))
    manifest=[]
    for rel,p in sorted(include):
        try:manifest.append({'path':rel,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        except Exception:pass
    meta={'schema':'k01.ai_handoff_manifest.v2_0','generated_local_time':time.strftime('%Y-%m-%d %H:%M:%S'),'project':'K01','file_count':len(manifest),'files':manifest,
          'note':'Current semantic/control/evidence handoff. Native SOLIDWORKS binaries are excluded by design. Includes parts registry, separate EBOM/MBOM, P007 exemplar/MBD/drawing/inspection data, graph/state, FEM/FEMM evidence and current diagnostic logs.'}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for rel,p in sorted(include):
            try:z.write(p,rel)
            except Exception:pass
        z.writestr('K01_AI_HANDOFF_MANIFEST.json',json.dumps(meta,ensure_ascii=False,indent=2))
    result={'ok':True,'id':'AI-HANDOFF-CURRENT','path':str(out),'size':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(manifest)}
    try: register_build(root,'K01.AI.HANDOFF.CURRENT',{'tool':'ai_handoff_v2_0.py','native_cad_binaries_excluded':True})
    except Exception as e: result['record_warning']=repr(e)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();res=build_handoff(Path(a.repo_root));print('AI handoff built:',res['files'],'files, SHA-256',res['sha256']);print('Path:',res['path']);return 0
if __name__=='__main__':raise SystemExit(main())
