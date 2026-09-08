from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();apath=r/'reports/medtas/drawing/current/K01_DRAWING_ARTIFACT_GATE04E_v1_8.json';planp=r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json';out=r/'reports/medtas/drawing/current/K01_DRAWING_VERIFY_GATE04E_v1.json';issues=[];per={}
    art=load(apath) if apath.exists() else {};plan=load(planp) if planp.exists() else {}
    if not apath.exists():issues.append('DRAWING-VERIFY-ARTIFACT-001: drawing artifact manifest missing')
    if not planp.exists():issues.append('DRAWING-VERIFY-PLAN-001: release plan missing')
    ready=set(plan.get('ready_drawings',[]) or []);all_draw={d.get('drawing_no') for d in plan.get('drawings',[]) or []};pdfs={x.get('drawing_no'):x for x in art.get('artifacts',[]) or [] if x.get('kind')=='PDF'};natives={x.get('drawing_no'):x for x in art.get('artifacts',[]) or [] if x.get('kind')=='SLDDRW'}
    for dn in sorted(all_draw):
        if dn not in ready:per[dn]={'state':'BLOCKED_PRODUCT_DEFINITION','pdf':False,'native':False};continue
        ok=dn in pdfs and dn in natives;per[dn]={'state':'ARTIFACT_READY' if ok else 'MISSING_ARTIFACT','pdf':dn in pdfs,'native':dn in natives}
        if not ok:issues.append('DRAWING-VERIFY-MISSING-ARTIFACT:'+dn)
    rows=sorted((x.get('drawing_no'),x.get('kind'),x.get('sha256')) for x in art.get('artifacts',[]) or []);current_hash=hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();visual=r/'reports/medtas/drawing/current/K01_DRAWING_VISUAL_APPROVAL_GATE04E_v1_8.json';
    if not visual.exists(): visual=r/'reports/medtas/drawing/current/K01_DRAWING_VISUAL_APPROVAL_GATE04E_v1_7.json'
    vis=load(visual) if visual.exists() else {};visual_pass=str(vis.get('verdict','')).upper()=='PASS' and vis.get('artifact_set_hash')==current_hash
    if ready and art.get('status')=='PASS' and not visual_pass:issues.append('DRAWING-VISUAL-001: explicit visual QA approval missing/stale for current generated artifact set')
    # Full release requires every drawing definition-ready and verified. Partial artifacts remain useful release candidates but do not make the pack PASS.
    full=bool(all_draw) and ready==all_draw and art.get('status')=='PASS' and visual_pass and not [x for x in issues if not x.startswith('DRAWING-VISUAL-')]
    verdict='PASS' if full else 'PASS_WITH_LIMITATIONS' if ready and art.get('status')=='PASS' else 'HOLD'
    metrics={'drawings_total':len(all_draw),'definition_ready':len(ready),'pdf_generated':len(pdfs),'native_generated':len(natives),'visual_approval':visual_pass,'artifact_set_hash':current_hash}
    payload={'schema':'k01.drawing_verify.gate04e.v1_8','verdict':verdict,'metrics':metrics,'per_drawing':per,'issues':issues,'policy':'Per-drawing candidate generation is allowed. Full release requires all required drawings definition-ready + SLDDRW/PDF + current visual QA.'};dump(out,payload);register_build(r,'K01.DRAWING.VERIFY.GATE04E',{'tool':'verify_drawing_pack_v1_8.py'});register_verify(r,'K01.DRAWING.VERIFY.GATE04E',verdict,metrics=metrics,limitations=issues);print(verdict,'drawing verification');[print(' -',x) for x in issues];return 0 if verdict in ('PASS','PASS_WITH_LIMITATIONS') else 1
if __name__=='__main__':raise SystemExit(main())
