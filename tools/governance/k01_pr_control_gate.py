from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

RUNTIME_PREFIXES = (
    "reports/",
    "evidence/current/",
    "_hotfix_backup/",
    "handoff/",
    "Downloads/",
    "review_upload/",
)
GOVERNANCE_PREFIXES = (
    ".github/workflows/",
    "tools/governance/",
    "tests/governance/",
    "control/change/",
    "control/configuration/",
    "docs/architecture/K01_CONFIGURATION_MODEL_SIMPLE.md",
)
FORBIDDEN_BLANKET_PATTERNS = {"*", "**", "/**", "**/*", "./**", "."}


@dataclass(frozen=True)
class Change:
    status: str
    path: str


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if cp.returncode:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    return cp.stdout


def changed(repo: Path, base: str, head: str) -> list[Change]:
    cp = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-status", "-z", f"{base}...{head}"],
        capture_output=True,
    )
    if cp.returncode:
        raise RuntimeError(cp.stderr.decode("utf-8", "replace") or "git diff failed")
    fields = cp.stdout.decode("utf-8", "replace").split("\0")
    out: list[Change] = []
    i = 0
    while i < len(fields):
        status = fields[i]
        i += 1
        if not status:
            break
        code = status[0]
        if code in {"R", "C"}:
            # Recovery/configuration changes should not hide origin identity through rename/copy.
            if i + 1 >= len(fields):
                raise RuntimeError("malformed rename/copy diff")
            old = fields[i]
            new = fields[i + 1]
            i += 2
            out.append(Change("D", old.replace("\\", "/")))
            out.append(Change("A", new.replace("\\", "/")))
        else:
            if i >= len(fields):
                raise RuntimeError("malformed name-status diff")
            path = fields[i]
            i += 1
            out.append(Change(code, path.replace("\\", "/")))
    return out


def match(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if pattern.startswith("./"):
        pattern = pattern[2:]
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def exact_pattern(pattern: str) -> bool:
    return not any(ch in pattern for ch in "*?[")


def load_transaction(repo: Path, changes: list[Change], branch: str) -> tuple[str, dict]:
    matches: list[tuple[str, dict]] = []
    for ch in changes:
        path = ch.path
        if not (path.startswith("control/change/") and path.endswith(".json")):
            continue
        f = repo / path
        if not f.is_file():
            continue
        try:
            obj = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if obj.get("change_id") == branch:
            matches.append((path, obj))
    if len(matches) != 1:
        raise ValueError(f"HOLD_TRANSACTION_IDENTITY {[p for p, _ in matches]}")
    return matches[0]


def is_governance_path(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in GOVERNANCE_PREFIXES)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--branch", required=True)
    a = ap.parse_args()

    repo = Path(a.repo)
    changes = changed(repo, a.base, a.head)
    if not changes:
        print("HOLD_EMPTY_PR")
        return 2

    try:
        tx_path, tx = load_transaction(repo, changes, a.branch)
    except ValueError as e:
        print(str(e))
        return 2

    if tx.get("schema") != "k01.change_transaction.minimal.v1":
        print("HOLD_TRANSACTION_SCHEMA")
        return 2
    if str(tx.get("change_id") or "") != a.branch:
        print("HOLD_TRANSACTION_BRANCH_MISMATCH")
        return 2
    if not str(tx.get("intent") or "").strip():
        print("HOLD_TRANSACTION_INTENT_MISSING")
        return 2

    allowed = tx.get("allowed_paths") or []
    new_files = tx.get("new_files") or []
    if not isinstance(allowed, list) or not allowed:
        print("HOLD_ALLOWED_PATHS_MISSING")
        return 2
    if not isinstance(new_files, list):
        print("HOLD_NEW_FILES_SCHEMA")
        return 2
    if any(str(p).strip() in FORBIDDEN_BLANKET_PATTERNS for p in allowed):
        print("HOLD_BLANKET_SCOPE_FORBIDDEN")
        return 2

    allowed = [str(x).replace("\\", "/") for x in allowed]
    declared_new = {str(x).replace("\\", "/") for x in new_files}

    # Runtime may be removed during the one-time S2 migration, but never added or modified.
    for ch in changes:
        if any(ch.path.startswith(prefix) for prefix in RUNTIME_PREFIXES):
            if ch.status != "D":
                print("HOLD_FORBIDDEN_RUNTIME_PATH", ch.status, ch.path)
                return 2

    # Only files that can redefine the required GitHub checks are trust roots.
    # Other governance utilities (for example local change_control.py) may evolve in
    # normal scoped PRs; changing them cannot make this base-branch gate return PASS.
    gate_self_change = any(
        ch.path.startswith(".github/workflows/")
        or ch.path == "tools/governance/k01_pr_control_gate.py"
        or ch.path == "tests/governance/test_k01_pr_control_gate.py"
        for ch in changes
    )
    if gate_self_change:
        extra = [
            ch.path
            for ch in changes
            if ch.path != tx_path and not is_governance_path(ch.path)
        ]
        if extra:
            print("HOLD_SELF_MODIFYING_GATE_MIXED_CHANGE", extra)
            return 2

    bad_scope = [
        ch.path
        for ch in changes
        if ch.path != tx_path and not any(match(ch.path, pat) for pat in allowed)
    ]
    if bad_scope:
        print("HOLD_PATH_OUTSIDE_SCOPE", bad_scope)
        return 2

    # M2: additions must be named explicitly, not merely covered by a directory glob.
    undeclared_added = [
        ch.path
        for ch in changes
        if ch.status == "A" and ch.path != tx_path and ch.path not in declared_new
    ]
    if undeclared_added:
        print("HOLD_NEW_FILE_NOT_EXACTLY_DECLARED", undeclared_added)
        return 2

    # Exact new-file declarations must themselves be exact names.
    if any(not exact_pattern(p) for p in declared_new):
        print("HOLD_NEW_FILE_DECLARATION_MUST_BE_EXACT")
        return 2

    print("PASS_K01_CONTROL_GATE", a.branch, "changes=", len(changes), "new=", len(declared_new))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
