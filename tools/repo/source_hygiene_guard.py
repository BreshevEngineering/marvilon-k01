from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
from datetime import datetime, timezone

def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def tree_sig(p):
    fs=sorted(x for x in p.rglob("*") if x.is_file()); h=hashlib.sha256()
    for f in fs:
        rel=f.relative_to(p).as_posix(); h.update(rel.encode()); h.update(b"\0"); h.update(sha(f).encode()); h.update(b"\n")
    return len(fs),h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default="."); ap.add_argument("--write-report",action="store_true"); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    reg=load(root/"control/repo/K01_SUPERSEDED_SOURCE_REGISTRY_CURRENT.json"); issues=[]
    for u in reg.get("move_units",[]):
        src=root/u["source_path"]; dst=root/u["archive_path"]
        if src.exists(): issues.append({"rule":"SUPERSEDED_ACTIVE_PATH_PRESENT","path":u["source_path"]})
        if not dst.exists(): issues.append({"rule":"DECLARED_ARCHIVE_ITEM_MISSING","path":u["archive_path"]}); continue
        if u["kind"]=="FILE":
            if u.get("source_sha256") and sha(dst)!=u["source_sha256"]: issues.append({"rule":"ARCHIVE_HASH_MISMATCH","path":u["archive_path"]})
        else:
            cnt,sig=tree_sig(dst)
            if u.get("source_file_count") is not None and cnt!=u["source_file_count"]: issues.append({"rule":"ARCHIVE_COUNT_MISMATCH","path":u["archive_path"],"got":cnt})
            if u.get("source_tree_sha256") and sig!=u["source_tree_sha256"]: issues.append({"rule":"ARCHIVE_TREE_HASH_MISMATCH","path":u["archive_path"]})
    pc=load(root/"control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json"); c10=next((x for x in pc.get("characteristics",[]) if x.get("id")=="C10"),{})
    if c10.get("status")!="CONTROLLED_PROCESS_ARCHITECTURE": issues.append({"rule":"C10_ACTIVE_SOURCE_NOT_CONTROLLED","status":c10.get("status")})
    ctx=load(root/"control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json").get("characteristics",{}).get("C10",{})
    if "WELD_SYMBOL" in json.dumps(ctx,ensure_ascii=False).upper() and "DO_NOT_AUTHOR_WELD_SYMBOL" not in json.dumps(ctx,ensure_ascii=False).upper(): issues.append({"rule":"C10_CONTEXT_STILL_WELD_CARRIER"})
    cp=load(root/"control/product_definition/K01_J2_CONTAINMENT_CLOSURE_PLAN.json"); txt=json.dumps(cp,ensure_ascii=False).lower()
    if "weld vs adhesive applicability" in txt: issues.append({"rule":"LEGACY_PROCESS_AMBIGUITY_ACTIVE"})
    ai=load(root/"control/drawings/K01_D006_AUTHORING_INPUT.json")
    if ai.get("authoring_authorized") is not False: issues.append({"rule":"FULL_DRAWING_NOT_FAIL_CLOSED"})
    for x in ai.get("release_blockers",[]):
        if "weld-or-adhesive" in str(x).lower(): issues.append({"rule":"STALE_C10_DRAWING_BLOCKER","value":x})
    mfg=load(root/"control/manufacturing/K01_P007_MANUFACTURING_FEASIBILITY_CURRENT.json")
    if mfg.get("selection")!="MFG-P007-MONOLITHIC": issues.append({"rule":"P007_MONOLITHIC_ROUTE_NOT_SELECTED","selection":mfg.get("selection")})
    drawreg=load(root/"control/drawings/K01_DRAWING_CHARACTERISTICS_v1_7.json")
    d006=next((x for x in drawreg.get("drawings",[]) if x.get("drawing_no")=="K01-D-006"),{})
    for ch in d006.get("characteristics",[]):
        if ch.get("id")=="K01-D006-WELD": issues.append({"rule":"K01-D006-WELD_ACTIVE_REGISTRY","value":ch})
    edr029=root/"control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json"
    if edr029.is_file():
        defs=load(root/"control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json")
        for cid in ("C07","C08","C11"):
            c=next((x for x in defs.get("characteristics",[]) if x.get("id")==cid),{})
            if c.get("definition_state")!="CONTROLLED" or c.get("release_blocking") is not False:
                issues.append({"rule":"EDR029_NOT_PROPAGATED_TO_ACTIVE_DEFINITION","characteristic":cid,"state":c.get("definition_state"),"release_blocking":c.get("release_blocking")})
    fam=load(root/"control/drawings/K01_P007_DRAWING_FAMILY_BINDING_CURRENT.json")
    if "release drawing must hide unauthorized claims" in json.dumps(fam,ensure_ascii=False).lower(): issues.append({"rule":"STALE_C01_C02_ONLY_DRAWING_DOCTRINE"})
    status="PASS_SOURCE_HYGIENE" if not issues else "HOLD_SOURCE_HYGIENE"
    rep={"schema":"k01.source_hygiene.current.v1","generated_utc":datetime.now(timezone.utc).isoformat(),"status":status,"issues":issues,"archive_root":"archive/","rule":"Superseded/history sources are never active authority and never default AI-handoff context."}
    if a.write_report:
        out=root/"reports/control/K01_SOURCE_HYGIENE_CURRENT.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print("REPORT:",out)
    print("SOURCE_HYGIENE:",status,"issues=",len(issues))
    for i in issues: print("HOLD:",json.dumps(i,ensure_ascii=False))
    return 0 if not issues else 2
if __name__=="__main__": raise SystemExit(main())
