from __future__ import annotations
import argparse,json,sys,subprocess
from datetime import datetime,timezone
from pathlib import Path

THIS=Path(__file__).resolve(); REPO=THIS.parents[2]
if str(REPO) not in sys.path: sys.path.insert(0,str(REPO))
from tools.repo.control_namespace_guard import audit as namespace_audit

CONTRACT=Path('control/project/K01_ACTIVE_STEP_GATE.json')
CHECKPOINT=Path('control/project/K01_CHECKPOINT_CURRENT.json')
REPORT=Path('reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json')

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def get(obj,path):
    v=obj
    for k in path:
        if not isinstance(v,dict) or k not in v:return None
        v=v[k]
    return v

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default='.');a=ap.parse_args();root=Path(a.repo_root).resolve()
    rows=[]
    def add(name,ok,actual=None,expected=None): rows.append({'check':name,'status':'PASS' if ok else 'FAIL','actual':actual,'expected':expected})
    c=load(root/CONTRACT); cp=load(root/CHECKPOINT)
    add('checkpoint matches active step',cp.get('checkpoint_id')==c.get('checkpoint_id'),cp.get('checkpoint_id'),c.get('checkpoint_id'))
    for rel in c.get('required_files') or []: add('required file '+rel,(root/rel).is_file(),rel,'exists')
    # Source availability is checked directly from the current source contract.
    # AI handoff ZIP freshness is transport/session state and is intentionally not
    # an engineering authority for the active step.
    source_contract_path=root/'control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json'
    add('source contract exists',source_contract_path.is_file(),str(source_contract_path),'exists')
    if source_contract_path.is_file():
        sc=load(source_contract_path)
        for rel in sc.get('required') or []:
            add('required source '+rel,(root/rel).is_file(),rel,'exists on disk')
    ns=namespace_audit(root);add('control namespace guard',str(ns.get('status','')).startswith('PASS'),ns.get('status'),'PASS*')
    rg=subprocess.run([sys.executable,str(root/'tools/repo/repo_guard.py'),'--repo-root',str(root),'--live'],cwd=str(root),capture_output=True,text=True,errors='replace')
    add('repository migration guard',rg.returncode==0,rg.stdout.strip() or rg.stderr.strip(),'repo_guard PASS')
    for spec in c.get('required_statuses') or []:
        p=root/spec['file']; obj=load(p) if p.is_file() else {}; actual=get(obj,spec.get('path') or [])
        vals=spec.get('allowed_values') or []; prefs=spec.get('allowed_prefixes') or []
        ok=(actual in vals) if vals else any(str(actual).startswith(x) for x in prefs)
        add('status '+spec['file']+'::'+'.'.join(spec.get('path') or []),ok,actual,vals or prefs)
    impacts=c.get('impact_declarations') or {}
    required_impacts=['requirements','materials','bom','dimxpert_drawings','inspection','dependencies','technical_filter','rollback','evidence']
    for k in required_impacts:add('impact declaration '+k,bool(str(impacts.get(k,'')).strip()),impacts.get(k),'non-empty')
    ok=all(x['status']=='PASS' for x in rows)
    rep={'schema':'k01.engineering_step_gate.v1','generated_utc':datetime.now(timezone.utc).isoformat(),'step_id':c.get('step_id'),'intent':c.get('intent'),'status':c.get('result_on_pass') if ok else 'HOLD_STEP_GATE','mutation_authorized':bool(c.get('mutation_authorized')) if ok else False,'checks':rows,'control_namespace':ns,'impact_declarations':impacts,'rule':'A step gate confirms control/evidence readiness for the declared intent only. It never upgrades OPEN release evidence.'}
    out=root/REPORT;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('engineering_step_gate:',rep['status'],'mutation_authorized=',rep['mutation_authorized']);print('REPORT:',out)
    for x in rows:
        if x['status']!='PASS': print('HOLD:',x['check'],'actual=',x['actual'],'expected=',x['expected'])
    return 0 if ok else 2
if __name__=='__main__':raise SystemExit(main())
