from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    a = ap.parse_args()
    repo = Path(a.repo_root.strip().strip('"')).resolve()

    checks = [
        ("CENTER_SELFTEST",
         [sys.executable, str(repo/"center"/"selftest.py"), str(repo)]),
        ("REPO_GUARD_LIVE",
         [sys.executable, str(repo/"tools"/"repo"/"repo_guard.py"),
          "--repo-root", str(repo), "--live"]),
        ("CANONICAL_HASH_SELFTEST",
         [sys.executable, str(repo/"tools"/"medtas"/"canonical_hash_selftest_v1_5.py")]),
        ("STATE_REDUCER_FIXTURES",
         [sys.executable, str(repo/"tests"/"medtas"/"state_reducer_fixtures_v1_9.py")]),
        ("REGISTRY_SELFTEST",
         [sys.executable, str(repo/"tools"/"medtas"/"registry_selftest_v1_9.py"),
          "--repo-root", str(repo)]),
        ("STATUS_MODEL_SELFTEST",
         [sys.executable, str(repo/"tools"/"medtas"/"status_model_selftest_v1_8.py"),
          "--repo-root", str(repo)]),
    ]

    results = []
    failures = 0
    print("="*72)
    print("K01 CANONICAL ASSURANCE")
    print("="*72)
    for ident, cmd in checks:
        missing = None
        # executable script path is first *.py after interpreter
        py_paths = [Path(x) for x in cmd[1:] if str(x).lower().endswith(".py")]
        for p in py_paths:
            if not p.exists():
                missing = p
                break
        if missing:
            rc = 127
            out = ""
            err = f"missing: {missing}"
        else:
            cp = run(cmd, str(repo))
            rc, out, err = cp.returncode, cp.stdout, cp.stderr
        ok = rc == 0
        failures += 0 if ok else 1
        results.append({"id":ident,"pass":ok,"returncode":rc,"stdout":out,"stderr":err})
        print(("PASS " if ok else "HOLD ") + ident + f" rc={rc}")
        if not ok:
            if out.strip(): print(out.strip())
            if err.strip(): print(err.strip())

    status = "PASS" if failures == 0 else "HOLD"
    report = {
        "schema":"k01.canonical_assurance.v1",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "status":status,
        "failures":failures,
        "checks":results,
        "note":"Current assurance excludes legacy Command Center v8/v11 regression tests; Center 1.0 has its own selftest."
    }
    outdir = repo/"reports"/"assurance"
    outdir.mkdir(parents=True, exist_ok=True)
    rp = outdir/"K01_CANONICAL_ASSURANCE_CURRENT.json"
    rp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("report:", rp)
    print("assurance_status:", status)
    return 0 if failures == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
