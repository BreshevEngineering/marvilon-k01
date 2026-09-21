from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from medtas_v16_common import register_build, register_verify

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json"
POLICY = ROOT / "control/product_definition/K01_PRODUCT_DEFINITION_POLICY_CURRENT.json"
LEGACY = ROOT / "control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json"
CONTEXT = ROOT / "control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json"
DATUMS = ROOT / "control/product_definition/K01_DATUM_REFERENCE_SYSTEM_REGISTRY_v1.json"
REQS = ROOT / "control/requirements/requirements.json"
ALLOC = ROOT / "control/requirements/K01_REQUIREMENT_ALLOCATION_REGISTRY_v1.json"
DERIVED = ROOT / "control/engineering/K01_DERIVED_ENGINEERING_INPUTS_v1.json"
TOL_PLAN = ROOT / "control/drawings/K01_P007_FUNCTIONAL_TOLERANCE_PLAN.json"
METHODS = ROOT / "control/project/K01_EXECUTION_METHOD_REGISTRY_CURRENT.json"
MFG = ROOT / "control/manufacturing/K01_P007_MANUFACTURING_FEASIBILITY_CURRENT.json"
EFFECTIVITY = ROOT / "control/configuration/K01_EFFECTIVITY_POLICY_v1.json"
BINDING_POLICY = ROOT / "control/verification/K01_CAD_BINDING_INVARIANCE_POLICY_v1.json"
FEEDBACK_POLICY = ROOT / "control/change/K01_ENGINEERING_FEEDBACK_POLICY_v1.json"
FEEDBACK_REG = ROOT / "control/change/K01_ENGINEERING_FEEDBACK_REGISTRY_CURRENT.json"
EXEC = ROOT / "control/project/K01_ENGINEERING_EXECUTION_CONTRACT_CURRENT.json"

OUT_DIR = ROOT / "reports/product_definition/current"
OUT_JSON = OUT_DIR / "K01_P007_PRODUCT_DEFINITION_COMPILED.json"
OUT_MD = OUT_DIR / "K01_P007_PRODUCT_DEFINITION_COMPILED.md"
OUT_CTRL = ROOT / "reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json"
OUT_CHAIN = ROOT / "reports/control/K01_ENGINEERING_CHAIN_READINESS_CURRENT.json"
OUT_DRAW_GATE = ROOT / "reports/control/K01_D006_DRAWING_AUTHORING_GATE_CURRENT.json"
SLICE_FILES = {
    "drawing": OUT_DIR / "K01_P007_PD_SLICE_DRAWING.json",
    "variation": OUT_DIR / "K01_P007_PD_SLICE_VARIATION.json",
    "inspection": OUT_DIR / "K01_P007_PD_SLICE_INSPECTION.json",
    "physics": OUT_DIR / "K01_P007_PD_SLICE_PHYSICS.json",
    "manufacturing": OUT_DIR / "K01_P007_PD_SLICE_MANUFACTURING.json",
    "configuration": OUT_DIR / "K01_P007_PD_SLICE_CONFIGURATION.json",
}


def load(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def obj_sha(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def req_registry_map(data):
    items = data.get("requirements", []) if isinstance(data, dict) else data
    return {x.get("id"): x for x in items if isinstance(x, dict) and x.get("id")}


def legacy_map(data):
    return {x.get("id"): x for x in data.get("characteristics", []) if x.get("id")}


def allocation_maps(data):
    by_req, by_char = {}, {}
    for a in data.get("allocations", []):
        aid = a.get("id")
        rid = a.get("requirement_id")
        if rid:
            by_req.setdefault(rid, []).append(a)
        for t in a.get("targets", []):
            cid = t.get("characteristic_id")
            if cid:
                by_char.setdefault(cid, []).append(aid)
    return by_req, by_char


def derived_map(data):
    return {x.get("id"): x for x in data.get("inputs", []) if x.get("id")}


def find_referenced_requirement_ids(decision: dict) -> list[str]:
    out = []
    for src in decision.get("authority_sources", []):
        if isinstance(src, str) and src.startswith("REQ-"):
            out.append(src)
    return out


def stale_legacy_reason(cid: str, legacy_spec: str | None, decision: dict) -> list[str]:
    if not legacy_spec:
        return []
    reasons = []
    v = decision.get("variation_semantics", {})
    s = legacy_spec.upper().replace(" ", "")
    if cid == "C01" and str(v.get("flatness", "")).upper() == "OPEN" and "FLATNESS" in legacy_spec.upper() and re.search(r"\d", legacy_spec):
        reasons.append("legacy numeric flatness exists while current flatness is OPEN")
    if cid == "C03" and str(v.get("perpendicularity", "")).upper() == "OPEN" and ("PERP" in legacy_spec.upper() or "PERPEND" in legacy_spec.upper()) and re.search(r"\d", legacy_spec):
        reasons.append("legacy numeric perpendicularity exists while current perpendicularity is OPEN")
    if cid == "C04" and str(v.get("position_tolerance", "")).upper() == "OPEN" and "POS" in legacy_spec.upper() and re.search(r"\d", legacy_spec):
        reasons.append("legacy numeric position tolerance exists while current position tolerance is OPEN")
    if cid == "C05" and (str(v.get("diameter_tolerance", "")).upper() == "OPEN" or str(v.get("thickness_tolerance", "")).upper() == "OPEN") and ("±" in legacy_spec or "+/-" in legacy_spec):
        reasons.append("legacy ± tolerance exists while current flange release tolerances are OPEN")
    if cid == "C06" and str(v.get("length_tolerance", "")).upper() == "OPEN" and ("±" in legacy_spec or "+/-" in legacy_spec):
        reasons.append("legacy ± tolerance exists while current OAL release tolerance is OPEN")
    if "±0.25" in legacy_spec or "+/-0.25" in s:
        reasons.append("template/default-like ±0.25 must not become product authority")
    return reasons


def has_numeric_projection_authority(decision: dict) -> bool:
    n = decision.get("nominal_or_requirement", {})
    if not isinstance(n, dict) or not n:
        return False
    vals = list(n.values())
    return any(isinstance(v, (int, float)) for v in vals) or any(isinstance(v, str) and v not in {"OPEN", ""} for v in vals)


def char_effectivity(context: dict):
    scope = context.get("configuration_scope", {})
    return {
        "revision_id": "OPEN_NOT_YET_ASSIGNED",
        "applicable_part_revision_or_baseline": scope.get("engineering_baseline", "OPEN"),
        "configuration": "Default",
        "effective_from": "DESIGN_REVIEW_BASELINE_ONLY",
        "effective_to_or_superseded_by": None,
        "change_record_id": "OPEN_FOR_RELEASE_REVISION",
        "status": scope.get("effectivity_status", "OPEN"),
    }


def slice_payload(kind: str, compiled: list[dict], coverage_gaps: list[dict], derived_inputs: dict, mfg: dict, context: dict, safe_projection_ids: list[str] | None = None):
    if kind == "drawing":
        chars = [{k: x.get(k) for k in (
            "id", "role", "category", "definition_state", "requirement_allocation_ids",
            "nominal_or_requirement", "variation_semantics", "datum_reference_system", "measurement_condition",
            "manufacturing_feasibility", "revision_effectivity", "drawing_projection", "drawing_authoring", "release_blocking"
        )} for x in compiled]
        drawing_gap_categories = {"SURFACE_TEXTURE", "EDGE_CONDITION", "MANUFACTURING_FEASIBILITY", "CONFIGURATION_EFFECTIVITY", "MEASUREMENT_CONDITION"}
        extra = {
            "coverage_gaps": [g for g in coverage_gaps if g.get("category") in drawing_gap_categories],
            "safe_projection_ids": list(safe_projection_ids or []),
        }
    elif kind == "variation":
        chars = [{k: x.get(k) for k in (
            "id", "definition_state", "requirement_allocation_ids", "derived_input_ids", "variation_semantics",
            "datum_reference_system", "measurement_condition", "manufacturing_feasibility", "inspection_strategy", "release_blocking"
        )} for x in compiled]
        extra = {}
    elif kind == "inspection":
        chars = [{k: x.get(k) for k in (
            "id", "definition_state", "requirement_allocation_ids", "nominal_or_requirement", "variation_semantics",
            "datum_reference_system", "measurement_condition", "manufacturing_feasibility", "inspection_strategy",
            "revision_effectivity", "release_blocking"
        )} for x in compiled]
        extra = {"coverage_gaps": [g for g in coverage_gaps if g.get("category") == "INSPECTION"]}
    elif kind == "physics":
        chars = [{k: x.get(k) for k in (
            "id", "definition_state", "requirement_allocation_ids", "nominal_or_requirement", "authority_sources",
            "derived_input_ids", "manufacturing_feasibility", "release_blocking"
        )} for x in compiled]
        extra = {"derived_engineering_inputs": list(derived_inputs.values())}
    elif kind == "manufacturing":
        chars = [{k: x.get(k) for k in (
            "id", "definition_state", "requirement_allocation_ids", "nominal_or_requirement", "variation_semantics",
            "datum_reference_system", "measurement_condition", "manufacturing_feasibility", "inspection_strategy",
            "revision_effectivity", "release_blocking"
        )} for x in compiled]
        extra = {"manufacturing_route": mfg}
    elif kind == "configuration":
        chars = [{"id": x.get("id"), "revision_effectivity": x.get("revision_effectivity"), "definition_state": x.get("definition_state")} for x in compiled]
        extra = {"configuration_scope": context.get("configuration_scope", {})}
    else:
        raise ValueError(kind)
    return {"schema": f"k01.product_definition_slice.{kind}.v1", "part": "K01-P-007", "kind": kind, "characteristics": chars, **extra}


def main() -> int:
    required = [DECISIONS, POLICY, LEGACY, CONTEXT, DATUMS, REQS, ALLOC, DERIVED, TOL_PLAN, METHODS, MFG, EFFECTIVITY, BINDING_POLICY, FEEDBACK_POLICY, FEEDBACK_REG, EXEC]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise SystemExit("MISSING INPUTS: " + ", ".join(missing))

    decisions, policy, legacy, context, datums = load(DECISIONS), load(POLICY), load(LEGACY), load(CONTEXT), load(DATUMS)
    reqs, alloc, derived = load(REQS), load(ALLOC), load(DERIVED)
    methods, mfg = load(METHODS), load(MFG)
    reqmap = req_registry_map(reqs)
    legmap = legacy_map(legacy)
    alloc_by_req, alloc_by_char = allocation_maps(alloc)
    der_map = derived_map(derived)
    ctx_map = context.get("characteristics", {})

    compiled, stale_specs, missing_reqs, missing_characteristic_ids = [], [], [], []
    missing_allocations, safe_projection_ids, pmi_ready_ids, release_blockers = [], [], [], []
    measurement_gaps, binding_gaps, inspection_gaps = [], [], []
    effectivity = char_effectivity(context)

    for d in decisions.get("characteristics", []):
        cid = d["id"]
        lm = legmap.get(cid)
        if cid.startswith("C") and lm is None:
            missing_characteristic_ids.append(cid)
        legacy_spec = lm.get("candidate_spec") if lm else None
        reasons = stale_legacy_reason(cid, legacy_spec, d)
        if reasons:
            stale_specs.append({"id": cid, "legacy_candidate_spec": legacy_spec, "reasons": reasons, "disposition": "IGNORED_FOR_COMPILED_AUTHORITY"})

        req_ids = find_referenced_requirement_ids(d)
        bad_req = [rid for rid in req_ids if rid not in reqmap]
        missing_reqs.extend({"characteristic_id": cid, "requirement_id": rid} for rid in bad_req)
        allocation_ids = list(alloc_by_char.get(cid, []))
        for rid in req_ids:
            if rid not in alloc_by_req:
                missing_allocations.append({"characteristic_id": cid, "requirement_id": rid})

        cctx = ctx_map.get(cid, {})
        mcond = cctx.get("measurement_condition", {"status": "OPEN_NOT_DECLARED"})
        inspection = cctx.get("inspection_strategy", {"method": "OPEN", "capability": "OPEN"})
        binding_inv = {
            "required_level": cctx.get("binding_invariance_required", "OPEN"),
            "status": cctx.get("binding_invariance_status", "OPEN"),
            "policy": str(BINDING_POLICY.relative_to(ROOT)),
        }
        mfg_ctx = {
            "route_id": cctx.get("manufacturing_route_id", mfg.get("route_id")),
            "route_status": mfg.get("status"),
            "selection": mfg.get("selection"),
        }
        if str(mcond.get("status", "")).upper().startswith("OPEN"):
            measurement_gaps.append(cid)
        if "OPEN" in str(binding_inv.get("status", "")).upper() or "NOT_QUALIFIED" in str(binding_inv.get("status", "")).upper() or "REBIND_REQUIRED" in str(binding_inv.get("status", "")).upper():
            binding_gaps.append(cid)
        if "OPEN" in str(inspection.get("method", "")).upper() or "OPEN" in str(inspection.get("capability", "")).upper():
            inspection_gaps.append(cid)

        state = d.get("definition_state")
        projection = d.get("drawing_projection", "")
        if state in {"CONTROLLED", "PARTIAL"} and has_numeric_projection_authority(d) and not projection.upper().startswith("OMIT"):
            safe_projection_ids.append(cid)
        binding = str(d.get("cad_binding", ""))
        if cid in {"C02", "C05"} and ("PASS" in binding or "READY" in binding):
            pmi_ready_ids.append(cid)
        if d.get("release_blocking") and state != "CONTROLLED":
            release_blockers.append({"id": cid, "state": state, "role": d.get("role"), "class": "CHARACTERISTIC"})

        compiled.append({
            **d,
            "part": "K01-P-007",
            "revision_effectivity": dict(effectivity),
            "requirement_allocation_ids": allocation_ids,
            "derived_input_ids": [],
            "datum_reference_system": cctx.get("datum_reference_system", {"status": "OPEN_NOT_DECLARED"}),
            "measurement_condition": mcond,
            "inspection_strategy": inspection,
            "manufacturing_feasibility": mfg_ctx,
            "drawing_authoring": cctx.get("drawing_authoring", {"targets": [], "status": "OPEN_NOT_DECLARED"}),
            "binding_invariance": binding_inv,
            "legacy_candidate_spec": legacy_spec,
            "legacy_spec_disposition": "STALE_IGNORED" if reasons else ("INFORMATION_ONLY" if legacy_spec else "NONE"),
            "linked_requirement_ids": req_ids,
            "projection_authority": "COMPILED_DECISION_AND_REFERENCED_SOURCES",
        })

    coverage_gaps = list(decisions.get("coverage_gaps", []))
    coverage_gaps += [
        {"id": "PDG-MANUFACTURING-ROUTE", "category": "MANUFACTURING_FEASIBILITY", "state": mfg.get("status"), "requirement": "Select and qualify P007 manufacturing route/supplier capability before release of process-dependent semantics.", "release_blocking": True},
        {"id": "PDG-CONFIG-EFFECTIVITY", "category": "CONFIGURATION_EFFECTIVITY", "state": context.get("configuration_scope", {}).get("effectivity_status", "OPEN"), "requirement": "Assign released part/characteristic revision and effectivity; design-review baseline scope is insufficient for release.", "release_blocking": True},
        {"id": "PDG-BINDING-INVARIANCE", "category": "CAD_BINDING_INVARIANCE", "state": "HOLD" if binding_gaps else "PASS", "requirement": "Qualify characteristic-to-geometry binding at required L2/L3 level; save/reopen PMI persistence alone is insufficient.", "release_blocking": True},
        {"id": "PDG-MEASUREMENT-CONDITIONS", "category": "MEASUREMENT_CONDITION", "state": "OPEN" if measurement_gaps else "PASS", "requirement": "Control temperature/part state/fixture/measurement force where applicable, especially thin-wall P007 features.", "release_blocking": True},
    ]
    release_blockers.extend({"id": x["id"], "state": x.get("state"), "role": x.get("category"), "class": "COVERAGE_GAP"} for x in coverage_gaps if x.get("release_blocking") and str(x.get("state")).upper() not in {"PASS", "CONTROLLED"})

    definition_consistency_pass = not missing_reqs and not missing_characteristic_ids
    allocation_identity_pass = not missing_allocations
    material_ok = any(x["id"] == "C09" and x.get("definition_state") == "CONTROLLED" for x in compiled)
    candidate_ready = definition_consistency_pass and allocation_identity_pass and material_ok and len(safe_projection_ids) >= 5
    release_ready = candidate_ready and not release_blockers and not stale_specs
    status = "PASS_DRAWING_CANDIDATE_READY__HOLD_RELEASE" if candidate_ready and not release_ready else ("PASS_DRAWING_RELEASE_READY" if release_ready else "HOLD_PRODUCT_DEFINITION")

    source_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in required}
    slices = {}
    fingerprints = {}
    for kind, path in SLICE_FILES.items():
        payload = slice_payload(kind, compiled, coverage_gaps, der_map, mfg, context, safe_projection_ids=safe_projection_ids)
        fp = obj_sha(payload)
        payload["slice_sha256"] = fp
        dump(path, payload)
        slices[kind] = str(path.relative_to(ROOT))
        fingerprints[kind] = fp

    compiled_doc = {
        "schema": "k01.product_definition.compiled.v3_1",
        "generated_utc": now_utc(),
        "part": "K01-P-007",
        "drawing": "K01-D-006",
        "status": status,
        "policy": str(POLICY.relative_to(ROOT)),
        "execution_contract": str(EXEC.relative_to(ROOT)),
        "source_hashes": source_hashes,
        "authority_rule": "Derived contract only; upstream domain authorities remain authoritative.",
        "medtas_node_id": "K01.PD.P007.COMPILED",
        "characteristics": compiled,
        "coverage_gaps": coverage_gaps,
        "stale_legacy_specs": stale_specs,
        "gates": {
            "DEFINITION_CONSISTENCY": "PASS" if definition_consistency_pass else "HOLD",
            "REQUIREMENT_ALLOCATION_IDENTITY": "PASS" if allocation_identity_pass else "HOLD",
            "DRAWING_CANDIDATE_READY": "PASS" if candidate_ready else "HOLD",
            "PMI_AUTHORING_READY": {"status": "PASS_PARTIAL_SCOPE" if pmi_ready_ids else "HOLD", "safe_characteristic_ids": pmi_ready_ids},
            "BINDING_INVARIANCE_RELEASE": "HOLD" if binding_gaps else "PASS",
            "MANUFACTURING_FEASIBILITY_RELEASE": "HOLD" if mfg.get("selection") == "OPEN" else "PASS",
            "CONFIGURATION_EFFECTIVITY_RELEASE": "HOLD" if "OPEN" in str(context.get("configuration_scope", {}).get("effectivity_status", "OPEN")) else "PASS",
            "DRAWING_RELEASE_READY": "PASS" if release_ready else "HOLD",
        },
        "safe_projection_ids": safe_projection_ids,
        "release_blockers": release_blockers,
        "missing_requirement_links": missing_reqs,
        "missing_requirement_allocations": missing_allocations,
        "missing_characteristic_ids": missing_characteristic_ids,
        "measurement_condition_open_ids": sorted(set(measurement_gaps)),
        "binding_invariance_open_ids": sorted(set(binding_gaps)),
        "inspection_strategy_open_ids": sorted(set(inspection_gaps)),
        "requirement_allocation_registry": str(ALLOC.relative_to(ROOT)),
        "derived_engineering_inputs": str(DERIVED.relative_to(ROOT)),
        "datum_reference_system_registry": str(DATUMS.relative_to(ROOT)),
        "manufacturing_feasibility": str(MFG.relative_to(ROOT)),
        "effectivity_policy": str(EFFECTIVITY.relative_to(ROOT)),
        "binding_invariance_policy": str(BINDING_POLICY.relative_to(ROOT)),
        "engineering_feedback_policy": str(FEEDBACK_POLICY.relative_to(ROOT)),
        "slice_files": slices,
        "slice_fingerprints": fingerprints,
        "drawing_compiler_contract": {
            "input": str(OUT_JSON.relative_to(ROOT)),
            "drawing_slice": slices["drawing"],
            "required_projection_fingerprint": fingerprints["drawing"],
            "may_project_only": "safe_projection_ids plus explicit nonnumeric OPEN notes",
            "must_not_read_as_authority": ["legacy candidate_spec", "SOLIDWORKS template/general tolerances", "drawing free text", "PDF text"],
            "required_annotation_evidence_fields": ["characteristic_id", "projection_method", "source_projection_fingerprint", "semantic_readback_or_fallback_class"],
            "fallback_rule": "If native associative projection fails, preserve usable linked SLDDRW and emit controlled Cxx callout from compiled drawing slice; mark PROJECTION_FALLBACK. Never invent tolerance semantics."
        },
        "execution_methods": methods.get("methods", []),
    }
    full_payload = {"characteristics": compiled, "coverage_gaps": coverage_gaps, "registries": {"alloc": alloc, "derived": derived, "mfg": mfg, "context": context}}
    compiled_doc["compiled_definition_sha256"] = obj_sha(full_payload)
    compiled_doc["drawing_projection_sha256"] = fingerprints["drawing"]
    compiled_doc["variation_sha256"] = fingerprints["variation"]
    compiled_doc["inspection_sha256"] = fingerprints["inspection"]
    compiled_doc["physics_sha256"] = fingerprints["physics"]
    compiled_doc["manufacturing_sha256"] = fingerprints["manufacturing"]
    compiled_doc["configuration_sha256"] = fingerprints["configuration"]

    dump(OUT_JSON, compiled_doc)

    md = [
        "# K01-P-007 Product Definition — compiled v3\n",
        f"**Status:** `{status}`  ",
        f"**Full fingerprint:** `{compiled_doc['compiled_definition_sha256']}`  ",
        f"**Drawing slice:** `{compiled_doc['drawing_projection_sha256']}`  ",
        f"**Variation slice:** `{compiled_doc['variation_sha256']}`  ",
        f"**Inspection slice:** `{compiled_doc['inspection_sha256']}`\n",
        "## Chain gates\n",
    ]
    for k, v in compiled_doc["gates"].items():
        md.append(f"- **{k}**: `{v if isinstance(v, str) else v.get('status')}`")
    md += ["\n## Characteristic matrix\n", "| ID | State | Allocations | Datum/DRF | Measurement | Binding invariance |", "|---|---|---|---|---|---|"]
    for x in compiled:
        md.append(f"| {x['id']} | {x.get('definition_state')} | {','.join(x.get('requirement_allocation_ids', [])) or '-'} | {x.get('datum_reference_system',{}).get('status','-')} | {x.get('measurement_condition',{}).get('status','-')} | {x.get('binding_invariance',{}).get('status','-')} |")
    md += ["\n## Release blockers\n"]
    for x in release_blockers:
        md.append(f"- {x['id']} — {x.get('role')} — {x.get('state')}")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    control = {
        "schema": "k01.product_definition_readiness.current.v3_1",
        "generated_utc": compiled_doc["generated_utc"],
        "status": status,
        "part": "K01-P-007",
        "compiled_definition": str(OUT_JSON.relative_to(ROOT)),
        "compiled_definition_sha256": compiled_doc["compiled_definition_sha256"],
        "drawing_projection_sha256": compiled_doc["drawing_projection_sha256"],
        "gates": compiled_doc["gates"],
        "safe_projection_ids": safe_projection_ids,
        "stale_legacy_spec_count": len(stale_specs),
        "release_blocker_count": len(release_blockers),
        "release_blockers": release_blockers,
        "chain_open_counts": {
            "missing_allocations": len(missing_allocations),
            "measurement_conditions": len(set(measurement_gaps)),
            "binding_invariance": len(set(binding_gaps)),
            "inspection_strategy": len(set(inspection_gaps)),
            "manufacturing_route": 1 if mfg.get("selection") == "OPEN" else 0,
            "configuration_effectivity": 1 if "OPEN" in str(context.get("configuration_scope", {}).get("effectivity_status", "OPEN")) else 0,
        },
        "next": "Drawing projection may use only drawing slice fingerprint. Release remains HOLD until chain/release blockers close." if candidate_ready else "Close Product Definition chain consistency blockers before drawing work."
    }
    dump(OUT_CTRL, control)

    chain = {
        "schema": "k01.engineering_chain_readiness.current.v1",
        "generated_utc": compiled_doc["generated_utc"],
        "status": "PASS_CHAIN_CONTROLLED__HOLD_RELEASE" if candidate_ready else "HOLD_CHAIN_CONTROL",
        "requirement_allocation": {"status": "PASS" if allocation_identity_pass else "HOLD", "missing": missing_allocations},
        "derived_inputs": {"status": "CONTROLLED_REGISTRY_WITH_OPEN_OR_SCREENING_VALUES", "count": len(der_map)},
        "manufacturing_feasibility": {"status": mfg.get("status"), "selection": mfg.get("selection")},
        "datum_reference_systems": {"status": "CONTROLLED_WITH_OPEN_J2_FINAL_DRF", "registry": str(DATUMS.relative_to(ROOT))},
        "measurement_conditions": {"status": "HOLD_RELEASE" if measurement_gaps else "PASS", "open_ids": sorted(set(measurement_gaps))},
        "binding_invariance": {"status": "HOLD_RELEASE" if binding_gaps else "PASS", "open_ids": sorted(set(binding_gaps))},
        "analysis_split": {"physics": "SEPARATE_INVALIDATION_DOMAIN", "variation_capability": "SEPARATE_INVALIDATION_DOMAIN"},
        "inspection_strategy": {"status": "HOLD_RELEASE" if inspection_gaps else "PASS", "open_ids": sorted(set(inspection_gaps)), "rule": "method in S2; plan/results in S6"},
        "configuration_effectivity": {"status": context.get("configuration_scope", {}).get("effectivity_status")},
        "feedback_loop": {"policy": str(FEEDBACK_POLICY.relative_to(ROOT)), "open_records": len(load(FEEDBACK_REG).get('records', []))},
        "fingerprints": compiled_doc["slice_fingerprints"],
    }
    dump(OUT_CHAIN, chain)

    draw_gate = {
        "schema": "k01.d006.drawing_authoring_gate.current.v2",
        "generated_utc": compiled_doc["generated_utc"],
        "drawing": "K01-D-006",
        "status": "PASS_TO_DRAWING_PROJECTION_COMPILER" if candidate_ready else "HOLD_PRODUCT_DEFINITION",
        "compiled_definition_sha256": compiled_doc["compiled_definition_sha256"],
        "drawing_projection_sha256": compiled_doc["drawing_projection_sha256"],
        "allowed": ["refine/copy existing linked SLDDRW", "project controlled drawing-slice semantics", "explicitly mark OPEN values/notes", "retain manual 10-20% visual cleanup"] if candidate_ready else [],
        "prohibited": ["read legacy candidate_spec as release authority", "invent/inherit general tolerances", "use inspection result as drawing authority", "release drawing while DRAWING_RELEASE_READY=HOLD"],
        "source": str(OUT_JSON.relative_to(ROOT)),
        "drawing_slice": slices["drawing"],
        "medtas_node_id": "K01.PD.P007.DRAWING_SLICE"
    }
    dump(OUT_DRAW_GATE, draw_gate)

    build_record = register_build(ROOT, "K01.PD.P007.COMPILED", "tools/medtas/product_definition_guard_v11.py", extra={"compiled_definition_sha256": compiled_doc["compiled_definition_sha256"]})
    verification_record = register_verify(ROOT, "K01.PD.P007.COMPILED", "PASS" if candidate_ready else "HOLD", metrics={"drawing_candidate_ready": candidate_ready, "drawing_release_ready": release_ready, "release_blocker_count": len(release_blockers)}, limitations=[] if candidate_ready else ["Product Definition candidate gate not ready"], notes="PASS verifies chain/compiled contract consistency for design-review projection; not release readiness.")
    for kind, fp in fingerprints.items():
        node = f"K01.PD.P007.{kind.upper()}_SLICE"
        register_build(ROOT, node, "tools/medtas/product_definition_guard_v11.py", extra={"slice_sha256": fp})
        register_verify(ROOT, node, "PASS" if candidate_ready else "HOLD", metrics={"slice_sha256": fp}, limitations=[])

    print(f"STATUS: {status}")
    print(f"CHAIN_CONTROL: {'PASS_WITH_OPEN_RELEASE_GAPS' if candidate_ready else 'HOLD'}")
    print(f"DRAWING_CANDIDATE_READY: {'PASS' if candidate_ready else 'HOLD'}")
    print(f"PMI_AUTHORING_READY: {'PASS_PARTIAL_SCOPE ' + ','.join(pmi_ready_ids) if pmi_ready_ids else 'HOLD'}")
    print(f"DRAWING_RELEASE_READY: {'PASS' if release_ready else 'HOLD'}")
    print(f"DRAWING_SLICE_SHA256: {compiled_doc['drawing_projection_sha256']}")
    print(f"VARIATION_SLICE_SHA256: {compiled_doc['variation_sha256']}")
    print(f"INSPECTION_SLICE_SHA256: {compiled_doc['inspection_sha256']}")
    print(f"RELEASE_BLOCKERS: {len(release_blockers)}")
    print(f"COMPILED: {OUT_JSON}")
    print(f"CHAIN_REPORT: {OUT_CHAIN}")
    print(f"MEDTAS_STATE_HASH: {build_record['built_state_hash']}")
    print(f"MEDTAS_VERIFY: {verification_record['verdict']}")
    return 0 if candidate_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
