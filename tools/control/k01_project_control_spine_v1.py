from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re
from pathlib import Path

REPO_DEFAULT = Path(r"D:\BreshevEngineering\marvilon-k01")
CAD_DEFAULT = Path(r"D:\Marvilon\K01")
LOCAL_DEFAULT = Path(r"D:\BreshevEngineering\K01_local")

OUTS = {
    "workspace": Path("reports/control/K01_WORKSPACE_ORDER_CURRENT.json"),
    "cad": Path("reports/control/K01_CAD_ASSEMBLY_STATUS_CURRENT.json"),
    "mbd": Path("reports/control/K01_MBD_DIMXPERT_STATUS_CURRENT.json"),
    "bom": Path("reports/control/K01_BOM_RELEASE_STATUS_CURRENT.json"),
    "analysis": Path("reports/control/K01_ANALYSIS_REGISTER_CURRENT.json"),
    "drawing": Path("reports/control/K01_DRAWING_LANE_STATUS_CURRENT.json"),
    "master": Path("reports/control/K01_PROJECT_CONTROL_SPINE_CURRENT.json"),
    "master_md": Path("reports/control/K01_PROJECT_CONTROL_SPINE_CURRENT.md"),
    "center": Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json"),
}

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return default

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def sha256(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def file_rec(p: Path):
    return {
        "path": str(p),
        "exists": p.is_file(),
        "size_bytes": p.stat().st_size if p.is_file() else None,
        "sha256": sha256(p) if p.is_file() else None,
    }

def scan_files(root: Path, patterns):
    out = []
    if not root.exists():
        return out
    for pat in patterns:
        for p in root.rglob(pat):
            if p.is_file():
                out.append(p)
    # stable dedupe
    seen = set()
    rows = []
    for p in sorted(out, key=lambda x: str(x).lower()):
        s = str(p).lower()
        if s in seen: continue
        seen.add(s); rows.append(p)
    return rows

def load_first_existing(repo: Path, rels):
    for rel in rels:
        p = repo / rel
        if p.is_file():
            return rel, read_json(p, {})
    return None, {}

def recursive_find(obj, keys):
    hits = []
    def walk(x, path="$"):
        if isinstance(x, dict):
            for k,v in x.items():
                p = path + "." + str(k)
                if str(k).lower() in keys:
                    hits.append((p, v))
                walk(v, p)
        elif isinstance(x, list):
            for i,v in enumerate(x):
                walk(v, f"{path}[{i}]")
    walk(obj)
    return hits

def build_workspace(repo: Path, cad: Path, local: Path):
    expected_repo = ["control","tools","reports","docs","tests","cad_api"]
    expected_cad = [
        "cad/parts","cad/assemblies","cad/drawings/current","cad/drawings/candidates",
        "cad/candidates","cad/archive","cad/promotion_staging"
    ]
    root_files = []
    if repo.exists():
        root_files = [p.name for p in repo.iterdir() if p.is_file()]
    cad_root_files = []
    cadroot = cad / "cad"
    if cadroot.exists():
        cad_root_files = [p.name for p in cadroot.iterdir() if p.is_file()]
    return {
        "schema": "k01.workspace_order.current.v1",
        "generated_utc": now(),
        "status": "PASS_SCAN_COMPLETE",
        "roots": {
            "engineering_repo": str(repo),
            "cad_workspace": str(cad),
            "local_workbench": str(local),
        },
        "zones": {
            "engineering_authority": str(repo / "control"),
            "generated_evidence": str(repo / "reports"),
            "automation_tools": str(repo / "tools"),
            "solidworks_api": str(repo / "cad_api"),
            "canonical_parts": str(cad / "cad/parts"),
            "canonical_assembly": str(cad / "cad/assemblies"),
            "drawing_current": str(cad / "cad/drawings/current"),
            "drawing_candidates_history": str(cad / "cad/drawings/candidates"),
            "cad_candidates": str(cad / "cad/candidates"),
            "cad_archive": str(cad / "cad/archive"),
            "local_current_patchset": str(local / "CURRENT_20260917"),
            "local_backups": str(local / "backups"),
            "local_incoming": str(local / "incoming"),
            "local_retired": str(local / "retired"),
        },
        "expected_repo_dirs": {x: (repo/x).is_dir() for x in expected_repo},
        "expected_cad_dirs": {x: (cad/x).is_dir() for x in expected_cad},
        "repo_root_files": root_files,
        "cad_root_files": cad_root_files,
        "rules": [
            "Do not bulk-move engineering files automatically.",
            "CURRENT is resolved only by authority, never by newest timestamp.",
            "Drawing candidates are history/evidence until Drawing Control publishes them.",
            "K01_local is patch/workbench only; no engineering authority originates there.",
            "Broad Git cleanup remains release debt unless artifact identity becomes unsafe.",
        ],
    }

def build_cad(repo: Path, cad: Path):
    assembly = cad / r"cad\assemblies\K01-A-001_Calibration_Module.SLDASM"
    evidence_candidates = [
        repo / "reports/control/K01_BASELINE_02C_POST_PROMOTION_QA_CURRENT.json",
        repo / "reports/cad/current/K01_A001_POST_PROMOTION_QA_CURRENT.json",
        repo / "reports/cad/current/K01_GATE04E_NATIVE_SNAPSHOT_CURRENT.json",
        repo / "reports/cad/current/K01_GATE04B_DATUM_C_ASSEMBLY_QA.json",
    ]
    ev = []
    best = {}
    for p in evidence_candidates:
        if p.is_file():
            obj = read_json(p,{}) or {}
            ev.append({"path": str(p.relative_to(repo)), "sha256": sha256(p)})
            if not best: best = obj
    hits = recursive_find(best, {"component_count","modeled_occurrences","mate_errors","active_mate_errors","unexpected_interference_total","semantic_warnings"})
    return {
        "schema": "k01.cad_assembly_status.current.v1",
        "generated_utc": now(),
        "canonical_assembly": file_rec(assembly),
        "expected_identity": {
            "assembly_id": "K01-A-001",
            "baseline": "02C",
            "expected_modeled_occurrences": 14,
        },
        "observed_from_best_available_report": [{"path":p,"value":v} for p,v in hits],
        "evidence": ev,
        "status": "CONTROLLED_BASELINE__FRESH_NATIVE_QA_NOT_RUN_BY_THIS_TOOL",
        "mutation": "NONE",
        "rules": [
            "Canonical assembly must never reference candidate paths after promotion.",
            "Any CAD write requires Technical Filter + exact target + rollback + mutation lease.",
            "Assembly verification must include occurrence count, mates, candidate references, interference and configuration/effectivity.",
        ],
    }

def build_mbd(repo: Path):
    files = scan_files(repo, ["*MBD*CURRENT*.json","*DIMXPERT*CURRENT*.json","*MBD*.json","*DIMXPERT*.json"])
    rows = []
    for p in files[:50]:
        obj = read_json(p,{})
        rows.append({
            "path": p.relative_to(repo).as_posix(),
            "sha256": sha256(p),
            "status": (obj or {}).get("status") if isinstance(obj,dict) else None,
        })
    return {
        "schema": "k01.mbd_dimxpert_status.current.v1",
        "generated_utc": now(),
        "status": "INVENTORIED__NO_NATIVE_AUTHORING",
        "policy": "Product Characteristic -> native CAD semantic feature -> DimXpert/PMI -> tolerance analysis -> drawing -> inspection traceability.",
        "current_records": rows,
        "P004": {
            "state": "WAITING_PRODUCT_DEFINITION",
            "known_nominals": ["OD 6.54 mm","BORE 5.055 mm","LENGTH 8.00 mm"],
            "release_rule": "Do not author DimXpert/PMI tolerance values until P004 Product Definition characteristics are RELEASED/DERIVED with authority.",
        },
        "known_historical_mapping_risk": [
            "P003 seat ID 6.60 and P004 OD 6.54 were previously NOT_FOUND by dimension-name discovery.",
            "DimXpert import into drawing is not a trusted automatic release path.",
            "Geometry-signature ambiguity must fail closed.",
        ],
        "mutation": "NONE",
    }

def find_bom_sources(repo: Path):
    pats = ["*EBOM*CURRENT*.json","*MBOM*CURRENT*.json","*BOM*CURRENT*.json","*BOM*.csv","*BOM*.json"]
    return scan_files(repo, pats)

def build_bom(repo: Path):
    sources = find_bom_sources(repo)
    rows = []
    for p in sources[:60]:
        obj = read_json(p, None) if p.suffix.lower()==".json" else None
        status = obj.get("status") if isinstance(obj,dict) else None
        rows.append({"path": p.relative_to(repo).as_posix(), "sha256": sha256(p), "status": status})
    return {
        "schema": "k01.bom_release_status.current.v1",
        "generated_utc": now(),
        "status": "HOLD_RELEASE_BOM__STRUCTURE_CONTROLLED",
        "structural_baseline": {
            "canonical_assembly": "K01-A-001",
            "expected_modeled_occurrences": 14,
            "P017_expected_qty": 1,
        },
        "authority_rule": "CAD occurrence tree + product/parts registry + manufacturing process definitions. Generated BOM is never hand-edited engineering authority.",
        "known_open_release_rows": [
            "B001 supplier/lot magnetic data",
            "P002/P004 production TECAPEEK PVX material/process",
            "P013 retention qualification",
            "P014 material/temper/fatigue/process",
            "P015 production PPS grade + winding/leads/electrical",
            "P016 Long Run compatibility/process",
            "P017 native material assignment/effectivity",
            "J2 seal purchased-item identity/CoC",
            "J2 M2.5 clamp screw purchased-item identity/locking process",
            "release revisions/effectivity",
        ],
        "states_kept_separate": [
            "BOM_MODEL","EBOM_ARTIFACT","EBOM_VERIFY","MBOM_MODEL","MBOM_ARTIFACT","MBOM_VERIFY"
        ],
        "discovered_sources": rows,
        "mutation": "NONE",
    }

def analysis_entry(domain, status, trust, evidence, decision, limitations):
    return {
        "domain": domain, "status": status, "trust_level": trust,
        "evidence": evidence, "decision_supported": decision, "limitations": limitations
    }

def build_analysis(repo: Path):
    femm = repo / "reports/femm/final_candidate_20260916_v3/K01_FEMM_FINAL_CANDIDATE_SUMMARY_V3.json"
    femm_obj = read_json(femm,{}) if femm.is_file() else {}
    femm_ev = [femm.relative_to(repo).as_posix()] if femm.is_file() else []
    swsim = [p.relative_to(repo).as_posix() for p in scan_files(repo, ["*P007*PRESSURE*.json","*P007*BUCKLING*.json","*T07*.json"])[:20]]
    cfd = [p.relative_to(repo).as_posix() for p in scan_files(repo, ["*CFD*CURRENT*.json","*FLOW*CURRENT*.json","*OUT*MID*IN*.json"])[:20]]
    tol = [p.relative_to(repo).as_posix() for p in scan_files(repo, ["*TOL*CURRENT*.json","*CHAIN*CURRENT*.json","*TOLERANCE*.json"])[:30]]
    entries = [
        analysis_entry("FEMM",
            "NUMERICAL_DESIGN_CANDIDATE_PASS__PHYSICAL_QUALIFICATION_OPEN" if femm.is_file() else "EVIDENCE_NOT_RESOLVED",
            "ENGINEERING",
            femm_ev,
            "350-turn magnetic design candidate is numerically screened; do not claim physical qualification.",
            ["B001 actual lot magnetic data open","P015 production winding/thermal definition open","bench correlation open"]),
        analysis_entry("Flow/CFD","CONSOLIDATION_OPEN","ENGINEERING",cfd,
            "Existing CFD evidence retained; final OUT/MID/IN authority must be consolidated, not broadly rerun.",
            ["Verify exact IN=10 mm case identity before final envelope publication"]),
        analysis_entry("Structural/SWSIM","SCREENING_OR_ENGINEERING_EVIDENCE_EXISTS","ENGINEERING",swsim,
            "P007 pressure/buckling evidence retained with limitations.",
            ["Do not promote screening to physical qualification"]),
        analysis_entry("Tolerance/Variation","ACTIVE_FOR_NEXT_PD","ENGINEERING",tol,
            "Worst-case functional chains must precede release tolerances.",
            ["P004 guide-clearance requirement band still unresolved","PEEK temperature sensitivity must be included"]),
        analysis_entry("Pressure/Vacuum/Containment","P007_DEFINITION_CLOSED__L8_TEST_OPEN","ENGINEERING",
            ["control/decisions/EDR-035_J2_MEDIA_SEAL_LEAK_RELEASE.json"],
            "C12 quantitative assembled-J2 acceptance is defined; physical leak qualification remains L8.",
            ["Assembled J2 acceptance is not a bare P007 part leak test"]),
        analysis_entry("EBOM","HOLD_RELEASE","ENGINEERING",[], "Structure exists; release closure remains open.", []),
        analysis_entry("MBOM","HOLD_RELEASE","ENGINEERING",[], "Manufacturing transformations/process items remain open.", []),
        analysis_entry("Inspection/Metrology","PARTIAL","ENGINEERING",[], "P007 inspection definition exists; project-wide inspection closure remains open.", []),
        analysis_entry("Configuration/Release","HOLD","ENGINEERING",[], "Release baseline not yet clean/pinned/reproducible.", []),
    ]
    return {
        "schema": "k01.analysis_register.current.v1",
        "generated_utc": now(),
        "status": "CONTROLLED_DOMAIN_LEDGER",
        "required_fields": ["QUESTION","INPUT_AUTHORITY","LOAD_CASE","METHOD/SOLVER","EXPECTED_RESPONSE","TRUST_LEVEL","RESULT","INTERPRETATION","DECISION_SUPPORTED","LIMITATIONS","STALE_TRIGGERS"],
        "domains": entries,
        "rule": "Every calculation/analysis result is reported with authority, method, trust level, limitations, decision supported and stale triggers. PASS_WITH_LIMITATIONS never collapses to PASS.",
        "mutation": "NONE",
    }

def build_drawing(repo: Path):
    dc = repo / "reports/control/K01_DRAWING_CONTROL_CURRENT.json"
    dcobj = read_json(dc,{}) if dc.is_file() else {}
    current = ((dcobj.get("drawings") or {}).get("K01-D-006") or {}) if isinstance(dcobj,dict) else {}
    author = repo / "reports/drawing/current/K01-D-006_V2_REFINED_AUTHORING_CURRENT.json"
    author_obj = read_json(author,{}) if author.is_file() else {}
    return {
        "schema": "k01.drawing_lane_status.current.v1",
        "generated_utc": now(),
        "status": "DRAWING_AUTHORING_SEPARATED_FROM_MAIN_ENGINEERING_LANE",
        "live_runtime_authority": "reports/control/K01_DRAWING_CONTROL_CURRENT.json",
        "D006": {
            "current_from_drawing_control": current,
            "visual_reference": {
                "name": "K01-D-006_GOLDEN_VISUAL_APPROVED.PDF",
                "role": "USER_APPROVED_PRESENTATION_REFERENCE",
                "authority_limit": "Visual/layout reference only; does not itself replace Drawing Control or upstream Product Definition.",
            },
            "api_refined_candidate": {
                "source_report": author.relative_to(repo).as_posix() if author.is_file() else None,
                "candidate_root": author_obj.get("candidate_root") if isinstance(author_obj,dict) else None,
                "disposition": "REJECTED_PRESENTATION__HISTORY_ONLY",
                "reason": "User explicitly rejected further uncontrolled drawing generation in this engineering branch; API presentation quality is not accepted.",
            },
            "next_native_work": "ONLY_IN_MARVILON_DRAWING_BRANCH_UNDER_USER_CONTROL",
        },
        "main_branch_policy": [
            "No new drawing generation in main engineering lane.",
            "No automatic D8 mutation from this lane.",
            "No Drawing System redesign here.",
            "Before any future drawing authoring, Product Definition must already be READY.",
            "Main lane may verify semantic traceability after a user-controlled drawing candidate is supplied.",
        ],
        "mutation": "NONE",
    }

def render_md(master):
    ws=master["workspace"]; cad=master["cad"]; mbd=master["mbd"]; bom=master["bom"]; ana=master["analysis"]; dr=master["drawing"]
    lines = [
        "# K01 PROJECT CONTROL SPINE",
        "",
        f"Generated UTC: `{master['generated_utc']}`",
        "",
        "## Control invariant",
        "",
        "`Need/Function -> Requirements/Interfaces -> Architecture/Decision -> Nominal Design/Materials -> Analysis -> Tolerances/Processes -> Product Definition -> Drawing -> Verification -> Physical Qualification -> Released TPD -> R01`",
        "",
        "## Roots",
        f"- Engineering repo: `{ws['roots']['engineering_repo']}`",
        f"- CAD workspace: `{ws['roots']['cad_workspace']}`",
        f"- Local workbench: `{ws['roots']['local_workbench']}`",
        "",
        "## 3D / assembly",
        f"- Canonical A001 exists: **{cad['canonical_assembly']['exists']}**",
        f"- Current SHA: `{cad['canonical_assembly']['sha256']}`",
        f"- Expected modeled occurrences: **{cad['expected_identity']['expected_modeled_occurrences']}**",
        f"- Status: **{cad['status']}**",
        "",
        "## DimXpert / MBD",
        f"- Status: **{mbd['status']}**",
        f"- P004: **{mbd['P004']['state']}** — no PMI tolerance authoring before Product Definition.",
        "",
        "## BOM",
        f"- Status: **{bom['status']}**",
        f"- Structural target: A001 / 14 modeled occurrences / P017 x1",
        f"- Open release rows: **{len(bom['known_open_release_rows'])}**",
        "",
        "## Drawings",
        f"- Status: **{dr['status']}**",
        f"- D006 API refined candidate: **REJECTED_PRESENTATION / HISTORY ONLY**",
        f"- Native drawing work: **Marvilon drawing branch under user control**",
        "",
        "## Analysis ledger",
    ]
    for x in ana["domains"]:
        lines.append(f"- **{x['domain']}** — {x['status']} / trust={x['trust_level']}")
    lines += [
        "",
        "## Current main-engineering preparation",
        "- D006 native drawing work is separated from this lane.",
        "- Next Product Definition prepared here: **K01-P-004 Front Guide Bushing**.",
        "- No D004 authoring is allowed until P004 Product Definition is READY.",
        "",
        "## Project release remains HOLD",
        "- EBOM/MBOM release not closed.",
        "- L8 physical/process qualification remains open where declared.",
        "- Remaining Product Definitions/drawings remain open.",
        "- Git/configuration clean release snapshot remains a later release dependency.",
        "- SW2026 migration + full chamber integration remain after controlled module freeze.",
    ]
    return "\n".join(lines) + "\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(REPO_DEFAULT))
    ap.add_argument("--cad-root",default=str(CAD_DEFAULT))
    ap.add_argument("--local-root",default=str(LOCAL_DEFAULT))
    args=ap.parse_args()
    repo=Path(args.repo_root); cad=Path(args.cad_root); local=Path(args.local_root)
    if not repo.is_dir(): raise SystemExit("HOLD: engineering repo missing")
    if not cad.is_dir(): raise SystemExit("HOLD: CAD workspace missing")

    workspace=build_workspace(repo,cad,local)
    cadst=build_cad(repo,cad)
    mbd=build_mbd(repo)
    bom=build_bom(repo)
    analysis=build_analysis(repo)
    drawing=build_drawing(repo)

    master={
        "schema":"k01.project_control_spine.current.v1",
        "generated_utc":now(),
        "status":"PASS_CONTROL_SPINE_REFRESHED",
        "engineering_chain":[
            "STAKEHOLDER_NEED_FUNCTION","CONTROLLED_REQUIREMENTS_INTERFACES",
            "ARCHITECTURE_ALTERNATIVES_TRADE_DECISION","NOMINAL_DESIGN_MATERIALS",
            "ENGINEERING_ANALYSES","JOINTS_SEALS_TOLERANCES_MANUFACTURING",
            "CANDIDATE_PRODUCT_DEFINITION","DRAWING_PMI_MBD_EBOM_MBOM",
            "VERIFICATION","PHYSICAL_QUALIFICATION","RELEASED_TPD","PRODUCT_BASELINE_R01"
        ],
        "workspace":workspace,"cad":cadst,"mbd":mbd,"bom":bom,"analysis":analysis,"drawing":drawing,
        "governance":{
            "wip_limit":1,
            "product_over_evidence_over_automation":True,
            "technical_filter_before_mutation":True,
            "manual_controlled_default_for_one_off_cad_drawing":True,
            "center_is_projection_only":True,
            "open_partial_never_auto_pass":True,
        }
    }
    for key,obj in [("workspace",workspace),("cad",cadst),("mbd",mbd),("bom",bom),("analysis",analysis),("drawing",drawing)]:
        write_json(repo/OUTS[key],obj)
    write_json(repo/OUTS["master"],master)
    (repo/OUTS["master_md"]).write_text(render_md(master),encoding="utf-8")

    center={
        "schema":"k01.center.master_feed.current.v1",
        "generated_utc":now(),
        "authority":"PROJECTION_ONLY",
        "source":"reports/control/K01_PROJECT_CONTROL_SPINE_CURRENT.json",
        "home":{
            "product_structure":{"assembly":"K01-A-001","expected_modeled_occurrences":14},
            "drawing_lane":"SEPARATE_USER_CONTROLLED_MARVILON_BRANCH",
            "bom_status":bom["status"],
            "analysis_domains":[{"domain":x["domain"],"status":x["status"],"trust":x["trust_level"]} for x in analysis["domains"]],
            "next_product_definition_prepared":"K01-P-004",
        },
        "program_board":[
            "D006 user-controlled drawing finalization",
            "P004 Product Definition closure",
            "remaining own-part Product Definitions",
            "magnetic physical qualification",
            "EBOM/MBOM release closure",
            "remaining drawings",
            "manufacturing/inspection capability and FAI",
            "verification/qualification evidence",
            "Git/configuration release checkpoint",
            "SW2026 migration + full chamber integration -> Released TPD -> R01",
        ]
    }
    write_json(repo/OUTS["center"],center)

    print("PASS: K01 project control spine refreshed.")
    print("MASTER:",repo/OUTS["master_md"])
    print("WORKSPACE:",repo/OUTS["workspace"])
    print("CAD:",repo/OUTS["cad"])
    print("MBD/DIMXPERT:",repo/OUTS["mbd"])
    print("BOM:",repo/OUTS["bom"])
    print("ANALYSIS:",repo/OUTS["analysis"])
    print("DRAWING:",repo/OUTS["drawing"])
    print("CENTER FEED:",repo/OUTS["center"])
    print("NO NATIVE CAD/DRAWING FILE WAS MODIFIED.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
