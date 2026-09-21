#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

EXTERNAL_STEP13 = Path(r"D:\BreshevEngineering\Additional\k01_step13_integrated\payload\tools\engineering\run_p007_pmi_step13.py")
EXTERNAL_STEP13_CORE = Path(r"D:\BreshevEngineering\Additional\k01_step13_integrated\payload\cad_api\p007_pmi\K01P007PmiStep13.cs")

REPO_ASSETS = [
    "control/environment/K01_SOLIDWORKS_2018_RUNTIME.json",
    "cad_api/README_RUN_FIRST.txt",
    "cad_api/medtas/K01CadSemanticA001.cs",
    "cad_api/medtas/K01MbdDimXpertPart.cs",
    "cad_api/medtas/K01DrawingPackGenerator.cs",
    "cad_api/bridge/K01SolidWorksLiveBridge.cs",
    "cad_api/gates/gate04b/K01Gate04B_DatumC_AssemblyQA.cs",
    "cad_api/gates/gate04b/K01Baseline02C_ReferenceRewrite.cs",
    "cad_api/gates/gate04b/K01Baseline02C_StableAssemblyQA.cs",
    "cad_api/medtas/K01P007PersistentRefRebind.cs",
    "cad_api/medtas/K01P007DimXpertPhaseA.cs",
    "control/product_definition/K01_P007_PMI_WRITE_EVIDENCE.json",
    "reports/cad/p007_pmi_step13/K01_P007_PMI_STEP13_CURRENT.json",
    "reports/engineering/K01_STEP13_INTEGRATED_CURRENT.log",
    "reports/control/K01_P007_CANONICAL_PERSISTENT_REBIND_CURRENT.json",
    "reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json",
]

SYSTEM_ASSETS = [
    "cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_RULES_v1.md",
    "cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json",
    "tools/medtas/sw_api_proven_freeze_v1.py",
    "tools/medtas/sw_api_preflight_v1.py",
    "tools/medtas/p007_pmi_proven_step13_current_v1.py",
    "cad_api/solidworks_2018_proven/RUN_P007_PMI_PROVEN_CURRENT.cmd",
]

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def copy_asset(src: Path, dst: Path, role: str, rows: list[dict]):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    rows.append({
        "role": role,
        "source": str(src),
        "snapshot": str(dst),
        "sha256": sha256(dst),
        "size": dst.stat().st_size
    })

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    args=ap.parse_args()
    root=Path(args.repo_root).resolve()
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    base=root/"cad_api"/"solidworks_2018_proven"/"snapshots"/stamp
    rows=[]; missing=[]

    for rel in REPO_ASSETS + SYSTEM_ASSETS:
        src=root/rel
        if src.is_file():
            copy_asset(src, base/"repo"/rel, "REPO_PROVEN_OR_CONTROL", rows)
        else:
            missing.append(str(src))

    if EXTERNAL_STEP13.is_file():
        copy_asset(EXTERNAL_STEP13, base/"external"/"step13"/EXTERNAL_STEP13.name, "PROVEN_EXTERNAL_STEP13_WRITER", rows)
    else:
        missing.append(str(EXTERNAL_STEP13))

    if EXTERNAL_STEP13_CORE.is_file():
        copy_asset(EXTERNAL_STEP13_CORE, base/"external"/"step13"/EXTERNAL_STEP13_CORE.name, "PROVEN_EXTERNAL_STEP13_CSHARP_CORE", rows)
    else:
        missing.append(str(EXTERNAL_STEP13_CORE))

    manifest={
        "schema":"k01.solidworks_api.proven_manifest.v1",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "snapshot_id":stamp,
        "status":"PASS_PROVEN_API_FROZEN" if (EXTERNAL_STEP13.is_file() and EXTERNAL_STEP13_CORE.is_file()) else "HOLD_PROVEN_STEP13_TRANSITIVE_SOURCE_MISSING",
        "copy_only":True,
        "no_moves":True,
        "snapshot_root":str(base),
        "assets":rows,
        "missing":missing,
        "primary_proven_capability":"P007_DIMXPERT_WRITE_C02_C05",
        "primary_proven_writer":str(EXTERNAL_STEP13),
        "rule":"Do not start a parallel implementation for a capability with a frozen PROVEN implementation."
    }

    report=root/"reports"/"control"/"K01_SOLIDWORKS_PROVEN_MANIFEST_CURRENT.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    bundle=root/"reports"/"control"/"K01_SOLIDWORKS_PROVEN_BUNDLE_CURRENT.zip"
    with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as z:
        z.write(report, "K01_SOLIDWORKS_PROVEN_MANIFEST_CURRENT.json")
        for row in rows:
            p=Path(row["snapshot"])
            z.write(p, str(p.relative_to(base.parent.parent.parent.parent)).replace("\\","/") if base.parent.parent.parent.parent in p.parents else p.name)

    print("STATUS:",manifest["status"])
    print("SNAPSHOT:",base)
    print("ASSETS:",len(rows))
    print("MISSING:",len(missing))
    for x in missing:
        print(" -",x)
    print("MANIFEST:",report)
    print("BUNDLE:",bundle)
    return 0 if manifest["status"].startswith("PASS") else 2

if __name__=="__main__":
    raise SystemExit(main())
