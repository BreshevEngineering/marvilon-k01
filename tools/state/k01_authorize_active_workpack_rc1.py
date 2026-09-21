from __future__ import annotations

from pathlib import Path
import datetime
import json

from k01_active_workpack_gate_rc1 import (
    _authorization_basis,
    _frontier_view,
    _operator_view,
    canonical_json_sha,
    evaluate_active_workpack_gate,
    rd_json,
    sha256,
)


REPO = Path(r"D:\BreshevEngineering\marvilon-k01")


def main():
    repo = REPO
    current_path = repo / "reports/control/K01_CONTROL_SYSTEM_RC1_CURRENT.json"

    current = rd_json(current_path) or {}
    typed_holds = current.get("typed_holds") or []
    operator_lock = current.get("operator_lock")
    if not isinstance(operator_lock, dict):
        operator_lock = _operator_view(repo)

    frontier = _frontier_view(repo)

    # Preflight is intentionally evaluated without requiring authorization,
    # because this tool is the mechanism that creates that authorization.
    preflight = evaluate_active_workpack_gate(
        repo,
        frontier,
        operator_lock,
        typed_holds=typed_holds,
        write_report=True,
        require_authorization=False,
    )

    if not preflight.get("technical_preconditions_pass"):
        print("HOLD_MUTATION_AUTHORIZATION_PREFLIGHT")
        for b in preflight.get("preflight_blockers", []):
            print("BLOCKER:", b)
        print("NO AUTHORIZATION WAS WRITTEN.")
        return 2

    action_class = preflight.get("action_class")
    if action_class == "READ_ONLY":
        print("NO AUTHORIZATION REQUIRED: READ_ONLY")
        return 0

    if action_class not in {"ENGINEERING_MUTATION", "CONTROL_MUTATION", "PROMOTION"}:
        print("HOLD: invalid action class:", action_class)
        return 2

    contract_path = repo / "control/system/K01_ACTIVE_WORKPACK_EXECUTION_CONTRACT_CURRENT.json"
    contract = rd_json(contract_path) or {}
    inputs = preflight.get("required_inputs") or []
    basis = _authorization_basis(
        repo,
        frontier,
        contract_path,
        contract,
        operator_lock,
        inputs,
    )
    scope_hash = canonical_json_sha(basis)

    print("============================================================")
    print("K01 ACTIVE WORKPACK MUTATION AUTHORIZATION RC1.3")
    print("============================================================")
    print("GOAL LOCK:", frontier.get("deliverable"))
    print("ACTIVE OBJECT:", frontier.get("active_engineering_object"))
    print("ACTIVE WORKPACK:", frontier.get("active_workpack_id"))
    print("ACTION CLASS:", action_class)
    print("INPUTS FRESH:", preflight.get("input_summary", {}).get("fresh"), "/", preflight.get("input_summary", {}).get("count"))
    print("AUTHORIZATION SCOPE SHA256:", scope_hash)
    print("")
    print("ALLOWED:")
    for x in (contract.get("mutation_scope") or {}).get("allowed", []):
        print(" +", x)
    print("")
    print("FORBIDDEN:")
    for x in (contract.get("mutation_scope") or {}).get("forbidden", []):
        print(" -", x)
    print("")
    print("EXPECTED RESULT:", contract.get("expected_result"))
    print("")
    print("This authorization is valid only for the exact workpack, action class,")
    print("contract, Operator Lock, Completion Frontier and bound input identities shown above.")
    print("Any relevant change makes it stale.")
    print("")

    answer = input("Type AUTHORIZE to authorize this exact mutation scope: ").strip()
    if answer != "AUTHORIZE":
        print("NO CHANGE: mutation authorization was not granted.")
        return 2

    operator_path = repo / "control/system/K01_OPERATOR_LOCK_CURRENT.json"
    frontier_path = repo / "control/state/K01_COMPLETION_FRONTIER_CURRENT.json"

    record = {
        "schema": "k01.active_workpack.authorization.current.v1",
        "authorized_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "authorized_by": "HUMAN_OPERATOR",
        "goal_lock": frontier.get("deliverable"),
        "active_engineering_object": frontier.get("active_engineering_object"),
        "active_workpack_id": frontier.get("active_workpack_id"),
        "action_class": action_class,
        "authorization_scope_sha256": scope_hash,
        "contract_path": "control/system/K01_ACTIVE_WORKPACK_EXECUTION_CONTRACT_CURRENT.json",
        "contract_sha256": sha256(contract_path),
        "operator_lock_path": "control/system/K01_OPERATOR_LOCK_CURRENT.json",
        "operator_lock_sha256": sha256(operator_path),
        "frontier_path": "control/state/K01_COMPLETION_FRONTIER_CURRENT.json",
        "frontier_sha256": sha256(frontier_path),
        "required_inputs": [
            {
                "id": x.get("id"),
                "resolved_path": x.get("resolved_path"),
                "sha256": x.get("current_sha256"),
            }
            for x in inputs
        ],
        "mutation_scope": contract.get("mutation_scope"),
        "expected_result": contract.get("expected_result"),
        "valid_until": (
            "ACTIVE workpack, action class, execution contract, Operator Lock, "
            "Completion Frontier or any bound input identity changes; or workpack closes."
        ),
        "promotion_included": action_class == "PROMOTION",
        "rule": "Authorization is human authority for this bounded mutation scope only; it is not release/promotion approval unless action_class=PROMOTION.",
    }

    out = repo / "control/system/K01_ACTIVE_WORKPACK_AUTHORIZATION_CURRENT.json"
    out.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("PASS_ACTIVE_WORKPACK_MUTATION_AUTHORIZED")
    print("OUT:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
