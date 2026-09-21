from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

try:
    from medtas_v16_common import graph_path
except Exception:  # pragma: no cover
    graph_path = None


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def runtime_probe(root: Path, rec: dict) -> dict:
    probe = rec.get("runtime_probe") or {}
    if not probe:
        return {"state": "NOT_APPLICABLE"}
    p = root / probe.get("path", "")
    kind = probe.get("kind")
    if not p.exists():
        return {"state": "MISSING_PROBE", "path": str(p)}
    if kind == "calculix_preflight":
        d = load_json(p)
        ready = bool(d.get("ready_to_run"))
        return {
            "state": "READY" if ready else "BLOCKED_RUNTIME",
            "ready_to_run": ready,
            "calculix_executable": d.get("calculix_executable"),
            "gmsh_executable": d.get("gmsh_executable"),
            "blocking": d.get("blocking", []),
        }
    if kind in ("bom_verify", "mbom_verify"):
        d = load_json(p)
        verdict = str(d.get("verdict") or d.get("status") or "UNKNOWN")
        return {
            "state": "READY" if verdict == "PASS" else "HOLD_RUNTIME",
            "verdict": verdict,
            "issues": d.get("issues", []),
            "warnings": d.get("warnings", []),
        }
    if kind == "femm_verification":
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        pass_lim = "PASS_WITH_LIMITATIONS" in text
        force_unverified = "Absolute force quantification remains NOT VERIFIED" in text or "absolute force extraction is **NOT VERIFIED**" in text
        return {
            "state": "PASS_WITH_LIMITATIONS" if pass_lim else "EVIDENCE_PRESENT",
            "absolute_force_verified": not force_unverified,
            "note": "FEMM field/automation evidence exists; force extraction is not release evidence." if force_unverified else "See verification report.",
        }
    return {"state": "PROBE_PRESENT", "path": str(p)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.repo_root).resolve()

    reg_path = root / "control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json"
    if not reg_path.exists():
        raise RuntimeError(f"engineering domain registry missing: {reg_path}")
    registry = load_json(reg_path)

    gp = graph_path(root) if graph_path else None
    if not gp:
        raise RuntimeError("authoritative engineering_build_graph missing from Authority Map")
    gp = Path(gp)
    graph = load_json(gp)
    graph_nodes = {n.get("node_id") for n in graph.get("nodes", [])}

    results = []
    blocking = []
    declared_gaps = []
    runtime_holds = []
    release_blocking_domains = []

    for rec in registry.get("domains", []):
        rid = rec["id"]
        mode = rec.get("mode")
        missing_paths = [p for p in rec.get("authority_paths", []) if not (root / p).exists()]
        missing_nodes = [n for n in rec.get("graph_nodes", []) if n not in graph_nodes]
        gaps = list(rec.get("declared_gaps", []))
        probe = runtime_probe(root, rec)

        issues = []
        if missing_paths:
            issues += [f"MISSING_AUTHORITY:{p}" for p in missing_paths]
        if missing_nodes:
            issues += [f"MISSING_GRAPH_NODE:{n}" for n in missing_nodes]

        if mode == "GRAPH_REQUIRED":
            state = "COVERED"
            if issues:
                state = "BLOCKED_COVERAGE"
                blocking.extend([f"{rid}:{x}" for x in issues])
            elif gaps:
                state = "COVERED_WITH_DECLARED_GAPS"
                declared_gaps.extend([f"{rid}:{g}" for g in gaps])
        elif mode == "DECLARED_GAP_ALLOWED":
            if not gaps or not rec.get("gap_action"):
                state = "BLOCKED_UNDECLARED_GAP"
                blocking.append(f"{rid}:DECLARED_GAP_ALLOWED_REQUIRES_GAP_AND_ACTION")
            else:
                state = "DECLARED_OPEN_GAP"
                declared_gaps.extend([f"{rid}:{g}" for g in gaps])
                # Missing graph nodes are expected in this mode; authority paths, if declared, are still mandatory.
                if missing_paths:
                    state = "BLOCKED_COVERAGE"
                    blocking.extend([f"{rid}:{x}" for x in issues if x.startswith("MISSING_AUTHORITY")])
        else:
            state = "BLOCKED_BAD_MODE"
            blocking.append(f"{rid}:UNKNOWN_MODE:{mode}")

        if probe.get("state") in {"BLOCKED_RUNTIME", "HOLD_RUNTIME", "PASS_WITH_LIMITATIONS", "MISSING_PROBE"}:
            runtime_holds.append({"domain": rid, "probe": probe})

        rel = rec.get("release_relevance")
        if rel in {"BLOCKS_RELEASE", "BLOCKS_IF_APPLICABLE"} and (state != "COVERED" or probe.get("state") in {"BLOCKED_RUNTIME", "HOLD_RUNTIME", "PASS_WITH_LIMITATIONS", "MISSING_PROBE"}):
            release_blocking_domains.append(rid)

        results.append({
            "id": rid,
            "title": rec.get("title"),
            "mode": mode,
            "release_relevance": rel,
            "coverage_state": state,
            "missing_authority_paths": missing_paths,
            "missing_graph_nodes": missing_nodes,
            "declared_gaps": gaps,
            "gap_action": rec.get("gap_action"),
            "runtime_probe": probe,
            "status_note": rec.get("status_note"),
        })

    if blocking:
        status = "HOLD_ENGINEERING_SYSTEM_COVERAGE"
        rc = 3
    elif declared_gaps or runtime_holds:
        status = "PASS_ENGINEERING_SYSTEM_COVERAGE__DECLARED_GAPS"
        rc = 0
    else:
        status = "PASS_ENGINEERING_SYSTEM_COVERAGE"
        rc = 0

    report = {
        "schema": "k01.engineering_system_coverage.current.v1",
        "generated_utc": now_utc(),
        "status": status,
        "registry": str(reg_path.relative_to(root)).replace("\\", "/"),
        "graph": str(gp.relative_to(root)).replace("\\", "/"),
        "summary": {
            "domains": len(results),
            "coverage_blockers": len(blocking),
            "declared_gap_items": len(declared_gaps),
            "runtime_hold_or_limitation_domains": len(runtime_holds),
            "release_relevant_open_domains": sorted(set(release_blocking_domains)),
        },
        "blocking": blocking,
        "declared_gaps": declared_gaps,
        "runtime_holds": runtime_holds,
        "domains": results,
        "rules": registry.get("principles", []),
    }
    out_json = root / "reports/control/K01_ENGINEERING_SYSTEM_COVERAGE_CURRENT.json"
    dump_json(out_json, report)

    md = [
        "# K01 Engineering System Coverage — Current",
        "",
        f"**Status:** `{status}`",
        f"**Graph:** `{report['graph']}`",
        "",
        "| Domain | Coverage | Runtime | Release relevance |",
        "|---|---|---|---|",
    ]
    for r in results:
        md.append(f"| {r['id']} | {r['coverage_state']} | {r['runtime_probe'].get('state')} | {r['release_relevance']} |")
    if blocking:
        md += ["", "## Coverage blockers"] + [f"- {x}" for x in blocking]
    if declared_gaps:
        md += ["", "## Declared engineering gaps"] + [f"- {x}" for x in declared_gaps]
    if runtime_holds:
        md += ["", "## Runtime holds / limitations"]
        for x in runtime_holds:
            md.append(f"- {x['domain']}: `{x['probe'].get('state')}`")
    out_md = root / "reports/control/K01_ENGINEERING_SYSTEM_COVERAGE_CURRENT.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"STATUS: {status}")
    print(f"DOMAINS: {len(results)}")
    print(f"COVERAGE_BLOCKERS: {len(blocking)}")
    print(f"DECLARED_GAP_ITEMS: {len(declared_gaps)}")
    print(f"RUNTIME_HOLD_OR_LIMITATION_DOMAINS: {len(runtime_holds)}")
    print("RELEASE_RELEVANT_OPEN_DOMAINS: " + ",".join(sorted(set(release_blocking_domains))))
    print(f"REPORT: {out_json}")
    print(f"MD: {out_md}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
