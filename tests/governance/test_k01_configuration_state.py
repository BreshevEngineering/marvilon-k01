import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

STATE = Path(__file__).resolve().parents[2] / "tools/governance/k01_configuration_state.py"


def run(*args, cwd=None):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, errors="replace")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StateTests(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name) / "repo"
        cad = Path(td.name) / "cadroot"
        root.mkdir()
        cad.mkdir()
        run("git", "init", str(root))
        run("git", "-C", str(root), "config", "user.email", "test@example.com")
        run("git", "-C", str(root), "config", "user.name", "K01 Test")
        part = cad / "cad/parts/P001.SLDPRT"
        part.parent.mkdir(parents=True)
        part.write_bytes(b"CAD")
        mf = root / "control/configuration/K01_CAD_MANIFEST_BASELINE.json"
        mf.parent.mkdir(parents=True)
        mf.write_text(json.dumps({
            "schema": "k01.cad_manifest.baseline.v2",
            "items": [{"relative": "cad/parts/P001.SLDPRT", "sha256": sha(part)}],
        }))
        (root / ".gitignore").write_text("/reports/\n")
        run("git", "-C", str(root), "add", ".")
        run("git", "-C", str(root), "commit", "-m", "base")
        return td, root, cad, part

    def test_clean_pass(self):
        td, root, cad, _ = self.make_repo()
        with td:
            cp = run(sys.executable, str(STATE), "--repo-root", str(root), "--cad-root", str(cad))
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertIn("PASS_CONFIGURATION_STATE", cp.stdout)

    def test_dirty_hold(self):
        td, root, cad, _ = self.make_repo()
        with td:
            (root / "x.txt").write_text("dirty")
            cp = run(sys.executable, str(STATE), "--repo-root", str(root), "--cad-root", str(cad))
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("HOLD_CONFIGURATION_STATE__WORKTREE_DIRTY", cp.stdout)

    def test_cad_drift_hold(self):
        td, root, cad, part = self.make_repo()
        with td:
            part.write_bytes(b"MUTATED")
            cp = run(sys.executable, str(STATE), "--repo-root", str(root), "--cad-root", str(cad))
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("HOLD_CAD_BASELINE_DRIFT", cp.stdout)


if __name__ == "__main__":
    unittest.main()
