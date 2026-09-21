from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

REPORT=Path("reports/control/K01_ROOT_CLEANUP_CURRENT.json")
TRANSPORT_MANIFEST=Path("K01_AI_HANDOFF_MANIFEST.json")

def load_json(p:Path):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return None

def run(cmd,cwd):
    return subprocess.run(cmd,cwd=str(cwd),capture_output=True,text=True,errors="replace")

def main():
    ap=argparse.ArgumentParser(
        description="K01 repository-root cleanup. File/folder relocation requires explicit per-action authorization."
    )
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--apply",action="store_true")
    ap.add_argument("--quarantine-center-package",action="store_true",
                    help="Explicitly authorize relocation of the validated legacy Center package.")
    ap.add_argument("--relocate-inbox",action="store_true",
                    help="Explicitly authorize relocation of repository _inbox.")
    ap.add_argument("--inbox-target",default=None,
                    help="Required explicit target when --relocate-inbox is used.")
    ap.add_argument("--quarantine-root-handoff-manifest",action="store_true",
                    help="Explicitly authorize relocation of a recognized root handoff manifest.")
    a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    actions=[];errors=[]

    # No relocation is implicit. --apply alone performs checks only.
    if a.quarantine_center_package:
        q=root/"tools/repo/quarantine_center_panel_package.py"
        qr=run([sys.executable,str(q),"--repo-root",str(root)]+(["--apply"] if a.apply else []),root)
        actions.append({"action":"quarantine_center_panel_package","authorized":True,
                        "rc":qr.returncode,"stdout":qr.stdout.strip(),"stderr":qr.stderr.strip()})
        if qr.returncode!=0:errors.append("CENTER_PACKAGE_QUARANTINE_FAILED")
    else:
        actions.append({"action":"quarantine_center_panel_package","status":"SKIP_NO_EXPLICIT_AUTHORIZATION"})

    if a.relocate_inbox:
        if not a.inbox_target:
            errors.append("INBOX_TARGET_REQUIRED")
            actions.append({"action":"relocate_local_inbox","status":"HOLD_EXPLICIT_TARGET_REQUIRED"})
        else:
            inbox=root/"tools/repo/relocate_local_inbox.py"
            cmd=[sys.executable,str(inbox),"--repo-root",str(root),"--target",a.inbox_target]
            if a.apply:cmd.append("--apply")
            ir=run(cmd,root)
            actions.append({"action":"relocate_local_inbox","authorized":True,
                            "target":a.inbox_target,"rc":ir.returncode,
                            "stdout":ir.stdout.strip(),"stderr":ir.stderr.strip()})
            if ir.returncode!=0:errors.append("LOCAL_INBOX_RELOCATION_FAILED")
    else:
        actions.append({"action":"relocate_local_inbox","status":"SKIP_NO_EXPLICIT_AUTHORIZATION"})

    tm=root/TRANSPORT_MANIFEST
    if a.quarantine_root_handoff_manifest:
        if tm.is_file():
            obj=load_json(tm) or {}
            schema=str(obj.get("schema") or "")
            if not schema.startswith("k01.ai_handoff"):
                errors.append("UNRECOGNIZED_ROOT_HANDOFF_MANIFEST")
                actions.append({"action":"root_handoff_manifest","status":"HOLD_UNRECOGNIZED","schema":schema})
            elif a.apply:
                stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
                dst=root/"reports/migration/quarantine"/("handoff_manifest_"+stamp)/TRANSPORT_MANIFEST.name
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.move(str(tm),str(dst))
                actions.append({"action":"root_handoff_manifest","status":"PASS_MOVED",
                                "authorized":True,"destination":str(dst)})
            else:
                actions.append({"action":"root_handoff_manifest","status":"PASS_DRYRUN_MOVE",
                                "authorized":True,"schema":schema})
        else:
            actions.append({"action":"root_handoff_manifest","status":"PASS_ABSENT"})
    else:
        actions.append({"action":"root_handoff_manifest","status":"SKIP_NO_EXPLICIT_AUTHORIZATION"})

    guard=None
    if a.apply and not errors:
        g=root/"tools/repo/repo_guard.py"
        gr=run([sys.executable,str(g),"--repo-root",str(root),"--live"],root)
        guard={"rc":gr.returncode,"stdout":gr.stdout.strip(),"stderr":gr.stderr.strip()}
        if gr.returncode!=0:errors.append("REPO_GUARD_AFTER_CLEANUP_FAILED")

    status=("HOLD_ROOT_CLEANUP" if errors else
            ("PASS_CHECK_ONLY_NO_IMPLICIT_RELOCATION" if a.apply else "PASS_DRYRUN_NO_IMPLICIT_RELOCATION"))
    rep={
      "schema":"k01.root_cleanup.current.v2",
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "status":status,
      "apply":a.apply,
      "native_CAD_mutated":False,
      "actions":actions,
      "repo_guard_after_apply":guard,
      "errors":errors,
      "rule":"No file or folder is relocated without an explicit action flag and, for inbox relocation, an explicit target path."
    }
    out=root/REPORT
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("root_cleanup:",status)
    print("REPORT:",out)
    for e in errors:print("HOLD:",e)
    return 0 if not errors else 2

if __name__=="__main__":
    raise SystemExit(main())
