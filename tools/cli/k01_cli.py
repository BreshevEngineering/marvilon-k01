from __future__ import annotations
import argparse, importlib.util, json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return default

def run_process(cmd, cwd=None) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode

def capture(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace")

def load_center_state_builder(repo: Path):
    p = repo / "center" / "build_state.py"
    if not p.exists():
        raise RuntimeError(f"Center state builder missing: {p}")
    spec = importlib.util.spec_from_file_location("k01_center_build_state", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import Center state builder: {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def current_state(repo: Path):
    return load_center_state_builder(repo).build(repo)

def cmd_selftest(repo: Path) -> int:
    p = repo / "center" / "selftest.py"
    if not p.exists():
        print("HOLD: center selftest missing:", p)
        return 2
    return run_process([sys.executable, str(p), str(repo)], cwd=str(repo))

def cmd_center(repo: Path) -> int:
    rc = cmd_selftest(repo)
    if rc != 0:
        return rc
    server = repo / "center" / "server.py"
    if not server.exists():
        print("HOLD: center server missing:", server)
        return 2
    return run_process([sys.executable, str(server), "--repo-root", str(repo)], cwd=str(repo))

def cmd_status(repo: Path) -> int:
    print("=" * 68)
    print("K01 STATUS — CANONICAL READ-ONLY VIEW")
    print("=" * 68)
    try:
        state = current_state(repo)
    except Exception as e:
        print("HOLD: cannot build canonical state:", repr(e))
        return 2

    b = state.get("baseline", {})
    eb = state.get("bom", {}).get("ebom", {})
    mb = state.get("bom", {}).get("mbom", {})
    pd = state.get("product_definition", {})
    rr = state.get("release_readiness", {})

    print("engineering_baseline:", Path(str(b.get("assembly") or "")).name)
    print("baseline_status:", b.get("status"))
    print("baseline_sha256:", b.get("sha256"))
    print("simulation_evidence:", b.get("simulation_evidence_count"))
    print("bom_ebom:",
          "status=", eb.get("status"),
          "structure=", eb.get("structure_status"),
          "modeled=", eb.get("modeled_instances"),
          "rows=", eb.get("row_count"),
          "open=", len(eb.get("release_open_items") or []))
    print("bom_mbom:",
          "status=", mb.get("status"),
          "rows=", mb.get("row_count"),
          "open=", len(mb.get("release_open_items") or []))
    print("product_definition:", pd.get("status_counts"))
    print("release_readiness:", rr.get("status"), rr.get("reasons"))

    gs = capture(["git", "-C", str(repo), "status", "--short"])
    dirty = [l for l in gs.stdout.splitlines() if l.strip()]
    print("git_dirty_lines:", len(dirty))
    for l in dirty[:20]:
        print(" ", l)
    if len(dirty) > 20:
        print(f"  ... {len(dirty)-20} more")
    return 0

def cmd_commands(repo: Path) -> int:
    p = repo / "control" / "commands" / "K01_COMMAND_CATALOG.json"
    cat = load_json(p)
    if not isinstance(cat, dict):
        print("HOLD: command catalog missing:", p)
        return 2
    print("=" * 68)
    print("K01 COMMAND CATALOG")
    print("=" * 68)
    print("status:", cat.get("status"))
    print("canonical_entry:", cat.get("canonical_entry"))
    print("counts:", cat.get("counts"))
    print()
    for row in cat.get("commands", []):
        print(f"{row.get('status','?'):28} {row.get('launcher','?'):46} -> {row.get('future_route') or '-'}")
    return 0

def cmd_blockers(repo: Path) -> int:
    print("=" * 68)
    print("K01 ENGINEERING / RELEASE BLOCKERS")
    print("=" * 68)
    try:
        state = current_state(repo)
    except Exception as e:
        print("HOLD: cannot build canonical state:", repr(e))
        return 2
    rr = state.get("release_readiness", {})
    print("release_readiness:", rr.get("status"))
    for r in rr.get("reasons", []) or []:
        print("  RELEASE", r)

    p = repo / "control" / "analysis" / "K01_ANALYSIS_OPEN_ITEMS.json"
    obj = load_json(p, {}) or {}
    for x in obj.get("items", []) if isinstance(obj, dict) else []:
        if str(x.get("status","")).upper() not in ("PASS","CLOSED","RELEASED"):
            print(f"  ENGINEERING {x.get('id')} [{x.get('status')}] {x.get('title')}")
            for c in x.get("closure_criteria", []) or []:
                print("     -", c)
    return 0

def cmd_assurance(repo: Path) -> int:
    p = repo/"tools"/"assurance"/"k01_assurance.py"
    if not p.exists():
        print("HOLD: canonical assurance missing:", p)
        return 2
    return run_process([sys.executable, str(p), "--repo-root", str(repo)], cwd=str(repo))

def cmd_audit(repo: Path) -> int:
    print("="*68)
    print("K01 CANONICAL REPOSITORY / PROJECT AUDIT")
    print("="*68)
    guard = capture([sys.executable, str(repo/"tools"/"repo"/"repo_guard.py"),
                     "--repo-root", str(repo), "--live"], cwd=str(repo))
    st = capture([sys.executable, str(repo/"center"/"selftest.py"), str(repo)], cwd=str(repo))
    gs = capture(["git","-C",str(repo),"status","--short"], cwd=str(repo))
    dirty = [l for l in gs.stdout.splitlines() if l.strip()]

    print(guard.stdout.strip())
    if guard.stderr.strip(): print(guard.stderr.strip())
    print(st.stdout.strip())
    if st.stderr.strip(): print(st.stderr.strip())
    print("git_dirty_lines:", len(dirty))

    result = {
        "schema":"k01.canonical_audit.v1",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "status":"PASS_MIGRATION_GUARDS" if guard.returncode==0 and st.returncode==0 else "HOLD",
        "repo_guard_rc":guard.returncode,
        "center_selftest_rc":st.returncode,
        "git_dirty_lines":len(dirty),
        "git_status":dirty,
    }
    outdir=repo/"reports"/"foundation"
    outdir.mkdir(parents=True,exist_ok=True)
    rp=outdir/"K01_CANONICAL_AUDIT_CURRENT.json"
    rp.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("report:", rp)
    print("audit_status:", result["status"])
    return 0 if result["status"]=="PASS_MIGRATION_GUARDS" else 2

def cmd_evidence(repo: Path) -> int:
    p = repo/"tools"/"medtas"/"calculation_evidence_index_v2_2.py"
    if not p.exists():
        print("HOLD: evidence index implementation missing:", p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_handoff(repo: Path) -> int:
    p = repo/"tools"/"medtas"/"ai_handoff_v2_0.py"
    if not p.exists():
        print("HOLD: handoff implementation missing:", p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def main():
    ap = argparse.ArgumentParser(prog="run.cmd")
    ap.add_argument("--repo-root", required=True)
    sub = ap.add_subparsers(dest="command")
    for name, help_text in [
        ("center","Run Center 1.0 after selftest"),
        ("selftest","Run current read-only project selftest"),
        ("status","Build canonical current status from Center state model"),
        ("commands","Show legacy-to-canonical command catalog"),
        ("blockers","Show current engineering/release blockers"),
        ("assurance","Run canonical assurance suite"),
        ("audit","Run blocking repo guard + project selftest"),
        ("evidence","Build calculation evidence index"),
        ("handoff","Build AI handoff package"),
        ("help","Show available commands"),
    ]:
        sub.add_parser(name, help=help_text)
    a = ap.parse_args()

    repo = Path(a.repo_root.strip().strip('"')).resolve()
    if not (repo / ".git").exists():
        print("HOLD: invalid repo root", repo)
        return 2

    if a.command in (None, "help"):
        ap.print_help()
        print()
        print("Canonical commands:")
        print("  run.cmd status")
        print("  run.cmd blockers")
        print("  run.cmd commands")
        print("  run.cmd selftest")
        print("  run.cmd assurance")
        print("  run.cmd audit")
        print("  run.cmd evidence")
        print("  run.cmd handoff")
        print("  run.cmd center")
        print()
        print("Engineering execution routes (BOM, CAD, drawings, DimXpert, FEMM,")
        print("structural analysis, release) remain fail-closed until consolidated.")
        return 0

    dispatch = {
        "selftest":cmd_selftest, "center":cmd_center, "status":cmd_status,
        "commands":cmd_commands, "blockers":cmd_blockers, "assurance":cmd_assurance,
        "audit":cmd_audit, "evidence":cmd_evidence, "handoff":cmd_handoff,
    }
    return dispatch[a.command](repo)

if __name__ == "__main__":
    raise SystemExit(main())
