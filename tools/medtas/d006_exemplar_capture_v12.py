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
WORKSPACE = ROOT / "reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json"
D1 = ROOT / "reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json"
SLICE = ROOT / "reports/product_definition/current/K01_P007_PD_SLICE_DRAWING.json"
POLICY = ROOT / "control/drawings/K01_D006_EXEMPLAR_POLICY_CURRENT.json"
CS = ROOT / "cad_api/solidworks_2018_proven/current/K01_D006_EXEMPLAR_V12/K01D006ExemplarScanV12.cs"
RAW = ROOT / "reports/cad/d006_exemplar_v12_current/K01_D006_EXEMPLAR_SCAN_V12_RAW_CURRENT.txt"
OUT = ROOT / "reports/drawing/current/K01-D-006_EXEMPLAR_CAPTURE_CURRENT.json"
OUT_MD = ROOT / "reports/drawing/current/K01-D-006_EXEMPLAR_CAPTURE_CURRENT.md"
CTRL = ROOT / "reports/control/K01_D006_EXEMPLAR_CAPTURE_CURRENT.json"


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
        if p.exists(): return p
    raise RuntimeError("csc.exe missing")


def redist() -> Path:
    for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"), Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
        if (p / "SolidWorks.Interop.sldworks.dll").exists(): return p
    raise RuntimeError("SOLIDWORKS 2018 API redist missing")


def parse_kv(p: Path) -> dict[str, str]:
    out = {}
    for raw in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def compile_helper() -> Path:
    rd = redist(); refs = [rd / "SolidWorks.Interop.sldworks.dll", rd / "SolidWorks.Interop.swconst.dll", rd / "SolidWorks.Interop.swdimxpert.dll"]
    for r in refs:
        if not r.exists(): raise RuntimeError(f"interop missing: {r}")
    build = RAW.parent / "build_scan"; build.mkdir(parents=True, exist_ok=True)
    exe = build / "K01D006ExemplarScanV12.exe"
    cmd = [str(csc()), "/nologo", "/langversion:5", "/target:exe", "/optimize+", "/out:"+str(exe)] + ["/reference:"+str(r) for r in refs] + [str(CS)]
    cp = run(cmd, ROOT)
    if cp.stdout: print(cp.stdout, end="")
    if cp.stderr: print(cp.stderr, end="")
    if cp.returncode != 0: raise RuntimeError("V12 exemplar scan helper compile failed")
    for r in refs: shutil.copy2(r, build / r.name)
    return exe


def main() -> int:
    status = "HOLD_D006_EXEMPLAR_CAPTURE_V12"
    try:
        if sw_running(): raise RuntimeError("Close SolidWorks before exemplar capture so readback/export uses the saved files on disk.")
        for p in (WORKSPACE, D1, SLICE, POLICY, CS):
            if not p.exists(): raise RuntimeError(f"missing input: {p.relative_to(ROOT)}")
        ws, d1, ds = load(WORKSPACE), load(D1), load(SLICE)
        if ws.get("status") != "PASS_D006_EXEMPLAR_WORKSPACE_PREPARED": raise RuntimeError("exemplar workspace is not prepared")
        part = Path(ws["workspace"]["part"]); drawing = Path(ws["workspace"]["drawing"])
        if not part.is_file() or not drawing.is_file(): raise RuntimeError("workspace part/drawing missing")
        # Preserve external source evidence; only the dedicated workspace may have changed.
        src_drw = Path(ws["source"]["v10_drawing"]); src_part = Path(ws["source"]["p007_part"])
        if sha256(src_drw) != ws["source"]["v10_drawing_sha256"]: raise RuntimeError("source V10 drawing changed after workspace preparation")
        if sha256(src_part) != ws["source"]["p007_part_sha256"]: raise RuntimeError("source P007 part changed after workspace preparation")
        exe = compile_helper(); RAW.parent.mkdir(parents=True, exist_ok=True)
        cp = run([str(exe), "--drawing", str(drawing), "--part", str(part), "--report", str(RAW)], ROOT, timeout=600)
        if cp.stdout: print(cp.stdout, end="")
        if cp.stderr: print(cp.stderr, end="")
        kv = parse_kv(RAW)
        c02_model = kv.get("C02_MODEL_H7") == "True"
        c02_drawing = kv.get("C02_DRAWING_H7") == "True"
        c01_datum_a = kv.get("C01_DRAWING_DATUM_A") == "True"
        drawing_mm = kv.get("DRAWING_LENGTH_UNIT_MM") == "True"
        c02_evidence_mode = kv.get("C02_DRAWING_EVIDENCE_MODE", "")
        refs = int(kv.get("P007_VIEW_REFS", "0") or 0)
        c05_safe = kv.get("C05_MODEL_NONE") == "True"
        # Source identity for a frozen exemplar is path + SHA captured at PREP.
        # V10 did not have a V11 drawing-slice fingerprint; it consumed the full compiled
        # Product Definition fingerprint. Early V12 workspaces accidentally wrote a missing
        # `drawing_projection_sha256` field under the misleading name `drawing_slice_sha256`.
        # That legacy metadata defect must never invalidate proven native PMI transport.
        source_v10_compiled_fp = str(
            ws.get("source_v10_compiled_definition_sha256")
            or (ws.get("source") or {}).get("v10_compiled_definition_sha256")
            or ""
        )
        legacy_misnamed_fp = str(ws.get("drawing_slice_sha256") or "")
        current_slice_fp = str(ds.get("slice_sha256") or "")
        frozen_source_trace_present = bool(
            (ws.get("source") or {}).get("v10_drawing")
            and (ws.get("source") or {}).get("v10_drawing_sha256")
            and (ws.get("source") or {}).get("p007_part")
            and (ws.get("source") or {}).get("p007_part_sha256")
        )
        source_trace_mode = (
            "FROZEN_PATH_SHA_PLUS_V10_COMPILED_FP"
            if source_v10_compiled_fp
            else "FROZEN_PATH_SHA_ONLY__LEGACY_V12_METADATA_GAP"
        )
        # V10 fallback callouts are design-review carriers, not release-native PMI.
        # They must be removed/hidden during D6 regardless of fingerprint freshness.
        fallback_cleanup_required = True
        d1_plan_current = str(ws.get("d1_plan_sha256") or "") == str(d1.get("authoring_plan_sha256") or "")
        checks = {
            "EXQA-001_SOURCE_INVARIANCE": True,
            "EXQA-002_FROZEN_SOURCE_PROVENANCE": frozen_source_trace_present,
            "EXQA-003_P007_LINKED_VIEWS": refs > 0,
            "EXQA-004_C02_MODEL_NATIVE_H7": c02_model,
            "EXQA-005_C02_DRAWING_LINKED_H7": c02_drawing,
            "EXQA-006_C01_DRAWING_DATUM_A": c01_datum_a,
            "EXQA-007_DRAWING_LENGTH_UNIT_MM": drawing_mm,
            "EXQA-008_C05_UNRELEASED_TOLERANCE_NOT_DEFAULTED": c05_safe,
            "EXQA-009_D2_SCOPE_FROM_D1": set(["C01.DATUM_A","C02.DIAMETER_FIT","C09.MATERIAL"]).issubset(set(d1.get("d2_authorizable_claim_ids") or [])),
            "EXQA-010_D1_PLAN_UNCHANGED_SINCE_WORKSPACE_PREP": d1_plan_current,
        }
        blocking = [k for k,v in checks.items() if k not in {"EXQA-008_C05_UNRELEASED_TOLERANCE_NOT_DEFAULTED"} and not v]
        warnings = [] if c05_safe else ["C05 Diameter4 is not tolerance NONE in the exemplar model; do not treat/import it as released semantics."]
        if not source_v10_compiled_fp:
            warnings.append("Legacy V12 workspace has no recoverable V10 compiled-definition fingerprint because PREP read a non-existent drawing_projection_sha256 field. Exact frozen source path+SHA provenance is verified, so native C01/C02 transport remains valid. Do not use legacy V10 fallback callouts for D7; remove/hide them during D6.")
        if fallback_cleanup_required:
            warnings.append("V10 fallback callouts are design-review carriers only and must be removed/hidden before D7 release-native semantic QA.")
        if c02_drawing and c02_evidence_mode == "LINKED_MODEL_DISPLAY_DIMENSION_SEMANTIC_FALLBACK":
            warnings.append("SW2018 drawing readback did not preserve a usable DimXpert identity flag/name for C02; exemplar acceptance uses linked P007 view + native display-dimension value/tolerance provenance. Full D3 must still prove claim identity and binding invariance.")
        if not blocking:
            status = "PASS_D006_EXEMPLAR_NATIVE_TRANSPORT__D6_CLEANUP_REQUIRED"
        else:
            status = "HOLD_D006_EXEMPLAR_SEMANTIC_BASE"
        pdf = Path(kv.get("PDF", "")) if kv.get("PDF") else None
        bmp = Path(kv.get("BMP", "")) if kv.get("BMP") else None
        payload = {
            "schema":"k01.d006.exemplar_capture.current.v1",
            "generated_utc":now(),
            "status":status,
            "drawing":"K01-D-006","part":"K01-P-007",
            "lane":"DESIGN_REVIEW_EXEMPLAR_NOT_RELEASE",
            "workspace":{"part":str(part),"part_sha256":sha256(part),"drawing":str(drawing),"drawing_sha256":sha256(drawing)},
            "drawing_slice_sha256":current_slice_fp,
            "fingerprints":{
                "source_v10_compiled_definition_sha256":source_v10_compiled_fp or None,
                "legacy_misnamed_workspace_fingerprint":legacy_misnamed_fp or None,
                "current_drawing_slice_sha256":current_slice_fp,
                "frozen_source_trace_present":frozen_source_trace_present,
                "source_trace_mode":source_trace_mode,
                "fallback_cleanup_required":fallback_cleanup_required,
                "d1_plan_current":d1_plan_current
            },
            "checks":checks,
            "warnings":warnings,
            "native_readback":{
                "C01_drawing_datum_A":c01_datum_a,
                "C01_drawing_view":kv.get("C01_DRAWING_VIEW"),
                "C02_model_h7":c02_model,
                "C02_drawing_h7":c02_drawing,
                "C02_drawing_view":kv.get("C02_DRAWING_VIEW"),
                "C02_drawing_evidence_mode":c02_evidence_mode,
                "C05_model_none":c05_safe,
                "drawing_length_unit_mm":drawing_mm,
                "drawing_display_dimension_count":int(kv.get("DRAWING_DISPLAY_DIM_COUNT","0") or 0),
                "drawing_dimxpert_flag_count":int(kv.get("DRAWING_DIMXPERT_FLAG_COUNT","0") or 0),
                "drawing_datum_count":int(kv.get("DRAWING_DATUM_COUNT","0") or 0),
                "p007_view_refs":refs
            },
            "artifacts":{"pdf":str(pdf) if pdf else None,"pdf_sha256":sha256(pdf) if pdf and pdf.exists() else None,"bmp":str(bmp) if bmp else None,"bmp_sha256":sha256(bmp) if bmp and bmp.exists() else None},
            "d3_release_native_status":"PARTIAL__C01_C02_SAVED_DRAWING_PRESENTATION_PROVEN__CLAIM_IDENTITY_ANNOTATION_VIEW_AND_BINDING_INVARIANCE_STILL_REQUIRE_D3",
            "d7_release_native_status":"NOT_RUN__EXEMPLAR_PRECHECK_ONLY",
            "visual_qa":"PENDING_HUMAN",
            "release":"HOLD",
            "raw":str(RAW)
        }
        dump(OUT,payload)
        md=["# K01-D-006 exemplar capture V12","",f"**Status:** `{status}`  ",f"**C01 drawing Datum A:** `{c01_datum_a}`  ",f"**C02 model H7:** `{c02_model}`  ",f"**C02 drawing linked H7:** `{c02_drawing}`  ",f"**C02 drawing evidence:** `{c02_evidence_mode or 'NONE'}`  ",f"**Drawing units MM:** `{drawing_mm}`  ",f"**P007 linked views:** `{refs}`  ",f"**Source trace mode:** `{source_trace_mode}`  ",f"**Fallback cleanup required:** `{fallback_cleanup_required}`  ",f"**Visual QA:** `PENDING_HUMAN`  ","**Release:** `HOLD`","","## Checks"]+[f"- `{k}` — {'PASS' if v else 'HOLD'}" for k,v in checks.items()]+["","## Fingerprints",f"- source V10 compiled definition: `{source_v10_compiled_fp or 'LEGACY_METADATA_GAP'}`",f"- legacy misnamed workspace field: `{legacy_misnamed_fp or 'EMPTY'}`",f"- current Product Definition drawing slice: `{current_slice_fp}`","","## Boundary","","This controlled manual exemplar proves saved native drawing presentation of the authorized C01/C02 scope and the drawing environment. Frozen source identity is exact path + SHA. Legacy V10 fallback callouts are design-review carriers and must be removed/hidden in D6 before D7. Full D3 claim identity/binding invariance, D7 provenance QA, visual QA, and manufacturing-route/release blockers remain open."]
        OUT_MD.parent.mkdir(parents=True,exist_ok=True);OUT_MD.write_text("\n".join(md)+"\n",encoding="utf-8")
        next_action = "Proceed to D6 cleanup/layout on this exact exemplar. Hide/remove stale V10 fallback notes first; retain native Datum A and C02 Ø14.10 H7. Do not change engineering semantics. Then perform visual QA and continue to D3/D7." if not blocking else "Resolve only the listed blocking checks before further exemplar work."
        dump(CTRL,{"schema":"k01.d006.exemplar_capture_gate.current.v1","generated_utc":payload["generated_utc"],"status":status,"blocking_checks":blocking,"warnings":warnings,"report":str(OUT.relative_to(ROOT)),"next":next_action})
        br=register_build(ROOT,"K01.DRAWING.D006.EXEMPLAR.CAPTURE","tools/medtas/d006_exemplar_capture_v12.py",limitations=["Full D3 invariance pending","Full D7 pending","Visual QA pending","Release HOLD","V10 fallback carriers require D6 cleanup before D7"],extra={"workspace_drawing":str(drawing),"drawing_slice_sha256":current_slice_fp,"source_v10_compiled_definition_sha256":source_v10_compiled_fp or None,"source_trace_mode":source_trace_mode})
        verdict="PASS_WITH_LIMITATIONS" if not blocking else "HOLD"
        register_verify(ROOT,"K01.DRAWING.D006.EXEMPLAR.CAPTURE",verdict,metrics={"C01_drawing_datum_A":c01_datum_a,"C02_model_h7":c02_model,"C02_drawing_h7":c02_drawing,"C02_evidence_mode":c02_evidence_mode,"drawing_length_unit_mm":drawing_mm,"p007_view_refs":refs,"drawing_display_dimension_count":payload["native_readback"]["drawing_display_dimension_count"],"drawing_dimxpert_flag_count":payload["native_readback"]["drawing_dimxpert_flag_count"]},limitations=warnings+["Full D3/D7 release-native verification not yet implemented","Visual QA pending"])
        print("STATUS:",status)
        print("BLOCKING_CHECKS:", ",".join(blocking) if blocking else "NONE")
        print("SOURCE_TRACE_MODE:", source_trace_mode)
        print("FALLBACK_CLEANUP_REQUIRED:", fallback_cleanup_required)
        print("C01_DRAWING_DATUM_A:",c01_datum_a,"view="+str(kv.get("C01_DRAWING_VIEW") or ""))
        print("C02_MODEL_H7:",c02_model)
        print("C02_DRAWING_H7:",c02_drawing,"view="+str(kv.get("C02_DRAWING_VIEW") or ""),"evidence="+c02_evidence_mode)
        print("DRAWING_LENGTH_UNIT_MM:",drawing_mm)
        print("P007_VIEW_REFS:",refs)
        print("PDF:",pdf)
        print("BMP:",bmp)
        print("REPORT:",OUT)
        print("MEDTAS_STATE_HASH:",br["built_state_hash"])
        return 0 if not blocking else 3
    except Exception as e:
        dump(CTRL,{"schema":"k01.d006.exemplar_capture_gate.current.v1","generated_utc":now(),"status":status,"error":repr(e)})
        print("STATUS:",status);print("ERROR:",repr(e));print("REPORT:",CTRL);return 2


if __name__ == "__main__":
    raise SystemExit(main())
