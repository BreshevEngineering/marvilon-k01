from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from medtas_v16_common import register_build, register_verify

NODE_ID = "K01.DRAWING.D006.PROJECTION"
COMPILED = Path("reports/product_definition/current/K01_P007_PRODUCT_DEFINITION_COMPILED.json")
DRAWING_SLICE = Path("reports/product_definition/current/K01_P007_PD_SLICE_DRAWING.json")
GATE = Path("reports/control/K01_D006_DRAWING_AUTHORING_GATE_CURRENT.json")
PROFILE = Path("control/drawings/K01_D006_PROJECTION_PROFILE_v10.json")
OUT = Path("reports/drawing/current/K01-D-006_PROJECTION_CURRENT.json")
OUT_MD = Path("reports/drawing/current/K01-D-006_PROJECTION_CURRENT.md")
WORK = Path("reports/cad/d006_projection_v10_current")
CS = Path("cad_api/solidworks_2018_proven/current/K01_D006_PROJECTION_V10/K01D006ProjectionV10.cs")
CANDIDATE_ROOT = Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def fmt(v, digits=2):
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return f"{float(v):.{digits}f}"
    return str(v)


def char_map(compiled: dict) -> dict[str, dict]:
    return {str(x.get("id")): x for x in compiled.get("characteristics", []) if x.get("id")}


def build_callout(c: dict) -> str:
    cid = c["id"]
    n = c.get("nominal_or_requirement") or {}
    v = c.get("variation_semantics") or {}
    if cid == "C01":
        return "[C01] DATUM A — J2 MATING FACE | FLATNESS / ORIENTATION: OPEN"
    if cid == "C02":
        return (
            f"[C02] Ø{fmt(n.get('diameter_mm'))} {v.get('diameter_fit','')} | DATUM {n.get('datum','B')} | "
            f"BORE DEPTH {fmt(n.get('bore_depth_mm'))} NOM | DEPTH TOL: {v.get('depth_tolerance','OPEN')}"
        ).replace("  ", " ")
    if cid == "C04":
        return (
            f"[C04] {int(n.get('count',3))}X Ø{fmt(n.get('hole_diameter_mm'))} THRU | "
            f"PCD Ø{fmt(n.get('pcd_mm'))} NOM | {fmt(n.get('equal_spacing_deg'),0)}° EQ | "
            f"SIZE/POS TOL: {v.get('hole_size_tolerance','OPEN')}/{v.get('position_tolerance','OPEN')}"
        )
    if cid == "C05":
        return (
            f"[C05] FLANGE Ø{fmt(n.get('diameter_mm'))} NOM | T {fmt(n.get('thickness_mm'))} NOM | "
            f"RELEASE TOL: {v.get('diameter_tolerance','OPEN')}/{v.get('thickness_tolerance','OPEN')}"
        )
    if cid == "C06":
        return f"[C06] OAL {fmt(n.get('overall_length_mm'))} NOM | RELEASE TOL: {v.get('length_tolerance','OPEN')}"
    if cid == "C07":
        return f"[C07] CAN OD Ø{fmt(n.get('diameter_mm'))} NOM | RELEASE TOL: {v.get('diameter_tolerance','OPEN')}"
    if cid == "C08":
        return (
            f"[C08] CAN ID Ø{fmt(n.get('id_mm'))} NOM | RADIAL WALL {fmt(n.get('radial_wall_mm'))} NOM | "
            f"RELEASE TOL: {v.get('id_tolerance','OPEN')}/{v.get('wall_tolerance','OPEN')}"
        )
    if cid == "C09":
        return f"[C09] MATERIAL: {n.get('material','OPEN')}"
    if cid == "K01-D006-BLIND-END":
        return f"[K01-D006-BLIND-END] THICKNESS {fmt(n.get('thickness_mm'))} NOM | RELEASE TOL: {v.get('thickness_tolerance','OPEN')}"
    # Future-proof fallback is still driven by compiled authority, never by legacy candidate text.
    projection = str(c.get("drawing_projection") or "").replace("PROJECT ", "").strip()
    return f"[{cid}] {projection or 'CONTROLLED CHARACTERISTIC — SEE PRODUCT DEFINITION'}"


def build_projection_plan(drawing_slice: dict, profile: dict) -> dict:
    fingerprint = str(drawing_slice.get("slice_sha256") or "")
    safe = [str(x) for x in drawing_slice.get("safe_projection_ids", [])]
    cm = char_map(drawing_slice)
    zones = profile["callout_zones"]
    zone_index: dict[str, int] = {k: 0 for k in zones}
    evidence = []
    notes = []

    for cid in safe:
        if cid not in cm:
            raise RuntimeError(f"safe projection characteristic missing from compiled definition: {cid}")
        zone = profile.get("characteristic_zone", {}).get(cid, "META")
        if zone not in zones:
            raise RuntimeError(f"layout zone missing for {cid}: {zone}")
        z = zones[zone]
        i = zone_index[zone]
        zone_index[zone] += 1
        text = build_callout(cm[cid])
        note = {
            "characteristic_id": cid,
            "zone": zone,
            "x_m": float(z["x_m"]),
            "y_m": float(z["y_start_m"]) - i * float(z["y_step_m"]),
            "text": text,
            "projection_method": "CONTROLLED_NOTE_FALLBACK",
            "source_projection_fingerprint": fingerprint,
            "semantic_readback_or_fallback_class": "PROJECTION_FALLBACK__EDITABLE_BASE_DRAWING",
        }
        notes.append(note)
        evidence.append({k: note[k] for k in (
            "characteristic_id", "projection_method", "source_projection_fingerprint", "semantic_readback_or_fallback_class"
        )})

    # Explicit OPEN engineering states may be visible on design-review drawing, but must stay nonnumeric.
    open_zone = profile.get("open_zone", "OPEN")
    z = zones[open_zone]
    open_items = []
    for cid in ("C10", "C11", "C12"):
        c = cm.get(cid)
        if c and str(c.get("definition_state", "")).upper().startswith("OPEN"):
            open_items.append({"id": cid, "role": c.get("role"), "state": c.get("definition_state")})
    for g in drawing_slice.get("coverage_gaps", []):
        if str(g.get("state", "")).upper().startswith("OPEN"):
            open_items.append({"id": str(g.get("id")), "role": str(g.get("category") or g.get("requirement") or "OPEN"), "state": g.get("state")})
    for i, item in enumerate(open_items):
        text = f"[{item['id']}] {item['role']} : {item['state']}"
        notes.append({
            "characteristic_id": item["id"],
            "zone": open_zone,
            "x_m": float(z["x_m"]),
            "y_m": float(z["y_start_m"]) - i * float(z["y_step_m"]),
            "text": text,
            "projection_method": "EXPLICIT_OPEN_NOTE",
            "source_projection_fingerprint": fingerprint,
            "semantic_readback_or_fallback_class": "NONNUMERIC_OPEN_STATE",
        })

    return {
        "schema": "k01.d006.projection_plan.v10",
        "drawing": "K01-D-006",
        "part": drawing_slice.get("part"),
        "source_projection_fingerprint": fingerprint,
        "safe_projection_ids": safe,
        "notes": notes,
        "projection_evidence": evidence,
        "view_layout": profile.get("view_layout", []),
        "policy": "Drawing Product Definition slice only. Fallback notes are design-review projection carriers, not a released dimensional authority.",
    }


def write_tsv(path: Path, plan: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for n in plan["notes"]:
        text = str(n["text"]).replace("\t", " ").replace("\r", " ").replace("\n", "\\n")
        lines.append("\t".join([str(n["characteristic_id"]), str(n["zone"]), f"{n['x_m']:.6f}", f"{n['y_m']:.6f}", text]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_layout_tsv(path: Path, plan: dict):
    lines = []
    for x in plan.get("view_layout", []):
        lines.append("\t".join([str(x["selector"]), f"{float(x['x_m']):.6f}", f"{float(x['y_m']):.6f}", f"{float(x['scale']):.6f}", str(x.get("role", ""))]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_seed(root: Path) -> tuple[Path, str]:
    base = CANDIDATE_ROOT
    candidates = []
    if base.exists():
        patterns = [
            ("BASE_V7", "base_v7_*/K01-D-006*_BASE_V7_CANDIDATE.SLDDRW"),
            ("REFINED_EXISTING", "refined_existing_*/K01-D-006*_REFINED_CANDIDATE.SLDDRW"),
            ("PROFESSIONAL_SEED", "professional_*/K01-D-006*_PROFESSIONAL_CANDIDATE*.SLDDRW"),
        ]
        for klass, pattern in patterns:
            for p in base.glob(pattern):
                if p.is_file():
                    candidates.append((p.stat().st_mtime, klass, p))
        # Prefer the most recent within the best class, not a newer low-quality fallback class.
        for klass in ("BASE_V7", "REFINED_EXISTING", "PROFESSIONAL_SEED"):
            xs = [x for x in candidates if x[1] == klass]
            if xs:
                _, _, p = max(xs, key=lambda x: x[0])
                return p, klass
    raise RuntimeError("No existing linked K01-D-006 seed drawing found under D:\\Marvilon\\K01\\cad\\drawings\\candidates\\K01-D-006")


def csc() -> Path:
    w = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for p in (w / "Microsoft.NET/Framework64/v4.0.30319/csc.exe", w / "Microsoft.NET/Framework/v4.0.30319/csc.exe"):
        if p.exists():
            return p
    raise RuntimeError("csc.exe missing")


def redist() -> Path:
    for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"), Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
        if (p / "SolidWorks.Interop.sldworks.dll").exists():
            return p
    raise RuntimeError("SOLIDWORKS 2018 API redist missing")


def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, errors="replace", timeout=timeout)


def sw_running() -> bool:
    cp = run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"], timeout=30)
    return "sldworks.exe" in ((cp.stdout or "") + (cp.stderr or "")).lower()


def parse_kv(path: Path) -> dict[str, str]:
    out = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=r"D:\BreshevEngineering\marvilon-k01")
    a = ap.parse_args()
    root = Path(str(a.repo_root).strip().strip('"')).resolve()
    compiled_path = root / COMPILED
    drawing_slice_path = root / DRAWING_SLICE
    gate_path = root / GATE
    profile_path = root / PROFILE
    work = root / WORK
    report_path = root / OUT
    md_path = root / OUT_MD
    status = "HOLD_D006_PROJECTION_V10"
    try:
        if sw_running():
            raise RuntimeError("Close SolidWorks before V10 so the existing saved SLDDRW is the controlled seed.")
        compiled, drawing_slice, gate, profile = load(compiled_path), load(drawing_slice_path), load(gate_path), load(profile_path)
        full_fp = str(compiled.get("compiled_definition_sha256") or "")
        fp = str(drawing_slice.get("slice_sha256") or "")
        if not full_fp:
            raise RuntimeError("compiled Product Definition full fingerprint missing")
        if not fp:
            raise RuntimeError("drawing Product Definition slice fingerprint missing")
        if str(compiled.get("drawing_projection_sha256") or "") != fp or str(gate.get("drawing_projection_sha256") or "") != fp:
            raise RuntimeError("drawing projection fingerprint mismatch between compiled definition, drawing slice and drawing gate")
        if gate.get("status") != "PASS_TO_DRAWING_PROJECTION_COMPILER":
            raise RuntimeError("drawing authoring gate is not PASS_TO_DRAWING_PROJECTION_COMPILER")
        if (compiled.get("gates") or {}).get("DRAWING_CANDIDATE_READY") != "PASS":
            raise RuntimeError("DRAWING_CANDIDATE_READY is not PASS")

        plan = build_projection_plan(drawing_slice, profile)
        safe = set(plan["safe_projection_ids"])
        projected = {x["characteristic_id"] for x in plan["projection_evidence"]}
        if projected != safe:
            raise RuntimeError(f"projection plan coverage mismatch projected={sorted(projected)} safe={sorted(safe)}")

        work.mkdir(parents=True, exist_ok=True)
        plan_json = work / "K01_D006_PROJECTION_PLAN_V10_CURRENT.json"
        notes_tsv = work / "K01_D006_PROJECTION_NOTES_V10_CURRENT.tsv"
        layout_tsv = work / "K01_D006_PROJECTION_LAYOUT_V10_CURRENT.tsv"
        raw = work / "K01_D006_PROJECTION_V10_RAW_CURRENT.txt"
        dump(plan_json, plan)
        write_tsv(notes_tsv, plan)
        write_layout_tsv(layout_tsv, plan)

        seed, seed_class = find_seed(root)
        seed_sha = sha256(seed)
        rd = redist()
        refs = [rd / "SolidWorks.Interop.sldworks.dll", rd / "SolidWorks.Interop.swconst.dll"]
        for x in refs:
            if not x.exists():
                raise RuntimeError(f"SOLIDWORKS interop missing: {x}")
        build = work / "build"
        build.mkdir(parents=True, exist_ok=True)
        exe = build / "K01D006ProjectionV10.exe"
        cmd = [str(csc()), "/nologo", "/langversion:5", "/target:exe", "/optimize+", "/out:" + str(exe)]
        cmd += ["/reference:" + str(x) for x in refs]
        cmd += [str(root / CS)]
        cp = run(cmd, cwd=root)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        if cp.returncode != 0:
            raise RuntimeError("D006 V10 projection helper compile failed")
        for x in refs:
            shutil.copy2(x, build / x.name)

        cp = run([
            str(exe),
            "--drawing", str(seed),
            "--notes", str(notes_tsv),
            "--layout", str(layout_tsv),
            "--fingerprint", fp,
            "--out-root", str(CANDIDATE_ROOT),
            "--report", str(raw),
        ], cwd=root, timeout=600)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        kv = parse_kv(raw)
        output_drw = Path(kv.get("OUTPUT_DRAWING", "")) if kv.get("OUTPUT_DRAWING") else None
        output_pdf = Path(kv.get("OUTPUT_PDF", "")) if kv.get("OUTPUT_PDF") else None
        output_bmp = Path(kv.get("OUTPUT_BMP", "")) if kv.get("OUTPUT_BMP") else None
        read_ids = {x for x in (kv.get("READBACK_IDS", "").split(",") if kv.get("READBACK_IDS") else []) if x}
        semantic_pass = cp.returncode == 0 and read_ids.issuperset(safe) and kv.get("SOURCE_DRAWING_INVARIANT") == "True"
        if not semantic_pass:
            raise RuntimeError(f"V10 semantic projection incomplete: return={cp.returncode} read={sorted(read_ids)} safe={sorted(safe)}")
        for p in (output_drw, output_pdf, output_bmp):
            if p is None or not p.exists():
                raise RuntimeError(f"V10 output missing: {p}")

        status = "PASS_D006_PROJECTION_V10_BASE__VISUAL_QA_REQUIRED"
        evidence = []
        for x in plan["projection_evidence"]:
            y = dict(x)
            y["semantic_readback"] = x["characteristic_id"] in read_ids
            evidence.append(y)
        report = {
            "schema": "k01.d006.projection.current.v10_1",
            "generated_utc": now_utc(),
            "status": status,
            "node_id": NODE_ID,
            "drawing": "K01-D-006",
            "part": "K01-P-007",
            "compiled_definition": str(COMPILED).replace("\\", "/"),
            "compiled_definition_sha256": full_fp,
            "drawing_slice": str(DRAWING_SLICE).replace("\\", "/"),
            "drawing_projection_sha256": fp,
            "source_seed": {"path": str(seed), "class": seed_class, "sha256": seed_sha, "invariant": True},
            "candidate": {
                "slddrw": str(output_drw), "sha256": sha256(output_drw),
                "pdf": str(output_pdf), "pdf_sha256": sha256(output_pdf),
                "bmp": str(output_bmp), "bmp_sha256": sha256(output_bmp),
            },
            "semantic_projection": {
                "status": "PASS",
                "safe_projection_ids": plan["safe_projection_ids"],
                "projected_safe_ids": sorted(read_ids.intersection(safe)),
                "coverage": f"{len(read_ids.intersection(safe))}/{len(safe)}",
                "projection_evidence": evidence,
                "fallback_count": len(evidence),
                "native_drawing_semantic_carrier_count": 0,
                "rule": "Fallback callouts are compiled-definition-driven design-review carriers. They are editable working-base semantics, not release dimensions/GD&T."
            },
            "visual_qa": {"status": "PENDING_HUMAN", "manual_last_mile_target": "10-20% layout/leader/spacing/title-block cleanup"},
            "release": {"status": "HOLD", "reason": "DRAWING_RELEASE_READY remains HOLD in Product Definition"},
            "open_notes": [x for x in plan["notes"] if x["projection_method"] == "EXPLICIT_OPEN_NOTE"],
            "raw_report": str(raw),
            "projection_plan": str(plan_json),
        }
        dump(report_path, report)
        md = [
            "# K01-D-006 drawing projection V10", "",
            f"**Status:** `{status}`  ",
            f"**Compiled Product Definition:** `{full_fp}`  ",
            f"**Drawing projection slice:** `{fp}`  ",
            f"**Semantic projection coverage:** `{report['semantic_projection']['coverage']}`  ",
            "**Visual QA:** `PENDING_HUMAN`  ",
            "**Release:** `HOLD`", "",
            "## Projected characteristics", "",
        ]
        for n in plan["notes"]:
            if n["projection_method"] == "CONTROLLED_NOTE_FALLBACK":
                md.append(f"- `{n['characteristic_id']}` — {n['text']}")
        md += ["", "## Boundary", "", "This is a usable editable base drawing. Controlled note fallbacks do not become released dimensional authority; release requires native/approved semantic carriers, visual QA and closure of Product Definition blockers."]
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

        br = register_build(root, NODE_ID, "tools/medtas/d006_projection_compiler_v10.py", limitations=["Visual QA pending", "Projection carriers are controlled fallback notes, not released native dimensions"], extra={"compiled_definition_sha256": full_fp, "drawing_projection_sha256": fp, "candidate_slddrw": str(output_drw)})
        vr = register_verify(root, NODE_ID, "PASS_WITH_LIMITATIONS", metrics={"semantic_projection_coverage": report["semantic_projection"]["coverage"], "fallback_count": len(evidence), "source_seed_invariant": True, "visual_qa": "PENDING_HUMAN", "drawing_release_ready": False}, limitations=["Human visual QA required", "Release Product Definition blockers remain open"], notes="V10 verifies complete controlled semantic projection to an editable base SLDDRW. It does not assert released manufacturing drawing quality.")
        print("STATUS:", status)
        print("SEMANTIC_PROJECTION:", report["semantic_projection"]["coverage"], "PASS")
        print("FALLBACK_CALLOUTS:", len(evidence))
        print("VISUAL_QA: PENDING_HUMAN")
        print("DRAWING_RELEASE: HOLD")
        print("DRAWING:", output_drw)
        print("PDF:", output_pdf)
        print("BMP:", output_bmp)
        print("REPORT:", report_path)
        print("MEDTAS_STATE_HASH:", br["built_state_hash"])
        print("MEDTAS_VERIFY:", vr["verdict"])
        return 0
    except Exception as e:
        report = {
            "schema": "k01.d006.projection.current.v10_1",
            "generated_utc": now_utc(),
            "status": status,
            "error": repr(e),
            "rule": "Do not regress to rejected V6/V7 methods. V10 consumes only the V11 drawing slice for projection semantics; fix only bounded structural/projection issues."
        }
        dump(report_path, report)
        print("STATUS:", status)
        print("ERROR:", repr(e))
        print("REPORT:", report_path)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
