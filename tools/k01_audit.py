r"""
K01 fast engineering audit.

Compares reports/cad/current/*.json against:
- master/K01_master.json
- params/k01_params.py
- master/cad_contracts.json

No part-specific numeric values or material decisions are hard-coded here.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = REPO_ROOT / "reports" / "cad" / "current"
CONTRACT_FILE = REPO_ROOT / "master" / "cad_contracts.json"


class Report:
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.checked = 0

    def fail(self, part, msg):
        self.failures.append((part, msg))

    def warn(self, part, msg):
        self.warnings.append((part, msg))

    @property
    def ok(self):
        return not self.failures


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_params(path: Path):
    spec = importlib.util.spec_from_file_location("k01_params_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9.]+", "", str(s or "").lower())


def material_matches(expected: str, actual: str) -> bool:
    e, a = norm(expected), norm(actual)
    if not e or not a:
        return False

    canonical = [
        ("316l", "1.4404"),
        ("tecapeekpvx", "tecapeekpvx"),
        ("nitronic60", "nitronic60"),
        ("430fr", "430fr"),
        ("inconel625", "alloy625"),
    ]
    for x, y in canonical:
        e_has = x in e or y in e
        a_has = x in a or y in a
        if e_has and a_has:
            return True
    return e in a or a in e


def find_part_master(master: dict, part_no: str):
    parts = master.get("parts") or {}
    if part_no in parts:
        return parts[part_no]
    for key, value in parts.items():
        if str(key).startswith(part_no):
            return value
        if isinstance(value, dict):
            fname = str(value.get("filename") or "")
            if fname.startswith(part_no):
                return value
    return None


def iter_nodes(nodes):
    for n in nodes:
        yield n
        yield from iter_nodes(n.get("subfeatures", []))


def dimensions_by_name(payload):
    out = {}
    for feat in iter_nodes(
        payload.get("feature_tree", {}).get("features", [])
    ):
        for d in feat.get("dimensions", []):
            for key in (d.get("name"), d.get("full_name")):
                if key:
                    out.setdefault(str(key).split("@")[0], d)
    return out


def check_freshness(payload):
    src = payload.get("source_file") or {}
    raw_path = str(src.get("path") or "")
    expected = src.get("sha256")

    if not raw_path:
        return None, "snapshot has no native CAD path"

    p = Path(raw_path)
    if not p.exists():
        # Expected on GitHub Actions/Linux because native CAD is intentionally
        # outside Git.
        return None, f"native CAD not available on this machine: {raw_path}"

    if not expected:
        return False, "snapshot lacks native SLDPRT SHA-256"

    return (
        (sha256_file(p) == expected),
        "native CAD SHA-256 matches snapshot"
        if sha256_file(p) == expected
        else "snapshot stale: native SLDPRT changed after export",
    )


def apply(rep, part, severity, msg):
    if str(severity).upper() == "WARN":
        rep.warn(part, msg)
    else:
        rep.fail(part, msg)


def audit_one(path, contract, master, params, rep):
    payload = load_json(path)
    title = str(payload.get("document", {}).get("title") or path.stem)
    part = re.sub(r"\.SLDPRT$", "", title, flags=re.I)
    rep.checked += 1

    if payload.get("export_status") not in ("PASS", "PASS_WITH_WARNINGS"):
        rep.fail(part, f"export_status={payload.get('export_status')!r}")

    fresh, msg = check_freshness(payload)
    if fresh is False:
        rep.fail(part, msg)
    elif fresh is None:
        rep.warn(part, msg)

    if contract.get("single_solid"):
        n = payload.get("body", {}).get("solid_body_count")
        if n is None:
            rep.fail(part, "solid body count was not read")
        elif n != 1:
            rep.fail(part, f"solid bodies={n}; expected 1")

    if contract.get("check_material", True):
        pm = find_part_master(master, str(contract.get("part_no") or ""))
        expected = pm.get("material") if isinstance(pm, dict) else None
        actual = payload.get("material", {}).get("name")

        if not expected:
            rep.warn(part, "master has no material for this part")
        elif not actual:
            rep.fail(part, f"material not assigned; expected {expected}")
        elif not material_matches(str(expected), str(actual)):
            rep.fail(part, f"material={actual!r}; expected {expected!r}")

    eq_rule = contract.get("equation_link") or {}
    if eq_rule.get("required"):
        sev = eq_rule.get("severity", "ERROR")
        eq = payload.get("equations") or {}
        linked = eq.get("link_to_file")
        fpath = str(eq.get("file_path") or "")
        hint = str(eq_rule.get("file_hint") or "")

        if linked is None:
            apply(rep, part, sev, "equation link state could not be read")
        elif not linked:
            apply(rep, part, sev, "external equation file is not linked")
        elif hint and hint.lower() not in fpath.lower():
            apply(
                rep, part, sev,
                f"unexpected equation file: {fpath!r}; expected {hint!r}",
            )

    have = dimensions_by_name(payload)
    for dname, rule in (contract.get("dimensions") or {}).items():
        sev = rule.get("severity", "ERROR")
        pname = str(rule.get("param") or "")
        tol = float(rule.get("tol_mm", 0.005))

        if not hasattr(params, pname):
            apply(rep, part, sev, f"params has no {pname!r}")
            continue

        expected = getattr(params, pname)
        if not isinstance(expected, (int, float)):
            apply(rep, part, sev, f"{pname} is not numeric: {expected!r}")
            continue

        d = have.get(dname)
        if d is None:
            apply(
                rep, part, sev,
                f"stable dimension {dname!r} not found",
            )
            continue

        actual = d.get("value_mm")
        if not isinstance(actual, (int, float)):
            apply(
                rep, part, sev,
                f"{dname!r} has no value_mm; raw={d.get('system_value_SI')!r}",
            )
            continue

        delta = abs(float(actual) - float(expected))
        if delta > tol:
            apply(
                rep, part, sev,
                f"{dname}={actual:.6f} mm, expected {expected:.6f} "
                f"from {pname}; delta={delta:.6f}",
            )

    if contract.get("dimensions"):
        n = int(payload.get("summary", {}).get("dimension_count") or 0)
        if n == 0:
            rep.fail(
                part,
                "zero dimensions captured although a dimension contract exists",
            )


def main(argv):
    contracts = load_json(CONTRACT_FILE)
    params_path = REPO_ROOT / contracts["params_file"]
    master_path = REPO_ROOT / contracts["master_file"]

    params = load_params(params_path)
    master = load_json(master_path)

    rep = Report()

    if len(argv) > 1:
        files = [Path(a) for a in argv[1:]]
        for p in files:
            key = p.stem
            contract = contracts.get("parts", {}).get(key)
            if contract is None:
                rep.warn(key, "no contract; skipped")
                continue
            audit_one(p, contract, master, params, rep)
    else:
        for key, contract in contracts.get("parts", {}).items():
            p = SNAPSHOT_DIR / f"{key}.json"
            if not p.exists():
                apply(
                    rep, key,
                    contract.get("snapshot_severity", "ERROR"),
                    f"snapshot missing: {p}",
                )
                continue
            audit_one(p, contract, master, params, rep)

    print("=" * 60)
    print("K01 FAST ENGINEERING AUDIT")
    print("=" * 60)
    print(f"Checked snapshots: {rep.checked}")

    for part, msg in rep.warnings:
        print(f"WARN  {part}: {msg}")
    for part, msg in rep.failures:
        print(f"FAIL  {part}: {msg}")

    if rep.failures:
        print("FAIL")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
