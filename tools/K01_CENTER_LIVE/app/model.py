"""Presentation adapter. Never evaluates engineering acceptance."""
import hashlib, json, mimetypes, subprocess, os, sys, re
from workflow import connect
from p007 import build_case
from pathlib import Path
from datetime import datetime, timezone
DEFAULTS = {'verdict': 'evidence/verdict.json', 'graph': 'control/graph.json', 'ebom': 'reports/bom/current/K01_EBOM_A001_CURRENT.json', 'mbom': 'reports/bom/current/K01_MBOM_A001_CURRENT.json', 'artifacts': 'evidence/current/K01_EVIDENCE_INDEX.json', 'ledger': 'evidence/ledger.jsonl', 'cad_root': None, 'commands': {'verdict': ['verdict'], 'audit': ['audit'], 'selftest': ['selftest']}}

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def records(value):
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        return [dict(v, id=v.get('id', k)) for k, v in value.items() if isinstance(v, dict)]
    return []

def reasons(v):
    x = v.get('reasons', v.get('reason', v.get('why', v.get('issues', v.get('open_items', [])))))
    return x if isinstance(x, list) else [x] if x else []

class Model:

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.cfg = dict(DEFAULTS)
        p = Path(__file__).resolve().parents[1] / 'settings.json'
        if p.exists():
            self.cfg.update(json.loads(p.read_text(encoding='utf-8-sig')))
        self.cfg['commands'] = self.available_commands()
        self.files = {}

    def dispatcher_argv(self):
        return ['cmd.exe', '/d', '/c', str(self.root / 'run.cmd')] if os.name == 'nt' else [sys.executable, str(self.root / 'tools/run.py')]

    def available_commands(self):
        self.capabilities = {'state': 'NOT_CONNECTED', 'reason': 'Enable capability_query_enabled only after the dispatcher implements --list --json.'}
        if not self.cfg.get('capability_query_enabled'):
            return {}
        try:
            result = subprocess.run(self.dispatcher_argv() + ['--list', '--json'], cwd=self.root, capture_output=True, text=True, encoding='utf-8', timeout=10)
            if result.returncode:
                raise ValueError('Capability query failed: ' + result.stderr[-1000:])
            data = json.loads(result.stdout)
            if data.get('schema') != 'k01.commands.v1' or not isinstance(data.get('commands'), list):
                raise ValueError('Unsupported capability schema')
            allowed = {}
            for c in data['commands']:
                if not isinstance(c, dict):
                    raise ValueError('Invalid command record')
                name = c.get('id')
                args = c.get('argv')
                if not isinstance(name, str) or not isinstance(args, list) or (not args) or (not all((isinstance(x, str) and re.fullmatch('[A-Za-z0-9_.-]+', x) for x in args))):
                    raise ValueError('Invalid command ID/arguments')
                if c.get('center_enabled') is True:
                    allowed[name] = args
            self.capabilities = {'state': 'CONNECTED', 'document': data}
            return allowed
        except (ValueError, OSError, subprocess.TimeoutExpired) as e:
            self.capabilities = {'state': 'ERROR', 'reason': str(e)}
            return {}

    def resolve(self, raw):
        p = Path(raw)
        p = (self.root / p).resolve() if not p.is_absolute() else p.resolve()
        roots = [self.root]
        if self.cfg.get('cad_root'):
            roots.append(Path(self.cfg['cad_root']).resolve())
        if not any((p.is_relative_to(r) for r in roots)):
            raise ValueError('Path outside configured roots')
        return p

    def register(self, p):
        p = self.resolve(str(p))
        key = hashlib.sha256(str(p).encode()).hexdigest()[:24]
        self.files[key] = p
        return key

    def selected_path(self, key):
        return self.cfg.get('sources', {}).get(key)

    def source_candidates(self):
        paths = ['evidence/verdict.json', 'evidence/current/K01_CENTER_VIEW.json', 'reports/center/K01_CENTER_STATE_CURRENT.json', 'control/center/K01_CENTER_INPUT_CURRENT.json', 'control/project/K01_PROJECT_CLOSURE_MATRIX.json', 'control/state/K01_STATE_CURRENT_v8.json', 'control/command_center/data/K01_control_state_v1.json']
        return [p for p in paths if (self.root / p).is_file()]

    def source(self, key):
        raw = self.selected_path(key)
        info = {'path': raw, 'state': 'MISSING', 'sha256': None, 'file_id': None}
        if not raw:
            info.update(state='MISSING', error='No source declared in settings.json')
            return ({}, info)
        try:
            p = self.resolve(raw)
            if not p.is_file():
                return ({}, info)
            data = p.read_bytes()
            info.update(state='AVAILABLE', sha256=hashlib.sha256(data).hexdigest(), file_id=self.register(p), modified=datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat())
            d = json.loads(data.decode('utf-8-sig'))
            if not isinstance(d, (dict, list)):
                raise ValueError('JSON object or array expected')
            return (d, info)
        except (OSError, ValueError) as e:
            info.update(state='ERROR', error=str(e))
            return ({}, info)

    def git_state(self):
        try:

            def call(args):
                r = subprocess.run(['git', '-C', str(self.root)] + args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
                if r.returncode:
                    raise ValueError(r.stderr.strip())
                return r.stdout.strip()
            branch = call(['branch', '--show-current'])
            head = call(['rev-parse', 'HEAD'])
            history = call(['log', '-12', '--format=%h%x09%aI%x09%s'])
            return {'state': 'AVAILABLE', 'branch': branch, 'head': head, 'commits': [dict(zip(['hash', 'date', 'subject'], x.split('\t', 2))) for x in history.splitlines()]}
        except (OSError, ValueError, subprocess.TimeoutExpired) as e:
            return {'state': 'UNAVAILABLE', 'reason': str(e)}

    def state(self):
        self.files = {}
        docs = {}
        sources = {}
        for key in ['verdict', 'graph', 'graph_authority', 'assurance_coherence', 'ebom', 'mbom', 'artifacts', 'requirements', 'actuator_requirements']:
            docs[key], sources[key] = self.source(key)
        v = docs['verdict']
        v = v if isinstance(v, dict) else {}
        if sources['verdict']['state'] == 'AVAILABLE' and v.get('schema') != 'k01.center.view.v3':
            sources['verdict'].update(state='UNSUPPORTED_SCHEMA', error='Expected k01.center.view.v3')
            v = {}
        raw = v.get('overall', v.get('verdict', v.get('production_release')))
        if raw is None and isinstance(v.get('release_readiness'), dict):
            raw = v['release_readiness'].get('status')
        if raw is None and sources['verdict']['path'] == 'evidence/verdict.json':
            raw = v.get('status')
        if isinstance(raw, dict):
            raw = raw.get('status')
        if sources['verdict']['state'] == 'AVAILABLE' and (not isinstance(raw, str)):
            raw = 'NOT_REPORTED'
        overall = raw if sources['verdict']['state'] == 'AVAILABLE' else sources['verdict']['state']
        groups = {k: records(v.get(k, [])) for k in ['nodes', 'requirements', 'gates', 'blockers']}
        groups['nodes'] = records(v.get('graph', []))
        req = docs['requirements']
        if isinstance(req, dict) and req.get('schema') == 'k01.requirements.v1' and isinstance(req.get('requirements'), list):
            groups['requirements'] = records(req['requirements'])
        elif isinstance(req, dict) and req.get('schema') == 'k01.release_requirements.current.v1' and isinstance(req.get('requirements'), dict):
            groups['requirements'] = [dict(x, status=x.get('requirement_status', 'NOT_DECLARED'), source=sources['requirements']['path']) for x in records(req['requirements'])]
        elif sources['requirements']['state'] == 'AVAILABLE':
            sources['requirements'].update(adapter_state='DOCUMENT_ONLY', note='Source connected. Structured requirement mapping is not yet verified; inspect the original document.')
        for rs in groups.values():
            for x in rs:
                x['reasons'] = reasons(x)
                x.setdefault('status', x.get('severity', 'NOT_DECLARED'))
        blockers = groups['blockers']
        boms = {}
        for k in ['ebom', 'mbom']:
            d = docs[k]
            d = d if isinstance(d, dict) else {}
            boms[k] = {'status': d.get('status', sources[k]['state']), 'rows': records(d.get('rows', d.get('items', []))), 'reasons': reasons(d), 'transformations': d.get('manufacturing_transformations', [])}
        if not blockers:
            for key, bom in boms.items():
                for i, reason in enumerate(bom['reasons']):
                    blockers.append({'id': key.upper() + '-' + str(i + 1), 'status': bom['status'], 'reasons': [reason], 'source': sources[key]['path']})
        d = docs['artifacts']
        ars = records(d if isinstance(d, list) else d.get('artifacts', d.get('entries', d.get('items', []))))
        for a in ars:
            raw = a.get('path', a.get('file_path'))
            a['file_id'] = None
            if not raw and a.get('candidates'):
                base = Path(self.cfg.get('cad_root') or str(self.root / 'cad')) if a.get('root') == 'cad' else self.root
                if a.get('root') == 'cad' and (base / 'cad').is_dir():
                    base = base / 'cad'
                choices = [base / str(c) for c in a['candidates']]
                raw = str(next((p for p in choices if p.is_file()), choices[0]))
                a['path'] = raw
            if not isinstance(raw, str):
                a['availability'] = 'NO_PATH'
                continue
            try:
                p = self.resolve(raw)
                a['availability'] = 'AVAILABLE' if p.is_file() else 'MISSING'
                if p.is_file():
                    a['file_id'] = self.register(p)
                    a['extension'] = p.suffix.lower()
            except (ValueError, OSError):
                a['availability'] = 'OUTSIDE_ROOT'
        coherence = docs.get('assurance_coherence') if isinstance(docs.get('assurance_coherence'), dict) else {}
        coherence_status = coherence.get('status') if sources.get('assurance_coherence', {}).get('state') == 'AVAILABLE' else sources.get('assurance_coherence', {}).get('state', 'MISSING')
        if coherence_status == 'PASS_ASSURANCE_COHERENCE':
            action_lock = {'state':'UNLOCKED','reason':'Cross-layer assurance coherence is proven. Engineering gates still control each action.'}
        elif coherence_status == 'HOLD_ASSURANCE_COHERENCE':
            action_lock = {'state':'LOCKED','reason':'Cross-layer assurance coherence is HOLD; mutation/stage-transition actions must remain disabled.','blocking_checks':[c.get('id') for c in coherence.get('checks',[]) if isinstance(c,dict) and not c.get('pass',False)]}
        else:
            action_lock = {'state':'UNKNOWN','reason':'Assurance coherence report is unavailable or unsupported; mutation/stage-transition actions must not be enabled.'}
        catalog = connect(self, docs, ars)
        history = []
        history_errors = []
        try:
            p = self.resolve(self.cfg['ledger'])
            if p.exists():
                lines = p.read_text(encoding='utf-8-sig').splitlines()
                for i, line in enumerate(lines[-200:], max(1, len(lines) - 199)):
                    try:
                        history.append(json.loads(line))
                    except ValueError:
                        history_errors.append(f'Ledger line {i}: invalid JSON')
        except (ValueError, OSError) as e:
            history_errors.append(str(e))
        checks = []
        for item in v.get('inputs', []):
            if not isinstance(item, dict) or not item.get('path'):
                continue
            expected = item.get('sha256', item.get('physical_sha256'))
            obs = 'UNVERIFIED'
            try:
                p = self.resolve(item['path'])
                obs = 'MISSING' if not p.is_file() else ('MATCH' if digest(p) == expected else 'CHANGED') if expected else 'UNVERIFIED'
            except (ValueError, OSError):
                obs = 'ERROR'
            checks.append({'path': item['path'], 'state': obs})
        return {'p007': build_case(self, blockers, ars, boms), 'requirement_documents': {k: docs[k] for k in ['requirements', 'actuator_requirements']}, 'source_candidates': self.source_candidates(), 'capabilities': self.capabilities, 'command_catalog': catalog, 'git': self.git_state(), 'schema': 'k01.center.view.v1', 'overall': overall, 'generated_utc': v.get('generated_utc', v.get('generated', v.get('utc'))), 'sources': sources, 'groups': groups, 'blockers': blockers, 'boms': boms, 'graph': docs['graph'], 'graph_authority': docs.get('graph_authority', {}), 'assurance_coherence': coherence, 'action_lock': action_lock, 'artifacts': ars, 'history': list(reversed(history)), 'history_errors': history_errors, 'input_checks': checks, 'freshness': v.get('freshness', 'NOT_DECLARED'), 'commands': list(self.cfg['commands']), 'repo_root': str(self.root), 'source_mode': 'EXPLICIT_SOURCE', 'source_document': v}
