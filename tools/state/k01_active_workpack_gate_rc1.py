from __future__ import annotations

from pathlib import Path
import datetime
import hashlib
import json

VALID_ACTION_CLASSES = {
    "READ_ONLY",
    "ENGINEERING_MUTATION",
    "CONTROL_MUTATION",
    "PROMOTION",
}

AUTH_REQUIRED_CLASSES = {
    "ENGINEERING_MUTATION",
    "CONTROL_MUTATION",
    "PROMOTION",
}


def rd_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(repo: Path, path: Path):
    try:
        return path.relative_to(repo).as_posix()
    except Exception:
        return str(path)


def canonical_json_sha(obj) -> str:
    raw = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _active_marker_conflicts(next_actions):
    """
    Completion Frontier next_allowed_action.id is canonical.
    Explicit executable markers elsewhere are diagnostic unless they identify
    another workpack, in which case WIP=1 is violated.
    """
    if not isinstance(next_actions, (dict, list)):
        return []

    hits = []

    def walk(v, path="$"):
        if isinstance(v, dict):
            token = None
            for key in ("class", "status", "state", "presentation_state", "execution_class"):
                x = v.get(key)
                if isinstance(x, str) and x.upper() in {"ACTIVE_NOW", "EXECUTABLE_NOW", "ACTIVE"}:
                    token = x.upper()
                    break
            if token:
                ident = v.get("id") or v.get("workpack_id") or v.get("action_id") or path
                hits.append({"id": ident, "token": token, "path": path})
            for k, x in v.items():
                walk(x, f"{path}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]")

    walk(next_actions)

    unique = {}
    for h in hits:
        unique[str(h["id"])] = h
    return list(unique.values())


def _resolve_input(repo: Path, item):
    absolute = item.get("absolute_path")
    relative = item.get("path")

    if absolute:
        path = Path(absolute)
    elif relative:
        path = repo / relative
    else:
        return {
            **item,
            "present": False,
            "fresh": False,
            "identity_unambiguous": False,
            "reason": "NO_PATH",
        }

    expected = item.get("sha256")
    present = path.is_file()
    current = sha256(path) if present else None
    fresh = bool(present and expected and current == expected)

    return {
        **item,
        "resolved_path": str(path),
        "present": present,
        "current_sha256": current,
        "fresh": fresh,
        "identity_unambiguous": fresh,
        "reason": (
            "PASS_PATH_AND_SHA"
            if fresh
            else "MISSING"
            if not present
            else "SHA_MISMATCH"
            if expected
            else "NO_EXPECTED_SHA"
        ),
    }


def _authorization_basis(
    repo: Path,
    frontier: dict,
    contract_path: Path,
    contract: dict,
    operator_lock: dict,
    resolved_inputs: list,
):
    operator_path = repo / "control/system/K01_OPERATOR_LOCK_CURRENT.json"
    frontier_path = repo / "control/state/K01_COMPLETION_FRONTIER_CURRENT.json"

    return {
        "goal_lock": frontier.get("deliverable"),
        "active_engineering_object": frontier.get("active_engineering_object"),
        "active_workpack_id": frontier.get("active_workpack_id") or frontier.get("next_id"),
        "action_class": contract.get("action_class"),
        "contract_sha256": sha256(contract_path) if contract_path.is_file() else None,
        "operator_lock_sha256": sha256(operator_path) if operator_path.is_file() else None,
        "frontier_sha256": sha256(frontier_path) if frontier_path.is_file() else None,
        "required_inputs": [
            {
                "id": x.get("id"),
                "expected_sha256": x.get("sha256"),
                "current_sha256": x.get("current_sha256"),
                "resolved_path": x.get("resolved_path"),
            }
            for x in resolved_inputs
        ],
        "mutation_scope": contract.get("mutation_scope"),
        "expected_result": contract.get("expected_result"),
    }


def _authorization_state(
    repo: Path,
    action_class: str | None,
    basis: dict,
    preflight_pass: bool,
):
    if action_class not in AUTH_REQUIRED_CLASSES:
        return {
            "status": "NOT_REQUIRED_READ_ONLY",
            "required": False,
            "valid": True,
            "path": "control/system/K01_ACTIVE_WORKPACK_AUTHORIZATION_CURRENT.json",
        }

    path = repo / "control/system/K01_ACTIVE_WORKPACK_AUTHORIZATION_CURRENT.json"

    if not preflight_pass:
        return {
            "status": "BLOCKED_BY_PREFLIGHT",
            "required": True,
            "valid": False,
            "path": rel(repo, path),
        }

    if not path.is_file():
        return {
            "status": "MISSING",
            "required": True,
            "valid": False,
            "path": rel(repo, path),
        }

    record = rd_json(path)
    if not isinstance(record, dict):
        return {
            "status": "INVALID",
            "required": True,
            "valid": False,
            "path": rel(repo, path),
        }

    current_scope_hash = canonical_json_sha(basis)
    reasons = []

    if record.get("authorization_scope_sha256") != current_scope_hash:
        reasons.append("AUTHORIZATION_SCOPE_CHANGED")
    if record.get("active_workpack_id") != basis.get("active_workpack_id"):
        reasons.append("ACTIVE_WORKPACK_CHANGED")
    if record.get("action_class") != action_class:
        reasons.append("ACTION_CLASS_CHANGED")
    if record.get("contract_sha256") != basis.get("contract_sha256"):
        reasons.append("EXECUTION_CONTRACT_CHANGED")
    if record.get("operator_lock_sha256") != basis.get("operator_lock_sha256"):
        reasons.append("OPERATOR_LOCK_CHANGED")
    if record.get("frontier_sha256") != basis.get("frontier_sha256"):
        reasons.append("COMPLETION_FRONTIER_CHANGED")

    if reasons:
        return {
            "status": "STALE",
            "required": True,
            "valid": False,
            "path": rel(repo, path),
            "reasons": reasons,
            "record": record,
            "current_scope_sha256": current_scope_hash,
        }

    return {
        "status": "AUTHORIZED",
        "required": True,
        "valid": True,
        "path": rel(repo, path),
        "record": record,
        "current_scope_sha256": current_scope_hash,
    }


def evaluate_active_workpack_gate(
    repo: Path,
    frontier: dict,
    operator_lock: dict,
    typed_holds: list | None = None,
    write_report: bool = True,
    require_authorization: bool = True,
):
    repo = Path(repo)
    typed_holds = list(typed_holds or [])

    contract_path = repo / "control/system/K01_ACTIVE_WORKPACK_EXECUTION_CONTRACT_CURRENT.json"
    contract = rd_json(contract_path)

    next_actions_path = repo / "control/project/K01_NEXT_ACTIONS_CURRENT.json"
    next_actions = rd_json(next_actions_path) if next_actions_path.is_file() else None

    goal = frontier.get("deliverable")
    active_object = frontier.get("active_engineering_object")
    active_workpack_id = frontier.get("active_workpack_id") or frontier.get("next_id")
    active_workpack_text = frontier.get("active_workpack_text") or frontier.get("next_text")

    op_record = operator_lock.get("record") if isinstance(operator_lock, dict) else None
    op_status = operator_lock.get("status") if isinstance(operator_lock, dict) else None
    if not isinstance(op_record, dict):
        op_record = {}

    # Q1
    q1_goal = (
        op_status == "CONFIRMED"
        and op_record.get("confirmed_goal_lock") == goal
        and bool(goal)
    )

    # Q2
    marker_hits = _active_marker_conflicts(next_actions)
    conflicting_ids = {
        str(x.get("id"))
        for x in marker_hits
        if str(x.get("id")) != str(active_workpack_id)
    }
    q2_single = (
        bool(active_workpack_id)
        and op_status == "CONFIRMED"
        and op_record.get("confirmed_active_workpack_id") == active_workpack_id
        and len(conflicting_ids) == 0
    )

    # Q3
    # IMPORTANT RC1.3 semantic correction:
    # A workpack closure target is not itself a prohibition on starting that same workpack.
    # Only holds with blocks_active_workpack=true are pre-execution blockers.
    workpack_target_holds = []
    blocking_holds = []
    blocking_engineering_holds = []

    for h in typed_holds:
        if not isinstance(h, dict):
            continue

        # Upgrade compatibility:
        # RC1.2 emitted ACTIVE-BLOCKER with blocks_active_workpack=true even when it
        # represented the closure target named by Completion Frontier. Treat that
        # exact legacy shape as WORKPACK_TARGET so a stale RC1.2 report cannot
        # deadlock the RC1.3 upgrade.
        legacy_target = bool(
            h.get("type") == "ENGINEERING_HOLD"
            and h.get("id") == "ACTIVE-BLOCKER"
            and str(h.get("reason")) == str(frontier.get("active_blocker"))
        )

        if legacy_target:
            normalized = dict(h)
            normalized["id"] = "ACTIVE-WORKPACK-TARGET"
            normalized["role"] = "WORKPACK_TARGET"
            normalized["blocks_active_workpack"] = False
            normalized["blocks_workpack_closure"] = True
            workpack_target_holds.append(normalized)
            continue

        if h.get("role") == "WORKPACK_TARGET" or h.get("blocks_workpack_closure"):
            workpack_target_holds.append(h)
        if h.get("blocks_active_workpack"):
            blocking_holds.append(h)
            if h.get("type") == "ENGINEERING_HOLD":
                blocking_engineering_holds.append(h)

    if not workpack_target_holds and frontier.get("active_blocker"):
        workpack_target_holds.append(
            {
                "type": "ENGINEERING_HOLD",
                "id": "ACTIVE-WORKPACK-TARGET",
                "reason": frontier.get("active_blocker"),
                "role": "WORKPACK_TARGET",
                "blocks_active_workpack": False,
                "blocks_workpack_closure": True,
                "blocks_lifecycle_exit": True,
                "blocks_release": True,
            }
        )

    q3_blocking_engineering_hold_present = len(blocking_engineering_holds) > 0
    q3_pass_no_blocking_engineering_hold = not q3_blocking_engineering_hold_present

    # Q4/Q5
    contract_ok = isinstance(contract, dict)
    contract_matches = bool(
        contract_ok
        and contract.get("active_workpack_id") == active_workpack_id
        and contract.get("active_engineering_object") == active_object
    )

    action_class = contract.get("action_class") if contract_ok else None
    action_class_valid = action_class in VALID_ACTION_CLASSES

    resolved_inputs = []
    if contract_ok:
        for item in contract.get("required_inputs", []):
            if isinstance(item, dict):
                resolved_inputs.append(_resolve_input(repo, item))

    q4_inputs = bool(
        contract_ok
        and contract_matches
        and resolved_inputs
        and all(
            x.get("identity_unambiguous") and x.get("fresh")
            for x in resolved_inputs
        )
    )

    preflight_blockers = []
    if not q1_goal:
        preflight_blockers.append("GOAL_LOCK_NOT_OPERATOR_CONFIRMED")
    if not q2_single:
        preflight_blockers.append("ACTIVE_WORKPACK_NOT_SINGLE_OR_OPERATOR_BOUND")
    if q3_blocking_engineering_hold_present:
        preflight_blockers.append("BLOCKING_ENGINEERING_HOLD_PRESENT")
    for h in blocking_holds:
        if h not in blocking_engineering_holds:
            preflight_blockers.append(
                "TYPED_HOLD_BLOCKS_ACTIVE:" + str(h.get("id") or h.get("type"))
            )
    if not contract_ok:
        preflight_blockers.append("ACTIVE_WORKPACK_EXECUTION_CONTRACT_MISSING_OR_INVALID")
    elif not contract_matches:
        preflight_blockers.append("EXECUTION_CONTRACT_DOES_NOT_MATCH_ACTIVE_FRONTIER")
    if not q4_inputs:
        preflight_blockers.append("ACTIVE_WORKPACK_INPUTS_NOT_UNAMBIGUOUS_AND_FRESH")
    if not action_class_valid:
        preflight_blockers.append("ACTION_CLASS_INVALID_OR_MISSING")

    preflight_pass = len(preflight_blockers) == 0

    basis = _authorization_basis(
        repo,
        frontier,
        contract_path,
        contract or {},
        operator_lock,
        resolved_inputs,
    )
    authorization = _authorization_state(
        repo,
        action_class,
        basis,
        preflight_pass,
    )

    # Human authorization is part of the final execution permission.
    # --preflight-only changes the CLI return criterion, not the meaning of
    # can_start_active_workpack.
    final_pass = preflight_pass and authorization.get("valid", False)

    ready_for_authorization = bool(
        preflight_pass
        and authorization.get("required")
        and authorization.get("status") in {"MISSING", "STALE", "INVALID"}
    )

    report = {
        "schema": "k01.active_workpack.execution_gate.rc1.v2",
        "control_system_revision": "RC1.3",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "preflight_status": (
            "PASS_ACTIVE_WORKPACK_PREFLIGHT"
            if preflight_pass
            else "HOLD_ACTIVE_WORKPACK_PREFLIGHT"
        ),
        "status": (
            "PASS_ACTIVE_WORKPACK_EXECUTION_GATE"
            if final_pass
            else "HOLD_ACTIVE_WORKPACK_EXECUTION_GATE"
        ),
        "goal_lock": goal,
        "active_engineering_object": active_object,
        "active_workpack_id": active_workpack_id,
        "active_workpack_text": active_workpack_text,
        "action_class": action_class,
        "technical_preconditions_pass": preflight_pass,
        "authorization": authorization,
        "authorization_scope_sha256": canonical_json_sha(basis),
        "ready_for_operator_authorization": ready_for_authorization,
        "can_start_active_workpack": final_pass,
        "five_control_questions": {
            "1_goal_lock_operator_confirmed": q1_goal,
            "2_active_workpack_single_and_operator_bound": q2_single,
            "3_engineering_hold_blocks_active_workpack_present": q3_blocking_engineering_hold_present,
            "3_pass_no_blocking_engineering_hold": q3_pass_no_blocking_engineering_hold,
            "4_inputs_unambiguously_identified_and_fresh": q4_inputs,
            "5_action_class": action_class,
        },
        "workpack_target_holds": workpack_target_holds,
        "blocking_precondition_holds": blocking_holds,
        "active_marker_diagnostic": {
            "markers": marker_hits,
            "conflicting_ids": sorted(conflicting_ids),
            "rule": (
                "Completion Frontier next_allowed_action.id is canonical; "
                "a contradictory executable marker for another workpack violates WIP=1."
            ),
        },
        "execution_contract": {
            "path": rel(repo, contract_path),
            "present": contract_ok,
            "matches_frontier": contract_matches,
            "sha256": sha256(contract_path) if contract_path.is_file() else None,
        },
        "required_inputs": resolved_inputs,
        "input_summary": {
            "count": len(resolved_inputs),
            "present": sum(1 for x in resolved_inputs if x.get("present")),
            "fresh": sum(1 for x in resolved_inputs if x.get("fresh")),
            "ambiguous_or_stale": [
                x.get("id")
                for x in resolved_inputs
                if not (x.get("identity_unambiguous") and x.get("fresh"))
            ],
        },
        "mutation_scope": (contract or {}).get("mutation_scope"),
        "expected_result": (contract or {}).get("expected_result"),
        "preflight_blockers": preflight_blockers,
        "rules": [
            "Operator Lock confirms intent and the single ACTIVE workpack.",
            "A frontier active blocker may be the closure target of the ACTIVE workpack; that target must not be mislabeled as blocks_active_workpack=true.",
            "Any true blocks_active_workpack=true HOLD prevents starting the ACTIVE workpack.",
            "ACTIVE input identity requires exact path plus SHA-256.",
            "Hash drift on any required input makes preflight HOLD.",
            "ENGINEERING_MUTATION, CONTROL_MUTATION and PROMOTION require explicit scope-bound human authorization.",
            "Authorization becomes stale when workpack, action class, contract, Operator Lock, Completion Frontier or bound input scope changes.",
            "PROMOTION is always a separate action from engineering mutation.",
        ],
    }

    if write_report:
        out = repo / "reports/control"
        out.mkdir(parents=True, exist_ok=True)
        jp = out / "K01_ACTIVE_WORKPACK_GATE_CURRENT.json"
        mp = out / "K01_ACTIVE_WORKPACK_GATE_CURRENT.md"
        jp.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        q = report["five_control_questions"]
        lines = [
            "# K01 ACTIVE WORKPACK EXECUTION GATE — CURRENT",
            "",
            f"- Preflight: **{report['preflight_status']}**",
            f"- Execution gate: **{report['status']}**",
            f"- Goal Lock: `{goal}`",
            f"- Active object: `{active_object}`",
            f"- Active workpack: `{active_workpack_id}`",
            f"- Action class: **{action_class}**",
            f"- Authorization: **{authorization.get('status')}**",
            f"- Ready for operator authorization: **{ready_for_authorization}**",
            f"- Can start ACTIVE workpack: **{final_pass}**",
            "",
            "## Five control questions",
            f"1. Goal Lock operator-confirmed: **{q['1_goal_lock_operator_confirmed']}**",
            f"2. ACTIVE workpack single/operator-bound: **{q['2_active_workpack_single_and_operator_bound']}**",
            f"3. ENGINEERING_HOLD blocks_active_workpack=true present: **{q['3_engineering_hold_blocks_active_workpack_present']}**",
            f"   - pass/no blocking engineering hold: **{q['3_pass_no_blocking_engineering_hold']}**",
            f"4. Inputs unambiguously identified and fresh: **{q['4_inputs_unambiguously_identified_and_fresh']}**",
            f"5. Action class: **{q['5_action_class']}**",
            "",
            "## Workpack closure target",
        ]
        for h in workpack_target_holds:
            lines.append(
                f"- `{h.get('id')}` — {h.get('reason')} — blocks_active={h.get('blocks_active_workpack')}"
            )
        if not workpack_target_holds:
            lines.append("- none")

        lines += ["", "## Required inputs"]
        for x in resolved_inputs:
            lines.append(
                f"- `{x.get('id')}` — present={x.get('present')} fresh={x.get('fresh')} — {x.get('resolved_path')}"
            )

        lines += ["", "## Preflight blockers"]
        lines += [f"- {x}" for x in preflight_blockers] or ["- none"]

        mp.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return report


def _frontier_view(repo: Path):
    path = repo / "control/state/K01_COMPLETION_FRONTIER_CURRENT.json"
    raw = rd_json(path) or {}
    next_action = raw.get("next_allowed_action") or {}
    blocker = raw.get("active_blocker")
    if isinstance(blocker, dict):
        blocker = blocker.get("id") or blocker.get("name") or blocker.get("text")

    return {
        "deliverable": raw.get("current_deliverable"),
        "active_engineering_object": raw.get("active_engineering_object"),
        "active_workpack_id": next_action.get("id") if isinstance(next_action, dict) else None,
        "active_workpack_text": next_action.get("text") if isinstance(next_action, dict) else None,
        "next_id": next_action.get("id") if isinstance(next_action, dict) else None,
        "next_text": next_action.get("text") if isinstance(next_action, dict) else None,
        "active_blocker": blocker,
    }


def _operator_view(repo: Path):
    path = repo / "control/system/K01_OPERATOR_LOCK_CURRENT.json"
    record = rd_json(path)
    if not isinstance(record, dict):
        return {"status": "MISSING", "record": {}}
    return {"status": "CONFIRMED", "record": record}


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument(
        "--preflight-only",
        action="store_true",
        help="Evaluate the five questions without requiring mutation authorization.",
    )
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    rc1_path = repo / "reports/control/K01_CONTROL_SYSTEM_RC1_CURRENT.json"

    typed_holds = []
    operator_lock = _operator_view(repo)

    current = rd_json(rc1_path)
    if isinstance(current, dict):
        typed_holds = current.get("typed_holds") or []
        op = current.get("operator_lock")
        if isinstance(op, dict):
            operator_lock = op

    report = evaluate_active_workpack_gate(
        repo,
        _frontier_view(repo),
        operator_lock,
        typed_holds=typed_holds,
        write_report=True,
        require_authorization=not args.preflight_only,
    )

    q = report["five_control_questions"]

    print("============================================================")
    print("K01 ACTIVE WORKPACK EXECUTION GATE RC1.3")
    print("============================================================")
    print("1 GOAL_LOCK_CONFIRMED:", q["1_goal_lock_operator_confirmed"])
    print("2 ACTIVE_WORKPACK_SINGLE:", q["2_active_workpack_single_and_operator_bound"])
    print(
        "3 ENGINEERING_HOLD_BLOCKS_ACTIVE_PRESENT:",
        q["3_engineering_hold_blocks_active_workpack_present"],
    )
    print(
        "3 PASS_NO_BLOCKING_ENGINEERING_HOLD:",
        q["3_pass_no_blocking_engineering_hold"],
    )
    print(
        "4 INPUTS_UNAMBIGUOUS_AND_FRESH:",
        q["4_inputs_unambiguously_identified_and_fresh"],
    )
    print("5 ACTION_CLASS:", q["5_action_class"])
    print("PREFLIGHT:", report["preflight_status"])
    print("MUTATION_AUTHORIZATION:", report["authorization"]["status"])
    print(
        "READY_FOR_OPERATOR_AUTHORIZATION:",
        report["ready_for_operator_authorization"],
    )
    print("CAN_START_ACTIVE_WORKPACK:", report["can_start_active_workpack"])
    print("STATUS:", report["status"])
    for b in report["preflight_blockers"]:
        print("BLOCKER:", b)
    print("REPORT:", repo / "reports/control/K01_ACTIVE_WORKPACK_GATE_CURRENT.json")

    if args.preflight_only:
        return 0 if report["technical_preconditions_pass"] else 2
    return 0 if report["can_start_active_workpack"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
