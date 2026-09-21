
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from datetime import datetime
import json, argparse, traceback
from .utils import load_json, save_json
from .validator import prebuild_gate
from .compiler import compile_manifest
from .preview import build_semantic_preview
from .qa import audit_dxf
from .legacy_bridge import execute_legacy_bridge

ROOT = Path(__file__).resolve().parents[1]

def load_family(family_id):
    p = ROOT / "families" / (family_id + ".json")
    if not p.is_file():
        raise RuntimeError("DRAWING_FAMILY_NOT_FOUND: " + str(p))
    return load_json(p)

def run_result(repo_root: str, contract_path: str, requested_mode: str, outdir: str, native: bool):
    contract = load_json(contract_path)
    family = load_family(contract["drawing_family"])
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    result = {
        "schema": "marvilon.drawing_result.v1",
        "drawing_id": contract["drawing_id"],
        "part_id": contract["part_id"],
        "requested_mode": requested_mode,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "execution_state": "PARTIAL_GENERATED",
        "engineering_state": "HOLD_ENGINEERING_DEFINITION",
        "release_state": "HOLD_RELEASE",
        "artifacts": {},
        "native_adapter": None,
    }

    try:
        gate = prebuild_gate(contract, family, requested_mode)
        save_json(out / "prebuild_gate.json", gate)
        result["engineering_state"] = gate["engineering_state"]
        result["release_state"] = gate["release_state"]
        result["generation_mode"] = gate["generation_mode"]
        result["artifacts"]["prebuild_gate"] = str(out / "prebuild_gate.json")

        if not gate["generation_allowed"]:
            result["execution_state"] = "FAILED_UNSAFE"
            result["reason"] = "Unsafe structural definition blocked generation."
            save_json(out / "RESULT_CURRENT.json", result)
            return result, 3

        # Always compile a manifest and produce a preview.
        manifest = compile_manifest(contract, family, gate["generation_mode"])
        save_json(out / "build_manifest.json", manifest)
        preview_path = build_semantic_preview(contract, manifest, out / "prebuild_semantic_schedule.dxf")
        preview_qa = audit_dxf(contract, preview_path)
        save_json(out / "prebuild_semantic_schedule_qa.json", preview_qa)

        result["artifacts"]["build_manifest"] = str(out / "build_manifest.json")
        result["artifacts"]["prebuild_semantic_schedule_dxf"] = str(out / "prebuild_semantic_schedule.dxf")
        result["artifacts"]["prebuild_semantic_schedule_qa"] = str(out / "prebuild_semantic_schedule_qa.json")
        result["execution_state"] = "GENERATED"

        # Prepare native bridge spec even if native execution is disabled.
        from .legacy_bridge import contract_to_legacy_spec
        legacy_spec = contract_to_legacy_spec(
            contract, family,
            str(Path(r"D:\Marvilon\K01\cad\drawings\candidates") / contract["drawing_id"])
        )
        save_json(out / "legacy_bridge_spec.json", legacy_spec)
        result["artifacts"]["legacy_bridge_spec"] = str(out / "legacy_bridge_spec.json")

        if native:
            native_result = execute_legacy_bridge(repo_root, contract, family, out / "native_bridge")
            result["native_adapter"] = native_result
            if native_result.get("drawing"):
                result["artifacts"]["slddrw"] = native_result["drawing"]
            if native_result.get("pdf"):
                result["artifacts"]["pdf"] = native_result["pdf"]
            if native_result.get("report"):
                result["artifacts"]["native_report"] = native_result["report"]
            if native_result.get("dxf"):
                result["artifacts"]["native_dxf"] = native_result["dxf"]
                try:
                    native_qa = audit_dxf(contract, native_result["dxf"])
                    save_json(out / "native_dxf_contract_qa.json", native_qa)
                    result["artifacts"]["native_dxf_contract_qa"] = str(out / "native_dxf_contract_qa.json")
                    result["native_dxf_qa_status"] = native_qa["status"]
                except Exception as qa_exc:
                    result["native_dxf_qa_status"] = "HOLD_NATIVE_DXF_QA_RUNTIME"
                    result["native_dxf_qa_error"] = repr(qa_exc)

            # Result-first: keep execution success if preview/manifest exist even when the
            # native adapter is partial/HOLD. Native failure is recorded, not hidden.
            if native_result["adapter_execution_state"] == "GENERATED":
                result["execution_state"] = "GENERATED"
            else:
                result["execution_state"] = "PARTIAL_GENERATED"

        has_native = bool(result["artifacts"].get("slddrw") or result["artifacts"].get("pdf"))
        has_native_qa = bool(result["artifacts"].get("native_dxf_contract_qa"))
        if has_native and has_native_qa:
            result["result_level"] = "LEVEL_3_NATIVE_DRAWING_PLUS_QA"
        elif has_native:
            result["result_level"] = "LEVEL_2_NATIVE_DRAWING"
        else:
            result["result_level"] = "LEVEL_1_CONTRACT_MANIFEST_PREVIEW"
        result["status"] = (
            "RESULT_GENERATED__HOLD_RELEASE"
            if result["release_state"] == "HOLD_RELEASE"
            else "RESULT_GENERATED__RELEASE_ELIGIBLE"
        )
        save_json(out / "RESULT_CURRENT.json", result)

        # execution success if at least the concrete manifest + DXF preview exist.
        return result, 0

    except Exception as exc:
        result["execution_state"] = "FAILED_UNSAFE"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
        save_json(out / "RESULT_CURRENT.json", result)
        return result, 3

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=r"D:\BreshevEngineering\marvilon-k01")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--mode", choices=["review","manufacturing"], default="manufacturing")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--native", action="store_true")
    args = ap.parse_args()

    result, rc = run_result(args.repo_root, args.contract, args.mode, args.outdir, args.native)

    print("="*88)
    print("MARVILON DRAWING SYSTEM V5.2.2 SELF-CONTAINED")
    print("DRAWING=" + result.get("drawing_id",""))
    print("EXECUTION_STATE=" + result.get("execution_state",""))
    print("ENGINEERING_STATE=" + result.get("engineering_state",""))
    print("RELEASE_STATE=" + result.get("release_state",""))
    print("STATUS=" + result.get("status", result.get("reason","")))
    for k,v in result.get("artifacts",{}).items():
        print(k.upper() + "=" + str(v))
    if result.get("native_adapter"):
        n = result["native_adapter"]
        print("NATIVE_ADAPTER=" + n.get("adapter_execution_state",""))
        print("NATIVE_LEGACY_RC=" + str(n.get("legacy_return_code","")))
    print("RESULT_JSON=" + str(Path(args.outdir) / "RESULT_CURRENT.json"))
    raise SystemExit(rc)

if __name__ == "__main__":
    main()
