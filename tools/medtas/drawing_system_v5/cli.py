
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .utils import load_json, save_json
from .validator import prebuild_gate, validate_schema
from .compiler import compile_manifest
from .preview import build_semantic_preview
from .qa import audit_dxf

ROOT = Path(__file__).resolve().parents[1]

def load_family(family_id):
    p = ROOT / "families" / (family_id + ".json")
    if not p.is_file():
        raise RuntimeError("DRAWING_FAMILY_NOT_FOUND: " + str(p))
    return load_json(p)

def cmd_validate(args):
    contract = load_json(args.contract)
    family = load_family(contract["drawing_family"])
    result = prebuild_gate(contract, family, args.mode)
    if args.out:
        save_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["generation_allowed"] else 3

def cmd_compile(args):
    contract = load_json(args.contract)
    family = load_family(contract["drawing_family"])
    gate = prebuild_gate(contract, family, args.mode)
    if not gate["generation_allowed"]:
        save_json(args.gate_out, gate)
        print("STATUS=" + gate["status"])
        print("BUILD_ALLOWED=FALSE")
        print("GATE_REPORT=" + str(args.gate_out))
        return 3
    manifest = compile_manifest(contract, family, args.mode)
    save_json(args.out, manifest)
    save_json(args.gate_out, gate)
    print("STATUS=PASS_CONTRACT_COMPILE")
    print("MANIFEST=" + str(args.out))
    print("GATE_REPORT=" + str(args.gate_out))
    return 0

def cmd_preview(args):
    contract = load_json(args.contract)
    family = load_family(contract["drawing_family"])
    gate = prebuild_gate(contract, family, "review")
    if not gate["generation_allowed"]:
        print("STATUS=" + gate["status"])
        return 3
    manifest = compile_manifest(contract, family, "review")
    path = build_semantic_preview(contract, manifest, args.out)
    print("STATUS=PASS_SEMANTIC_PREVIEW")
    print("DXF=" + path)
    return 0

def cmd_qa_dxf(args):
    contract = load_json(args.contract)
    result = audit_dxf(contract, args.dxf)
    if args.out:
        save_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("PASS_") else 3

def cmd_pipeline(args):
    contract = load_json(args.contract)
    family = load_family(contract["drawing_family"])
    gate = prebuild_gate(contract, family, args.mode)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    save_json(outdir / "prebuild_gate.json", gate)

    print("DRAWING=" + contract["drawing_id"])
    print("PART=" + contract["part_id"])
    print("FAMILY=" + contract["drawing_family"])
    print("MODE=" + args.mode)
    print("PREBUILD=" + gate["status"])

    # Semantic preview is allowed whenever review prebuild is structurally valid.
    review_gate = prebuild_gate(contract, family, "review")
    if review_gate["generation_allowed"]:
        manifest_review = compile_manifest(contract, family, "review")
        save_json(outdir / "build_manifest_review.json", manifest_review)
        build_semantic_preview(contract, manifest_review, outdir / "semantic_preview.dxf")
        print("PREVIEW=PASS " + str(outdir / "semantic_preview.dxf"))

    if gate["generation_allowed"]:
        manifest = compile_manifest(contract, family, args.mode)
        save_json(outdir / "build_manifest.json", manifest)
        print("COMPILE=PASS " + str(outdir / "build_manifest.json"))
        return 0

    print("COMPILE=BLOCKED")
    return 3

def main():
    ap = argparse.ArgumentParser(prog="marvilon-drawing-system-v5")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.add_argument("--contract", required=True)
    p.add_argument("--mode", choices=["review","manufacturing"], default="review")
    p.add_argument("--out")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("compile")
    p.add_argument("--contract", required=True)
    p.add_argument("--mode", choices=["review","manufacturing"], default="review")
    p.add_argument("--out", required=True)
    p.add_argument("--gate-out", required=True)
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("preview")
    p.add_argument("--contract", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("qa-dxf")
    p.add_argument("--contract", required=True)
    p.add_argument("--dxf", required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_qa_dxf)

    p = sub.add_parser("pipeline")
    p.add_argument("--contract", required=True)
    p.add_argument("--mode", choices=["review","manufacturing"], default="review")
    p.add_argument("--outdir", required=True)
    p.set_defaults(func=cmd_pipeline)

    args = ap.parse_args()
    raise SystemExit(args.func(args))

if __name__ == "__main__":
    main()
