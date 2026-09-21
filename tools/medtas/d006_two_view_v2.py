#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from d006_two_view_v1 import build_manifest

OUT_ROOT = Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")
CS = Path("cad_api/solidworks_2018_proven/current/K01_D006_TWO_VIEW_V2/K01D006TwoViewV2.cs")
WORK = Path("reports/cad/d006_two_view_v2_current")
MANIFEST = Path("reports/drawing/current/K01_D006_CHARACTERISTIC_MANIFEST_CURRENT.tsv")
EDR31 = Path("control/decisions/EDR-031_P007_J2_SEAL_FACE_SURFACE_TEXTURE_ENGINEERING_REVIEW.json")
READINESS = Path("reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json")


def run(cmd, cwd=None, timeout=900):
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
    )


def need(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sw_running():
    cp = run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"], timeout=30)
    return "sldworks.exe" in ((cp.stdout or "") + (cp.stderr or "")).lower()


def latest_v1():
    dirs = sorted(
        [p for p in OUT_ROOT.glob("two_view_v1_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    need(bool(dirs), "No two_view_v1_* candidate found under " + str(OUT_ROOT))
    d = dirs[0]
    dr = d / "K01-D-006_Hermetic_Magnetic_Can_TWO_VIEW_CANDIDATE.SLDDRW"
    pt = d / "K01-P-007_Hermetic_Magnetic_Can_TWO_VIEW_SOURCE_CANDIDATE.SLDPRT"
    need(dr.is_file(), "Latest V1 drawing missing: " + str(dr))
    need(pt.is_file(), "Latest V1 part copy missing: " + str(pt))
    return dr, pt


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
    raise RuntimeError("SOLIDWORKS API redist missing")


def append_review_authorities(root: Path, manifest_path: Path):
    edr31 = jload(root / EDR31)
    need(
        edr31.get("status") == "ACCEPT_ENGINEERING_REVIEW_CANDIDATE__RELEASE_CONDITIONAL",
        "EDR-031 is not the accepted engineering-review surface-texture authority",
    )
    accepted = edr31.get("accepted_option") or {}
    need(accepted.get("parameter") == "Ra", "EDR-031 parameter is not Ra")
    ra = float(accepted.get("value_um_max"))
    need(abs(ra - 0.8) < 1e-12, "EDR-031 Ra authority drift")

    readiness = jload(root / READINESS)
    release_state = readiness.get("status", "")
    need(
        release_state == "PASS_DRAWING_CANDIDATE_READY__HOLD_RELEASE",
        "Unexpected P007 readiness state: " + release_state,
    )

    chars = jload(root / "control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json")
    datum_a = chars.get("datum_A") or {}
    datum_a_entities = datum_a.get("entities") or []
    need(datum_a.get("binding_mode") == "COMPOSITE_COPLANAR_FACE_SET", "Datum A binding mode drift")
    need(len(datum_a_entities) == 2, f"Datum A authority must contain exactly two controlled patches, got {len(datum_a_entities)}")
    datum_a_areas = [float(e["area_m2"]) for e in datum_a_entities]
    need(all(a > 0.0 for a in datum_a_areas), "Datum A authority contains invalid face area")
    need(abs(datum_a_areas[0] - datum_a_areas[1]) > 1e-12, "Datum A controlled face areas are not distinguishable")

    edr29 = jload(root / "control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json")
    edr32 = jload(root / "control/decisions/EDR-032_P007_C02_LOCATOR_DEPTH_RELEASE.json")
    edr33 = jload(root / "control/decisions/EDR-033_P007_C04_ISO5458_PATTERN_RELEASE.json")

    need(edr32.get("status") == "ACCEPTED_RELEASE_DEFINITION", "EDR-032 not accepted")
    need(edr33.get("status") == "ACCEPTED_RELEASE_DEFINITION", "EDR-033 not accepted")
    c02 = next(c for c in chars["characteristics"] if c["id"] == "C02")
    c02_spec = c02.get("candidate_spec", "")
    c04_spec = edr33["decision"]["P007_release_spec"]
    c07_spec = edr29["decision"]["C07"]["release_spec"]
    c08_spec = edr29["decision"]["C08"]["release_spec"]

    def fit(spec: str, diameter: str, label: str):
        m = re.search(rf"Ø\s*{re.escape(diameter)}\s*([A-Za-z][0-9]+)", spec, re.I)
        need(m is not None, f"Cannot parse {label} fit from: {spec}")
        return m.group(1)

    c02_fit = fit(c02_spec, "14.10", "C02")
    c04_fit = fit(c04_spec, "2.90", "C04")
    c07_fit = fit(c07_spec, "10", "C07")
    c08_fit = fit(c08_spec, "9.40", "C08")
    need(c02_fit == "H7" and c04_fit == "H10" and c07_fit == "h9" and c08_fit == "H9", "fit authority drift")

    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(f"C02_FIT\t{c02_fit}\n")
        f.write(f"C04_FIT\t{c04_fit}\n")
        f.write(f"C07_FIT\t{c07_fit}\n")
        f.write(f"C08_FIT\t{c08_fit}\n")
        f.write(f"J2_SEAL_RA_UM_MAX\t{ra}\n")
        f.write(f"DATUM_A_FACE_AREA_1_M2\t{datum_a_areas[0]:.15g}\n")
        f.write(f"DATUM_A_FACE_AREA_2_M2\t{datum_a_areas[1]:.15g}\n")
        f.write("DATUM_A_BINDING_SOURCE\tK01_P007_PRODUCT_CHARACTERISTICS.datum_A.entities\n")
        f.write("J2_SEAL_RA_SCOPE\tENGINEERING_REVIEW_CONDITIONAL\n")
        f.write(f"P007_READINESS\t{release_state}\n")
        f.write("C02_DEPTH_AUTHORITY\tEDR-032_P007_C02_LOCATOR_DEPTH_RELEASE\n")
        f.write("C04_PATTERN_AUTHORITY\tEDR-033_P007_C04_ISO5458_PATTERN_RELEASE\n")
        f.write("D006_RELEASE_STATE\tHOLD\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    a = ap.parse_args()
    root = Path(a.repo_root).resolve()
    try:
        print(
            "TZ_PRECHECK: K01-TZ-AI-OPERATING v1.0 | "
            "GOAL=FULL K01-D-006 | WIP=1 | PRODUCT>EVIDENCE>AUTOMATION"
        )
        print("MODE: TWO_VIEW_V2 ISO/GPS PROFESSIONAL REFINEMENT | RELEASE=HOLD")
        need(
            not sw_running(),
            "Close SolidWorks before TWO_VIEW_V2; saved V1 candidate must be the controlled input.",
        )
        drawing, part = latest_v1()
        need((root / CS).is_file(), "C# helper missing: " + str(root / CS))
        need((root / EDR31).is_file(), "EDR-031 missing: " + str(root / EDR31))
        need((root / READINESS).is_file(), "P007 readiness missing: " + str(root / READINESS))

        manifest = root / MANIFEST
        build_manifest(root, manifest)
        append_review_authorities(root, manifest)

        rd = redist()
        refs = [rd / "SolidWorks.Interop.sldworks.dll", rd / "SolidWorks.Interop.swconst.dll"]
        for p in refs:
            need(p.is_file(), "interop missing: " + str(p))

        build = root / WORK / "build"
        build.mkdir(parents=True, exist_ok=True)
        report = root / WORK / "K01_D006_TWO_VIEW_V2_CURRENT.txt"
        exe = build / "K01D006TwoViewV2.exe"
        cmd = [
            str(csc()),
            "/nologo",
            "/langversion:5",
            "/target:exe",
            "/optimize+",
            "/out:" + str(exe),
        ]
        cmd += ["/reference:" + str(x) for x in refs]
        cmd += [str(root / CS)]
        cp = run(cmd, cwd=root)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        need(cp.returncode == 0, "TWO_VIEW_V2 C# compile failed")
        for x in refs:
            shutil.copy2(x, build / x.name)

        cp = run(
            [
                str(exe),
                "--drawing",
                str(drawing),
                "--part",
                str(part),
                "--manifest",
                str(manifest),
                "--out-root",
                str(OUT_ROOT),
                "--report",
                str(report),
            ],
            cwd=root,
            timeout=900,
        )
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        need(cp.returncode in (0, 3), "TWO_VIEW_V2 helper execution error")
        return cp.returncode
    except Exception as e:
        print("STATUS: HOLD_D006_TWO_VIEW_V2")
        print("ERROR:", repr(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
