"""Run the existing project handoff, then add a read-only requirements inventory."""
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from requirements_inventory import inventory

APP = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((APP/'settings.json').read_text(encoding='utf-8-sig'))
    root = Path(cfg['repo_root']).resolve()
    if not root.is_dir():
        raise ValueError('Project directory missing: ' + str(root))
    folder = APP/'runtime/handoff'
    folder.mkdir(parents=True, exist_ok=True)
    report = inventory(root)
    (folder/'K01_REQUIREMENTS_INVENTORY.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    tool = root/'tools/medtas/ai_handoff_v2_0.py'
    if not tool.is_file():
        raise ValueError('Existing handoff implementation missing: ' + str(tool))
    base = root/'reports/control/K01_AI_HANDOFF_CURRENT.zip'
    previous_mtime = base.stat().st_mtime_ns if base.exists() else None
    result = subprocess.run([sys.executable,str(tool),'--repo-root',str(root)],cwd=root)
    if result.returncode:
        print('Existing handoff failed; no combined package was published.')
        return result.returncode
    base = root/'reports/control/K01_AI_HANDOFF_CURRENT.zip'
    if not base.is_file():
        raise ValueError('Builder returned success but handoff ZIP is missing')
    if previous_mtime is not None and base.stat().st_mtime_ns == previous_mtime:
        raise ValueError('Handoff ZIP was not updated by this run')
    with zipfile.ZipFile(base) as archive:
        if archive.testzip():
            raise ValueError('Existing handoff ZIP failed integrity check')
    target = folder/'K01_AI_HANDOFF_WITH_REQUIREMENTS.zip'
    temporary = target.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(base,'K01_AI_HANDOFF_CURRENT.zip')
        archive.writestr('K01_REQUIREMENTS_INVENTORY.json',json.dumps(report,indent=2,ensure_ascii=False))
        for item in report['files']:
            path=root/item['path'];raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=item['sha256']:
                raise ValueError('Requirements source changed during export: '+item['path'])
            archive.writestr('requirement_sources/'+item['path'],raw)
    temporary.replace(target)
    print('UPLOAD THIS FILE: '+str(target))
    print('Inventory: '+str(len(report['files']))+' source files, '+str(len(report['occurrences']))+' requirement records, '+str(len(report['errors']))+' read/size errors.')
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        print('HANDOFF FAILED: '+str(exc))
        raise SystemExit(2)
