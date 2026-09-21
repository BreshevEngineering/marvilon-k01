from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if cp.returncode:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    return cp.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--cad-root", required=True)
    ap.add_argument("--json-out")
    a = ap.parse_args()

    repo = Path(a.repo_root)
    cad = Path(a.cad_root)

    dirty = [
        line
        for line in git(repo, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
        if line.strip()
    ]
    if dirty:
        result = {
            "schema": "k01.configuration_state.v2",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "HOLD_CONFIGURATION_STATE__WORKTREE_DIRTY",
            "dirty_count": len(dirty),
        }
        print(result["status"], len(dirty))
        if a.json_out:
            Path(a.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 2

    manifest = repo / "control/configuration/K01_CAD_MANIFEST_BASELINE.json"
    if not manifest.is_file():
        print("HOLD_CONFIGURATION_STATE__CAD_MANIFEST_MISSING")
        return 2

    obj = json.loads(manifest.read_text(encoding="utf-8-sig"))
    drift: list[dict] = []
    for row in obj.get("items", []):
        p = cad / row["relative"]
        if not p.is_file():
            drift.append({"relative": row["relative"], "reason": "MISSING"})
            continue
        got = sha256_file(p)
        if got != row["sha256"]:
            drift.append(
                {
                    "relative": row["relative"],
                    "reason": "BINARY_SHA_DRIFT",
                    "expected": row["sha256"],
                    "got": got,
                }
            )

    head = git(repo, "rev-parse", "HEAD")
    manifest_sha = sha256_file(manifest)
    state_id = "K01-CS-" + hashlib.sha256(
        (head + "\n" + manifest_sha).encode("utf-8")
    ).hexdigest()[:16]
    result = {
        "schema": "k01.configuration_state.v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_CONFIGURATION_STATE" if not drift else "HOLD_CAD_BASELINE_DRIFT",
        "state_id": state_id,
        "git_head": head,
        "cad_manifest_sha256": manifest_sha,
        "cad_drift": drift,
    }
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"], state_id, "cad_drift=", len(drift))
    return 0 if not drift else 2


if __name__ == "__main__":
    raise SystemExit(main())
