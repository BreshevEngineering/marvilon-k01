"""Inventory evidence, not an authoritative requirements registry."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def inventory(root):
    root = Path(root).resolve()
    files, occurrences, errors = [], [], []
    # Inventory the control tree; historical sources are retained and labelled.
    for path in sorted((root / 'control').rglob('*.json')):
        if not path.resolve().is_relative_to(root):
            errors.append({'path': str(path), 'error': 'Outside repository root'})
            continue
        rel = path.relative_to(root).as_posix()
        try:
            if path.stat().st_size > 10_000_000:
                errors.append({'path': rel, 'error': 'Too large; not inspected'})
                continue
            raw = path.read_bytes()
            data = json.loads(raw.decode('utf-8-sig'))
        except (OSError, ValueError) as exc:
            errors.append({'path': rel, 'error': str(exc)})
            continue
        if 'requirement' not in rel.lower() and not (isinstance(data, dict) and 'requirements' in data):
            continue
        historical = any(x in path.parts for x in ('history', 'archive', 'retired'))
        files.append({'path': rel, 'sha256': hashlib.sha256(raw).hexdigest(), 'schema': data.get('schema') if isinstance(data, dict) else None, 'historical': historical})
        collection = data.get('requirements') if isinstance(data, dict) else None
        if isinstance(collection, dict):
            rows = [(key, v) for key, v in collection.items() if isinstance(v, dict)]
        elif isinstance(collection, list):
            rows = [(str(i), v) for i, v in enumerate(collection) if isinstance(v, dict)]
        else:
            rows = []
        for key, record in rows:
            identity = record.get('id', key)
            # Keep exact records: no synthetic release or verification verdict.
            occurrences.append({'id': identity, 'source': rel, 'historical': historical, 'record': record,
                'missing_traceability_fields': [k for k in ('source', 'verification_method') if not record.get(k)]})
    for path in sorted((root/'control').rglob('*')):
        if path.is_file() and path.suffix.lower() in {'.csv', '.xlsx', '.md', '.docx'} and 'requirement' in path.relative_to(root).as_posix().lower():
            try:
                if not path.resolve().is_relative_to(root):
                    raise ValueError('Outside repository root')
                if path.stat().st_size > 10_000_000:
                    raise ValueError('Too large; not inspected')
                raw = path.read_bytes()
                files.append({'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'schema':None,'parse_state':'DOCUMENT_ONLY','historical':any(x in path.parts for x in ('history','archive','retired'))})
            except (OSError,ValueError) as exc:
                errors.append({'path':str(path),'error':str(exc)})
    by_id = defaultdict(list)
    for row in occurrences:
        by_id[str(row['id'])].append(row)
    duplicates = []
    for identity, rows in by_id.items():
        active = [r for r in rows if not r['historical']]
        if len(active) > 1:
            variants = {json.dumps(r['record'], sort_keys=True) for r in active}
            duplicates.append({'id': identity, 'sources': [r['source'] for r in active], 'observation': 'DIFFERENT_RECORDS_REVIEW' if len(variants)>1 else 'REPEATED_RECORD'})
    return {'schema': 'k01.requirements.inventory.v1', 'generated_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'JSON files under control; top-level requirements collections only. Other forms remain unparsed.',
            'repo_root': str(root), 'files': files, 'occurrences': occurrences, 'duplicate_ids': duplicates, 'errors': errors,
            'authority': 'INVENTORY_ONLY: duplicates are observations, not automatic conflicts; missing fields require source review.'}
