"""Authoritative declaration and execution of the reviewed Center routes."""
import json
import subprocess
import sys
from pathlib import Path

ROUTES = {
    'pds-status': ('Project status', 'tools/pds/k01_pds.py', ['--repo-root', '.', 'status']),
    'pds-next': ('Next engineering task', 'tools/pds/k01_pds.py', ['--repo-root', '.', 'next']),
    'center-build': ('Rebuild Center evidence', 'tools/assurance/build_center_state.py', ['--repo-root', '.']),
}


def capabilities(root):
    return {'schema': 'k01.commands.v1', 'commands': [
        {'id': key, 'label': label, 'argv': [key], 'center_enabled': (root / script).is_file(),
         'reason': None if (root / script).is_file() else 'Implementation missing: ' + script}
        for key, (label, script, args) in ROUTES.items()]}


def main(args=None, root=None):
    args = sys.argv[1:] if args is None else args
    root = Path(__file__).resolve().parents[2] if root is None else Path(root)
    if args == ['--list', '--json']:
        print(json.dumps(capabilities(root)))
        return 0
    if len(args) != 1 or args[0] not in ROUTES:
        print('Unknown or parameterized route rejected.', file=sys.stderr)
        return 2
    _, script, parameters = ROUTES[args[0]]
    if not (root / script).is_file():
        print('Implementation missing: ' + script, file=sys.stderr)
        return 2
    return subprocess.run([sys.executable, str(root / script)] + parameters, cwd=root).returncode


if __name__ == '__main__':
    raise SystemExit(main())
