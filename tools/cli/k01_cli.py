from __future__ import annotations
import argparse, importlib.util, json, subprocess, sys
from pathlib import Path

def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return default

def run_process(cmd, cwd=None) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode

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
    mod = load_center_state_builder(repo)
    return mod.build(repo)

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

    gs = subprocess.run(
        ["git", "-C", str(repo), "status", "--short"],
        capture_output=True, text=True, errors="replace"
    )
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
    items = obj.get("items", []) if isinstance(obj, dict) else []
    for x in items:
        if str(x.get("status","")).upper() not in ("PASS","CLOSED","RELEASED"):
            print(f"  ENGINEERING {x.get('id')} [{x.get('status')}] {x.get('title')}")
            for c in x.get("closure_criteria", []) or []:
                print("     -", c)
    return 0

def main():
    ap = argparse.ArgumentParser(prog="run.cmd")
    ap.add_argument("--repo-root", required=True)
    sub = ap.add_subparsers(dest="command")
    sub.add_parser("center", help="Run Center 1.0 after selftest")
    sub.add_parser("selftest", help="Run current read-only project selftest")
    sub.add_parser("status", help="Build canonical current status from Center state model")
    sub.add_parser("commands", help="Show legacy-to-canonical command catalog")
    sub.add_parser("blockers", help="Show current engineering/release blockers")
    sub.add_parser("help", help="Show available commands")
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
        print("  run.cmd center")
        print()
        print("Engineering execution routes (BOM, CAD, drawings, DimXpert, FEMM,")
        print("analysis, release) remain blocked until each domain is consolidated.")
        return 0
    if a.command == "selftest":
        return cmd_selftest(repo)
    if a.command == "center":
        return cmd_center(repo)
    if a.command == "status":
        return cmd_status(repo)
    if a.command == "commands":
        return cmd_commands(repo)
    if a.command == "blockers":
        return cmd_blockers(repo)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
