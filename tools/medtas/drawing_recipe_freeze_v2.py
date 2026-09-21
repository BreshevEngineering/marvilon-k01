#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, shutil
from pathlib import Path

CAD_ROOT = Path(r"D:\Marvilon\K01\cad")
EVIDENCE = [
    "control/drawings/K01_D006_EXEMPLAR_POLICY_CURRENT.json",
    "RUN_K01_D006_PREPARE_EXEMPLAR_V12.cmd",
    "reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json",
    "control/drawings/K01_D006_MANUAL_FINISH_WORKPACK_CURRENT.md",
    "RUN_K01_D006_CAPTURE_EXEMPLAR_V12.cmd",
    "reports/drawing/current/K01-D-006_EXEMPLAR_CAPTURE_CURRENT.json",
    "control/drawings/K01_DRAWING_FAMILY_RULES_CURRENT.json",
    "control/drawings/K01_P007_DRAWING_FAMILY_BINDING_CURRENT.json",
    "RUN_K01_DRAWING_FAMILY_PLAN_V13.cmd",
    "reports/drawing/current/K01-D-006_FAMILY_PLAN_CURRENT.json",
    "RUN_K01_D3_VERIFY_P007_V15.cmd",
    "RUN_K01_D3_VERIFY_P007_V17.cmd",
    "reports/drawing/current/K01-P-007_D3_AUTHORING_VERIFY_CURRENT.json",
    "RUN_K01_D7_QA_D006_V15.cmd",
    "reports/drawing/current/K01-D-006_D7_SEMANTIC_QA_CURRENT.json",
    "RUN_K01_D006_REFINE_EXISTING.cmd",
    "tools/medtas/d006_exemplar_prepare_v12.py",
    "tools/medtas/d006_exemplar_capture_v12.py",
    "tools/medtas/d006_refine_existing_current_v1.py",
    "tools/medtas/drawing_family_plan_v13.py",
    "tools/medtas/drawing_d3_verify_v15.py",
    "tools/medtas/drawing_d3_verify_v17.py",
    "tools/medtas/drawing_d7_semantic_qa_v15.py",
    "control/drawings/placement/K01-D-003_PLACEMENT_CURRENT.json",
]

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',required=True)
    a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    if not root.is_dir():
        print('STATUS: HOLD_RECIPE_FREEZE');print('ERROR: repo root missing');return 2
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    base=CAD_ROOT/'drawings'/'exemplars'/'recipe_evidence'/('snapshot_'+stamp)
    repo_dst=base/'repo'
    repo_dst.mkdir(parents=True,exist_ok=False)
    rows=[]
    for rel in EVIDENCE:
        src=root/Path(rel)
        row={'relative':rel,'source':str(src),'exists':src.is_file()}
        if src.is_file():
            dst=repo_dst/Path(rel)
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
            row.update({'snapshot':str(dst),'sha256':sha256(dst),'size_bytes':dst.stat().st_size})
        rows.append(row)
    # Also snapshot the already pinned D003/D006 golden baseline manifest if present.
    golden_manifest=CAD_ROOT/'drawings'/'exemplars'/'K01_DRAWING_GOLDEN_BASELINE_CURRENT.json'
    gm=None
    if golden_manifest.is_file():
        dst=base/'K01_DRAWING_GOLDEN_BASELINE_CURRENT.json'
        shutil.copy2(golden_manifest,dst)
        gm={'source':str(golden_manifest),'snapshot':str(dst),'sha256':sha256(dst),'size_bytes':dst.stat().st_size}
    manifest={
        'schema':'k01.drawing_golden_recipe_evidence.v2',
        'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'drawing_system_checkpoint':'826cf15f0dff8a1013b35652b8ff2c3a26935ece',
        'purpose':'Immutable workstation snapshot of the legacy exemplar/presentation recipe that produced the accepted D003/D006 drawing quality.',
        'snapshot_root':str(base),
        'files':rows,
        'golden_baseline_manifest':gm,
        'missing_count':sum(1 for x in rows if not x['exists']),
        'rule':'Missing legacy files are reported, never invented. New generic drawing work uses the frozen golden recipe plus explicit presentation gate.',
    }
    mp=base/'K01_DRAWING_GOLDEN_RECIPE_EVIDENCE.json'
    mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    current=CAD_ROOT/'drawings'/'exemplars'/'recipe_evidence'/'CURRENT.json'
    current.write_text(json.dumps({'schema':'k01.drawing_golden_recipe_evidence.pointer.v1','snapshot_manifest':str(mp),'created_utc':manifest['created_utc']},indent=2)+'\n',encoding='utf-8')
    print('STATUS: PASS_RECIPE_FREEZE')
    print('SNAPSHOT:',base)
    print('MANIFEST:',mp)
    print('FOUND:',sum(1 for x in rows if x['exists']),'/',len(rows))
    print('MISSING:',manifest['missing_count'])
    return 0

if __name__=='__main__': raise SystemExit(main())
