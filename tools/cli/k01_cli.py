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


def cmd_namespace_guard(repo: Path) -> int:
    p=repo/"tools"/"repo"/"control_namespace_guard.py"
    return run_process([sys.executable,str(p),"--repo-root",str(repo),"--write-report"],cwd=str(repo))

def cmd_tech_filter(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"technical_filter_map_v2_2.py"
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_step_gate(repo: Path) -> int:
    p=repo/"tools"/"assurance"/"engineering_step_gate.py"
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_requirements_coverage(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"build_requirements_coverage_v1_9.py"
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_baseline_preflight(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"baseline_02c_promotion_preflight.py"
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_baseline_promotion_dryrun(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"baseline_02c_promotion_dryrun.py"
    if not p.exists():
        print("HOLD: Baseline-02C promotion dry-run implementation missing:", p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_baseline_promotion_apply(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"baseline_02c_promotion_apply.py"
    if not p.exists():
        print("HOLD: Baseline-02C promotion apply implementation missing:", p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo),"--apply"],cwd=str(repo))

def cmd_baseline_candidate_requalify(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"baseline_02c_candidate_requalify.py"
    if not p.exists():
        print("HOLD: Baseline-02C candidate requalification implementation missing:", p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_baseline_promote_verified(repo: Path) -> int:
    # One user-facing engineering command: refresh the generic pre-write controls,
    # semantically requalify any artifact-SHA drift, then promote only if all gates pass.
    rc=cmd_prewrite(repo)
    if rc!=0:
        print("HOLD: prewrite control did not PASS; candidate requalification/promotion not started")
        return rc
    rc=cmd_baseline_candidate_requalify(repo)
    if rc!=0:
        print("HOLD: candidate requalification did not PASS; canonical promotion not started")
        return rc
    return cmd_baseline_promotion_apply(repo)

def cmd_baseline_finalize(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"baseline_02c_post_promotion_finalize.py"
    if not p.exists():
        print("HOLD: Baseline-02C post-promotion finalizer missing:",p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_p007_professional_start(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"p007_professional_start_v1.py"
    if not p.exists():
        print("HOLD: P007 professional-start implementation missing:",p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_p007_rebind(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"p007_persistent_ref_rebind_v1.py"
    if not p.exists():
        print("HOLD: P007 persistent-reference rebind tool missing:",p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_p007_pmi_phase_a(repo: Path) -> int:
    p=repo/"tools"/"medtas"/"p007_dimxpert_phase_a_v1.py"
    if not p.exists():
        print("HOLD: P007 DimXpert Phase-A tool missing:",p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_panel(repo: Path) -> int:
    p=repo/"tools"/"assurance"/"build_engineering_dashboard.py"
    if not p.exists():
        print("HOLD: engineering dashboard builder missing:", p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo),"--open"],cwd=str(repo))

def cmd_state_sync(repo: Path) -> int:
    p=repo/"tools"/"state"/"k01_state_sync_v3.py"
    if not p.exists():
        print("HOLD: global project state sync v3 missing:",p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_temporal_guard(repo: Path) -> int:
    p=repo/"tools"/"state"/"k01_temporal_coherence_guard_v1.py"
    if not p.exists():
        print("HOLD: temporal-coherence guard missing:",p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo),"--write-report"],cwd=str(repo))

def cmd_handoff(repo: Path) -> int:
    # Handoff completeness is not only file presence. First synchronize all global
    # STATE_CURRENT views from one reducer, then fail closed on temporal inconsistency.
    rc=cmd_state_sync(repo)
    if rc!=0:
        print("HOLD: state synchronization failed; handoff not built")
        return rc
    rc=cmd_temporal_guard(repo)
    if rc!=0:
        print("HOLD: temporal coherence failed; handoff not built")
        return rc
    p = repo/"tools"/"medtas"/"ai_handoff_v2_0.py"
    if not p.exists():
        print("HOLD: handoff implementation missing:", p)
        return 2
    return run_process([sys.executable,str(p),"--repo-root",str(repo)],cwd=str(repo))

def cmd_root_cleanup(repo: Path, apply: bool=False) -> int:
    p=repo/"tools"/"repo"/"root_cleanup.py"
    cmd=[sys.executable,str(p),"--repo-root",str(repo)]
    if apply: cmd.append("--apply")
    return run_process(cmd,cwd=str(repo))

def cmd_prewrite(repo: Path) -> int:
    p=repo/"tools"/"assurance"/"prewrite_control.py"
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
        ("handoff","Build temporally coherent AI handoff package"),
        ("state-sync","Regenerate all global STATE_CURRENT views from one reducer"),
        ("temporal-guard","Verify state-epoch / current-file temporal coherence"),
        ("requirements-coverage","Rebuild requirement-to-registered-evidence coverage"),
        ("baseline02c-preflight","Run read-only Baseline-02C promotion preflight"),
        ("baseline02c-promotion-dryrun","Build read-only Baseline-02C stable-promotion transaction manifest"),
        ("baseline02c-promotion-apply","Execute guarded Baseline-02C stable promotion with backup/staging/full QA/rollback"),
        ("baseline02c-requalify","Requalify current Datum-C candidate geometry/assembly after artifact SHA drift"),
        ("baseline02c-promote-verified","Requalify current verified candidate and promote it only if all QA passes"),
        ("baseline02c-finalize","Finalize promoted canonical A001: semantic snapshot, freshness, EBOM/MBOM, CP-P, next P007 gate"),
        ("p007-start","Reconcile canonical P007, close C02 draft drift, prepare canonical PMI rebinding work"),
        ("p007-rebind","Regenerate canonical P007 persistent references and prove close/reopen resolution"),
        ("p007-pmi-a","Create timestamped P007 candidate and author verified native DimXpert Phase-A PMI"),
        ("panel","Build and open the visual K01 engineering control panel"),
        ("namespace-guard","Validate control authority/version namespace"),
        ("tech-filter","Rebuild 24-category technical-filter map"),
        ("step-gate","Run the current checkpoint/step gate"),
        ("root-cleanup","Dry-run controlled repository-root cleanup"),
        ("root-cleanup-apply","Apply validated repository-root cleanup"),
        ("prewrite-check","Refresh generic controls and run the current step gate"),
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
        print("  run.cmd state-sync")
        print("  run.cmd temporal-guard")
        print("  run.cmd requirements-coverage")
        print("  run.cmd baseline02c-preflight")
        print("  run.cmd baseline02c-promotion-dryrun")
        print("  run.cmd baseline02c-promotion-apply")
        print("  run.cmd baseline02c-requalify")
        print("  run.cmd baseline02c-promote-verified")
        print("  run.cmd baseline02c-finalize")
        print("  run.cmd p007-start")
        print("  run.cmd p007-rebind")
        print("  run.cmd p007-pmi-a")
        print("  run.cmd panel")
        print("  run.cmd namespace-guard")
        print("  run.cmd tech-filter")
        print("  run.cmd step-gate")
        print("  run.cmd root-cleanup")
        print("  run.cmd root-cleanup-apply")
        print("  run.cmd prewrite-check")
        print("  run.cmd center")
        print()
        print("Engineering execution routes (BOM, CAD, drawings, DimXpert, FEMM,")
        print("structural analysis, release) remain fail-closed until consolidated.")
        return 0

    dispatch = {
        "selftest":cmd_selftest, "center":cmd_center, "status":cmd_status,
        "commands":cmd_commands, "blockers":cmd_blockers, "assurance":cmd_assurance,
        "audit":cmd_audit, "evidence":cmd_evidence, "handoff":cmd_handoff,
        "state-sync":cmd_state_sync, "temporal-guard":cmd_temporal_guard,
        "requirements-coverage":cmd_requirements_coverage, "baseline02c-preflight":cmd_baseline_preflight,
        "baseline02c-promotion-dryrun":cmd_baseline_promotion_dryrun,
        "baseline02c-promotion-apply":cmd_baseline_promotion_apply,
        "baseline02c-requalify":cmd_baseline_candidate_requalify,
        "baseline02c-promote-verified":cmd_baseline_promote_verified,
        "baseline02c-finalize":cmd_baseline_finalize,
        "p007-start":cmd_p007_professional_start,
        "p007-rebind":cmd_p007_rebind,
        "p007-pmi-a":cmd_p007_pmi_phase_a,
        "panel":cmd_panel,
        "namespace-guard":cmd_namespace_guard, "tech-filter":cmd_tech_filter, "step-gate":cmd_step_gate,
        "root-cleanup":lambda r: cmd_root_cleanup(r,False),
        "root-cleanup-apply":lambda r: cmd_root_cleanup(r,True),
        "prewrite-check":cmd_prewrite,
    }
    return dispatch[a.command](repo)

if __name__ == "__main__":
    raise SystemExit(main())
