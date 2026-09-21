"""P007/D006 work surface. Suggested actions never change source verdicts."""
import json

def work_item(record, actions):
    item = dict(record)
    action = actions.get(item.get('id'), {})
    item.update(
        suggested_action=action.get('next_action', 'NOT_DECLARED: no next action in the product definition'),
        expected_evidence=action.get('expected_evidence', 'NOT_DECLARED: no completion evidence in the product definition'),
        action_source='product_definition.work_items' if action else None,
    )
    return item


def build_case(model, blockers, artifacts, boms):
    documents = []
    for label, path in model.cfg.get('p007_documents', {}).items():
        row = {'label': label, 'path': path, 'availability': 'MISSING', 'file_id': None}
        try:
            p = model.resolve(path)
            if p.is_file():
                row.update(availability='AVAILABLE', file_id=model.register(p))
                data = json.loads(p.read_text(encoding='utf-8-sig'))
                row['source_document'] = data
                row['schema'] = data.get('schema') if isinstance(data, dict) else None
        except (OSError, ValueError) as exc:
            row.update(availability='ERROR', error=str(exc))
        documents.append(row)
    actions = {}
    for document in documents:
        body = document.get('source_document', {})
        if isinstance(body, dict) and isinstance(body.get('work_items'), list):
            for item in body['work_items']:
                if isinstance(item, dict) and isinstance(item.get('id'), str):
                    if item['id'] in actions:
                        actions[item['id']] = {'next_action': 'CONFLICT: duplicate work item ID; resolve source definitions', 'expected_evidence': 'NOT_DECLARED'}
                    else:
                        actions[item['id']] = item
    requirements = []
    try:
        req, info = model.source('requirements')
        definition = next((d.get('source_document', {}) for d in documents if d['label'] == 'Drawing release definition'), {})
        if req.get('schema') == 'k01.release_requirements.current.v1' and definition.get('schema') == 'k01.d006.release_definition.v1':
            for role, identity in definition.get('requirements', {}).items():
                record = req.get('requirements', {}).get(identity)
                requirements.append(dict(record, role=role) if isinstance(record, dict) else {'id':identity,'role':role,'requirement_status':'MISSING'})
    except (ValueError, OSError, AttributeError):
        pass
    def relevant(x):
        text = str(x).upper()
        return any(t in text for t in ('P007', 'P-007', 'D006', 'D-006', 'DRAWINGS_DIMXPERT'))
    unique = {}
    for a in artifacts:
        if relevant(a):
            unique[a.get('file_id') or a.get('path')] = a
    return {
        'requirements': requirements,
        'title': 'P007 / D006 — product definition and drawing',
        'issues': [work_item(b, actions) for b in blockers if relevant(b)],
        'documents': documents,
        'artifacts': list(unique.values()),
        'parts': [r for r in boms['ebom']['rows'] if r.get('part_number', r.get('PartNo')) == 'K01-P-007'],
        'action_policy': 'Actions come from exact work item IDs in source documents. Missing guidance remains NOT_DECLARED.',
    }
