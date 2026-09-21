from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from medtas_v16_common import register_build, register_verify

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json"
POLICY = ROOT / "control/product_definition/K01_PRODUCT_DEFINITION_POLICY_v2_0.json"
LEGACY = ROOT / "control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json"
REQS = ROOT / "control/requirements/requirements.json"
TOL_PLAN = ROOT / "control/drawings/K01_P007_FUNCTIONAL_TOLERANCE_PLAN.json"
METHODS = ROOT / "control/project/K01_EXECUTION_METHOD_REGISTRY_CURRENT.json"
OUT_DIR = ROOT / "reports/product_definition/current"
OUT_JSON = OUT_DIR / "K01_P007_PRODUCT_DEFINITION_COMPILED.json"
OUT_MD = OUT_DIR / "K01_P007_PRODUCT_DEFINITION_COMPILED.md"
OUT_CTRL = ROOT / "reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json"
OUT_DRAW_GATE = ROOT / "reports/control/K01_D006_DRAWING_AUTHORING_GATE_CURRENT.json"


def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def req_registry_map(data):
    # Current registry is either {requirements:[...]} or a list-shaped legacy wrapper.
    items = data.get("requirements", []) if isinstance(data, dict) else data
    return {x.get("id"): x for x in items if isinstance(x, dict) and x.get("id")}


def legacy_map(data):
    return {x.get("id"): x for x in data.get("characteristics", []) if x.get("id")}


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
    # OPEN-only process/acceptance records are not projected as numeric values.
    vals = list(n.values())
    return any(isinstance(v, (int, float)) for v in vals) or any(
        isinstance(v, str) and v not in {"OPEN", ""} for v in vals
    )


def main() -> int:
    required = [DECISIONS, POLICY, LEGACY, REQS, TOL_PLAN, METHODS]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise SystemExit("MISSING INPUTS: " + ", ".join(missing))

    decisions = load(DECISIONS)
    policy = load(POLICY)
    legacy = load(LEGACY)
    reqs = load(REQS)
    methods = load(METHODS)
    reqmap = req_registry_map(reqs)
    legmap = legacy_map(legacy)

    compiled = []
    stale_specs = []
    missing_reqs = []
    missing_characteristic_ids = []
    safe_projection_ids = []
    pmi_ready_ids = []
    release_blockers = []

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
        if bad_req:
            missing_reqs.extend({"characteristic_id": cid, "requirement_id": rid} for rid in bad_req)

        state = d.get("definition_state")
        projection = d.get("drawing_projection", "")
        if state in {"CONTROLLED", "PARTIAL"} and has_numeric_projection_authority(d) and not projection.upper().startswith("OMIT"):
            safe_projection_ids.append(cid)

        binding = str(d.get("cad_binding", ""))
        if cid in {"C02", "C05"} and ("PASS" in binding or "READY" in binding):
            pmi_ready_ids.append(cid)

        if d.get("release_blocking") and state != "CONTROLLED":
            release_blockers.append({"id": cid, "state": state, "role": d.get("role")})

        compiled.append({
            **d,
            "legacy_candidate_spec": legacy_spec,
            "legacy_spec_disposition": "STALE_IGNORED" if reasons else ("INFORMATION_ONLY" if legacy_spec else "NONE"),
            "linked_requirement_ids": req_ids,
            "projection_authority": "COMPILED_DECISION_AND_REFERENCED_SOURCES",
        })

    coverage_gaps = decisions.get("coverage_gaps", [])
    release_blockers.extend({"id": x["id"], "state": x.get("state"), "role": x.get("category")} for x in coverage_gaps if x.get("release_blocking"))

    definition_consistency_pass = not missing_reqs and not missing_characteristic_ids
    material_ok = any(x["id"] == "C09" and x.get("definition_state") == "CONTROLLED" for x in compiled)
    candidate_ready = definition_consistency_pass and material_ok and len(safe_projection_ids) >= 5
    release_ready = candidate_ready and not release_blockers and not stale_specs

    status = "PASS_DRAWING_CANDIDATE_READY__HOLD_RELEASE" if candidate_ready and not release_ready else (
        "PASS_DRAWING_RELEASE_READY" if release_ready else "HOLD_PRODUCT_DEFINITION"
    )

    source_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in required}
    compiled_doc = {
        "schema": "k01.product_definition.compiled.v2_0",
        "generated_utc": now_utc(),
        "part": "K01-P-007",
        "drawing": "K01-D-006",
        "status": status,
        "policy": str(POLICY.relative_to(ROOT)),
        "source_hashes": source_hashes,
        "authority_rule": "Derived contract only; upstream domain authorities remain authoritative.",
        "medtas_node_id": "K01.PD.P007.COMPILED",
        "characteristics": compiled,
        "coverage_gaps": coverage_gaps,
        "stale_legacy_specs": stale_specs,
        "gates": {
            "DEFINITION_CONSISTENCY": "PASS" if definition_consistency_pass else "HOLD",
            "DRAWING_CANDIDATE_READY": "PASS" if candidate_ready else "HOLD",
            "PMI_AUTHORING_READY": {"status": "PASS_PARTIAL_SCOPE" if pmi_ready_ids else "HOLD", "safe_characteristic_ids": pmi_ready_ids},
            "DRAWING_RELEASE_READY": "PASS" if release_ready else "HOLD",
        },
        "safe_projection_ids": safe_projection_ids,
        "release_blockers": release_blockers,
        "missing_requirement_links": missing_reqs,
        "missing_characteristic_ids": missing_characteristic_ids,
        "drawing_compiler_contract": {
            "input": str(OUT_JSON.relative_to(ROOT)),
            "may_project_only": "safe_projection_ids plus explicit nonnumeric OPEN notes",
            "must_not_read_as_authority": ["legacy candidate_spec", "SOLIDWORKS template/general tolerances", "drawing free text", "PDF text"],
            "required_annotation_evidence_fields": ["characteristic_id", "projection_method", "source_definition_fingerprint", "semantic_readback_or_fallback_class"],
            "fallback_rule": "If native associative projection fails, preserve the usable linked SLDDRW and emit a controlled Cxx callout from this compiled contract; mark PROJECTION_FALLBACK. Never invent tolerance semantics."
        },
        "execution_methods": methods.get("methods", []),
    }
    fingerprint_payload = json.dumps(compiled_doc["characteristics"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    compiled_doc["compiled_definition_sha256"] = hashlib.sha256(fingerprint_payload).hexdigest()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(compiled_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# K01-P-007 Product Definition — compiled readiness\n",
        f"**Status:** `{status}`  ",
        f"**Fingerprint:** `{compiled_doc['compiled_definition_sha256']}`  ",
        f"**Drawing candidate:** `{'PASS' if candidate_ready else 'HOLD'}`  ",
        f"**Drawing release:** `{'PASS' if release_ready else 'HOLD'}`\n",
        "## Characteristic matrix\n",
        "| ID | Role | State | Drawing projection | Release blocker |",
        "|---|---|---|---|---|",
    ]
    for x in compiled:
        proj = str(x.get("drawing_projection", "")).replace("|", "/")
        role = str(x.get("role", "")).replace("|", "/")
        md.append(f"| {x['id']} | {role} | {x.get('definition_state')} | {proj} | {'YES' if x.get('release_blocking') else 'NO'} |")
    md.append("\n## Stale legacy candidate semantics\n")
    if stale_specs:
        for x in stale_specs:
            md.append(f"- **{x['id']}**: `{x['legacy_candidate_spec']}` → IGNORE for release/projection because " + "; ".join(x["reasons"]))
    else:
        md.append("- None")
    md.append("\n## Release blockers\n")
    for x in release_blockers:
        md.append(f"- {x['id']} — {x.get('role')} — {x.get('state')}")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    control = {
        "schema": "k01.product_definition_readiness.current.v2_0",
        "generated_utc": compiled_doc["generated_utc"],
        "status": status,
        "part": "K01-P-007",
        "compiled_definition": str(OUT_JSON.relative_to(ROOT)),
        "compiled_definition_sha256": compiled_doc["compiled_definition_sha256"],
        "gates": compiled_doc["gates"],
        "safe_projection_ids": safe_projection_ids,
        "stale_legacy_spec_count": len(stale_specs),
        "release_blocker_count": len(release_blockers),
        "release_blockers": release_blockers,
        "next": "Drawing projection work may continue only by consuming the compiled Product Definition fingerprint. Release remains HOLD until blockers are closed." if candidate_ready else "Close Product Definition consistency blockers before any drawing work."
    }
    OUT_CTRL.parent.mkdir(parents=True, exist_ok=True)
    OUT_CTRL.write_text(json.dumps(control, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    draw_gate = {
        "schema": "k01.d006.drawing_authoring_gate.current.v1",
        "generated_utc": compiled_doc["generated_utc"],
        "drawing": "K01-D-006",
        "status": "PASS_TO_DRAWING_PROJECTION_COMPILER" if candidate_ready else "HOLD_PRODUCT_DEFINITION",
        "compiled_definition_sha256": compiled_doc["compiled_definition_sha256"],
        "allowed": [
            "refine/copy existing linked SLDDRW",
            "project controlled nominal/model semantics from compiled manifest",
            "explicitly mark OPEN values/notes",
            "retain manual 10-20% visual cleanup"
        ] if candidate_ready else [],
        "prohibited": [
            "read legacy candidate_spec as release authority",
            "invent or inherit general tolerances",
            "retry rejected UI-Automation/drawing-entity methods as primary path",
            "release drawing while DRAWING_RELEASE_READY=HOLD"
        ],
        "source": str(OUT_JSON.relative_to(ROOT)),
        "medtas_node_id": "K01.PD.P007.COMPILED"
    }
    OUT_DRAW_GATE.write_text(json.dumps(draw_gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Bind the compiled Product Definition artifact to the authoritative MEDTAS input state.
    # This is distinct from compiled_definition_sha256: CAD/interface binding context may change
    # even when the Cxx semantic payload is numerically unchanged.
    build_record = register_build(
        ROOT,
        "K01.PD.P007.COMPILED",
        "tools/medtas/product_definition_guard_v8.py",
        extra={"compiled_definition_sha256": compiled_doc["compiled_definition_sha256"]},
    )
    verification_record = register_verify(
        ROOT,
        "K01.PD.P007.COMPILED",
        "PASS" if candidate_ready else "HOLD",
        metrics={
            "drawing_candidate_ready": candidate_ready,
            "drawing_release_ready": release_ready,
            "release_blocker_count": len(release_blockers),
            "compiled_definition_sha256": compiled_doc["compiled_definition_sha256"],
        },
        limitations=[] if candidate_ready else ["Product Definition candidate gate not ready"],
        notes="PASS verifies compiled contract consistency/readiness only; it does not imply drawing release readiness.",
    )

    print(f"STATUS: {status}")
    print(f"DRAWING_CANDIDATE_READY: {'PASS' if candidate_ready else 'HOLD'}")
    print(f"PMI_AUTHORING_READY: {'PASS_PARTIAL_SCOPE ' + ','.join(pmi_ready_ids) if pmi_ready_ids else 'HOLD'}")
    print(f"DRAWING_RELEASE_READY: {'PASS' if release_ready else 'HOLD'}")
    print(f"SAFE_PROJECTION_IDS: {','.join(safe_projection_ids)}")
    print(f"STALE_LEGACY_SPECS: {len(stale_specs)}")
    print(f"RELEASE_BLOCKERS: {len(release_blockers)}")
    print(f"COMPILED: {OUT_JSON}")
    print(f"REPORT: {OUT_CTRL}")
    print(f"DRAWING_GATE: {OUT_DRAW_GATE}")
    print(f"MEDTAS_STATE_HASH: {build_record['built_state_hash']}")
    print(f"MEDTAS_VERIFY: {verification_record['verdict']}")
    return 0 if candidate_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
