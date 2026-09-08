from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from medtas_v16_common import load,dump

def root_hash(art):
    rows=sorted((x.get('drawing_no'),x.get('kind'),x.get('sha256')) for x in art.get('artifacts',[]) or [])
    return hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--approver',default='LOCAL_ENGINEER');a=ap.parse_args();r=Path(a.repo_root).resolve();apath=r/'reports/medtas/drawing/current/K01_DRAWING_ARTIFACT_GATE04E_v1_8.json';out=r/'reports/medtas/drawing/current/K01_DRAWING_VISUAL_APPROVAL_GATE04E_v1_8.json'
    if not apath.exists():print('BLOCKED: drawing artifact manifest missing');return 2
    art=load(apath)
    if art.get('status')!='PASS' or not art.get('artifacts'):print('BLOCKED: no current generated drawing artifact set to approve');return 3
    h=root_hash(art);print('Visual QA is a human release action. Review every CURRENT generated PDF/SLDDRW for clipping, overlap, ambiguity, scale, view coverage and title-block correctness.');print('Artifact set hash:',h);print('Generated drawings:',', '.join(art.get('generated_drawings',[]) or []));ans=input('Type APPROVE exactly to record visual QA for THIS artifact set: ').strip()
    if ans!='APPROVE':print('No approval recorded.');return 1
    payload={'schema':'k01.drawing_visual_approval.gate04e.v1_8','verdict':'PASS','approver':a.approver,'approved_at_utc':datetime.now(timezone.utc).isoformat(),'artifact_set_hash':h,'generated_drawings':art.get('generated_drawings',[]),'artifacts':art.get('artifacts',[]),'criteria':['no overlap/clipping','views communicate function','dimensions/PMI legible','no contradictory/duplicate release dimensions','title block/revision/model identity correct','PDF and SLDDRW correspond to same release candidate'],'note':'Approval is invalidated automatically if the drawing artifact set hash changes. Partial candidate packs can be approved visually without implying full drawing-pack release.'};dump(out,payload);print('PASS visual approval recorded:',out);return 0
if __name__=='__main__':raise SystemExit(main())
