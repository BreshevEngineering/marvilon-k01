"""
K01 repository guard — MIGRATION MODE.

Purpose:
- root can only shrink during migration;
- no new arbitrary root entries;
- grandfathered legacy root entries are frozen: delete is allowed, modify/re-add is not;
- current writable engineering roots remain usable;
- forbidden generated/binary artefacts cannot be added to Git;
- non-zero exit blocks pre-commit and CI.

This is intentionally a migration guard. A stricter final guard replaces it
after command/tool normalization is complete.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

SNAPSHOT_TAG = "snapshot-2026-09-08"
FORBIDDEN_EXT = {
    ".exe", ".dll", ".pyc", ".pyo", ".zip", ".log", ".bmp",
    ".cwr", ".pc0", ".sl3", ".tmp"
}
CANONICAL_WRITABLE_ROOT = {
    "requirements", "params", "contract", "backends", "tools",
    "control", "evidence", "center", "docs", "tests", "cad",
    "cad_api", "reports",
    "run.cmd", "README.md", "CHANGELOG.md", "pyproject.toml",
    ".github", ".githooks", ".gitignore", ".gitattributes",
}
ALLOWLIST_PATH = Path("control/repo/K01_ROOT_MIGRATION_ALLOWLIST.json")

def git(repo: Path, *args):
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, errors="replace"
    )
    return p.returncode, p.stdout.splitlines(), p.stderr.strip()

def resolve_repo(start: Path):
    rc, out, err = git(start, "rev-parse", "--show-toplevel")
    if rc != 0 or not out:
        raise SystemExit("repo_guard HOLD — cannot resolve git root")
    return Path(out[0]).resolve()

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def top(path: str):
    return path.replace("\\", "/").split("/", 1)[0]

class Guard:
    def __init__(self, repo: Path):
        self.repo = repo
        self.errors = []
        p = repo / ALLOWLIST_PATH
        if not p.exists():
            raise SystemExit(f"repo_guard HOLD — migration allowlist missing: {p}")
        obj = load_json(p)
        self.frozen = set(obj.get("grandfathered_frozen_root_entries", []))
        self.retired = set(obj.get("retired_root_entries", []))
        self.writable = set(obj.get("writable_root_entries", [])) | CANONICAL_WRITABLE_ROOT

    def err(self, path, rule, detail):
        self.errors.append(f"{path}\n      [{rule}] {detail}")

    def check_live_root(self):
        names = {p.name for p in self.repo.iterdir()}
        names.discard(".git")
        allowed = self.writable | self.frozen
        for name in sorted(names - allowed):
            self.err(name, "root closed", "new/unclassified root entry")
        for name in sorted(names & self.retired):
            self.err(name, "retired root entry", "must not be reintroduced")

    def check_tracked_forbidden(self, names):
        for rel in names:
            ext = Path(rel).suffix.lower()
            if ext in FORBIDDEN_EXT:
                self.err(rel, "forbidden artefact", f"{ext} must not enter Git")

    def check_staged(self):
        rc, diff, err = git(self.repo, "diff", "--cached", "--name-status", "-M")
        if rc != 0:
            self.err("<git>", "cannot inspect index", err)
            return

        staged_paths = []
        for line in diff:
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status = parts[0]
            path = parts[-1]
            staged_paths.append(path)
            root = top(path)

            if root in self.retired and not status.startswith("D"):
                self.err(path, "retired root entry", "only deletion is allowed")

            if root in self.frozen and not status.startswith("D"):
                self.err(path, "legacy root frozen",
                         "grandfathered legacy may only be deleted; route work through canonical locations")

            if root not in self.writable and root not in self.frozen and root not in self.retired:
                self.err(path, "root closed", "staged path introduces an unapproved root entry")

        self.check_tracked_forbidden(staged_paths)

    def check_ci(self):
        rc, names, err = git(self.repo, "ls-files")
        if rc != 0:
            self.err("<git>", "cannot list tracked files", err)
            return
        self.check_tracked_forbidden(names)

        # CI must also prove frozen legacy roots have not changed since protected snapshot.
        rc, diff, err = git(self.repo, "diff", "--name-status", "-M", f"{SNAPSHOT_TAG}..HEAD")
        if rc != 0:
            self.err("<git>", "cannot compare snapshot tag", err)
            return
        for line in diff:
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status = parts[0]
            path = parts[-1]
            root = top(path)
            if root in self.retired and not status.startswith("D"):
                self.err(path, "retired root entry", "reintroduced/modified after snapshot")
            if root in self.frozen and not status.startswith("D"):
                self.err(path, "legacy root frozen", "modified after protected snapshot")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--ci", action="store_true")
    mode.add_argument("--live", action="store_true")
    args = ap.parse_args()

    repo = resolve_repo(Path(args.repo_root).resolve())
    g = Guard(repo)
    if args.staged:
        g.check_staged()
    elif args.ci:
        g.check_live_root()
        g.check_ci()
    else:
        g.check_live_root()

    if not g.errors:
        print("repo_guard MIGRATION PASS")
        return 0
    print(f"repo_guard MIGRATION HOLD — violations: {len(g.errors)}\n")
    for e in g.errors:
        print("  " + e)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
