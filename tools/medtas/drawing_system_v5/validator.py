
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from .utils import load_json

MANUFACTURING_BLOCKING_DOCUMENT_FIELDS = {
    "general_tolerance": "general tolerance standard/class",
    "surface_texture": "surface texture requirements",
    "revision": "release revision",
}

def _schema_path():
    return Path(__file__).resolve().parents[1] / "schemas" / "drawing_contract_v2.schema.json"

def validate_schema(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Runtime validator intentionally uses only the Python standard library.
    Full JSON Schema remains a documentation/CI artifact, but production execution
    cannot depend on jsonschema/ezdxf/pip availability.
    """
    issues: List[Dict[str, Any]] = []

    def req(obj, key, path):
        if not isinstance(obj, dict) or key not in obj:
            issues.append({
                "class": "SCHEMA_ERROR",
                "path": path + "." + key if path else key,
                "message": "required field missing",
                "blocking": True,
            })
            return False
        return True

    if not isinstance(contract, dict):
        return [{
            "class": "SCHEMA_ERROR",
            "path": "",
            "message": "contract root must be an object",
            "blocking": True,
        }]

    for k in [
        "schema","drawing_id","part_id","part_family","drawing_family",
        "document","views","model_bindings","characteristics","release","model"
    ]:
        req(contract, k, "")

    if issues:
        return issues

    if contract["schema"] not in {"marvilon.drawing_contract.v2", "marvilon.drawing_contract.v2_1"}:
        issues.append({
            "class": "SCHEMA_ERROR",
            "path": "schema",
            "message": "unsupported drawing contract schema",
            "blocking": True,
        })

    if not isinstance(contract["drawing_id"], str) or not contract["drawing_id"]:
        issues.append({"class":"SCHEMA_ERROR","path":"drawing_id","message":"non-empty string required","blocking":True})
    if not isinstance(contract["part_id"], str) or not contract["part_id"]:
        issues.append({"class":"SCHEMA_ERROR","path":"part_id","message":"non-empty string required","blocking":True})

    doc = contract["document"]
    if not isinstance(doc, dict):
        issues.append({"class":"SCHEMA_ERROR","path":"document","message":"object required","blocking":True})
    else:
        for k in ["sheet","units","projection","scale","title","material","general_tolerance","surface_texture","revision"]:
            req(doc, k, "document")
        if doc.get("projection") not in {"FIRST_ANGLE","THIRD_ANGLE"}:
            issues.append({"class":"SCHEMA_ERROR","path":"document.projection","message":"FIRST_ANGLE or THIRD_ANGLE required","blocking":True})

    views = contract["views"]
    if not isinstance(views, list) or not views:
        issues.append({"class":"SCHEMA_ERROR","path":"views","message":"non-empty array required","blocking":True})
    else:
        for i,v in enumerate(views):
            if not isinstance(v, dict):
                issues.append({"class":"SCHEMA_ERROR","path":f"views.{i}","message":"object required","blocking":True})
                continue
            for k in ["id","kind","published","role"]:
                req(v, k, f"views.{i}")

    bindings = contract["model_bindings"]
    if not isinstance(bindings, dict):
        issues.append({"class":"SCHEMA_ERROR","path":"model_bindings","message":"object required","blocking":True})
    else:
        for name,b in bindings.items():
            if not isinstance(b, dict):
                issues.append({"class":"SCHEMA_ERROR","path":f"model_bindings.{name}","message":"object required","blocking":True})
                continue
            for k in ["kind","state"]:
                req(b, k, f"model_bindings.{name}")
            if b.get("state") not in {"CONTROLLED","OPEN"}:
                issues.append({"class":"SCHEMA_ERROR","path":f"model_bindings.{name}.state","message":"CONTROLLED or OPEN required","blocking":True})

    chars = contract["characteristics"]
    if not isinstance(chars, list) or not chars:
        issues.append({"class":"SCHEMA_ERROR","path":"characteristics","message":"non-empty array required","blocking":True})
    else:
        for i,c in enumerate(chars):
            if not isinstance(c, dict):
                issues.append({"class":"SCHEMA_ERROR","path":f"characteristics.{i}","message":"object required","blocking":True})
                continue
            for k in ["id","semantic_class","state","source_authority","requirement","view_id","drawing_projection"]:
                req(c, k, f"characteristics.{i}")

    release = contract["release"]
    if not isinstance(release, dict):
        issues.append({"class":"SCHEMA_ERROR","path":"release","message":"object required","blocking":True})
    else:
        for k in ["review_build_allowed","manufacturing_build_allowed","blockers"]:
            req(release, k, "release")

    model = contract["model"]
    if not isinstance(model, dict):
        issues.append({"class":"SCHEMA_ERROR","path":"model","message":"object required","blocking":True})
    else:
        for k in ["canonical_path","source_invariance_required"]:
            req(model, k, "model")

    return issues

def validate_family(contract: Dict[str, Any], family: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    published = [v for v in contract["views"] if v["published"]]
    pub_by_id = {v["id"]: v for v in published}
    all_by_id = {v["id"]: v for v in contract["views"]}

    expected = family.get("published_view_contract", [])
    for slot in expected:
        if slot["required"] and slot["slot"] not in pub_by_id:
            issues.append({
                "class": "MISSING_REQUIRED_VIEW",
                "item": slot["slot"],
                "blocking": True,
            })
        elif slot["slot"] in pub_by_id and pub_by_id[slot["slot"]]["kind"] != slot["kind"]:
            issues.append({
                "class": "WRONG_VIEW_KIND",
                "item": slot["slot"],
                "expected": slot["kind"],
                "observed": pub_by_id[slot["slot"]]["kind"],
                "blocking": True,
            })

    for dep in family.get("dependency_view_contract", []):
        if dep["required"] and dep["slot"] not in all_by_id:
            issues.append({
                "class": "MISSING_DEPENDENCY_VIEW",
                "item": dep["slot"],
                "blocking": True,
            })
        elif dep["slot"] in all_by_id and all_by_id[dep["slot"]]["published"]:
            issues.append({
                "class": "DEPENDENCY_VIEW_PUBLISHED",
                "item": dep["slot"],
                "blocking": True,
            })

    prohibited = set(family.get("prohibited_published_kinds", []))
    for view in published:
        if view["kind"] in prohibited:
            issues.append({
                "class": "PROHIBITED_PUBLISHED_VIEW",
                "item": view["id"],
                "kind": view["kind"],
                "blocking": True,
            })

    declared_count = contract.get("drawing_classification", {}).get("published_view_count")
    if declared_count is not None and declared_count != len(published):
        issues.append({
            "class": "PUBLISHED_VIEW_COUNT_MISMATCH",
            "expected": declared_count,
            "observed": len(published),
            "blocking": True,
        })
    return issues

def validate_characteristics(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    view_ids = {v["id"] for v in contract["views"]}
    bindings = contract["model_bindings"]
    seen = set()

    for c in contract["characteristics"]:
        cid = c["id"]
        if cid in seen:
            issues.append({"class": "DUPLICATE_CHARACTERISTIC_ID", "item": cid, "blocking": True})
        seen.add(cid)

        if c["view_id"] != "TITLE_BLOCK" and c["view_id"] not in view_ids:
            issues.append({
                "class": "UNKNOWN_VIEW_REFERENCE",
                "item": cid,
                "view_id": c["view_id"],
                "blocking": True,
            })

        for b in c.get("bindings", []):
            if b not in bindings:
                issues.append({
                    "class": "UNKNOWN_MODEL_BINDING",
                    "item": cid,
                    "binding": b,
                    "blocking": True,
                })

        if c["drawing_projection"] == "REQUIRED" and c["state"] in {"OPEN", "CANDIDATE"}:
            issues.append({
                "class": "UNRELEASED_CHARACTERISTIC_REQUIRED_ON_DRAWING",
                "item": cid,
                "state": c["state"],
                "blocking": True,
            })

        # Required engineering annotations must have at least one binding, except document/title data.
        if c["drawing_projection"] == "REQUIRED" and c["semantic_class"] not in {"MATERIAL", "DOCUMENT_NOTE"}:
            if not c.get("bindings"):
                issues.append({
                    "class": "REQUIRED_CHARACTERISTIC_WITHOUT_MODEL_BINDING",
                    "item": cid,
                    "blocking": True,
                })

        # A binding that is still OPEN cannot support a released required characteristic.
        for b in c.get("bindings", []):
            if bindings[b]["state"] == "OPEN" and c["drawing_projection"] == "REQUIRED":
                issues.append({
                    "class": "OPEN_BINDING_FOR_REQUIRED_CHARACTERISTIC",
                    "item": cid,
                    "binding": b,
                    "blocking": True,
                })
    return issues

def validate_document_definition(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    doc = contract["document"]

    gt = doc.get("general_tolerance", {})
    if gt.get("state") == "CONTROLLED":
        if not gt.get("standard") or not gt.get("class"):
            issues.append({
                "class": "GENERAL_TOLERANCE_CONTROLLED_BUT_INCOMPLETE",
                "blocking": True,
            })

    sf = doc.get("surface_texture", {})
    if sf.get("state") == "CONTROLLED" and sf.get("general_ra_um") is None and not sf.get("note"):
        issues.append({
            "class": "SURFACE_TEXTURE_CONTROLLED_BUT_EMPTY",
            "blocking": True,
        })

    rev = doc.get("revision", {})
    if rev.get("state") == "CONTROLLED" and not rev.get("value"):
        issues.append({
            "class": "REVISION_CONTROLLED_BUT_EMPTY",
            "blocking": True,
        })
    return issues


def prebuild_gate(contract: Dict[str, Any], family: Dict[str, Any], requested_mode: str) -> Dict[str, Any]:
    """
    Result-first semantics:
    - structural/unsafe definition defects block generation;
    - engineering/release HOLD does NOT block review artifact generation;
    - a manufacturing request with blockers automatically falls back to review generation.
    """
    issues = []
    issues.extend(validate_schema(contract))
    if not issues:
        issues.extend(validate_family(contract, family))
        issues.extend(validate_characteristics(contract))
        issues.extend(validate_document_definition(contract))

    structural_block = any(x.get("blocking") for x in issues)

    release_blockers = list(contract["release"].get("blockers", []))
    engineering_open = []

    for name in ("general_tolerance", "surface_texture", "revision"):
        block = contract["document"].get(name, {})
        if block.get("state") == "OPEN":
            engineering_open.append(MANUFACTURING_BLOCKING_DOCUMENT_FIELDS[name])

    for c in contract["characteristics"]:
        if c["state"] in {"OPEN", "CONTROLLED_WITH_OPEN_SUBREQUIREMENT"}:
            engineering_open.append(c["id"])

    release_eligible = (
        not structural_block
        and contract["release"].get("manufacturing_build_allowed", False)
        and not release_blockers
        and not engineering_open
    )

    review_generation_allowed = (
        not structural_block
        and contract["release"].get("review_build_allowed", False)
    )

    if requested_mode not in {"review", "manufacturing"}:
        raise ValueError("requested_mode must be review or manufacturing")

    if structural_block:
        generation_mode = None
        execution_status = "HOLD_UNSAFE_PREBUILD"
        generation_allowed = False
    elif requested_mode == "manufacturing" and not release_eligible:
        generation_mode = "review"
        execution_status = "PASS_PREBUILD__GENERATE_REVIEW_FALLBACK__HOLD_RELEASE"
        generation_allowed = review_generation_allowed
    else:
        generation_mode = requested_mode
        execution_status = (
            "PASS_MANUFACTURING_PREBUILD"
            if requested_mode == "manufacturing"
            else "PASS_REVIEW_PREBUILD"
        )
        generation_allowed = review_generation_allowed if requested_mode == "review" else release_eligible

    engineering_state = (
        "PASS_ENGINEERING_DEFINITION"
        if not engineering_open and not release_blockers
        else "HOLD_ENGINEERING_DEFINITION"
    )
    release_state = "RELEASE_ELIGIBLE" if release_eligible else "HOLD_RELEASE"

    return {
        "schema": "marvilon.drawing_prebuild_gate.v2_result_first",
        "drawing_id": contract["drawing_id"],
        "part_id": contract["part_id"],
        "requested_mode": requested_mode,
        "generation_mode": generation_mode,
        "execution_status": execution_status,
        "generation_allowed": generation_allowed,
        "engineering_state": engineering_state,
        "release_state": release_state,
        "structural_issues": issues,
        "engineering_open": sorted(set(engineering_open)),
        "release_blockers": release_blockers,
        "rule": (
            "HOLD does not stop artifact generation. "
            "Only unsafe structural/model-definition defects block generation. "
            "Manufacturing requests with release blockers generate review artifacts and remain HOLD_RELEASE."
        )
    }
