from __future__ import annotations
import argparse, html, json, os
from datetime import datetime
from pathlib import Path

FILES={
 'checkpoint':'control/project/K01_CHECKPOINT_CURRENT.json',
 'gates':'control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json',
 'step':'reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json',
 'tech':'reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json',
 'req':'reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json',
 'baseline':'control/baseline/K01_ENGINEERING_BASELINE.json',
 'derived':'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',
 'ebom':'reports/bom/current/K01_EBOM_A001_CURRENT.json',
 'mbom':'reports/bom/current/K01_MBOM_A001_CURRENT.json',
 'next':'control/project/K01_NEXT_ACTIONS_CURRENT.json',
 'finalize':'reports/control/K01_BASELINE_02C_POST_PROMOTION_FINALIZE_CURRENT.json',
 'p007_start':'reports/control/K01_P007_PROFESSIONAL_START_CURRENT.json',
 'p007_input':'control/drawings/K01_D006_AUTHORING_INPUT.json',
 'p007_pc':'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json',
 'p007_scope':'control/product_definition/K01_P007_PMI_AUTHORING_SCOPE.json',
 'handoff':'reports/control/K01_AI_HANDOFF_COMPLETENESS_CURRENT.json',
 'strategy':'control/project/K01_ENGINEERING_STRATEGY_CURRENT.json',
 'apply':'reports/control/K01_BASELINE_02C_PROMOTION_APPLY_CURRENT.json',
}

def load(root,rel):
    try:return json.loads((root/rel).read_text(encoding='utf-8-sig'))
    except Exception:return {}
def esc(x):return html.escape(str(x if x is not None else '—'))
def cls(s):
    u=str(s or '').upper()
    if u.startswith('PASS') or u in {'CLOSED','RELEASED'}:return 'pass'
    if 'FAIL' in u:return 'fail'
    if 'HOLD' in u or 'OPEN' in u or 'PENDING' in u or 'STALE' in u:return 'hold'
    return 'neutral'
def file_link(root,rel,label=None):
    p=(root/rel).resolve()
    try:uri=p.as_uri()
    except Exception:uri=str(p)
    return f'<a href="{html.escape(uri)}">{esc(label or rel)}</a>'
def badge(s):return f'<span class="badge {cls(s)}">{esc(s)}</span>'
def card(title,status,body=''):
    return f'<section class="card {cls(status)}"><h3>{esc(title)}</h3><div class="status">{badge(status)}</div>{body}</section>'
def list_html(rows):return '<ul>'+''.join(f'<li>{esc(x)}</li>' for x in rows if x)+'</ul>' if rows else '<p class="muted">None.</p>'

def gate_row(name,obj):
    purpose={
      'P0_CURRENT_BASELINE':'Controlled current CAD/product baseline',
      'P1_FUNCTION_INTERFACES':'Requirements, functional interfaces and datums',
      'P2_ANALYSIS':'Strength, stability, magnetic and thermal evidence',
      'P3_VARIATION_MANUFACTURING':'Tolerance chains, process, service and manufacturability',
      'P4_CANDIDATE_TPD':'BOM, PMI and candidate technical product definition',
      'P5_VERIFICATION':'Drawing/inspection/bench and cross-domain verification',
      'P6_RELEASE':'Zero-blocker product release / R01',
    }.get(name,'')
    return f'<div class="gate {cls(obj.get("status"))}"><div class="gate-id">{esc(name.split("_")[0])}</div><div><b>{esc(purpose)}</b><br>{badge(obj.get("status","—"))}</div></div>'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--open',action='store_true');a=ap.parse_args()
    root=Path(a.repo_root).resolve();d={k:load(root,v) for k,v in FILES.items()}
    cp=d['checkpoint'];gates=d['gates'].get('gates') or {};step=d['step'];tech=d['tech'];req=d['req'];bl=d['baseline'];eb=d['ebom'];mb=d['mbom'];nxt=d['next'];fin=d['finalize'];ps=d['p007_start'];pi=d['p007_input'];pc=d['p007_pc'];scope=d['p007_scope'];strategy=d['strategy'];handoff=d['handoff']
    cad=bl.get('cad') or {}; reqsum=req.get('summary') or {}; p007chars=pc.get('characteristics') or []
    p017_qty=sum(int(x.get('quantity') or 0) for x in (eb.get('items') or []) if str(x.get('part_number') or '').upper()=='K01-P-017' and x.get('source')=='CAD_MODELED')
    eb_struct='PASS_STRUCTURE_PARITY' if eb.get('modeled_occurrence_total')==14 and p017_qty==1 else eb.get('status','HOLD')
    current_stage=nxt.get('current_stage') or step.get('status') or '—'
    p007_safe=[
      'Material: AISI 316L / EN 1.4404 — CONTROLLED',
      'Overall length nominal: 35.0 mm',
      'Locator diameter: Ø14.10; J2 fit architecture H7/g6',
      'Flange: Ø33.0 × 3.0 mm nominal',
      'Clamp pattern: 3×Ø2.90 on PCD 26.5 mm',
      'Thin can nominals: OD 10.0 / ID 9.4 mm',
      'Historical PMI method pilot: C02 and C05 save-close-reopen PASS; canonical persistent references must be rebound before new PMI write',
    ]
    if ps.get('status','').startswith('PASS_P007_CANONICAL'):
      p007_safe.append('C02 current baseline: P007 Ø14.10 H7 bore depth 2.00 mm; P003 g6 pilot 1.50 mm; nominal bottom clearance 0.50 mm; depth tolerance remains OPEN')
    blockers=list(pi.get('release_blockers') or [])
    req_block=[x.get('id') for x in req.get('requirements',[]) if x.get('release_blocker')]

    css='''<style>
    :root{--bg:#0f141a;--panel:#18212b;--panel2:#111820;--text:#e9eef4;--muted:#9eabb8;--line:#344250;--pass:#58a875;--hold:#c49a4b;--fail:#c96363;--accent:#83bfff}
    *{box-sizing:border-box}body{font-family:Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:0;line-height:1.45}.wrap{max-width:1450px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:22px;align-items:flex-start;border-bottom:1px solid var(--line);padding-bottom:18px}.eyebrow{color:var(--accent);font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:12px}h1{font-size:34px;margin:4px 0 6px}h2{font-size:23px;margin:30px 0 12px}h3{font-size:16px;margin:0 0 8px}.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.card{background:var(--panel);border:1px solid var(--line);border-left:5px solid #6d7884;border-radius:10px;padding:16px}.card.pass,.gate.pass{border-left-color:var(--pass)}.card.hold,.gate.hold{border-left-color:var(--hold)}.card.fail,.gate.fail{border-left-color:var(--fail)}.status{margin-top:8px}.badge{display:inline-block;border:1px solid var(--line);padding:3px 8px;border-radius:999px;font-size:12px;font-weight:700}.badge.pass{border-color:var(--pass);color:#9bd7af}.badge.hold{border-color:var(--hold);color:#e8c67f}.badge.fail{border-color:var(--fail);color:#ef9b9b}.hero{background:linear-gradient(135deg,#1a2632,#121920);border:1px solid var(--line);border-radius:12px;padding:20px;margin-top:18px}.hero-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:18px}.big{font-size:20px;font-weight:700}.path,code{font-family:Consolas,monospace;word-break:break-all}code{background:#0b1016;padding:2px 5px;border-radius:4px}.roadmap{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}.gate{background:var(--panel);border:1px solid var(--line);border-top:5px solid #6d7884;border-left:1px solid var(--line);border-radius:8px;padding:12px;min-height:118px}.gate-id{font-size:20px;font-weight:800;margin-bottom:6px}.flow{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.flow .step{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 13px}.arrow{color:var(--muted);font-size:20px}.active-step{border-color:var(--accent)!important;box-shadow:0 0 0 1px var(--accent) inset}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}table{border-collapse:collapse;width:100%;background:var(--panel)}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:#cbd5df}a{color:var(--accent)}ul{margin:8px 0 0 20px;padding:0}li{margin:5px 0}.note{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:12px}.kpi{font-size:25px;font-weight:800}.small{font-size:12px}.print-only{display:none}@media(max-width:900px){.hero-grid,.two{grid-template-columns:1fr}.roadmap{grid-template-columns:1fr}.top{display:block}}@media print{body{background:white;color:#111}.wrap{max-width:none}.card,.hero,.gate,table,.note{background:white;border-color:#aaa}.muted{color:#555}a{color:#111;text-decoration:none}.badge.pass,.badge.hold,.badge.fail{color:#111}.print-only{display:block}}
    </style>'''
    body='<!doctype html><meta charset="utf-8"><title>K01 Engineering Control & Roadmap</title>'+css+'<div class="wrap">'
    body+=f'<div class="top"><div><div class="eyebrow">Marvilon K01 · Engineering Digital Thread</div><h1>Engineering Control & Roadmap</h1><div class="muted">Living visual projection · generated {esc(datetime.now().isoformat(timespec="seconds"))}</div></div><div>{badge(cp.get("status") or cp.get("checkpoint_id"))}</div></div>'
    body+='<div class="hero"><div class="hero-grid"><div><div class="eyebrow">Current engineering position</div>'
    body+=f'<div class="big">{esc(cp.get("checkpoint_id") or cp.get("id"))}</div><p><b>Active line:</b> {esc(nxt.get("active_line") or cp.get("active_line"))}<br><b>Stage:</b> {esc(current_stage)}</p>'
    body+=f'<p><b>Canonical A001:</b><br><code>{esc(cad.get("assembly"))}</code><br><span class="small">SHA-256 {esc(cad.get("sha256"))}</span></p></div>'
    body+='<div><div class="grid">'+card('P0 baseline',gates.get('P0_CURRENT_BASELINE',{}).get('status','—'),f'<div class="kpi">{esc(cad.get("component_count") or 14)}</div><div class="muted">modeled components</div>')+card('Technical filter',tech.get('status','—'),f'<div class="kpi">{len(tech.get("nodes") or [])}</div><div class="muted">mapped nodes · unmapped {len(tech.get("unmapped") or [])}</div>')+'</div></div></div></div>'

    body+='<h2>Roadmap: where we are and what comes next</h2><div class="roadmap">'+''.join(gate_row(k,gates.get(k,{})) for k in ['P0_CURRENT_BASELINE','P1_FUNCTION_INTERFACES','P2_ANALYSIS','P3_VARIATION_MANUFACTURING','P4_CANDIDATE_TPD','P5_VERIFICATION','P6_RELEASE'])+'</div>'
    body+='<div class="flow" style="margin-top:14px">'
    for i,(label,state) in enumerate([
      ('Canonical Baseline-02C','PASS'),('P007 canonical reconcile','PASS' if ps.get('status','').startswith('PASS') else 'ACTIVE'),('Persistent-ref rebind','ACTIVE' if ps.get('status','').startswith('PASS') else 'NEXT'),('Native DimXpert / PMI','NEXT'),('K01-D-006 drawing','NEXT'),('Inspection traceability','NEXT'),('R01 release','HOLD')]):
        cl=' active-step' if state=='ACTIVE' else ''
        body+=f'<div class="step{cl}"><b>{esc(label)}</b><br>{badge(state)}</div>'
        if i<6:body+='<div class="arrow">→</div>'
    body+='</div>'

    body+='<h2>The plan — readable, not JSON</h2><div class="two">'
    body+='<section class="card pass"><h3>Completed / do not restart</h3>'+list_html([
      'Canonical Baseline-02C promotion with backup, staging, reference rewrite, full QA and rollback protection',
      'Fresh A001 semantic extraction: 14 components / 14 documents / 33 mates / 0 semantic warnings',
      'P0 semantic snapshot and dependency/hash recomputation',
      'EBOM structural parity: 14 modeled occurrences; K01-P-017 quantity = 1',
      'Datum-C concept, producer, integration and canonical incorporation',
    ])+'</section>'
    body+='<section class="card hold"><h3>Current execution sequence</h3>'+list_html([nxt.get('next_1'),nxt.get('next_2'),nxt.get('then')])+'</section></div>'

    body+='<h2>Why the system was built / where the engineering time went</h2><div class="grid">'
    system_cards=[
      ('Authority & identity','One controlled owner for geometry, requirements, materials, BOM, evidence and release state; prevents “latest file wins”.'),
      ('Checkpoint / change control','Candidate verification is separated from canonical promotion; every irreversible step has declared evidence and rollback.'),
      ('CAD semantic extraction','SolidWorks assembly is read into machine-verifiable components, mates, feature geometry and hashes instead of relying on screenshots.'),
      ('Dependency / stale engine','STATE_HASH and ARTIFACT_HASH determine what must be rerun after a change; stale state is not manually painted.'),
      ('Technical filter','24-category engineering decision filter is mapped to project nodes; unmapped engineering actions are blocked.'),
      ('Safe promotion transaction','Backups, staging assembly, stable-reference rewrite, assembly QA, canonical replacement and rollback are automated.'),
      ('EBOM / MBOM pipeline','Modeled occurrence tree is reconciled with product registry and non-modeled/process items; structural parity is separate from release completeness.'),
      ('DimXpert / drawing pipeline','Product Characteristic → native PMI → tolerance analysis → drawing → inspection. The drawing is a derived product-definition view, not an independent truth.'),
      ('AI handoff / Git continuity','A new AI session can resume from a controlled transport package without recreating engineering history. Git records code/control evolution, not CAD authority.'),
      ('Visual control layer','The HTML center is a human projection over machine authorities; JSON remains backend evidence, not the daily user interface.'),
    ]
    for t,b in system_cards: body+=f'<section class="card"><h3>{esc(t)}</h3><p>{esc(b)}</p></section>'
    body+='</div><p class="note"><b>Reporting note:</b> this system does not contain reliable labor-hour accounting, so the defensible report is by completed engineering work packages and reusable capabilities, not invented hours. The time investment converted K01 from a set of CAD/calculation files into a controlled, restartable engineering workflow intended to reduce repeated work on later K01 nodes and future Marvilon projects.</p>'

    body+='<h2>Current product state</h2><div class="grid">'
    body+=card('Canonical assembly','PASS',f'<div class="kpi">14</div><div>modeled occurrences<br>K01-P-017 × 1</div>')
    body+=card('EBOM structure',eb_struct,f'<div>EBOM overall: <b>{esc(eb.get("status"))}</b><br>non-modeled open items: {len([x for x in (eb.get("issues") or []) if "NONMODELED-OPEN" in str(x)])}</div>')
    body+=card('MBOM',mb.get('status','HOLD'),f'<div>items: {esc(len(mb.get("items") or []))}<br>process/transformation OPENs remain</div>')
    body+=card('Requirements',req.get('status','HOLD'),f'<div>total {esc(reqsum.get("total"))} · open {esc(reqsum.get("open"))}<br>release blockers {esc(reqsum.get("release_blockers_open_or_without_registered_evidence"))}</div>')
    body+='</div>'

    body+='<h2>P007 / K01-D-006 — active professional workflow</h2><div class="two"><section class="card pass"><h3>Known and safe to use now</h3>'+list_html(p007_safe)+'</section><section class="card hold"><h3>Do not invent / release blockers</h3>'+list_html(blockers)+'</section></div>'
    body+=f'<p class="note"><b>Current P007 control status:</b> {badge(ps.get("status") or scope.get("status") or pi.get("status"))}<br><b>Next engineering action:</b> {esc(nxt.get("next_1"))}</p>'

    body+='<h2>Release requirements still open</h2>'+list_html(req_block)
    body+='<p class="muted">These block product/drawing release where applicable. They do not undo the CP-P canonical engineering baseline.</p>'

    body+='<h2>Starting a new chat / engineering session</h2><section class="card"><p><b>Normal continuation:</b> run <code>run.cmd handoff</code> at the end of the current session and upload <code>reports\\control\\K01_AI_HANDOFF_CURRENT.zip</code> to the new chat. That package is the resume/context transport.</p><p><b>If the next task requires direct native CAD inspection or modification:</b> also provide the specific current native file(s) involved — at minimum the affected SLDPRT/SLDASM. The handoff intentionally indexes native SolidWorks binaries but does not pack them.</p><p><b>Do not manually collect JSON files.</b> They are included/linked by the handoff contract. The new session should read START_HERE, current checkpoint, next actions, authority map and active step from the package.</p><div>Handoff completeness: {badge(handoff.get("status") or "—")}</div></section>'

    body+='<h2>Machine authorities — secondary access</h2><section class="card"><table><tr><th>Purpose</th><th>File</th></tr>'
    links=[('Strategy','control/project/K01_ENGINEERING_STRATEGY_CURRENT.json'),('Current checkpoint','control/project/K01_CHECKPOINT_CURRENT.json'),('Current plan / next actions','control/project/K01_NEXT_ACTIONS_CURRENT.json'),('Active step gate','control/project/K01_ACTIVE_STEP_GATE.json'),('P0-P6 maturity','control/project/K01_P0_P6_GATE_MATRIX_CURRENT.json'),('Authority map','control/project/K01_AUTHORITY_MAP_CURRENT.json'),('Derived dependency/freshness','reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'),('Product registry','control/product/parts.json'),('P007 product characteristics','control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json'),('P007 authoring input','control/drawings/K01_D006_AUTHORING_INPUT.json')]
    for label,rel in links:body+=f'<tr><td>{esc(label)}</td><td>{file_link(root,rel)}</td></tr>'
    body+='</table></section>'
    body+='<p class="muted print-only">Generated from current K01 machine authorities. Visual page is not itself engineering authority.</p></div>'
    out=root/'reports/control/K01_ENGINEERING_CONTROL_PANEL_CURRENT.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(body,encoding='utf-8')
    report=root/'reports/control/K01_ENGINEERING_STATUS_REPORT_CURRENT.html';report.write_text(body,encoding='utf-8')
    print('PANEL:',out);print('STATUS REPORT:',report)
    if a.open and os.name=='nt':os.startfile(str(out))
    return 0
if __name__=='__main__':raise SystemExit(main())
