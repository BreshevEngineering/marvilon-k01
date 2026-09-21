from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import medtas_state_engine_v1_1 as eng
from medtas_v16_common import graph_path


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        if default is not None:
            return default
        raise


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(s: str) -> str:
    return str(s or "").replace("\\", "/").lstrip("./")


def load_control(root: Path):
    registry = load(root / "control/project/K01_ENGINEERING_RELATIONSHIP_REGISTRY_v1.json")
    policy = load(root / "control/project/K01_CHANGE_IMPACT_POLICY_v1.json")
    gp = graph_path(root)
    if gp is None:
        raise RuntimeError("engineering_build_graph authority missing")
    graph = load(gp)
    return registry, policy, Path(gp), graph


def graph_index(graph: dict):
    nodes = {n["node_id"]: n for n in graph["nodes"]}
    children = defaultdict(list)
    parents = defaultdict(list)
    for n in graph["nodes"]:
        nid = n["node_id"]
        for edge in n.get("contract", {}).get("inputs", []):
            up = edge["node_id"]
            children[up].append(nid)
            parents[nid].append(up)
    return nodes, children, parents


def infer_entities_from_paths(registry: dict, paths: Iterable[str]) -> list[str]:
    hits = []
    for p in [norm(x) for x in paths]:
        pl = p.lower()
        for entity, rec in registry.get("entities", {}).items():
            for pat in rec.get("path_patterns", []):
                if fnmatch.fnmatch(pl, norm(pat).lower()):
                    hits.append(entity)
                    break
    return sorted(set(hits))


def entity_seeds(registry: dict, entity: str, domain: str) -> list[str]:
    rec = registry.get("entities", {}).get(entity)
    if not rec:
        raise KeyError(f"Unknown engineering entity: {entity}")
    mapping = rec.get("graph_seeds_by_domain", {})
    if domain in mapping:
        return list(mapping[domain])
    # Fail closed. We do not silently reinterpret an unknown change domain as generic geometry.
    raise KeyError(f"Entity {entity} has no controlled seed mapping for change domain {domain}")


def counterpart_reviews(registry: dict, policy: dict, entities: Iterable[str], domain: str) -> list[dict]:
    if not policy.get("change_domains", {}).get(domain, {}).get("cross_entity_review", False):
        return []
    ent = registry.get("entities", {})
    interfaces = set()
    original = set(entities)
    for eid in original:
        rec = ent.get(eid, {})
        if rec.get("type") == "interface":
            interfaces.add(eid)
        interfaces.update(rec.get("interfaces", []))
    reviews = []
    seen = set()
    for iid in sorted(interfaces):
        irec = ent.get(iid, {})
        for participant in irec.get("participants", []):
            key = (iid, participant)
            if key in seen:
                continue
            seen.add(key)
            reviews.append({
                "interface": iid,
                "entity": participant,
                "status": "COUNTERPART_REVIEW_REQUIRED",
                "reason": f"shared interface {iid} affected by {domain}",
                "is_changed_entity": participant in original,
            })
    return reviews


def descendants(graph: dict, seeds: Iterable[str]):
    nodes, children, parents = graph_index(graph)
    unknown = sorted(set(seeds) - set(nodes))
    if unknown:
        raise KeyError("Impact seed nodes absent from authoritative graph: " + ", ".join(unknown))
    dist = {s: 0 for s in seeds}
    paths = {s: [s] for s in seeds}
    q = deque(sorted(seeds))
    while q:
        cur = q.popleft()
        for child in sorted(children.get(cur, [])):
            nd = dist[cur] + 1
            if child not in dist or nd < dist[child]:
                dist[child] = nd
                paths[child] = paths[cur] + [child]
                q.append(child)
    return nodes, parents, dist, paths


def node_action(node: dict, policy: dict) -> str:
    producer_mode = node.get("producer", {}).get("mode", "source")
    if node.get("kind") == "verification" or node.get("contract", {}).get("verification_policy"):
        return "REVERIFY"
    return policy.get("node_actions", {}).get(producer_mode, "REVIEW")


def build_plan(root: Path, entities: list[str], domain: str, changed_nodes: list[str] | None = None, changed_paths: list[str] | None = None):
    registry, policy, gp, graph = load_control(root)
    inferred = infer_entities_from_paths(registry, changed_paths or [])
    effective_entities = sorted(set(entities or []) | set(inferred))
    if not effective_entities and not changed_nodes:
        raise RuntimeError("No controlled entity or graph node was supplied/inferred for impact analysis")

    seeds = set(changed_nodes or [])
    seed_reasons = []
    for entity in effective_entities:
        mapped = entity_seeds(registry, entity, domain)
        for node_id in mapped:
            seeds.add(node_id)
            seed_reasons.append({"entity": entity, "domain": domain, "node_id": node_id})

    nodes, parents, dist, paths = descendants(graph, sorted(seeds))
    records = eng.load_record_store(root / "reports/medtas/records/current")
    verifs = eng.load_record_store(root / "reports/medtas/verifications/current")
    derived = eng.evaluate_graph(graph, root, records, verifs)
    topo = eng.topological(nodes)
    impacted = [nid for nid in topo if nid in dist]

    plan = []
    for nid in impacted:
        cur = derived[nid]
        plan.append({
            "node_id": nid,
            "distance": dist[nid],
            "path": paths[nid],
            "current_state": cur.get("state"),
            "current_state_hash": cur.get("state_hash"),
            "current_artifact_hash": cur.get("artifact_hash"),
            "action": node_action(nodes[nid], policy),
            "producer_mode": nodes[nid].get("producer", {}).get("mode"),
            "kind": nodes[nid].get("kind"),
            "title": nodes[nid].get("title"),
        })

    reviews = counterpart_reviews(registry, policy, effective_entities, domain)
    release_impact = any(
        (nodes[nid].get("lifecycle", {}).get("criticality") in {"required_for_release", "required_for_gate"})
        or "RELEASE" in nid
        or "DRAWING" in nid
        or "INSPECTION" in nid
        for nid in impacted
    )
    return {
        "schema": "k01.change_impact.current.v9",
        "generated_utc": now_utc(),
        "status": "PASS_CHANGE_IMPACT_COMPUTED",
        "graph_authority": str(gp.relative_to(root)).replace("\\", "/"),
        "entities": effective_entities,
        "domain": domain,
        "changed_paths": [norm(x) for x in (changed_paths or [])],
        "explicit_changed_nodes": changed_nodes or [],
        "seed_nodes": sorted(seeds),
        "seed_reasons": seed_reasons,
        "counterpart_reviews": reviews,
        "affected_node_count": len(impacted),
        "release_path_affected": release_impact,
        "rebuild_order": plan,
        "rules": {
            "automatic_invalidation": True,
            "automatic_cross_part_mutation": False,
            "topological_rebuild_only": True,
            "open_values_never_autofilled": True,
        },
    }


def scan_current(root: Path, target: str | None = None):
    registry, policy, gp, graph = load_control(root)
    records = eng.load_record_store(root / "reports/medtas/records/current")
    verifs = eng.load_record_store(root / "reports/medtas/verifications/current")
    derived = eng.evaluate_graph(graph, root, records, verifs)
    nodes, children, parents = graph_index(graph)
    topo = eng.topological(nodes)
    scope = set(topo)
    if target:
        if target not in nodes:
            raise KeyError(f"Target node absent from authoritative graph: {target}")
        scope = {target}
        q = deque([target])
        while q:
            cur = q.popleft()
            for up in parents.get(cur, []):
                if up not in scope:
                    scope.add(up)
                    q.append(up)
    actionable_states = {"STALE", "DRIFT", "FRESH_UNVERIFIED", "MISSING", "BLOCKED", "HOLD"}
    items = []
    for nid in topo:
        if nid not in scope:
            continue
        state = derived[nid].get("state")
        if state not in actionable_states:
            continue
        items.append({
            "node_id": nid,
            "state": state,
            "action": policy.get("state_policy", {}).get(state, "REVIEW"),
            "reasons": derived[nid].get("reasons", []),
            "title": derived[nid].get("title"),
            "kind": derived[nid].get("kind"),
        })
    return {
        "schema": "k01.rebuild_plan.current.v9",
        "generated_utc": now_utc(),
        "status": "PASS_REBUILD_PLAN_COMPUTED",
        "graph_authority": str(gp.relative_to(root)).replace("\\", "/"),
        "target": target,
        "scope_node_count": len(scope),
        "actionable_count": len(items),
        "rebuild_order": items,
        "rule": "This is a plan, not permission to mutate engineering sources. Producers/gates remain authoritative for execution."
    }


def render_md(report: dict) -> str:
    out = ["# K01 change impact / rebuild plan", "", f"**Status:** `{report.get('status')}`", ""]
    if "domain" in report:
        out += [f"**Entities:** `{', '.join(report.get('entities', []))}`  ", f"**Domain:** `{report.get('domain')}`  ", f"**Affected nodes:** `{report.get('affected_node_count')}`  ", f"**Release path affected:** `{report.get('release_path_affected')}`", ""]
        if report.get("counterpart_reviews"):
            out += ["## Counterpart review", ""]
            for x in report["counterpart_reviews"]:
                out.append(f"- `{x['entity']}` via `{x['interface']}` — **{x['status']}**")
            out.append("")
    out += ["## Ordered actions", "", "| # | Node | State | Action | Reason/path |", "|---:|---|---|---|---|"]
    for i, x in enumerate(report.get("rebuild_order", []), 1):
        reason = " → ".join(x.get("path", [])) if x.get("path") else "; ".join(x.get("reasons", []))
        out.append(f"| {i} | `{x['node_id']}` | {x.get('current_state', x.get('state'))} | {x.get('action')} | {reason.replace('|','/')} |")
    return "\n".join(out) + "\n"


def write_current(root: Path, report: dict):
    out = root / "reports/control/K01_CHANGE_IMPACT_CURRENT.json"
    md = root / "reports/control/K01_CHANGE_IMPACT_CURRENT.md"
    dump(out, report)
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(render_md(report), encoding="utf-8")
    return out, md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=r"D:\BreshevEngineering\marvilon-k01")
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("what-if")
    w.add_argument("--entity", action="append", default=[])
    w.add_argument("--domain", required=True)
    w.add_argument("--node", action="append", default=[])
    w.add_argument("--path", action="append", default=[])

    s = sub.add_parser("scan-current")
    s.add_argument("--target")

    args = ap.parse_args()
    root = Path(str(args.repo_root).strip().strip('"')).resolve()
    if args.cmd == "what-if":
        report = build_plan(root, args.entity, args.domain, args.node, args.path)
    else:
        report = scan_current(root, args.target)
    out, md = write_current(root, report)
    print("STATUS:", report["status"])
    if "affected_node_count" in report:
        print("ENTITIES:", ",".join(report.get("entities", [])))
        print("DOMAIN:", report.get("domain"))
        print("SEEDS:", ",".join(report.get("seed_nodes", [])))
        print("AFFECTED_NODES:", report.get("affected_node_count"))
        print("COUNTERPART_REVIEWS:", len(report.get("counterpart_reviews", [])))
        print("RELEASE_PATH_AFFECTED:", report.get("release_path_affected"))
    else:
        print("ACTIONABLE_NODES:", report.get("actionable_count"))
    print("REPORT:", out)
    print("MD:", md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
