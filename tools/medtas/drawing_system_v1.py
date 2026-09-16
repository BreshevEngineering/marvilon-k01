#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

CS = Path(r"cad_api/solidworks_2018_proven/current/K01_DRAWING_SYSTEM_V1/K01DrawingSystemV1.cs")
WORK = Path(r"reports/cad/drawing_system_v1_current")


def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, errors="replace", timeout=timeout)


def need(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def sha256(path: Path):
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_kv_report(path: Path):
    out = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k and k not in out:
            out[k] = v
    return out


def artifact_record(path: Path):
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
        "size_bytes": path.stat().st_size if path.is_file() else None,
    }


def finalize_candidate(root: Path, spec_path: Path, spec: dict, report: Path):
    data = parse_kv_report(report)
    candidate_root = Path(data.get("CANDIDATE_ROOT", ""))
    need(candidate_root.is_dir(), "candidate root missing from report")
    generated_dir = Path(data.get("GENERATED_DIR", candidate_root / "generated"))
    manual_dir = Path(data.get("MANUAL_FINISH_DIR", candidate_root / "manual_finish"))
    evidence_dir = Path(data.get("EVIDENCE_DIR", candidate_root / "evidence"))
    manual_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_copy = evidence_dir / "semantic_report.txt"
    evidence_copy.write_text(report.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    drawing = Path(data.get("OUTPUT_DRAWING", generated_dir / (spec["drawing_id"] + ".SLDDRW")))
    pdf = Path(data.get("OUTPUT_PDF", generated_dir / (spec["drawing_id"] + ".PDF")))
    bmp = Path(data.get("OUTPUT_BMP", generated_dir / (spec["drawing_id"] + ".BMP")))
    candidate_id = candidate_root.name
    manifest = {
        "schema": "k01.drawing_candidate.v1",
        "candidate_id": candidate_id,
        "drawing_id": spec["drawing_id"],
        "part_id": spec["part_id"],
        "engine": "MARVILON_DRAWING_SYSTEM_V1",
        "engine_revision": "1.1-candidate-lifecycle",
        "created_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "state": "GENERATED",
        "release": "HOLD",
        "spec": {"path": str(spec_path), "sha256": sha256(spec_path)},
        "source_model": {"path": spec.get("model_path"), "sha256": data.get("SOURCE_SHA256_AFTER")},
        "placement_profile": data.get("PLACEMENT_PROFILE") or None,
        "placement_applied": data.get("PLACEMENT_APPLIED", "False").lower() == "true",
        "paths": {
            "candidate_root": str(candidate_root),
            "generated": str(generated_dir),
            "manual_finish": str(manual_dir),
            "evidence": str(evidence_dir),
        },
        "generated_artifacts": {
            "drawing": artifact_record(drawing),
            "pdf": artifact_record(pdf),
            "bmp": artifact_record(bmp),
            "semantic_report": artifact_record(evidence_copy),
        },
        "release_blockers": list(spec.get("release_blockers", [])),
    }
    (candidate_root / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("CANDIDATE MANIFEST: " + str(candidate_root / "candidate_manifest.json"))
    return candidate_root


def sw_running():
    cp = run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"], timeout=30)
    return "sldworks.exe" in ((cp.stdout or "") + (cp.stderr or "")).lower()


def csc():
    w = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for p in (w / "Microsoft.NET/Framework64/v4.0.30319/csc.exe", w / "Microsoft.NET/Framework/v4.0.30319/csc.exe"):
        if p.exists():
            return p
    raise RuntimeError("csc.exe missing")


def redist():
    for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"), Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
        if (p / "SolidWorks.Interop.sldworks.dll").exists():
            return p
    raise RuntimeError("SOLIDWORKS API redist missing")


def preflight(root: Path, spec_path: Path, mode: str):
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    need(spec.get("schema") == "k01.drawing_system_spec.v1", "wrong drawing-system spec schema")
    need(spec.get("drawing_id") and spec.get("part_id"), "drawing_id/part_id missing")
    readiness = spec.get("authoring_readiness") or {}
    if readiness:
        need(readiness.get("status") == "READY_FOR_AUTHORING", "drawing authoring readiness HOLD: " + str(readiness.get("status")) + " | " + str(readiness.get("reason", "close Product Definition first")))
    need(spec.get("material"), "material missing")
    views = spec.get("view_definitions", [])
    need(len(views) >= 1, "drawing-system spec requires at least one view definition")
    view_ids = [v.get("id") for v in views]
    need(len(view_ids) == len(set(view_ids)) and all(view_ids), "view id missing/duplicate")
    bindings = spec.get("bindings", {})
    need(bindings and isinstance(bindings, dict), "geometry bindings missing")
    supported_bindings = {"CYLINDER", "CYLINDER_SET", "PLANE_AT_CYL_END", "PLANE_SET_AT_CYL_END", "PLANE_EXTREME_X"}
    need(all((b or {}).get("kind") in supported_bindings for b in bindings.values()), "unsupported geometry binding kind")
    for name, b in bindings.items():
        if (b or {}).get("kind") == "PLANE_SET_AT_CYL_END":
            targets = (b or {}).get("area_m2_targets") or []
            need(len(targets) >= 2 and all(float(x) > 0 for x in targets), f"{name} plane-set area signatures missing")
        if (b or {}).get("kind") == "PLANE_EXTREME_X":
            need((b or {}).get("side") in {"MIN_X", "MAX_X"}, f"{name} PLANE_EXTREME_X side must be MIN_X/MAX_X")
    datums = spec.get("datum_features", [])
    ids = [d.get("id") for d in datums]
    need(all(ids), "datum id missing")
    need(len(ids) == len(set(ids)), "datum namespace collision: " + repr(ids))
    need(all(d.get("binding") in bindings for d in datums), "datum binding missing from binding registry")
    need(all(d.get("view") in view_ids for d in datums), "datum view missing/unknown in drawing spec")
    vs = spec.get("view_strategy") or {}
    if vs:
        need(vs.get("primary_representation") in {"LONGITUDINAL_SECTION","MODEL_VIEW","SECTION"}, "unsupported primary view strategy")
        for iv in vs.get("interface_end_views", []):
            if iv.get("required"):
                need(iv.get("view") in view_ids, "required interface end view missing: " + str(iv.get("view")))
    anns = spec.get("annotations", [])
    need(anns, "annotation authoring schedule missing")
    supported_annotations = {"DIAMETER", "DIAMETER_SET", "LINEAR", "GTOL", "TED_NOTE", "NOTE", "SURFACE_FINISH"}
    need(all((x or {}).get("kind") in supported_annotations for x in anns), "unsupported annotation kind")
    for x in anns:
        if x.get("kind") == "GTOL" and x.get("zone_modifier"):
            need(x.get("zone_modifier") in {"CZ", "CZR", "SIM"}, "unsupported GTOL zone modifier: " + str(x.get("zone_modifier")))
        if x.get("kind") == "SURFACE_FINISH":
            need(float(x.get("ra_um", 0)) > 0, "surface finish requires positive ra_um")
    ann_ids = [x.get("id") for x in anns]
    need(all(ann_ids) and len(ann_ids) == len(set(ann_ids)), "annotation id missing/duplicate")
    need(all(x.get("view") in view_ids for x in anns), "annotation references unknown view")
    chars = spec.get("characteristics", [])
    cids = [c.get("id") for c in chars]
    need(len(cids) == len(set(cids)), "duplicate characteristic id")
    need(all(c.get("source") and c.get("state") for c in chars), "characteristic source/state missing")
    blockers = list(spec.get("release_blockers", []))
    if mode == "release":
        need(not blockers, "release blocked by drawing spec: " + " | ".join(blockers))
    return spec, blockers


def cleanup_owned_sw(was_running: bool):
    if was_running or not sw_running():
        return
    for _ in range(10):
        time.sleep(0.5)
        if not sw_running():
            return
    run(["taskkill", "/F", "/T", "/IM", "SLDWORKS.exe"], timeout=30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--mode", choices=("review", "release"), default="review")
    a = ap.parse_args()
    root = Path(a.repo_root).resolve()
    spec_path = (root / a.spec).resolve()
    was_running = sw_running()
    try:
        print("TZ_PRECHECK: K01-TZ-AI-OPERATING v1.0 | ACTIVE=DRAWING SYSTEM V1 CANDIDATE BUILD | WIP=1 | PRODUCT>EVIDENCE>AUTOMATION")
        need(spec_path.is_file(), "drawing spec missing: " + str(spec_path))
        spec, blockers = preflight(root, spec_path, a.mode)
        print("DRAWING: " + spec["drawing_id"] + " | PART: " + spec["part_id"] + " | MODE: " + a.mode.upper())
        print("DATUM NAMESPACE: " + "/".join(d["id"] for d in spec["datum_features"]) + " UNIQUE=PASS")
        if blockers:
            print("RELEASE BLOCKERS: %d (review build allowed; release build prohibited)" % len(blockers))
            for b in blockers:
                print("  - " + b)
        need(not was_running, "Close SolidWorks before Drawing System v1; source CAD hash must be captured before automation starts.")
        need((root / CS).is_file(), "C# engine missing: " + str(root / CS))
        rd = redist()
        refs = [rd / "SolidWorks.Interop.sldworks.dll", rd / "SolidWorks.Interop.swconst.dll"]
        build = root / WORK / "build"
        build.mkdir(parents=True, exist_ok=True)
        exe = build / "K01DrawingSystemV1.exe"
        report = root / WORK / (spec["drawing_id"].replace("-", "_") + "_DRAWING_SYSTEM_V1_CURRENT.txt")
        placement = root / "control" / "drawings" / "placement" / (spec["drawing_id"] + "_PLACEMENT_CURRENT.json")
        cmd = [str(csc()), "/nologo", "/langversion:5", "/target:exe", "/optimize+", "/out:" + str(exe)]
        cmd += ["/reference:" + str(x) for x in refs]
        cmd += ["/reference:System.Web.Extensions.dll", str(root / CS)]
        cp = run(cmd, cwd=root)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        need(cp.returncode == 0, "Drawing System v1 C# compile failed")
        for x in refs:
            shutil.copy2(x, build / x.name)
        helper_cmd = [str(exe), "--spec", str(spec_path), "--report", str(report), "--mode", a.mode]
        if placement.is_file():
            helper_cmd += ["--placement", str(placement)]
        cp = run(helper_cmd, cwd=root, timeout=900)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        need(cp.returncode in (0, 3), "Drawing System v1 helper execution error")
        finalize_candidate(root, spec_path, spec, report)
        try:
            ctl = run([sys.executable, str(root / "tools/medtas/drawing_control_v1.py"), "--repo-root", str(root)], cwd=root, timeout=120)
            if ctl.stdout:
                print(ctl.stdout, end="")
            if ctl.stderr:
                print(ctl.stderr, end="")
            if ctl.returncode not in (0, 3):
                print("DRAWING CONTROL: WARN refresh return code=" + str(ctl.returncode))
        except Exception as ctl_err:
            print("DRAWING CONTROL: WARN " + repr(ctl_err))
        return cp.returncode
    except Exception as e:
        print("STATUS: HOLD_K01_DRAWING_SYSTEM_V1")
        print("ERROR:", repr(e))
        return 2
    finally:
        cleanup_owned_sw(was_running)


if __name__ == "__main__":
    raise SystemExit(main())
