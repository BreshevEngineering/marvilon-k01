import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parents[2] / "tools/governance/k01_pr_control_gate.py"


def run(*args, cwd=None):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, errors="replace")


class GateTests(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        self.assertEqual(run("git", "init", str(root)).returncode, 0)
        run("git", "-C", str(root), "config", "user.email", "test@example.com")
        run("git", "-C", str(root), "config", "user.name", "K01 Test")
        (root / "a.txt").write_text("base\n")
        (root / "reports").mkdir()
        (root / "reports/old.txt").write_text("runtime\n")
        run("git", "-C", str(root), "add", ".")
        run("git", "-C", str(root), "commit", "-m", "base")
        base = run("git", "-C", str(root), "rev-parse", "HEAD").stdout.strip()
        return td, root, base

    def commit_tx(self, root, branch, allowed, new_files=None, extra=None):
        (root / "control/change").mkdir(parents=True, exist_ok=True)
        (root / "control/change/tx.json").write_text(json.dumps({
            "schema": "k01.change_transaction.minimal.v1",
            "change_id": branch,
            "intent": "test",
            "allowed_paths": allowed,
            "new_files": new_files or [],
        }))
        if extra:
            extra()
        run("git", "-C", str(root), "add", "-A")
        run("git", "-C", str(root), "commit", "-m", "change")
        return run("git", "-C", str(root), "rev-parse", "HEAD").stdout.strip()

    def gate(self, root, base, branch, head):
        return run(sys.executable, str(GATE), "--repo", str(root), "--base", base, "--head", head, "--branch", branch)

    def test_modify_existing_pass(self):
        td, root, base = self.make_repo()
        with td:
            branch = "change/modify"
            run("git", "-C", str(root), "switch", "-c", branch)
            head = self.commit_tx(root, branch, ["a.txt"], extra=lambda: (root / "a.txt").write_text("changed\n"))
            cp = self.gate(root, base, branch, head)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_new_file_requires_exact_declaration(self):
        td, root, base = self.make_repo()
        with td:
            branch = "change/newbad"
            run("git", "-C", str(root), "switch", "-c", branch)
            def extra():
                (root / "docs").mkdir()
                (root / "docs/new.md").write_text("x")
            head = self.commit_tx(root, branch, ["docs/**"], [], extra)
            cp = self.gate(root, base, branch, head)
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("HOLD_NEW_FILE_NOT_EXACTLY_DECLARED", cp.stdout)

    def test_new_file_exact_declaration_pass(self):
        td, root, base = self.make_repo()
        with td:
            branch = "change/newgood"
            run("git", "-C", str(root), "switch", "-c", branch)
            def extra():
                (root / "docs").mkdir()
                (root / "docs/new.md").write_text("x")
            head = self.commit_tx(root, branch, ["docs/**"], ["docs/new.md"], extra)
            cp = self.gate(root, base, branch, head)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_runtime_addition_rejected(self):
        td, root, base = self.make_repo()
        with td:
            branch = "change/runtime-add"
            run("git", "-C", str(root), "switch", "-c", branch)
            def extra():
                (root / "reports/new.txt").write_text("new")
            head = self.commit_tx(root, branch, ["reports/new.txt"], ["reports/new.txt"], extra)
            cp = self.gate(root, base, branch, head)
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("HOLD_FORBIDDEN_RUNTIME_PATH", cp.stdout)

    def test_runtime_deletion_allowed(self):
        td, root, base = self.make_repo()
        with td:
            branch = "change/runtime-delete"
            run("git", "-C", str(root), "switch", "-c", branch)
            head = self.commit_tx(root, branch, ["reports/old.txt"], extra=lambda: (root / "reports/old.txt").unlink())
            cp = self.gate(root, base, branch, head)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_blanket_scope_rejected(self):
        td, root, base = self.make_repo()
        with td:
            branch = "change/blanket"
            run("git", "-C", str(root), "switch", "-c", branch)
            head = self.commit_tx(root, branch, ["**"], extra=lambda: (root / "a.txt").write_text("x"))
            cp = self.gate(root, base, branch, head)
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("HOLD_BLANKET_SCOPE_FORBIDDEN", cp.stdout)

    def test_self_modifying_gate_mixed_change_rejected(self):
        td, root, base = self.make_repo()
        with td:
            branch = "governance/bad"
            run("git", "-C", str(root), "switch", "-c", branch)
            def extra():
                (root / "tools/governance").mkdir(parents=True)
                (root / "tools/governance/k01_pr_control_gate.py").write_text("raise SystemExit(0)\n")
                (root / "product.txt").write_text("violation\n")
            head = self.commit_tx(
                root, branch,
                ["tools/governance/k01_pr_control_gate.py", "product.txt"],
                ["tools/governance/k01_pr_control_gate.py", "product.txt"],
                extra,
            )
            cp = self.gate(root, base, branch, head)
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("HOLD_SELF_MODIFYING_GATE_MIXED_CHANGE", cp.stdout)

    def test_governance_only_self_change_pass(self):
        td, root, base = self.make_repo()
        with td:
            branch = "governance/good"
            run("git", "-C", str(root), "switch", "-c", branch)
            def extra():
                (root / "tools/governance").mkdir(parents=True)
                (root / "tools/governance/k01_pr_control_gate.py").write_text("print('new gate')\n")
            p = "tools/governance/k01_pr_control_gate.py"
            head = self.commit_tx(root, branch, [p], [p], extra)
            cp = self.gate(root, base, branch, head)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_exact_dot_gitignore_scope_pass(self):
        td, root, base = self.make_repo()
        with td:
            (root / ".gitignore").write_text("base\n")
            run("git", "-C", str(root), "add", ".gitignore")
            run("git", "-C", str(root), "commit", "-m", "add gitignore")
            base = run("git", "-C", str(root), "rev-parse", "HEAD").stdout.strip()
            branch = "change/gitignore"
            run("git", "-C", str(root), "switch", "-c", branch)
            head = self.commit_tx(root, branch, [".gitignore"], extra=lambda: (root / ".gitignore").write_text("changed\n"))
            cp = self.gate(root, base, branch, head)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)


if __name__ == "__main__":
    unittest.main()
