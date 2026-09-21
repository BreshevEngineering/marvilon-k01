#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--capability", required=True)
    ap.add_argument("--allow-new-implementation", action="store_true")
    args=ap.parse_args()
    root=Path(args.repo_root).resolve()
    reg=load(root/"cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json")
    hits=[x for x in reg.get("capabilities",[]) if x.get("id")==args.capability]
    if not hits:
        print("STATUS: HOLD_CAPABILITY_NOT_REGISTERED")
        return 2
    cap=hits[0]
    print("CAPABILITY:",cap["id"])
    print("REGISTERED STATUS:",cap.get("status"))
    print("PRIMARY SOURCE:",cap.get("primary_source"))
    if str(cap.get("status","")).startswith("PROVEN"):
        print("STATUS: PASS_USE_PROVEN_IMPLEMENTATION")
        if args.allow_new_implementation:
            print("WARNING: override requested; document capability gap before coding")
        return 0
    if cap.get("status")=="EXPERIMENTAL_DO_NOT_USE_AS_PRIMARY":
        print("STATUS: HOLD_EXPERIMENTAL_NOT_PRIMARY")
        return 2
    print("STATUS: HOLD_CAPABILITY_NOT_PROVEN")
    return 2

if __name__=="__main__":
    raise SystemExit(main())
