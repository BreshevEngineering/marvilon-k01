from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DRYRUN_REL = Path("reports/control/K01_BASELINE_02C_PROMOTION_DRYRUN_CURRENT.json")
STEP_REL = Path("reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json")
OUT_REL = Path("reports/control/K01_BASELINE_02C_PROMOTION_APPLY_CURRENT.json")
BUILD_REL = Path("reports/cad/current/K01_GATE04B_DATUM_C_BUILD.json")
REWRITE_SRC_REL = Path("cad_api/gates/gate04b/K01Baseline02C_ReferenceRewrite.cs")
STABLE_QA_SRC_REL = Path("cad_api/gates/gate04b/K01Baseline02C_StableAssemblyQA.cs")

EXPECTED_STEP_PREFIX = "PASS_TO_BASELINE02C_PROMOTION_APPLY"
EXPECTED_DRYRUN_PREFIXES = (
    "PASS_DRYRUN_MANIFEST_READY",
    "PASS_DRYRUN_MANIFEST_REQUALIFIED_READY",
)
CHECKPOINT = "K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def same_path(a: Path, b: Path):
    return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))

def sw_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
            text=True, errors="ignore"
        )
        return "sldworks.exe" in out.lower()
    except Exception:
        return False

def wait_sw_closed(seconds=45):
    end = time.time() + seconds
    while time.time() < end:
        if not sw_running():
            return True
        time.sleep(1.0)
    return not sw_running()

def compile_cs(repo: Path, src_rel: Path, exe_name: str):
    pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    sld = pf / "SOLIDWORKS Corp" / "SOLIDWORKS" / "api" / "redist" / "SolidWorks.Interop.sldworks.dll"
    const = pf / "SOLIDWORKS Corp" / "SOLIDWORKS" / "api" / "redist" / "SolidWorks.Interop.swconst.dll"
    csc = windir / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
    if not csc.exists():
        csc = windir / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe"
    for p in (sld, const, csc, repo / src_rel):
        if not p.exists():
            raise RuntimeError("Compile dependency missing: " + str(p))

    bindir = repo / "cad_api" / "gates" / "gate04b" / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    exe = bindir / exe_name
    cmd = [
        str(csc), "/nologo", "/langversion:5", "/platform:x64", "/target:exe",
        "/out:" + str(exe),
        "/reference:" + str(sld),
        "/reference:" + str(const),
        "/reference:System.Web.Extensions.dll",
        str(repo / src_rel),
    ]
    cp = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, errors="replace")
    if cp.returncode != 0:
        raise RuntimeError("C# compile failed for %s\n%s\n%s" % (src_rel, cp.stdout, cp.stderr))
    shutil.copy2(sld, bindir / sld.name)
    shutil.copy2(const, bindir / const.name)
    return exe, {"command": cmd, "stdout": cp.stdout, "stderr": cp.stderr}

def run_helper(exe: Path, args, cwd: Path):
    cp = subprocess.run([str(exe)] + [str(x) for x in args],
                        cwd=str(cwd), capture_output=True, text=True, errors="replace")
    return {
        "rc": cp.returncode,
        "stdout": cp.stdout,
        "stderr": cp.stderr,
    }

def require_prefix(value, prefix, label):
    if not str(value or "").startswith(prefix):
        raise RuntimeError("%s=%r expected prefix %r" % (label, value, prefix))

def rollback(report, backup_root, stable, created_p017):
    rb = {"status": "NOT_RUN", "checks": []}
    report["rollback"] = rb
    if not backup_root or not backup_root.exists():
        rb["status"] = "HOLD_NO_BACKUP"
        return False
    if not wait_sw_closed(30):
        rb["status"] = "HOLD_SOLIDWORKS_RUNNING_CLOSE_AND_RESTORE_FROM_BACKUP"
        return False

    ok = True
    for key in ("P003", "P016", "A001"):
        src = backup_root / Path(stable[key]).name
        dst = Path(stable[key])
        if not src.is_file():
            rb["checks"].append({"id": key, "status": "FAIL_BACKUP_MISSING", "backup": str(src)})
            ok = False
            continue
        shutil.copy2(src, dst)
        expected = report["prestate"][key]["sha256"]
        actual = sha256(dst)
        good = actual.lower() == expected.lower()
        rb["checks"].append({"id": key, "status": "PASS" if good else "FAIL_HASH",
                             "actual": actual, "expected": expected})
        ok = ok and good

    p17 = Path(stable["P017"])
    if created_p017 and p17.exists():
        expected_created = report.get("candidate_sha256", {}).get("P017")
        actual = sha256(p17)
        if expected_created and actual.lower() == expected_created.lower():
            p17.unlink()
            rb["checks"].append({"id": "P017", "status": "PASS_DELETED_CREATED_TARGET"})
        else:
            rb["checks"].append({"id": "P017", "status": "HOLD_NOT_DELETED_HASH_CHANGED",
                                 "actual": actual, "expected_created": expected_created})
            ok = False
    rb["status"] = "PASS_ROLLED_BACK" if ok else "HOLD_ROLLBACK_INCOMPLETE"
    return ok

def main():
    ap = argparse.ArgumentParser(description="K01 Baseline-02C controlled canonical promotion")
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--apply", action="store_true",
                    help="Execute native CAD promotion. Without this flag only live prechecks run.")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    out = repo / OUT_REL

    report = {
        "schema": "k01.baseline_02c.promotion_apply.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING",
        "checkpoint": CHECKPOINT,
        "apply_requested": bool(args.apply),
        "native_CAD_mutated": False,
        "mutation_authorized": False,
        "phases": [],
        "error": "",
    }

    backup_root = None
    created_p017 = False
    stable = {}
    try:
        step = load(repo / STEP_REL)
        dry = load(repo / DRYRUN_REL)

        require_prefix(step.get("status"), EXPECTED_STEP_PREFIX, "engineering step gate")
        if step.get("mutation_authorized") is not True:
            raise RuntimeError("engineering step gate mutation_authorized is not true")
        dry_status = str(dry.get("status") or "")
        if not any(dry_status.startswith(prefix) for prefix in EXPECTED_DRYRUN_PREFIXES):
            raise RuntimeError(
                "promotion dry-run=%r expected one of prefixes %r"
                % (dry.get("status"), EXPECTED_DRYRUN_PREFIXES)
            )
        if dry.get("mutation_authorized") is not False:
            raise RuntimeError("dry-run report must remain mutation_authorized=false")
        if dry.get("checkpoint") != CHECKPOINT:
            raise RuntimeError("dry-run checkpoint mismatch")

        plan = dry["plan"]
        stable = {k: Path(v) for k, v in plan["stable_targets"].items()}
        cand = {k: Path(v) for k, v in plan["candidate_sources"].items()}
        frozen = dry["frozen_actual_sha256"]
        prestate = dry["prestate_stable"]

        report["stable_targets"] = {k: str(v) for k, v in stable.items()}
        report["candidate_sources"] = {k: str(v) for k, v in cand.items()}
        report["candidate_sha256"] = {
            "P003": frozen["P003_candidate"],
            "P016": frozen["P016_candidate"],
            "P017": frozen["P017_candidate"],
            "verification_A001": frozen["verification_A001"],
        }
        report["prestate"] = prestate

        # Exact identity / hash guards before any write.
        checks = []
        def ck(name, ok, actual=None, expected=None):
            checks.append({"check": name, "status": "PASS" if ok else "FAIL",
                           "actual": actual, "expected": expected})
            if not ok:
                raise RuntimeError("%s failed: actual=%r expected=%r" % (name, actual, expected))

        ck("SolidWorks closed before promotion", not sw_running(), sw_running(), False)

        for key, p, expected in [
            ("canonical A001", stable["A001"], frozen["canonical_A001"]),
            ("verification A001", cand["verification_A001"], frozen["verification_A001"]),
            ("P003 candidate", cand["P003"], frozen["P003_candidate"]),
            ("P016 candidate", cand["P016"], frozen["P016_candidate"]),
            ("P017 candidate", cand["P017"], frozen["P017_candidate"]),
            ("stable P003 prestate", stable["P003"], prestate["P003"]["sha256"]),
            ("stable P016 prestate", stable["P016"], prestate["P016"]["sha256"]),
        ]:
            ck(key + " exists", p.is_file(), str(p), True)
            if p.is_file():
                ck(key + " SHA", sha256(p).lower() == str(expected).lower(), sha256(p), expected)

        ck("stable P017 target absent", not stable["P017"].exists(), str(stable["P017"]), "absent")
        report["phases"].append({"id": "A0_PRECHECK", "status": "PASS", "checks": checks})

        # Compile both SolidWorks helpers before native CAD write.
        rewrite_exe, rewrite_compile = compile_cs(
            repo, REWRITE_SRC_REL, "K01Baseline02C_ReferenceRewrite.exe"
        )
        qa_exe, qa_compile = compile_cs(
            repo, STABLE_QA_SRC_REL, "K01Baseline02C_StableAssemblyQA.exe"
        )
        report["phases"].append({
            "id": "A0B_HELPER_COMPILE", "status": "PASS",
            "rewrite_exe": str(rewrite_exe), "qa_exe": str(qa_exe),
            "rewrite_compile": rewrite_compile, "qa_compile": qa_compile,
        })

        if not args.apply:
            report["status"] = "PASS_APPLY_INPUTS_READY_NO_NATIVE_WRITE"
            report["mutation_authorized"] = False
            write_json(out, report)
            print("STATUS:", report["status"])
            print("REPORT:", out)
            print("Native CAD mutated: False")
            return 0

        report["mutation_authorized"] = True

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cad_root = stable["A001"].parent.parent
        backup_root = cad_root / "archive" / "pre_baseline_02c_promotion" / stamp
        staging_root = cad_root / "promotion_staging" / "baseline_02c" / stamp
        backup_root.mkdir(parents=True, exist_ok=False)
        staging_root.mkdir(parents=True, exist_ok=False)

        # Backup only: never move existing files.
        for key in ("P003", "P016", "A001"):
            src = stable[key]
            shutil.copy2(src, backup_root / src.name)
        for rel in [DRYRUN_REL, STEP_REL, BUILD_REL]:
            src = repo / rel
            if src.is_file():
                shutil.copy2(src, backup_root / src.name)

        backup_manifest = {
            "schema": "k01.baseline_02c.backup_manifest.v1",
            "timestamp": stamp,
            "backup_root": str(backup_root),
            "prestate": {
                "P003": {"path": str(stable["P003"]), "sha256": sha256(stable["P003"])},
                "P016": {"path": str(stable["P016"]), "sha256": sha256(stable["P016"])},
                "A001": {"path": str(stable["A001"]), "sha256": sha256(stable["A001"])},
                "P017": {"path": str(stable["P017"]), "existed": False},
            },
            "rule": "Copies only. No existing directory/file is relocated by this promotion."
        }
        write_json(backup_root / "K01_BASELINE_02C_BACKUP_MANIFEST.json", backup_manifest)
        report["backup_root"] = str(backup_root)
        report["staging_root"] = str(staging_root)
        report["phases"].append({"id": "A1_BACKUP", "status": "PASS",
                                 "backup_manifest": str(backup_root / "K01_BASELINE_02C_BACKUP_MANIFEST.json")})

        # Materialize exact verified candidate binaries at stable identities.
        shutil.copy2(cand["P003"], stable["P003"])
        shutil.copy2(cand["P016"], stable["P016"])
        shutil.copy2(cand["P017"], stable["P017"])
        created_p017 = True
        for key in ("P003", "P016", "P017"):
            expected = report["candidate_sha256"][key]
            actual = sha256(stable[key])
            if actual.lower() != expected.lower():
                raise RuntimeError("stable %s SHA after materialization %s != %s" % (key, actual, expected))
        report["native_CAD_mutated"] = True
        report["phases"].append({"id": "A2_STABLE_PART_MATERIALIZATION", "status": "PASS",
                                 "stable_sha256": {k: sha256(stable[k]) for k in ("P003","P016","P017")}})

        # Build staging A001 from the already verified 14-occurrence candidate assembly.
        staging_asm = staging_root / "K01-A-001_Calibration_Module_BASELINE02C_STAGING.SLDASM"
        shutil.copy2(cand["verification_A001"], staging_asm)

        rewrite_report = repo / "reports" / "cad" / "current" / "K01_BASELINE_02C_STAGING_REFERENCE_REWRITE.json"
        rr = run_helper(rewrite_exe, [
            "--assembly", staging_asm,
            "--report", rewrite_report,
            "--old-p003", cand["P003"], "--new-p003", stable["P003"],
            "--old-p016", cand["P016"], "--new-p016", stable["P016"],
            "--old-p017", cand["P017"], "--new-p017", stable["P017"],
        ], repo)
        if rr["rc"] != 0:
            raise RuntimeError("staging reference rewrite failed\n%s\n%s" % (rr["stdout"], rr["stderr"]))
        rrj = load(rewrite_report)
        if rrj.get("status") != "PASS_REFERENCE_REWRITE":
            raise RuntimeError("staging reference rewrite report is not PASS")
        if not wait_sw_closed():
            raise RuntimeError("SOLIDWORKS still running after reference rewrite helper")
        report["phases"].append({"id": "A3_STAGING_REFERENCE_REWRITE", "status": "PASS",
                                 "assembly": str(staging_asm), "report": str(rewrite_report),
                                 "stdout": rr["stdout"]})

        # Full staging QA using the same motion/interference/readback logic as Gate04B.
        staging_qa = repo / "reports" / "cad" / "current" / "K01_BASELINE_02C_STAGING_ASSEMBLY_QA.json"
        qr = run_helper(qa_exe, ["--assembly", staging_asm, "--report", staging_qa], repo)
        if qr["rc"] != 0:
            raise RuntimeError("staging full assembly QA failed\n%s\n%s" % (qr["stdout"], qr["stderr"]))
        qj = load(staging_qa)
        if qj.get("status") != "PASS_STABLE_ASSEMBLY_QA":
            raise RuntimeError("staging stable assembly QA report is not PASS")
        if not wait_sw_closed():
            raise RuntimeError("SOLIDWORKS still running after staging QA")
        report["phases"].append({"id": "A4_STAGING_FULL_QA", "status": "PASS",
                                 "report": str(staging_qa), "assembly_sha256": sha256(staging_asm)})

        # Final pre-overwrite guard: canonical A001 must still be the frozen prestate.
        current_canonical_sha = sha256(stable["A001"])
        if current_canonical_sha.lower() != frozen["canonical_A001"].lower():
            raise RuntimeError("canonical A001 changed during staging: %s != %s" %
                               (current_canonical_sha, frozen["canonical_A001"]))
        if sw_running():
            raise RuntimeError("SOLIDWORKS unexpectedly running before canonical A001 replacement")

        # Only now replace canonical assembly bytes by the verified stable-reference staging assembly.
        shutil.copy2(staging_asm, stable["A001"])
        report["phases"].append({"id": "A5_CANONICAL_A001_REPLACE", "status": "PASS",
                                 "canonical_sha256": sha256(stable["A001"]),
                                 "staging_sha256": sha256(staging_asm)})

        # Full post-promotion QA against the canonical stable assembly.
        canonical_qa = repo / "reports" / "cad" / "current" / "K01_BASELINE_02C_POST_PROMOTION_ASSEMBLY_QA.json"
        qr2 = run_helper(qa_exe, ["--assembly", stable["A001"], "--report", canonical_qa], repo)
        if qr2["rc"] != 0:
            raise RuntimeError("canonical post-promotion full assembly QA failed\n%s\n%s" % (qr2["stdout"], qr2["stderr"]))
        q2 = load(canonical_qa)
        if q2.get("status") != "PASS_STABLE_ASSEMBLY_QA":
            raise RuntimeError("canonical post-promotion assembly QA report is not PASS")
        if not wait_sw_closed():
            raise RuntimeError("SOLIDWORKS still running after canonical QA")

        report["phases"].append({"id": "A6_POST_PROMOTION_FULL_QA", "status": "PASS",
                                 "report": str(canonical_qa)})
        report["poststate"] = {
            "P003": {"path": str(stable["P003"]), "sha256": sha256(stable["P003"])},
            "P016": {"path": str(stable["P016"]), "sha256": sha256(stable["P016"])},
            "P017": {"path": str(stable["P017"]), "sha256": sha256(stable["P017"])},
            "A001": {"path": str(stable["A001"]), "sha256": sha256(stable["A001"])},
        }
        report["status"] = "PASS_ENGINEERING_BASELINE_PROMOTED_PENDING_SNAPSHOT_STALE_BOM"
        report["next"] = (
            "Generate fresh canonical semantic snapshot, recompute dependency/freshness state, "
            "rebuild EBOM/MBOM and prove 14 occurrences with K01-P-017 qty=1. "
            "Do not claim R01 or product release."
        )
        write_json(out, report)
        print("STATUS:", report["status"])
        print("REPORT:", out)
        print("Backup:", backup_root)
        print("Canonical A001:", stable["A001"])
        print("Native CAD mutated: True")
        return 0

    except Exception as ex:
        report["error"] = repr(ex)
        if report.get("native_CAD_mutated") and backup_root is not None:
            try:
                good = rollback(report, backup_root, {k: str(v) for k,v in stable.items()}, created_p017)
                report["status"] = "FAIL_ROLLED_BACK" if good else "HOLD_ROLLBACK_INCOMPLETE"
            except Exception as rbex:
                report["rollback_exception"] = repr(rbex)
                report["status"] = "HOLD_ROLLBACK_EXCEPTION"
        else:
            report["status"] = "HOLD_BEFORE_NATIVE_WRITE"
        write_json(out, report)
        print("STATUS:", report["status"])
        print("REPORT:", out)
        print("ERROR:", repr(ex))
        if report.get("rollback"):
            print("ROLLBACK:", report["rollback"].get("status"))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
