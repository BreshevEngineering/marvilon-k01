#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

DRAW_ROOT = Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")
PART = Path(r"D:\Marvilon\K01\cad\candidates\p007_d2_exemplar\manual_exemplar_20260912_165501\K01-P-007_Hermetic_Magnetic_Can_D2_EXEMPLAR_CANDIDATE.SLDPRT")
CS = Path("cad_api/solidworks_2018_proven/current/K01_D006_TWO_VIEW_V1/K01D006TwoViewV1.cs")
WORK = Path("reports/cad/d006_two_view_v1_current")
MANIFEST = Path("reports/drawing/current/K01_D006_CHARACTERISTIC_MANIFEST_CURRENT.tsv")


def run(cmd, cwd=None, timeout=900):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, errors="replace", timeout=timeout)


def need(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def sw_running():
    cp = run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"], timeout=30)
    return "sldworks.exe" in ((cp.stdout or "") + (cp.stderr or "")).lower()


def csc():
    w = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for p in (
        w / "Microsoft.NET/Framework64/v4.0.30319/csc.exe",
        w / "Microsoft.NET/Framework/v4.0.30319/csc.exe",
    ):
        if p.exists():
            return p
    raise RuntimeError("csc.exe missing")


def redist():
    for p in (
        Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),
        Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),
    ):
        if (p / "SolidWorks.Interop.sldworks.dll").exists():
            return p
    raise RuntimeError("SOLIDWORKS 2018 API redist missing")


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def accepted_status(x: str):
    return x in {"PASS_DECISION", "ACCEPTED_RELEASE_DEFINITION"}


def latest_v2_drawing():
    candidates = list(DRAW_ROOT.glob("import_all_dims_v2_*/K01-D-006_Hermetic_Magnetic_Can_IMPORT_ALL_DIMS_CANDIDATE.SLDDRW"))
    need(candidates, f"No IMPORT_ALL_DIMS_V2 candidate under {DRAW_ROOT}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def one_float(pattern, text, label):
    m = re.search(pattern, text, flags=re.I)
    need(m is not None, f"Cannot parse {label} from: {text}")
    return float(m.group(1))


def build_manifest(root: Path, out: Path):
    edr024 = jload(root / "control/decisions/EDR-024_P007_C02_LOCATOR_DEPTH_BASELINE.json")
    edr025 = jload(root / "control/decisions/EDR-025_P007_MONOLITHIC_REMOVABLE_J2_BASELINE.json")
    edr028 = jload(root / "control/decisions/EDR-028_P007_C03_C04_RELEASE.json")
    edr029 = jload(root / "control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json")
    edr030 = jload(root / "control/decisions/EDR-030_P007_C01_C05_C06_BLIND_END_RELEASE.json")
    edr032 = jload(root / "control/decisions/EDR-032_P007_C02_LOCATOR_DEPTH_RELEASE.json")
    edr033 = jload(root / "control/decisions/EDR-033_P007_C04_ISO5458_PATTERN_RELEASE.json")
    chars = jload(root / "control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json")

    need(accepted_status(edr024.get("status", "")), "EDR-024 not accepted")
    need(accepted_status(edr025.get("status", "")), "EDR-025 not accepted")
    need(accepted_status(edr028.get("status", "")), "EDR-028 not accepted")
    need(accepted_status(edr029.get("status", "")), "EDR-029 not accepted")
    need(accepted_status(edr030.get("status", "")), "EDR-030 not accepted")
    need(accepted_status(edr032.get("status", "")), "EDR-032 not accepted")
    need(accepted_status(edr033.get("status", "")), "EDR-033 not accepted")

    c02 = next(c for c in chars["characteristics"] if c["id"] == "C02")
    c02_spec = c02.get("candidate_spec", "")
    c02_dia = one_float(r"Ø\s*([0-9.]+)\s*H7", c02_spec, "C02 diameter")
    c02_depth_spec = edr032["decision"]["P007_C02_release_spec"]
    m = re.search(r"depth\s*([0-9.]+)\s*±\s*([0-9.]+)", c02_depth_spec, re.I)
    need(m is not None, f"Cannot parse released C02 depth: {c02_depth_spec}")
    c02_depth, c02_depth_tol = map(float, m.groups())

    c03_spec = edr028["decision"]["C03"]["P007_release_spec"]
    c03_perp = one_float(r"Ø\s*([0-9.]+)\s*\(M\)", c03_spec, "C03 perpendicularity")

    c04_spec = edr033["decision"]["P007_release_spec"]
    c04_hole = one_float(r"Ø\s*([0-9.]+)\s*H10", c04_spec, "C04 hole")
    c04_pcd = one_float(r"TED\s+PCD\s*Ø\s*([0-9.]+)", c04_spec, "C04 PCD TED")
    c04_angle = one_float(r"TED\s+([0-9.]+)°", c04_spec, "C04 angle TED")
    c04_pos = one_float(r"POSITION\s*[⌀Ø]\s*([0-9.]+)", c04_spec, "C04 position")
    c04_cz = " CZ " in (" " + c04_spec.upper() + " ")
    c04_mmr = "Ⓜ" in c04_spec or "(M)" in c04_spec.upper()
    need(c04_cz and c04_mmr, "C04 EDR-033 must contain both CZ and MMR semantics")

    c07_spec = edr029["decision"]["C07"]["release_spec"]
    c07_dia = one_float(r"Ø\s*([0-9.]+)\s*h9", c07_spec, "C07 diameter")
    c08_spec = edr029["decision"]["C08"]["release_spec"]
    c08_dia = one_float(r"Ø\s*([0-9.]+)\s*H9", c08_spec, "C08 diameter")
    c11_spec = edr029["decision"]["C11"]["release_spec"]
    c11_runout = one_float(r"TOTAL\s+RUNOUT\s+([0-9.]+)", c11_spec, "C11 runout")

    c01_spec = edr030["decision"]["C01"]["release_spec"]
    c01_flat = one_float(r"FLATNESS\s+([0-9.]+)\s+CZ", c01_spec, "C01 flatness")
    c05_spec = edr030["decision"]["C05"]["release_spec"]
    c05_od = one_float(r"Ø\s*([0-9.]+)\s*±\s*([0-9.]+)", c05_spec, "C05 OD")
    m = re.search(r"Ø\s*([0-9.]+)\s*±\s*([0-9.]+).*?thickness\s*([0-9.]+)\s*±\s*([0-9.]+)", c05_spec, re.I)
    need(m is not None, f"Cannot parse C05 full spec: {c05_spec}")
    c05_od, c05_od_tol, c05_t, c05_t_tol = map(float, m.groups())
    c06_spec = edr030["decision"]["C06"]["release_spec"]
    m = re.search(r"OAL\s*([0-9.]+)\s*±\s*([0-9.]+)", c06_spec, re.I)
    need(m is not None, f"Cannot parse C06: {c06_spec}")
    c06_oal, c06_tol = map(float, m.groups())
    blind_spec = edr030["decision"]["K01-D006-BLIND-END"]["release_spec"]
    m = re.search(r"([0-9.]+)\s*±\s*([0-9.]+)", blind_spec)
    need(m is not None, f"Cannot parse blind end: {blind_spec}")
    blind_t, blind_tol = map(float, m.groups())
    edge = edr030["decision"]["EDGE_CONDITION"]["release_spec"]

    # Strong anti-regression assertions: these values are parsed from accepted EDRs,
    # not invented by the drawing executor.
    need(abs(c02_dia - 14.10) < 1e-9 and abs(c02_depth - 2.00) < 1e-9 and abs(c02_depth_tol - 0.05) < 1e-9, "C02 authority drift")
    need(abs(c03_perp - 0.003) < 1e-9, "C03 authority drift")
    need(abs(c04_hole - 2.90) < 1e-9 and abs(c04_pcd - 26.50) < 1e-9 and abs(c04_pos - 0.15) < 1e-9, "C04 authority drift")
    need(abs(c07_dia - 10.0) < 1e-9 and abs(c08_dia - 9.40) < 1e-9 and abs(c11_runout - 0.02) < 1e-9, "EDR-029 authority drift")
    need(abs(c01_flat - 0.03) < 1e-9 and abs(c05_od - 33.0) < 1e-9 and abs(c06_oal - 35.0) < 1e-9 and abs(blind_t - 1.0) < 1e-9, "EDR-030 authority drift")

    manifest = {
        "C01_FLATNESS_MM": c01_flat,
        "C02_DIA_MM": c02_dia,
        "C02_DEPTH_MM": c02_depth,
        "C02_DEPTH_TOL_MM": c02_depth_tol,
        "C03_PERP_MM": c03_perp,
        "C04_HOLE_DIA_MM": c04_hole,
        "C04_PCD_MM": c04_pcd,
        "C04_ANGLE_DEG": c04_angle,
        "C04_POSITION_MM": c04_pos,
        "C04_PATTERN_CZ": "TRUE" if c04_cz else "FALSE",
        "C04_POSITION_MMR": "TRUE" if c04_mmr else "FALSE",
        "C04_DATUM_B_MMR": "FALSE",
        "C05_OD_MM": c05_od,
        "C05_OD_TOL_MM": c05_od_tol,
        "C05_THK_MM": c05_t,
        "C05_THK_TOL_MM": c05_t_tol,
        "C06_OAL_MM": c06_oal,
        "C06_TOL_MM": c06_tol,
        "C07_DIA_MM": c07_dia,
        "C08_DIA_MM": c08_dia,
        "C08_WALL_REF_MM": one_float(r"([0-9.]+)\s*mm\s+nominal/reference", edr029["decision"]["C08"]["wall_definition"], "C08 wall reference"),
        "C11_RUNOUT_MM": c11_runout,
        "BLIND_THK_MM": blind_t,
        "BLIND_TOL_MM": blind_tol,
        "MATERIAL": "AISI 316L / EN 1.4404",
        "EDGE_CONDITION": edge,
        "ARCHITECTURE": edr025["decision"]["P007_construction"],
        "JOINT": edr025["decision"]["P003_P007_joint"],
        "WELD": edr025["decision"]["permanent_P003_P007_weld"],
        "C12": "OPEN_DO_NOT_AUTHOR_NUMERIC",
        "SURFACE_TEXTURE": "OPEN_DO_NOT_AUTHOR_GENERIC_RA",
        "C01_CZ_MODE": "ISO5458_CZ_CONTROLLED__SW2018_INLINE_LITERAL_IF_ACCEPTED",
        "C04_CZ_MODE": "ISO5458_CZ_CONTROLLED__SW2018_INLINE_LITERAL_IF_ACCEPTED",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(f"{k}\t{v}\n" for k, v in manifest.items()), encoding="utf-8")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    a = ap.parse_args()
    root = Path(a.repo_root).resolve()
    try:
        need(not sw_running(), "Close SolidWorks before TWO_VIEW_V1; saved drawing is the controlled input.")
        source_drawing = latest_v2_drawing()
        need(PART.is_file(), f"P007 D2 exemplar part missing: {PART}")
        need((root / CS).is_file(), f"C# helper missing: {root / CS}")
        manifest = root / MANIFEST
        build_manifest(root, manifest)

        rd = redist()
        refs = [rd / "SolidWorks.Interop.sldworks.dll", rd / "SolidWorks.Interop.swconst.dll"]
        for p in refs:
            need(p.is_file(), f"interop missing: {p}")
        build = root / WORK / "build"
        build.mkdir(parents=True, exist_ok=True)
        exe = build / "K01D006TwoViewV1.exe"
        report = root / WORK / "K01_D006_TWO_VIEW_V1_CURRENT.txt"
        cmd = [str(csc()), "/nologo", "/langversion:5", "/target:exe", "/optimize+", "/out:" + str(exe)]
        cmd += ["/reference:" + str(x) for x in refs]
        cmd += [str(root / CS)]
        cp = run(cmd, cwd=root)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        need(cp.returncode == 0, "TWO_VIEW_V1 C# compile failed")
        for x in refs:
            shutil.copy2(x, build / x.name)

        cp = run([
            str(exe),
            "--drawing", str(source_drawing),
            "--part", str(PART),
            "--manifest", str(manifest),
            "--out-root", str(DRAW_ROOT),
            "--report", str(report),
        ], cwd=root, timeout=900)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        need(cp.returncode in (0, 3), "TWO_VIEW_V1 helper execution error")
        return cp.returncode
    except Exception as e:
        print("STATUS: HOLD_D006_TWO_VIEW_V1")
        print("ERROR:", repr(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
