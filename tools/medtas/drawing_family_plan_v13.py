from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from medtas_v16_common import register_build, register_verify

ROOT = Path(__file__).resolve().parents[2]
COMPILED = ROOT / "reports/product_definition/current/K01_P007_PRODUCT_DEFINITION_COMPILED.json"
CONTEXT = ROOT / "control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json"
RULES = ROOT / "control/drawings/K01_DRAWING_FAMILY_RULES_CURRENT.json"
BINDING = ROOT / "control/drawings/K01_P007_DRAWING_FAMILY_BINDING_CURRENT.json"
OUT = ROOT / "reports/drawing/current/K01-D-006_FAMILY_PLAN_CURRENT.json"
OUT_MD = ROOT / "reports/drawing/current/K01-D-006_FAMILY_PLAN_CURRENT.md"
CTRL = ROOT / "reports/control/K01_D006_DRAWING_FAMILY_PLAN_CURRENT.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat()


def obj_sha(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalize_drawing_role(role: str) -> str:
    r = (role or "").upper()
    aliases = {
        "SECTION_AA": "AXIAL_FULL_SECTION",
        "SECTION_BB": "AXIAL_FULL_SECTION",
        "AXIAL_SECTION": "AXIAL_FULL_SECTION",
        "FLANGE_END": "FLANGE_END",
        "END_VIEW": "FLANGE_END",
        "TITLE_BLOCK": "TITLE_BLOCK",
        "GENERAL_NOTE": "GENERAL_NOTE_OR_SPEC_REFERENCE",
        "GENERAL_NOTE_OR_SPEC_REFERENCE": "GENERAL_NOTE_OR_SPEC_REFERENCE",
    }
    return aliases.get(r, r or "UNASSIGNED")


def authoring_class_for(claim_role: str, carrier: str, drawing_role: str) -> str:
    role = (claim_role or "").upper()
    carr = (carrier or "").upper()
    dvr = (drawing_role or "").upper()
    if "DATUM" in role or "DATUM" in carr:
        return "DATUM_DRF"
    if "GDT" in role or "GDT" in carr or "GEOMETRIC" in carr:
        return "GDT"
    if role in {"HOLE_PATTERN", "PCD"} or "PATTERN" in carr or "LOCATION" in carr:
        return "LOCATION_PATTERN"
    if "SURFACE" in role or "SURFACE" in carr:
        return "SURFACE"
    if role in {"MATERIAL", "PROCESS_NOTE"} or dvr in {"TITLE_BLOCK", "GENERAL_NOTE_OR_SPEC_REFERENCE"}:
        return "MATERIAL_PROCESS_PROPERTY"
    return "SIZE_FIT"


def main() -> int:
    required = [COMPILED, CONTEXT, RULES, BINDING]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        print("STATUS: HOLD_DRAWING_FAMILY_PLAN_V13_MISSING_INPUTS")
        for x in missing:
            print("MISSING:", x)
        return 2

    compiled, context, rules, binding = map(load, required)
    family_id = binding.get("family")
    family = rules.get("families", {}).get(family_id)
    issues = []
    if not family:
        issues.append(f"FAMILY_NOT_FOUND:{family_id}")

    view_plan = binding.get("view_plan", {})
    expected_views = []
    for key in ("primary", "secondary", "auxiliary"):
        v = view_plan.get(key)
        if isinstance(v, dict):
            expected_views.append({"slot": key, **v})
    for x in view_plan.get("omit", []):
        expected_views.append({"slot": "omit", **x})

    role_overrides = binding.get("claim_role_overrides", {})
    chars = {x.get("id"): x for x in compiled.get("characteristics", []) if x.get("id")}
    routed = []
    seen = set()
    order_table = {x.get("class"): int(x.get("order", 999)) for x in rules.get("authoring_order", [])}
    claim_routing = (family or {}).get("claim_routing", {})

    for cid, cctx in context.get("characteristics", {}).items():
        da = cctx.get("drawing_authoring", {})
        for target in da.get("targets", []) or []:
            claim_id = target.get("claim_id")
            if not claim_id:
                issues.append(f"CLAIM_ID_MISSING:{cid}")
                continue
            if claim_id in seen:
                issues.append(f"CLAIM_ID_DUPLICATE:{claim_id}")
            seen.add(claim_id)
            claim_role = role_overrides.get(claim_id)
            if not claim_role:
                issues.append(f"FAMILY_CLAIM_ROLE_MISSING:{claim_id}")
                claim_role = "UNCLASSIFIED"
            planned_role = claim_routing.get(claim_role)
            if not planned_role:
                issues.append(f"FAMILY_ROUTE_MISSING:{claim_id}:{claim_role}")
                planned_role = "UNASSIGNED"
            declared = normalize_drawing_role(target.get("drawing_view_role"))
            # TITLE_BLOCK and general notes are non-view presentation carriers.
            compatible = declared == planned_role or (
                planned_role in {"TITLE_BLOCK", "GENERAL_NOTE_OR_SPEC_REFERENCE"}
                and declared == planned_role
            )
            if not compatible:
                issues.append(f"VIEW_ROUTE_MISMATCH:{claim_id}:declared={declared}:family={planned_role}")
            aclass = authoring_class_for(claim_role, target.get("carrier"), planned_role)
            routed.append({
                "characteristic_id": cid,
                "claim_id": claim_id,
                "claim_role": claim_role,
                "family_view_role": planned_role,
                "declared_view_role": declared,
                "route_compatible": compatible,
                "annotation_view_role": target.get("annotation_view_role"),
                "carrier": target.get("carrier"),
                "authoring_class": target.get("authoring_class"),
                "authoring_order_class": aclass,
                "authoring_order": order_table.get(aclass, 999),
                "action": target.get("action"),
                "release_eligible": bool(target.get("release_eligible")),
                "manufacturing_route_dependency": target.get("manufacturing_route_dependency"),
                "definition_state": chars.get(cid, {}).get("definition_state"),
            })

    routed.sort(key=lambda x: (x["authoring_order"], x["family_view_role"], x["claim_id"]))
    coverage = len(routed)
    status = "PASS_DRAWING_FAMILY_PLAN_V13" if not issues else "HOLD_DRAWING_FAMILY_PLAN_V13"
    core = {
        "schema": "k01.d006.drawing_family_plan.current.v1",
        "status": status,
        "part": binding.get("part"),
        "drawing": binding.get("drawing"),
        "family": family_id,
        "source_product_definition_sha256": compiled.get("compiled_definition_sha256"),
        "source_drawing_projection_sha256": compiled.get("drawing_projection_sha256"),
        "classification": binding.get("classification", {}),
        "view_plan": expected_views,
        "claim_routes": routed,
        "claim_route_count": coverage,
        "authoring_order": rules.get("authoring_order", []),
        "learned_exemplar_rules": binding.get("learned_exemplar_rules", []),
        "issues": issues,
        "rules": {
            "semantic_authority": "Product Definition only; family plan never invents dimensions/tolerances/GD&T.",
            "view_selection": "Minimum views; P007 primary is axial full section, flange end is secondary, isometric is auxiliary.",
            "dimension_routing": "Existing controlled claims route by engineering role to a preferred view; no AutoDimensionScheme.",
            "human_boundary": "D6 keeps final view spacing, leader routing, overlap resolution and readability judgment.",
            "release_boundary": "Plan does not change D2 authorization or release HOLD state."
        }
    }
    core["family_plan_sha256"] = obj_sha(core)
    payload = {**core, "generated_utc": now()}
    dump(OUT, payload)

    lines = [
        "# K01-D-006 drawing family plan V13",
        "",
        f"**Status:** `{status}`  ",
        f"**Family:** `{family_id}`  ",
        f"**Claims routed:** `{coverage}`  ",
        f"**Plan SHA-256:** `{payload['family_plan_sha256']}`  ",
        "",
        "## View plan",
        "",
        "| Slot | Role | Required | Scale / disposition |",
        "|---|---|---:|---|",
    ]
    for v in expected_views:
        lines.append(f"| {v.get('slot')} | {v.get('role')} | {v.get('required','-')} | {v.get('preferred_scale') or v.get('disposition') or '-'} |")
    lines += ["", "## Claim routing", "", "| Order | Claim | Engineering role | View role | Release eligible |", "|---:|---|---|---|---:|"]
    for x in routed:
        lines.append(f"| {x['authoring_order']} | {x['claim_id']} | {x['claim_role']} | {x['family_view_role']} | {x['release_eligible']} |")
    if issues:
        lines += ["", "## Issues"] + [f"- `{x}`" for x in issues]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    dump(CTRL, {
        "schema":"k01.d006.drawing_family_plan_gate.current.v1",
        "generated_utc":payload["generated_utc"],
        "status":status,
        "family":family_id,
        "claim_route_count":coverage,
        "issues":issues,
        "report":str(OUT.relative_to(ROOT)),
        "next":"Use this family plan as D1/D5 presentation routing context. Proceed to D3/D7 on the existing exemplar; do not manually create unapproved semantics."
    })

    br = register_build(ROOT, "K01.DRAWING.D006.FAMILY.PLAN", "tools/medtas/drawing_family_plan_v13.py", limitations=["Presentation/routing only; no semantic authoring","D3/D7 still required"], extra={"family":family_id,"family_plan_sha256":payload["family_plan_sha256"]})
    register_verify(ROOT, "K01.DRAWING.D006.FAMILY.PLAN", "PASS" if not issues else "HOLD", metrics={"claim_route_count":coverage,"issues":len(issues)}, limitations=["No CAD mutation","No release authorization change"])
    print("STATUS:", status)
    print("FAMILY:", family_id)
    print("VIEWS:", ",".join([str(x.get("role")) for x in expected_views if x.get("slot") != "omit"]))
    print("OMIT:", ",".join([str(x.get("role")) for x in expected_views if x.get("slot") == "omit"]) or "NONE")
    print("CLAIMS_ROUTED:", coverage)
    print("ISSUES:", len(issues))
    print("PLAN_SHA256:", payload["family_plan_sha256"])
    print("REPORT:", OUT)
    print("MEDTAS_STATE_HASH:", br["built_state_hash"])
    return 0 if not issues else 3


if __name__ == "__main__":
    raise SystemExit(main())
