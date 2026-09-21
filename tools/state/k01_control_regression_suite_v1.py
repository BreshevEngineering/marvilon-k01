from __future__ import annotations
from pathlib import Path
import argparse,json,re,zipfile,hashlib,datetime

DEFAULT=Path(r"D:\BreshevEngineering\marvilon-k01")

def rd(p):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return None
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(DEFAULT))
    a=ap.parse_args();repo=Path(a.repo_root).resolve()
    results=[]
    def rec(id_,status,detail,evidence=None):
        results.append({"id":id_,"status":status,"detail":detail,"evidence":evidence})

    # CF-001 duplicate active EDR IDs
    by={}
    dr=repo/"control/decisions"
    if dr.is_dir():
        for p in dr.glob("EDR-*.json"):
            d=rd(p)
            if not isinstance(d,dict):continue
            x=d.get("decision_id") or d.get("edr_id") or d.get("id")
            if x:by.setdefault(str(x).upper(),[]).append(p.relative_to(repo).as_posix())
    dup={k:v for k,v in by.items() if len(v)>1}
    rec("CF-001","PASS" if not dup else "HOLD","duplicate active decision IDs",dup)

    # CF-002 use permanent engineering-value guard if present
    p=repo/"reports/control/K01_ENGINEERING_VALUE_COHERENCE_CURRENT.json";d=rd(p)
    st=(d or {}).get("status")
    rec("CF-002","PASS" if st=="PASS_ENGINEERING_VALUE_COHERENCE" else "HOLD_OR_NOT_PROVEN",
        "controlled engineering value coherence",{"path":str(p),"status":st})

    # CF-003 structured provenance: current P004 calc must have inputs if it is current
    p=repo/"reports/engineering/K01_P004_CALCULATION_REGISTER_CURRENT.json";d=rd(p)
    c3={}
    if isinstance(d,dict):
        c3=next((x for x in d.get("calculations",[]) if isinstance(x,dict) and x.get("id")=="P004-CALC-003"),{})
    ok=bool(c3.get("inputs")) and bool(c3.get("authority"))
    rec("CF-003","PASS" if ok else "HOLD_OR_NOT_PROVEN","structured calculation provenance",{"path":str(p),"calc3":c3})

    # CF-004 rollback safety: only static presence; deep execution is deliberately not run every session
    rollback=list(repo.glob("**/*ROLLBACK*.cmd"))+list(repo.glob("**/*rollback*.py"))
    rec("CF-004","PASS_STATIC" if rollback else "HOLD_OR_NOT_PROVEN","rollback implementation present; execution test belongs to DEEP_ASSURANCE",
        [x.relative_to(repo).as_posix() for x in rollback[:20]])

    # CF-005 epoch idempotence cannot be proven read-only; require explicit deep result if present
    rec("CF-005","DEEP_ASSURANCE_REQUIRED","State Epoch idempotence is not re-run in FAST regression mode.")

    # CF-006 GitHub freshness report existence
    gh=repo/"reports/git/K01_GITHUB_REMOTE_HEALTH_CURRENT.json"
    rec("CF-006","PASS_EVIDENCE_PRESENT" if gh.is_file() else "HOLD_OR_NOT_PROVEN","fresh remote check evidence must come from fetch/ls-remote",str(gh))

    # CF-007 staged index is not automatically engineering HOLD -- policy regression
    rec("CF-007","PASS_POLICY","staged Git index is CONFIGURATION_HOLD unless it invalidates active-workpack identity")

    # CF-008/009 handoff integrity
    z=repo/"reports/control/K01_AI_HANDOFF_CURRENT.zip"
    if not z.is_file():
        rec("CF-008","HOLD_OR_NOT_PROVEN","current handoff archive missing",str(z))
        rec("CF-009","HOLD_OR_NOT_PROVEN","reported artifact availability cannot be assumed",str(z))
    else:
        try:
            with zipfile.ZipFile(z,"r") as zz:
                bad=zz.testzip();names=zz.namelist()
            req=any("START_HERE" in n.upper() for n in names) and any("CONTROL_PANEL" in n.upper() for n in names)
            rec("CF-008","PASS" if bad is None and req else "HOLD","required handoff members/archive integrity",
                {"sha256":sha(z),"member_count":len(names),"bad":bad,"required_signals":req})
            rec("CF-009","PASS" if z.stat().st_size>0 and bad is None else "HOLD","artifact physically exists/readable",
                {"size":z.stat().st_size,"sha256":sha(z)})
        except Exception as e:
            rec("CF-008","HOLD","handoff unreadable",repr(e));rec("CF-009","HOLD","artifact unreadable",repr(e))

    # CF-010 generated panel explicitly declares non-authority
    panel=repo/"reports/control/K01_ENGINEERING_CONTROL_PANEL_CURRENT.md"
    txt=panel.read_text(encoding="utf-8-sig",errors="replace") if panel.is_file() else ""
    nonauth=("not an engineering authority" in txt.lower()) or ("navigation/summary" in txt.lower())
    rec("CF-010","PASS" if nonauth else "HOLD_OR_NOT_PROVEN","Control Panel must self-identify as projection/non-authority",str(panel))

    # CF-011 typed hold policy installed
    hp=repo/"control/system/K01_CONTROL_SYSTEM_RC1_CURRENT.json"
    hd=rd(hp)
    typed=isinstance(hd,dict) and "hold_types" in hd and "hold_contract" in hd
    rec("CF-011","PASS" if typed else "HOLD","typed HOLD model installed",str(hp))

    # CF-012 projection authority rule installed
    rule=(hd or {}).get("authority_rule","")
    rec("CF-012","PASS" if "never engineering authority" in rule.lower() else "HOLD","generated projection cannot become authority",rule)

    # CF-013 SW operating standard
    sw=repo/"cad_api/solidworks_2018_proven/K01_SOLIDWORKS_API_OPERATING_STANDARD_CURRENT.txt"
    rec("CF-013","PASS_EVIDENCE_PRESENT" if sw.is_file() else "HOLD_OR_NOT_PROVEN","persistent SW2018 API operating standard",str(sw))

    # CF-014 source registry
    sr=repo/"control/evidence/K01_SOURCE_REGISTRY_v2.json"
    rec("CF-014","PASS_EVIDENCE_PRESENT" if sr.is_file() else "HOLD","source registry exists; applicability binding remains per decision",str(sr))

    # CF-015 PASS scope policy installed
    prohibited=(hd or {}).get("prohibited_patterns",[])
    scoped=any("pass" in str(x).lower() and "scope" in str(x).lower() for x in prohibited)
    rec("CF-015","PASS" if scoped else "HOLD","PASS scope policy installed")

    report={
      "schema":"k01.control_regression_suite.current.v1",
      "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "mode":"FAST_REGRESSION",
      "results":results,
      "summary":{
        "pass_like":sum(1 for x in results if x["status"].startswith("PASS")),
        "hold_like":sum(1 for x in results if x["status"].startswith("HOLD")),
        "deep_required":sum(1 for x in results if x["status"]=="DEEP_ASSURANCE_REQUIRED")
      }
    }
    out=repo/"reports/control/K01_CONTROL_REGRESSION_SUITE_CURRENT.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("K01 CONTROL REGRESSION SUITE")
    for x in results:print(x["id"],x["status"],"-",x["detail"])
    print("REPORT:",out)
    # FAST suite does not stop engineering merely because deep assurance is pending.
    return 0 if report["summary"]["hold_like"]==0 else 2

if __name__=="__main__":raise SystemExit(main())
