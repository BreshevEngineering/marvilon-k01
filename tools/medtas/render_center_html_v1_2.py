#!/usr/bin/env python3
from __future__ import annotations
import argparse,html,json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def esc(x): return html.escape(str(x or ''))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); ap.add_argument('--feed',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); root=Path(a.repo_root); f=load(a.feed)
    rows=''.join(f"<tr><td><code>{esc(n['node_id'])}</code></td><td>{esc(n['title'])}</td><td><b>{esc(n['state'])}</b></td><td>{esc('; '.join(n.get('reasons',[])))}</td></tr>" for n in f['nodes'])
    ev=[]
    for e in f.get('evidence',[]):
        links=[]
        for x in e.get('files',[]):
            rel=x['path']; href='../'+rel.replace('reports/','') if rel.startswith('reports/') else '../../'+rel
            links.append(f"<a href='{esc(href)}'>{esc(Path(rel).name)}</a>" if x.get('exists') else f"<span class='missing'>{esc(Path(rel).name)} MISSING</span>")
        ev.append(f"<div class='card'><h3>{esc(e.get('title'))}</h3><p>{esc(e.get('summary'))}</p><p>{' · '.join(links)}</p></div>")
    fr=''.join(f"<li><code>{esc(x['node_id'])}</code> — {esc(x['title'])} <b>{esc(x['state'])}</b></li>" for x in f.get('frontier',[])) or '<li>No immediate frontier node.</li>'
    fail=''
    if f.get('last_failure'):
        lf=f['last_failure']; fail=f"<div class='fail'><b>Last failure:</b> {esc(lf.get('stage'))}: {esc(lf.get('error'))}</div>"
    css="body{font-family:Segoe UI,Arial,sans-serif;margin:28px;background:#f5f7fa;color:#17202a}h1,h2{margin:.2em 0}.grid{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:10px;margin:18px 0}.kpi,.card{background:white;border:1px solid #d7dee8;border-radius:10px;padding:14px}.kpi b{font-size:22px}table{width:100%;border-collapse:collapse;background:white}th,td{border-bottom:1px solid #e4e8ee;padding:9px;text-align:left;vertical-align:top}th{background:#eef2f6;position:sticky;top:0}.fail{background:#fff1f0;border:1px solid #ffccc7;padding:12px;border-radius:8px}.missing{color:#a8071a}code{font-family:Consolas,monospace}.small{font-size:12px;color:#5b6573}"
    counts=f['summary']['counts']; kpis=''.join(f"<div class='kpi'><div>{esc(k)}</div><b>{v}</b></div>" for k,v in sorted(counts.items()))
    doc=f"<!doctype html><html><head><meta charset='utf-8'><title>K01 MEDTAS Center</title><style>{css}</style></head><body><h1>K01 MEDTAS Engineering Build Graph</h1><div class='small'>Generated materialized view. Do not edit as source of truth.</div>{fail}<div class='grid'>{kpis}</div><h2>Next frontier</h2><ul>{fr}</ul><h2>Registered evidence</h2>{''.join(ev)}<h2>Nodes</h2><table><thead><tr><th>Node</th><th>Title</th><th>State</th><th>Reason</th></tr></thead><tbody>{rows}</tbody></table></body></html>"
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(doc,encoding='utf-8')
if __name__=='__main__': main()
