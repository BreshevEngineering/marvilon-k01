from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8-sig"))

def test_v15_files_and_policy():
    for rel in [
        "RUN_K01_D3_VERIFY_P007_V15.cmd","RUN_K01_D7_QA_D006_V15.cmd",
        "tools/medtas/drawing_d3_verify_v15.py","tools/medtas/drawing_d7_semantic_qa_v15.py",
        "cad_api/solidworks_2018_proven/current/K01_D3_D7_V15/K01P007D3VerifyV15.cs",
        "cad_api/solidworks_2018_proven/current/K01_D3_D7_V15/K01D006D7VerifyV15.cs"]:
        assert (ROOT/rel).is_file(), rel
    p=load("control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json")
    assert p["schema"].endswith("v15")
    assert p["v15_first_exemplar_assurance"]["d3"]["release_pending"]==["L3_PERTURB_RESTORE"]
    active=set(p["v15_first_exemplar_assurance"]["d7"]["active_checks"])
    assert {"DQA-001","DQA-010","DQA-017","DQA-020"} <= active

def test_graph_v25_has_d3_d7_and_is_acyclic():
    g=load("control/medtas/v1/graph/K01_engineering_build_graph_v2_5.json")
    nodes={n["node_id"]:n for n in g["nodes"]}
    assert "K01.DRAWING.D006.D3.AUTHORING_VERIFY" in nodes
    assert "K01.DRAWING.D006.D7.SEMANTIC_QA" in nodes
    d7={x["node_id"] for x in nodes["K01.DRAWING.D006.D7.SEMANTIC_QA"]["contract"]["inputs"]}
    assert "K01.DRAWING.D006.D3.AUTHORING_VERIFY" in d7
    assert "K01.DRAWING.D006.EXEMPLAR.WORKSPACE" in d7
    # Kahn topological test over declared graph edges.
    indeg={k:0 for k in nodes}; out={k:[] for k in nodes}
    for k,n in nodes.items():
        for inp in n.get("contract",{}).get("inputs",[]):
            src=inp["node_id"]
            assert src in nodes, (k,src)
            indeg[k]+=1; out[src].append(k)
    q=[k for k,v in indeg.items() if v==0]; seen=0
    while q:
        x=q.pop(); seen+=1
        for y in out[x]:
            indeg[y]-=1
            if indeg[y]==0:q.append(y)
    assert seen==len(nodes)

def test_authority_and_next_actions_point_to_v15():
    a=load("control/project/K01_AUTHORITY_MAP_CURRENT.json")
    assert a["control_families"]["engineering_build_graph"]["authority"].endswith(("K01_engineering_build_graph_v2_5.json","K01_engineering_build_graph_v2_6.json"))
    n=load("control/project/K01_NEXT_ACTIONS_CURRENT.json")
    assert n["current_stage"] in {"K01_D3_D7_EXEMPLAR_ASSURANCE_V15","K01_ASSURANCE_COHERENCE_V16_BEFORE_D3","K01_ASSURANCE_RECOVERY_V17_THEN_D3"}
    assert n["drawing_assurance_v15"]["d3_command"]=="RUN_K01_D3_VERIFY_P007_V15.cmd"
    assert n["drawing_assurance_v15"]["d7_command"]=="RUN_K01_D7_QA_D006_V15.cmd"

def test_domain_registry_keeps_project_wide_scope():
    r=load("control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json")
    domains={d["id"]:d for d in r["domains"]}
    for x in ["DRAWING_D1_D9","STRUCTURAL_FEA","MAGNETIC_FEMM","FLOW_CFD","THERMAL","PRESSURE_VACUUM_CONTAINMENT","EBOM","MBOM"]:
        assert x in domains
    dn=set(domains["DRAWING_D1_D9"]["graph_nodes"])
    assert "K01.DRAWING.D006.D3.AUTHORING_VERIFY" in dn
    assert "K01.DRAWING.D006.D7.SEMANTIC_QA" in dn
    gaps=" ".join(domains["DRAWING_D1_D9"].get("declared_gaps",[]))
    assert "L3" in gaps and "D8" in gaps and "D9" in gaps

def test_no_false_release_claim():
    n=load("control/project/K01_NEXT_ACTIONS_CURRENT.json")
    txt=json.dumps(n,ensure_ascii=False)
    assert "full release-native D3" in n["current_blocker"] or "Manufacturing release remains HOLD" in n["current_blocker"] or "HOLD_ASSURANCE_COHERENCE" in n["current_blocker"]
    p=load("control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json")
    assert "not a manufacturing-release waiver" in p["v15_first_exemplar_assurance"]["scope"]
