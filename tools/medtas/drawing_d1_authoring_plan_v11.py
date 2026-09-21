from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from medtas_v16_common import register_build, register_verify

ROOT = Path(__file__).resolve().parents[2]
COMPILED = ROOT / "reports/product_definition/current/K01_P007_PRODUCT_DEFINITION_COMPILED.json"
CONTEXT = ROOT / "control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json"
PARTS = ROOT / "control/product/parts.json"
POLICY = ROOT / "control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json"
MFG = ROOT / "control/manufacturing/K01_P007_MANUFACTURING_FEASIBILITY_CURRENT.json"
DELIVERY = ROOT / "control/drawings/K01_DRAWING_DELIVERY_CAPABILITY_CURRENT.json"
FAMILY_PLAN = ROOT / "reports/drawing/current/K01-D-006_FAMILY_PLAN_CURRENT.json"
OUT = ROOT / "reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json"
OUT_MD = ROOT / "reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.md"
OUT_CTRL = ROOT / "reports/control/K01_D006_D1_AUTHORING_READINESS_CURRENT.json"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat()


def obj_sha(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get_path(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def requires_annotation_view(carrier: str, drawing_view_role: str) -> bool:
    c = (carrier or "").upper()
    r = (drawing_view_role or "").upper()
    if r in {"TITLE_BLOCK", "GENERAL_NOTE", "GENERAL_NOTE_OR_SPEC_REFERENCE"}:
        return False
    return any(x in c for x in ("DIMXPERT", "DATUM", "GDT", "SIZE", "LOCATION", "HOLE"))


def is_open_value(v) -> bool:
    if isinstance(v, str):
        u = v.upper()
        return "OPEN" in u or "PENDING" in u or "NOT_YET" in u
    return False


def part_exists(parts, part_id: str) -> bool:
    raw = json.dumps(parts, ensure_ascii=False)
    return part_id in raw


def main() -> int:
    required = [COMPILED, CONTEXT, PARTS, POLICY, MFG, DELIVERY, FAMILY_PLAN]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        print("STATUS: HOLD_D1_MISSING_INPUTS")
        for x in missing:
            print("MISSING:", x)
        return 2

    compiled, context, parts, policy, mfg, delivery, family_plan = map(load, required)
    issues = []
    blockers = []
    tasks = []
    family_routes = {x.get("claim_id"): x for x in family_plan.get("claim_routes", []) if x.get("claim_id")}
    claim_ids = set()
    char_by_id = {x.get("id"): x for x in compiled.get("characteristics", []) if x.get("id")}

    if not part_exists(parts, "K01-P-007"):
        issues.append("PART_REGISTRY_MISSING:K01-P-007")

    if mfg.get("selection") == "OPEN":
        blockers.append({"code":"D1-BLK-MFG-ROUTE","blocks_stage":"RELEASE","subject":"K01-P-007","reason":"Manufacturing route is OPEN; process-dependent PMI/drawing semantics and release remain blocked. Route-independent controlled claims may still be authored in D2."})
    if delivery.get("manufacturer_or_supplier", {}).get("step_ap242_pmi_acceptance") == "OPEN":
        blockers.append({"code":"D1-BLK-DELIVERY-PROFILE","blocks_stage":"D9","subject":"STEP_AP242_PMI","reason":"Recipient acceptance is OPEN. This blocks D9 delivery simplification, not D1 plan generation or D2 authoring."})

    for cid, ch in char_by_id.items():
        cctx = context.get("characteristics", {}).get(cid, {})
        da = cctx.get("drawing_authoring")
        if not isinstance(da, dict):
            issues.append(f"DRAWING_AUTHORING_CONTEXT_MISSING:{cid}")
            continue
        targets = da.get("targets", [])
        if not isinstance(targets, list):
            issues.append(f"DRAWING_AUTHORING_TARGETS_INVALID:{cid}")
            continue
        for t in targets:
            claim_id = t.get("claim_id")
            if not claim_id:
                issues.append(f"CLAIM_ID_MISSING:{cid}")
                continue
            if claim_id in claim_ids:
                issues.append(f"CLAIM_ID_DUPLICATE:{claim_id}")
            claim_ids.add(claim_id)
            claim_paths = t.get("claim_paths", [])
            resolved = {}
            for cp in claim_paths:
                val, ok = get_path(ch, cp)
                if not ok:
                    issues.append(f"CLAIM_PATH_UNRESOLVED:{claim_id}:{cp}")
                resolved[cp] = val if ok else None

            carrier = t.get("carrier")
            av = t.get("annotation_view_role")
            dv = t.get("drawing_view_role")
            authoring_class = t.get("authoring_class")
            action = t.get("action")
            if not carrier or not authoring_class or not action or not dv:
                issues.append(f"TARGET_REQUIRED_FIELD_MISSING:{claim_id}")
            if requires_annotation_view(carrier, dv) and not av:
                issues.append(f"ANNOTATION_VIEW_ROLE_MISSING:{claim_id}")

            existing = t.get("existing_pmi_identity")
            signature = t.get("feature_signature") or t.get("binding_signature")
            compiled_binding = str(ch.get("cad_binding", ""))
            binding_anchor = None
            if existing:
                binding_anchor = {"kind":"EXISTING_PMI_IDENTITY","value":existing,"release_status":"D3_INVARIANCE_REQUIRED"}
            elif signature:
                binding_anchor = {"kind":"GEOMETRIC_SIGNATURE","value":signature,"release_status":"D3_INVARIANCE_REQUIRED"}
            elif "PASS_CANONICAL_PERSISTENT_REF" in compiled_binding:
                binding_anchor = {"kind":"CONTROLLED_PERSISTENT_BINDING_CONTEXT","value":compiled_binding,"release_status":"D3_GEOMETRIC_SIGNATURE_CAPTURE_REQUIRED"}
            elif "NATIVE_MATERIAL" in str(carrier).upper() or "TITLE_BLOCK" in str(dv).upper():
                binding_anchor = {"kind":"MODEL_PROPERTY","value":compiled_binding or carrier,"release_status":"D3_PROPERTY_READBACK_REQUIRED"}
            else:
                binding_anchor = {"kind":"MISSING","value":None,"release_status":"HOLD"}

            if t.get("release_eligible") and binding_anchor["kind"] == "MISSING":
                blockers.append({"code":"D1-BLK-BINDING","blocks_stage":"D2","subject":claim_id,"reason":"Release-eligible claim lacks deterministic binding anchor/signature; do not invent a face selector."})

            if authoring_class == "CONTROLLED_CLAIM":
                open_paths = [cp for cp,v in resolved.items() if is_open_value(v)]
                if open_paths:
                    issues.append(f"CONTROLLED_CLAIM_CONTAINS_OPEN:{claim_id}:{','.join(open_paths)}")

            lane = "RELEASE_NATIVE" if t.get("release_eligible") else "DESIGN_REVIEW_OR_FUTURE_RELEASE_AFTER_CLOSURE"
            disposition = "AUTHOR_OR_VERIFY" if not action.startswith("DO_NOT") and not action.startswith("HOLD") else ("DO_NOT_AUTHOR" if action.startswith("DO_NOT") else "HOLD_AUTHORING")
            route_dependency = str(t.get("manufacturing_route_dependency") or "UNCLASSIFIED").upper()
            fr = family_routes.get(claim_id, {})
            if not fr:
                issues.append(f"FAMILY_ROUTE_NOT_FOUND:{claim_id}")
            task = {
                "characteristic_id": cid,
                "claim_id": claim_id,
                "role": ch.get("role"),
                "definition_state": ch.get("definition_state"),
                "authoring_class": authoring_class,
                "lane": lane,
                "disposition": disposition,
                "action": action,
                "carrier": carrier,
                "claim_paths": claim_paths,
                "resolved_claim_values": resolved,
                "annotation_view_role": av,
                "drawing_view_role": dv,
                "binding_anchor": binding_anchor,
                "required_invariance_level": cctx.get("binding_invariance_required", "OPEN"),
                "existing_pmi_identity": existing,
                "release_eligible": bool(t.get("release_eligible")),
                "requirement_allocation_ids": ch.get("requirement_allocation_ids", []),
                "datum_reference_system": ch.get("datum_reference_system", {}),
                "measurement_condition": ch.get("measurement_condition", {}),
                "inspection_strategy": ch.get("inspection_strategy", {}),
                "revision_effectivity": ch.get("revision_effectivity", {}),
                "manufacturing_route_dependency": route_dependency,
                "exemplar_scope": t.get("exemplar_scope", "OBSERVE_OR_HOLD"),
                "drawing_family": family_plan.get("family"),
                "claim_role": fr.get("claim_role"),
                "family_view_role": fr.get("family_view_role"),
                "authoring_order_class": fr.get("authoring_order_class"),
                "authoring_order": fr.get("authoring_order", 999),
            }
            task["d2_authorizable_now"] = bool(
                authoring_class == "CONTROLLED_CLAIM"
                and disposition == "AUTHOR_OR_VERIFY"
                and binding_anchor["kind"] != "MISSING"
                and route_dependency in {"NONE", "ROUTE_INDEPENDENT"}
            )
            task["d2_authorization_reason"] = (
                "ROUTE_INDEPENDENT_CONTROLLED_CLAIM" if task["d2_authorizable_now"]
                else ("MANUFACTURING_ROUTE_DEPENDENT" if route_dependency not in {"NONE", "ROUTE_INDEPENDENT"}
                      else "NOT_FULLY_CONTROLLED_OR_NOT_AUTHORABLE")
            )
            tasks.append(task)

    tasks.sort(key=lambda x: (int(x.get("authoring_order", 999)), str(x.get("family_view_role") or ""), str(x.get("claim_id") or "")))
    controlled_targets = [x for x in tasks if x["authoring_class"] == "CONTROLLED_CLAIM"]
    if not controlled_targets:
        issues.append("NO_CONTROLLED_CLAIMS_IN_D1")

    plan_status = "PASS_D1_AUTHORING_PLAN" if not issues else "HOLD_D1_CONTRACT_ERRORS"
    d2_authorizable = [x for x in tasks if x.get("d2_authorizable_now")]
    d2_blocked_claims = [x for x in tasks if x.get("authoring_class") == "CONTROLLED_CLAIM" and not x.get("d2_authorizable_now")]
    d2_blockers = [
        {"code":"D1-BLK-D2-CLAIM","blocks_stage":"D2_CLAIM","subject":x.get("claim_id"),"reason":x.get("d2_authorization_reason")}
        for x in d2_blocked_claims
    ]
    if issues:
        d2_gate = "HOLD_D2_CONTRACT_ERRORS"
    elif d2_authorizable and d2_blocked_claims:
        d2_gate = "PASS_D2_PARTIAL_SCOPE_AUTHORIZABLE"
    elif d2_authorizable:
        d2_gate = "PASS_D2_ROUTE_INDEPENDENT_SCOPE_AUTHORIZABLE"
    else:
        d2_gate = "HOLD_D2_NO_AUTHORIZABLE_CONTROLLED_CLAIMS"
    plan_core = {
        "schema":"k01.d006.d1_authoring_plan.current.v2",
        "part":"K01-P-007","drawing":"K01-D-006",
        "source_product_definition_sha256": compiled.get("compiled_definition_sha256"),
        "source_drawing_slice_sha256": compiled.get("drawing_projection_sha256"),
        "drawing_pipeline_policy":"control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json",
        "drawing_family_plan":"reports/drawing/current/K01-D-006_FAMILY_PLAN_CURRENT.json",
        "drawing_family_plan_sha256":family_plan.get("family_plan_sha256"),
        "drawing_family":family_plan.get("family"),
        "view_plan":family_plan.get("view_plan", []),
        "status":plan_status,
        "d2_release_native_mutation_gate":d2_gate,
        "tasks":tasks,
        "structural_issues":issues,
        "release_native_blockers":blockers,
        "d2_mutation_blockers":d2_blockers,
        "d2_authorizable_claim_ids":[x.get("claim_id") for x in d2_authorizable],
        "d2_blocked_controlled_claim_ids":[x.get("claim_id") for x in d2_blocked_claims],
        "rules":{
            "claim_granularity":"CLAIM_LEVEL",
            "manual_authoring":"D2 only, from this plan; no freehand semantic additions",
            "annotation_views":"D2 records actual SOLIDWORKS annotation-view identity/orientation; D3 verifies against normalized role",
            "binding":"No runtime face IDs; missing deterministic signature stays HOLD",
            "open":"OPEN remains OPEN; design-review nominal authoring is not release-native tolerance authority",
            "layout":"Not part of D1/D2 semantics; D6 only",
            "claim_scoped_authorization":"Manufacturing-route OPEN blocks only route/process-dependent claims and release. It must not freeze unrelated controlled PMI authoring.",
            "exemplar":"A design-review exemplar may author route-independent controlled claims while release remains HOLD.",
            "family_routing":"D1 consumes V13 family-plan roles. Family rules select/rank views and route existing claims only; they do not invent Product Characteristics.",
            "authoring_order":"Datum/DRF -> size/fit -> location/pattern -> GD&T -> surface -> material/process."
        }
    }
    plan_core["authoring_plan_sha256"] = obj_sha(plan_core)
    plan = {**plan_core, "generated_utc": now()}
    dump(OUT, plan)

    md=["# K01-D-006 D1 authoring plan","",f"**Status:** `{plan_status}`",f"**D2 mutation gate:** `{d2_gate}`",f"**Plan SHA-256:** `{plan_core['authoring_plan_sha256']}`","", "## Tasks", "", "| Claim | Class | D2 now | Route dependency | Action | Annotation view role | Drawing view | Binding |", "|---|---|---:|---|---|---|---|---|"]
    for x in tasks:
        md.append(f"| {x['claim_id']} | {x['authoring_class']} | {'YES' if x.get('d2_authorizable_now') else 'NO'} | {x.get('manufacturing_route_dependency') or '-'} | {x['action']} | {x.get('annotation_view_role') or '-'} | {x.get('drawing_view_role') or '-'} | {x['binding_anchor']['kind']} / {x['binding_anchor']['release_status']} |")
    md += ["", "## Structural issues"] + ([f"- {x}" for x in issues] or ["- None"])
    md += ["", "## Release-native blockers"] + ([f"- {x['code']} — {x['subject']}: {x['reason']}" for x in blockers] or ["- None"])
    OUT_MD.parent.mkdir(parents=True,exist_ok=True); OUT_MD.write_text("\n".join(md)+"\n",encoding="utf-8")

    ctrl={
      "schema":"k01.d006.d1_authoring_readiness.current.v1","generated_utc":plan["generated_utc"],
      "status":plan_status,"d2_release_native_mutation_gate":d2_gate,
      "authoring_plan":str(OUT.relative_to(ROOT)),"authoring_plan_sha256":plan_core["authoring_plan_sha256"],
      "source_drawing_slice_sha256":compiled.get("drawing_projection_sha256"),
      "task_count":len(tasks),"controlled_claim_count":len(controlled_targets),"structural_issue_count":len(issues),"release_native_blocker_count":len(blockers),"d2_mutation_blocker_count":len(d2_blockers),
      "d2_authorizable_claim_ids":[x.get("claim_id") for x in d2_authorizable],
      "d2_blocked_controlled_claim_ids":[x.get("claim_id") for x in d2_blocked_claims],
      "next":"If D1 PASS and d2_authorizable_claim_ids is non-empty, prepare a dedicated exemplar working copy and manually author/verify only those claims. Manufacturing route OPEN continues to block process-dependent semantics and release."
    }
    dump(OUT_CTRL,ctrl)

    build = register_build(ROOT,"K01.DRAWING.D006.D1.AUTHORING_PLAN","tools/medtas/drawing_d1_authoring_plan_v11.py",extra={"authoring_plan_sha256":plan_core["authoring_plan_sha256"]})
    verdict = "PASS_WITH_LIMITATIONS" if not issues else "HOLD"
    register_verify(ROOT,"K01.DRAWING.D006.D1.AUTHORING_PLAN",verdict,metrics={"task_count":len(tasks),"controlled_claim_count":len(controlled_targets),"release_native_blocker_count":len(blockers)},limitations=[x["code"]+":"+x["subject"] for x in blockers],notes="D1 verifies plan contract only; it does not authorize D2 mutation when D2 gate is HOLD.")

    print(f"STATUS: {plan_status}")
    print(f"D2_RELEASE_NATIVE_MUTATION: {d2_gate}")
    print(f"TASKS: {len(tasks)}")
    print(f"CONTROLLED_CLAIMS: {len(controlled_targets)}")
    print(f"RELEASE_NATIVE_BLOCKERS: {len(blockers)}")
    print(f"D2_MUTATION_BLOCKERS: {len(d2_blockers)}")
    print("D2_AUTHORIZABLE_CLAIMS:", ",".join(x.get("claim_id") for x in d2_authorizable) or "NONE")
    print(f"PLAN_SHA256: {plan_core['authoring_plan_sha256']}")
    print(f"PLAN: {OUT}")
    print(f"REPORT: {OUT_CTRL}")
    print(f"MEDTAS_STATE_HASH: {build['built_state_hash']}")
    return 0 if not issues else 2


if __name__ == "__main__":
    raise SystemExit(main())
