"""Read-only, bounded export of the files needed for dispatcher integration."""
import hashlib
import io
import json
import zipfile


def collect(model):
    paths = ['run.cmd', 'tools/run.py', 'tools/cli/k01_cli.py', 'tools/pds/k01_pds.py', 'tools/assurance/build_center_state.py', 'tools/cad/d006_candidate_authoring.py', 'control/commands/K01_COMMAND_CATALOG.json']
    paths += list(model.cfg.get('p007_documents', {}).values())
    paths += [model.selected_path(k) for k in ('verdict', 'graph', 'requirements', 'actuator_requirements')]
    manifest = []
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as archive:
        for raw in dict.fromkeys(p for p in paths if p):
            row = {'path': raw}
            try:
                p = model.resolve(raw)
                relative = p.relative_to(model.root).as_posix()
                if not p.is_file():
                    row['state'] = 'MISSING'
                elif p.stat().st_size > 5_000_000:
                    row['state'] = 'TOO_LARGE'
                else:
                    content = p.read_bytes()
                    archive.writestr('project/' + relative, content)
                    row.update(state='INCLUDED', sha256=hashlib.sha256(content).hexdigest())
            except (OSError, ValueError) as exc:
                row.update(state='ERROR', error=str(exc))
            manifest.append(row)
        archive.writestr('manifest.json', json.dumps(manifest, indent=2))
    return data.getvalue()
