from __future__ import annotations
import argparse
from pathlib import Path
import hashlib,json
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();apath=r/'reports/medtas/drawing/current/K01_DRAWING_ARTIFACT_GATE04E_v1_7.json';planp=r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json';out=r/'reports/medtas/drawing/current/K01_DRAWING_VERIFY_GATE04E_v1.json'
    issues=[];metrics={}
    if not apath.exists():issues.append('DRAWING-VERIFY-ARTIFACT-001: drawing artifact manifest missing');art={}
    else:art=load(apath)
    if not planp.exists():issues.append('DRAWING-VERIFY-PLAN-001: release plan missing');plan={}
    else:plan=load(planp)
    if art.get('status')!='PASS':issues.append('DRAWING-VERIFY-ARTIFACT-002: artifact generation is not PASS')
    if plan.get('verdict')!='PASS':issues.append('DRAWING-VERIFY-PLAN-002: definition/release plan is not PASS')
    expected={d.get('drawing_no') for d in plan.get('drawings',[]) or []};got={x.get('drawing_no') for x in art.get('artifacts',[]) or [] if x.get('kind')=='PDF'};missing=sorted(expected-got)
    if missing:issues.append('DRAWING-VERIFY-MISSING-PDF:'+','.join(missing))
    # Semantic provenance can be machine-checked at this stage; visual readability still requires explicit review.
    visual=r/'reports/medtas/drawing/current/K01_DRAWING_VISUAL_APPROVAL_GATE04E_v1_7.json';vis=load(visual) if visual.exists() else {};rows=sorted((x.get('drawing_no'),x.get('kind'),x.get('sha256')) for x in art.get('artifacts',[]) or []);current_hash=hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();visual_pass=str(vis.get('verdict','')).upper()=='PASS' and vis.get('artifact_set_hash')==current_hash
    if not visual_pass:issues.append('DRAWING-VISUAL-001: explicit visual QA approval is missing/stale/not PASS for the current artifact set')
    verdict='PASS' if not issues else 'HOLD';metrics={'expected_drawings':len(expected),'pdf_drawings':len(got),'visual_approval':visual_pass,'artifact_set_hash':current_hash};payload={'schema':'k01.drawing_verify.gate04e.v1_7','verdict':verdict,'metrics':metrics,'issues':issues,'policy':'Release requires definition plan PASS + generated SLDDRW/PDF artifacts + explicit visual QA. A file existing is not sufficient.'};dump(out,payload);register_build(r,'K01.DRAWING.VERIFY.GATE04E',{'tool':'verify_drawing_pack_v1_7.py'});register_verify(r,'K01.DRAWING.VERIFY.GATE04E',verdict,metrics=metrics,limitations=issues)
    print(verdict,'drawing verification');[print(' -',x) for x in issues];return 0 if verdict=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
