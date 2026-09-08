#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Dict, Any, List, Tuple

TERMINAL_BLOCKERS={"MISSING","BLOCKED","HOLD"}

def _canonical_numbers(obj: Any):
    if isinstance(obj,float):
        if abs(obj)<1e-15: obj=0.0
        return format(obj,'.12g')
    if isinstance(obj,list): return [_canonical_numbers(x) for x in obj]
    if isinstance(obj,dict): return {k:_canonical_numbers(obj[k]) for k in sorted(obj)}
    return obj

def canonical_bytes(obj: Any)->bytes:
    # State material is already semantically curated. Here we only remove float-representation noise and sort keys.
    return json.dumps(_canonical_numbers(obj),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def sha256_obj(obj: Any)->str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()

def sha256_file(path: Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def load_record_store(path: Path|None)->Dict[str,dict]:
    out={}
    if not path or not path.exists(): return out
    for p in sorted(path.glob("*.json")):
        try:
            x=load_json(p)
            if x.get("node_id"): out[x["node_id"]]=x
        except Exception:
            pass
    return out

def output_manifest(node:dict,repo_root:Path)->Tuple[List[dict],List[str]]:
    manifest=[]; missing=[]
    for out in node["contract"].get("outputs",[]):
        if out.get("hash_mode")=="none": continue
        ptxt=out.get("path")
        if not ptxt:
            if out.get("required",True): missing.append(out["output_id"]+":UNBOUND")
            continue
        p=(repo_root/ptxt).resolve()
        if not p.exists():
            if out.get("required",True): missing.append(out["output_id"]+":MISSING")
            continue
        if p.is_file():
            manifest.append({"output_id":out["output_id"],"path":ptxt.replace("\\","/"),"size":p.stat().st_size,"sha256":sha256_file(p)})
        else:
            for f in sorted(x for x in p.rglob("*") if x.is_file()):
                manifest.append({"output_id":out["output_id"],"path":f.relative_to(repo_root).as_posix(),"size":f.stat().st_size,"sha256":sha256_file(f)})
    return sorted(manifest,key=lambda x:(x["output_id"],x["path"])),missing

def artifact_root(manifest:List[dict])->str|None:
    return sha256_obj(manifest) if manifest else None

def toolchain_identity(node:dict)->List[dict]:
    hp=node["contract"]["hash_policy"]
    if not hp.get("include_toolchain_identity",True): return []
    keep=[]
    for t in node["contract"].get("toolchain",[]):
        if not t.get("identity_affects_state",True): continue
        keep.append({k:t[k] for k in sorted(t) if k!="identity_affects_state"})
    return keep

def own_state_payload(node:dict,repo_root:Path)->Tuple[Any,List[str]]:
    src=node["contract"].get("state_payload_source",{"mode":"inline"})
    mode=src.get("mode","inline")
    if mode=="inline": return node["contract"].get("semantic_payload",{}),[]
    if mode=="json_file":
        ptxt=src.get("path")
        if not ptxt: return None,["state_payload:UNBOUND"]
        p=(repo_root/ptxt).resolve()
        if not p.exists(): return None,["state_payload:MISSING"]
        try: return load_json(p),[]
        except Exception as e: return None,["state_payload:INVALID_JSON:"+str(e)]
    return None,["state_payload:UNKNOWN_MODE:"+str(mode)]

def topological(nodes:Dict[str,dict])->List[str]:
    indeg={k:0 for k in nodes}; children={k:[] for k in nodes}
    for nid,n in nodes.items():
        for e in n["contract"].get("inputs",[]):
            up=e["node_id"]
            if up not in nodes:
                if e.get("required",True): raise KeyError("%s: missing input node %s"%(nid,up))
                continue
            indeg[nid]+=1; children[up].append(nid)
    q=sorted(k for k,v in indeg.items() if v==0); order=[]
    while q:
        x=q.pop(0); order.append(x)
        for c in sorted(children[x]):
            indeg[c]-=1
            if indeg[c]==0: q.append(c); q.sort()
    if len(order)!=len(nodes): raise ValueError("Engineering Build Graph contains a cycle")
    return order

def evaluate_graph(graph:dict,repo_root:Path,records:Dict[str,dict]|None=None,verifications:Dict[str,dict]|None=None)->Dict[str,dict]:
    records=records or {}; verifications=verifications or {}
    nodes={n["node_id"]:n for n in graph["nodes"]}; derived={}
    for nid in topological(nodes):
        n=nodes[nid]; reasons=[]; blocked=False; fps=[]
        for e in sorted(n["contract"].get("inputs",[]),key=lambda x:(x["node_id"],x["role"])):
            up=e["node_id"]
            if up not in derived:
                if e.get("required",True): blocked=True; reasons.append("required input unavailable: "+up)
                continue
            u=derived[up]
            if e.get("required",True) and u["state"] in TERMINAL_BLOCKERS:
                blocked=True; reasons.append("blocked by %s:%s"%(up,u["state"]))
            fp={"node_id":up,"role":e["role"],"consume":e["consume"]}
            if e["consume"] in ("state","both"): fp["state_hash"]=u.get("state_hash")
            if e["consume"] in ("artifact","both"): fp["artifact_hash"]=u.get("artifact_hash")
            fps.append(fp)
        own,own_errors=own_state_payload(n,repo_root); reasons.extend(own_errors)
        state_material={
            "schema_version":n["schema_version"],"node_id":nid,"kind":n["kind"],
            "contract_semantics":n["contract"].get("semantic_payload",{}),
            "own_state_payload":own,"inputs":fps,"toolchain":toolchain_identity(n),
            "hash_policy":n["contract"]["hash_policy"]
        }
        current_state_hash=sha256_obj(state_material)
        manifest,missing_outputs=output_manifest(n,repo_root); current_artifact_hash=artifact_root(manifest)
        br=n.get("build_record") or records.get(nid); vr=n.get("verification_record") or verifications.get(nid)
        if n.get("lifecycle",{}).get("superseded_by"):
            state="SUPERSEDED"; reasons.append("node superseded")
        elif blocked:
            state="BLOCKED"
        elif own_errors:
            state="MISSING"
        elif n["producer"]["mode"]=="source" and not n["contract"].get("outputs"):
            state="PASS"
        elif missing_outputs:
            state="MISSING"; reasons.extend(missing_outputs)
        elif n["producer"]["mode"] in ("derived","external") and not br:
            state="MISSING"; reasons.append("no build_record")
        else:
            built_hash=(br or {}).get("built_state_hash") or (br or {}).get("built_from_state_hash")
            if br and built_hash!=current_state_hash:
                state="STALE"; reasons.append("recorded STATE_HASH != current STATE_HASH")
            elif br and current_artifact_hash!=(br or {}).get("artifact_hash"):
                state="DRIFT"; reasons.append("current ARTIFACT_HASH != recorded ARTIFACT_HASH")
            elif n["kind"] in {"verification","baseline"} or n["contract"].get("verification_policy"):
                if not vr or vr.get("verified_state_hash")!=current_state_hash or vr.get("verified_artifact_hash")!=current_artifact_hash:
                    state="FRESH_UNVERIFIED"; reasons.append("verification missing or not bound to current hashes")
                else: state=vr.get("verdict","HOLD")
            else:
                lim=[]
                if isinstance(own,dict): lim=own.get("limitations",[]) or []
                state="PASS_WITH_LIMITATIONS" if lim else "PASS"
        derived[nid]={
            "state_hash":current_state_hash,"artifact_hash":current_artifact_hash,"state":state,
            "reasons":reasons,"inputs":fps,"artifact_manifest":manifest,
            "title":n.get("title"),"kind":n.get("kind")
        }
    return derived

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--graph",required=True); ap.add_argument("--repo-root",default="."); ap.add_argument("--records-dir"); ap.add_argument("--verifications-dir"); ap.add_argument("--out")
    a=ap.parse_args(); root=Path(a.repo_root).resolve(); graph=load_json(Path(a.graph))
    d=evaluate_graph(graph,root,load_record_store(Path(a.records_dir) if a.records_dir else None),load_record_store(Path(a.verifications_dir) if a.verifications_dir else None))
    payload={"schema_version":"MEDTAS-DERIVED-STATE-1.1","project":graph.get("project"),"nodes":d}
    txt=json.dumps(payload,ensure_ascii=False,indent=2)
    if a.out:
        p=Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt,encoding="utf-8")
    else: print(txt)
if __name__=="__main__": main()
