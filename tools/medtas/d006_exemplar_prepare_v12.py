from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from medtas_v16_common import register_build, register_verify

ROOT = Path(__file__).resolve().parents[2]
D1 = ROOT / "reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json"
V10 = ROOT / "reports/drawing/current/K01-D-006_PROJECTION_CURRENT.json"
POLICY = ROOT / "control/drawings/K01_D006_EXEMPLAR_POLICY_CURRENT.json"
PROVEN = ROOT / "reports/control/K01_P007_PMI_PROVEN_CURRENT.json"
V6_RAW = ROOT / "reports/cad/d006_automated_native_pmi_v6_current/K01_D006_AUTOMATED_NATIVE_PMI_V6_RAW_CURRENT.txt"
CS = ROOT / "cad_api/solidworks_2018_proven/current/K01_D006_EXEMPLAR_V12/K01D006ExemplarRelinkV12.cs"
OUT = ROOT / "reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json"
OUT_MD = ROOT / "reports/drawing/current/K01-D-006_EXEMPLAR_WORKPACK_CURRENT.md"
CTRL = ROOT / "reports/control/K01_D006_EXEMPLAR_PREP_CURRENT.json"
WORK = ROOT / "reports/cad/d006_exemplar_v12_current"
PART_ROOT = Path(r"D:\Marvilon\K01\cad\candidates\p007_d2_exemplar")
DRAW_ROOT = Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, errors="replace", timeout=timeout)


def sw_running() -> bool:
    cp = run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"], timeout=30)
    return "sldworks.exe" in ((cp.stdout or "") + (cp.stderr or "")).lower()


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


def parse_kv_text(text: str) -> dict[str, str]:
    out = {}
    for raw in text.splitlines():
        if "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def find_part_source() -> tuple[Path, str, bool]:
    if V6_RAW.exists():
        text = V6_RAW.read_text(encoding="utf-8-sig", errors="replace")
        kv = parse_kv_text(text)
        p = Path(kv.get("DRAWING_SOURCE_PART", "")) if kv.get("DRAWING_SOURCE_PART") else None
        semantics_ok = "PMI_AFTER C02=True" in text and "hole=H7" in text and "C05=True" in text and "swTolNONE" in text
        if p and p.is_file() and semantics_ok:
            return p, "V6_NATIVE_SEMANTICS_VERIFIED_SOURCE_REUSED", True
    proven = load(PROVEN)
    p = Path(proven["candidate"]["path"])
    if not p.is_file():
        raise RuntimeError(f"no P007 authoring source found; proven candidate missing: {p}")
    return p, "PROVEN_STEP13_SOURCE__C02_H7_AND_C05_NONE_REQUIRE_MANUAL_D2_CORRECTION", False


def compile_helper() -> tuple[Path, list[Path]]:
    rd = redist()
    refs = [rd / "SolidWorks.Interop.sldworks.dll", rd / "SolidWorks.Interop.swconst.dll"]
    for r in refs:
        if not r.exists():
            raise RuntimeError(f"interop missing: {r}")
    build = WORK / "build"
    build.mkdir(parents=True, exist_ok=True)
    exe = build / "K01D006ExemplarRelinkV12.exe"
    cmd = [str(csc()), "/nologo", "/langversion:5", "/target:exe", "/optimize+", "/out:" + str(exe)] + ["/reference:" + str(r) for r in refs] + [str(CS)]
    cp = run(cmd, ROOT)
    if cp.stdout:
        print(cp.stdout, end="")
    if cp.stderr:
        print(cp.stderr, end="")
    if cp.returncode != 0:
        raise RuntimeError("V12 exemplar relink helper compile failed")
    for r in refs:
        shutil.copy2(r, build / r.name)
    return exe, refs


def main() -> int:
    status = "HOLD_D006_EXEMPLAR_PREP_V12"
    try:
        if sw_running():
            raise RuntimeError("Close SolidWorks before exemplar workspace preparation; reference-safe relink requires saved documents as sources.")
        for p in (D1, V10, POLICY, PROVEN, CS):
            if not p.exists():
                raise RuntimeError(f"missing input: {p.relative_to(ROOT)}")
        d1, v10, policy = load(D1), load(V10), load(POLICY)
        if d1.get("status") != "PASS_D1_AUTHORING_PLAN":
            raise RuntimeError("D1 authoring plan is not PASS")
        auth = list(d1.get("d2_authorizable_claim_ids") or [])
        required = {"C01.DATUM_A", "C02.DIAMETER_FIT", "C09.MATERIAL"}
        if not required.issubset(set(auth)):
            raise RuntimeError(f"D2 route-independent exemplar scope incomplete; required={sorted(required)} actual={auth}")
        if v10.get("status") != "PASS_D006_PROJECTION_V10_BASE__VISUAL_QA_REQUIRED":
            raise RuntimeError("current V10 semantic base is not PASS")
        source_drawing = Path(v10["candidate"]["slddrw"])
        if not source_drawing.is_file():
            raise RuntimeError(f"V10 drawing missing: {source_drawing}")
        source_part, part_source_class, semantics_preverified = find_part_source()
        source_drawing_sha = sha256(source_drawing)
        source_part_sha = sha256(source_part)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        part_dir = PART_ROOT / ("manual_exemplar_" + stamp)
        draw_dir = DRAW_ROOT / ("manual_exemplar_v12_" + stamp)
        part_dir.mkdir(parents=True, exist_ok=False)
        draw_dir.mkdir(parents=True, exist_ok=False)
        part = part_dir / "K01-P-007_Hermetic_Magnetic_Can_D2_EXEMPLAR_CANDIDATE.SLDPRT"
        drawing = draw_dir / "K01-D-006_Hermetic_Magnetic_Can_EXEMPLAR_V12_CANDIDATE.SLDDRW"
        shutil.copy2(source_part, part)
        shutil.copy2(source_drawing, drawing)
        raw = WORK / "K01_D006_EXEMPLAR_RELINK_V12_RAW_CURRENT.txt"
        exe, _ = compile_helper()
        cp = run([str(exe), "--drawing", str(drawing), "--part", str(part), "--report", str(raw)], ROOT, timeout=600)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")
        if cp.returncode != 0:
            raise RuntimeError("exemplar reference-safe relink failed; see raw report")
        if sha256(source_drawing) != source_drawing_sha:
            raise RuntimeError("source V10 drawing changed during exemplar preparation")
        if sha256(source_part) != source_part_sha:
            raise RuntimeError("source P007 part changed during exemplar preparation")
        status = "PASS_D006_EXEMPLAR_WORKSPACE_PREPARED"
        payload = {
            "schema": "k01.d006.exemplar_workspace.current.v1",
            "generated_utc": now(),
            "status": status,
            "part": "K01-P-007",
            "drawing": "K01-D-006",
            "lane": policy["lane"],
            "d1_plan_sha256": d1.get("authoring_plan_sha256"),
            # V10 predates V11 domain slices. Preserve the exact semantic authority
            # V10 actually consumed; do not mislabel it as a drawing-slice fingerprint.
            "source_v10_compiled_definition_sha256": v10.get("compiled_definition_sha256"),
            "d2_authorizable_claim_ids": auth,
            "source": {
                "v10_drawing": str(source_drawing),
                "v10_drawing_sha256": source_drawing_sha,
                "v10_compiled_definition_sha256": v10.get("compiled_definition_sha256"),
                "v10_projection_schema": v10.get("schema"),
                "p007_part": str(source_part),
                "p007_part_sha256": source_part_sha,
                "p007_source_class": part_source_class,
                "c02_h7_c05_none_preverified": semantics_preverified,
                "source_invariance": True
            },
            "workspace": {
                "part": str(part),
                "part_initial_sha256": sha256(part),
                "drawing": str(drawing),
                "drawing_initial_sha256": sha256(drawing),
                "directory": str(draw_dir),
                "relink_raw": str(raw)
            },
            "manual_next": [
                "Open the workspace P007 part, not the proven/canonical source.",
                "Verify C02 Cylinder1/Diameter2 = Ø14.10 H7 with no shaft fit; if source class says manual correction required, correct it now.",
                "Do not author or change C05: it is not in the current D2-authorized claim scope. If the reused source already contains Cylinder2/Diameter4 with tolerance NONE, leave it as diagnostic design-review support; otherwise keep it out of the imported exemplar annotation view.",
                "Create/verify native Datum A on the controlled J2 mating face.",
                "Assign Datum A and C02 to the actual SOLIDWORKS annotation view whose orientation matches AV_J2_LONGITUDINAL; record its exact name.",
                "Verify native material AISI 316L / EN 1.4404. Save and close the part.",
                "Open the workspace SLDDRW. On Section A-A use Drawing View Import options manually: Import annotations ON; DimXpert annotations ON; Design annotations OFF; import the annotation-view content used above.",
                "Remove/hide only duplicate V10 fallback callouts for claims now shown natively. Do not alter unresolved OPEN/PARTIAL engineering values.",
                "Perform visual layout only, save drawing, close SOLIDWORKS, then run tools/commands/workflows_20260916/RUN_K01_D006_CAPTURE_EXEMPLAR_V12.cmd."
            ],
            "release": "HOLD__EXEMPLAR_NOT_RELEASE"
        }
        dump(OUT, payload)
        md = [
            "# K01-D-006 manual exemplar V12 workpack", "",
            f"**Status:** `{status}`  ",
            f"**Lane:** `{policy['lane']}`  ",
            f"**Workspace part:** `{part}`  ",
            f"**Workspace drawing:** `{drawing}`  ",
            f"**P007 source class:** `{part_source_class}`  ",
            f"**C02 H7 / C05 NONE preverified in source:** `{semantics_preverified}`", "",
            "## D2 authorizable claims", "",
        ] + [f"- `{x}`" for x in auth] + ["", "## Exact manual sequence", ""] + [f"{i+1}. {x}" for i, x in enumerate(payload["manual_next"])] + ["", "## Boundary", "", "This workspace is the manual exemplar used to learn the real SW2018 annotation-view/import/layout behavior. It is not a release drawing. Production-route-dependent characteristics remain blocked upstream."]
        OUT_MD.parent.mkdir(parents=True, exist_ok=True)
        OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
        ctrl = {
            "schema": "k01.d006.exemplar_prep.current.v1",
            "generated_utc": payload["generated_utc"],
            "status": status,
            "workspace": str(OUT.relative_to(ROOT)),
            "part": str(part),
            "drawing": str(drawing),
            "d2_authorizable_claim_ids": auth,
            "next": "Perform the bounded manual D2 + drawing import/layout sequence in the generated workpack, then close SOLIDWORKS and run tools/commands/workflows_20260916/RUN_K01_D006_CAPTURE_EXEMPLAR_V12.cmd."
        }
        dump(CTRL, ctrl)
        br = register_build(ROOT, "K01.DRAWING.D006.EXEMPLAR.WORKSPACE", "tools/medtas/d006_exemplar_prepare_v12.py", limitations=["Manual D2 authoring/import/layout required", "Release remains HOLD"], extra={"source_v10_compiled_definition_sha256": v10.get("compiled_definition_sha256"), "workspace_drawing": str(drawing)})
        register_verify(ROOT, "K01.DRAWING.D006.EXEMPLAR.WORKSPACE", "PASS_WITH_LIMITATIONS", metrics={"d2_authorizable_claims": len(auth), "source_invariance": True, "relinked": True}, limitations=["Manual authoring/import/layout pending", "Manufacturing route remains open for release"])
        print("STATUS:", status)
        print("D2_AUTHORIZABLE_CLAIMS:", ",".join(auth))
        print("PART:", part)
        print("DRAWING:", drawing)
        print("WORKPACK:", OUT_MD)
        print("REPORT:", CTRL)
        print("MEDTAS_STATE_HASH:", br["built_state_hash"])
        return 0
    except Exception as e:
        dump(CTRL, {"schema":"k01.d006.exemplar_prep.current.v1", "generated_utc":now(), "status":status, "error":repr(e)})
        print("STATUS:", status)
        print("ERROR:", repr(e))
        print("REPORT:", CTRL)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
