"""Install reviewed routes with exact-input guard; retain the original dispatcher."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent


def install(root, expected, app=APP):
    root = Path(root)
    target = root / 'run.cmd'
    source = app / 'integration/k01_center_routes.py'
    dst = root / 'tools/cli/k01_center_routes.py'
    spec = importlib.util.spec_from_file_location('routes', source)
    routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(routes)
    current = target.read_bytes()
    marker = b'REM K01 CENTER ROUTES V1'
    if marker in current:
        if not dst.is_file() or dst.read_bytes() != source.read_bytes():
            raise ValueError('Existing Center route implementation differs; no overwrite performed.')
        return
    if hashlib.sha256(current).hexdigest() != expected:
        raise ValueError('run.cmd changed since the supplied integration package. No project files changed. Export a new integration package.')
    if dst.exists():
        raise ValueError('Route target already exists; no overwrite performed.')
    backup = app / 'runtime/dispatcher_backup'
    backup.mkdir(parents=True, exist_ok=True)
    (backup / 'run.cmd.original').write_bytes(current)
    prefix = ['@echo off', marker.decode()]
    for name in ['--list'] + list(routes.ROUTES):
        prefix.append('if /I "%~1"=="' + name + '" goto K01_CENTER_DISPATCH_V1')
    prefix += ['goto K01_ORIGINAL_DISPATCH_V1', ':K01_CENTER_DISPATCH_V1',
               'py -3 "%~dp0tools\\cli\\k01_center_routes.py" %*',
               'exit /b %ERRORLEVEL%', ':K01_ORIGINAL_DISPATCH_V1']
    updated = ('\r\n'.join(prefix) + '\r\n').encode('ascii') + current
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(source.read_bytes())
    try:
        temp = target.with_suffix('.cmd.center-tmp')
        temp.write_bytes(updated)
        os.replace(temp, target)
    except Exception:
        dst.unlink()
        raise
    (backup / 'manifest.json').write_text(json.dumps({'original_sha256': expected, 'installed_sha256': hashlib.sha256(updated).hexdigest()}, indent=2))


if __name__ == '__main__':
    try:
        cfg = json.loads((APP / 'settings.json').read_text())
        expected = (HERE / 'expected_run_sha256.txt').read_text().strip()
        install(cfg['repo_root'], expected)
        cfg['capability_query_enabled'] = True
        (APP / 'settings.json').write_text(json.dumps(cfg, indent=2))
        print('Center routes connected. Original dispatcher saved in runtime/dispatcher_backup.')
    except Exception as exc:
        print('CONNECT FAILED: ' + str(exc))
        raise SystemExit(2)
