from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
SPEC=Path("control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v2.json")
PROM=Path("control/drawings/K01_D006_SPEC_PROMOTION_CURRENT.json")
DC=Path("reports/control/K01_DRAWING_CONTROL_CURRENT.json")
LEASE=Path("control/state/K01_NATIVE_MUTATION_LEASE_CURRENT.json")
REPORT=Path("reports/drawing/current/K01-D-006_V2_REFINED_AUTHORING_CURRENT.json")
DEFECT=Path("reports/drawing/current/K01-D-006_DRAWING_SYSTEM_SECTION_DEFECT_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_INPUT_CURRENT.json")
CS=Path("cad_api/solidworks_2018_proven/current/K01_D006_V2_REFINE_CURRENT/K01D006V2RefineCurrent.cs")
WORK=Path("reports/cad/d006_v2_refine_current")

def rd(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
def run(c,cwd=None,timeout=900): return subprocess.run(c,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)
def sw_running():
 cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30)
 return "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower()
def csc():
 w=Path(os.environ.get("WINDIR",r"C:\Windows"))
 for p in (w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"):
  if p.exists(): return p
 raise RuntimeError("csc.exe missing")
def redist():
 for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
  if (p/"SolidWorks.Interop.sldworks.dll").exists(): return p
 raise RuntimeError("SOLIDWORKS API redist missing")
def parsekv(p):
 d={}
 for line in p.read_text(encoding="utf-8-sig",errors="replace").splitlines():
  if "=" in line:
   k,v=line.split("=",1); d[k.strip()]=v.strip()
 return d
def artifact(p):
 return {"path":str(p),"exists":p.is_file(),"sha256":sha(p) if p.is_file() else None,"size_bytes":p.stat().st_size if p.is_file() else None}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default=str(R)); ap.add_argument("--owner",default=os.environ.get("USERNAME","K01_USER")); a=ap.parse_args(); repo=Path(a.repo_root)
 if sw_running(): raise SystemExit("HOLD: close SolidWorks before controlled current-clone refinement.")
 for rel in (SPEC,PROM,DC,NEXT,GATE,FRONT,CS):
  if not (repo/rel).exists(): raise SystemExit("HOLD: missing "+str(rel))
 n=rd(repo/NEXT); prom=rd(repo/PROM); spec=rd(repo/SPEC); dc=rd(repo/DC)
 if n.get("next_action_id")!="K01-NA-D006-NATIVE-MUTATION-LEASE": raise SystemExit("HOLD: frontier is not at D006 native-mutation lease.")
 if prom.get("status")!="PASS_D006_SPEC_PROMOTED__READY_FOR_NATIVE_CANDIDATE_LEASE": raise SystemExit("HOLD: D006 V2 spec promotion not PASS.")
 d=((dc.get("drawings") or {}).get("K01-D-006") or {})
 if not str(d.get("semantic_status","")).startswith("PASS_DRAWING_SYSTEM_V1"): raise SystemExit("HOLD: current D006 is not a previously semantic-PASS baseline.")
 cur=Path(((((d.get("current") or {}).get("artifacts") or {}).get("drawing") or {}).get("path") or ""))
 model=Path(spec.get("model_path","")); outroot=Path(spec.get("output_root",""))
 if not cur.is_file() or not model.is_file(): raise SystemExit("HOLD: current D006 or P007 source model missing.")
 cursha=sha(cur); modelsha=sha(model)
 ctlsha=(((((d.get("current") or {}).get("artifacts") or {}).get("drawing") or {}).get("sha256")))
 if ctlsha and ctlsha!=cursha: raise SystemExit("HOLD: current D006 hash differs from Drawing Control.")
 stamp=dt.datetime.now().strftime("%Y%m%d_%H%M%S")
 candroot=outroot/("refined_v2_"+stamp); gen=candroot/"generated"; manual=candroot/"manual_finish"; evidence=candroot/"evidence"
 for p in (gen,manual,evidence): p.mkdir(parents=True,exist_ok=True)

 rdll=redist(); refs=[rdll/"SolidWorks.Interop.sldworks.dll",rdll/"SolidWorks.Interop.swconst.dll"]; build=repo/WORK/"build"; build.mkdir(parents=True,exist_ok=True); exe=build/"K01D006V2RefineCurrent.exe"
 cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]+["/reference:"+str(x) for x in refs]+[str(repo/CS)],cwd=repo)
 print(cp.stdout,end=""); print(cp.stderr,end="",file=sys.stderr)
 if cp.returncode!=0: raise SystemExit("HOLD: refinement helper compile failed before native lease; no native mutation started.")
 for x in refs: shutil.copy2(x,build/x.name)

 lease={"schema":"k01.native_mutation_lease.current.v1","lease_id":"K01-D006-REFINE-V2-"+stamp,"status":"ACTIVE","owner_session":a.owner,"artifact_id":"K01-D006-NEW-V2-REFINED-CANDIDATE","native_path":str(gen),"baseline_current_drawing":str(cur),"baseline_current_drawing_sha256":cursha,"baseline_source_model":str(model),"baseline_source_model_sha256":modelsha,"allowed_operation":"COPY_CURRENT_D006_TO_NEW_CANDIDATE_AND_APPLY_RELEASE_NOTES_ONLY__DO_NOT_OVERWRITE_CURRENT","start_utc":now(),"rollback_reference":"Quarantine/delete new candidate directory; current D006 and source P007 must remain unchanged."}
 wr(repo/LEASE,lease); print("LEASE ACTIVE:",lease["lease_id"])

 raw=repo/WORK/"K01_D006_V2_REFINE_CURRENT_RAW_CURRENT.txt"
 cp=run([str(exe),"--drawing",str(cur),"--model",str(model),"--outdir",str(gen),"--report",str(raw)],cwd=repo,timeout=900)
 print(cp.stdout,end=""); print(cp.stderr,end="",file=sys.stderr)
 if sw_running():
  cleanup=run(["taskkill","/F","/T","/IM","SLDWORKS.exe"],timeout=30)
  print("CLEANUP: terminated automation-owned SolidWorks after helper")
  if cleanup.stdout: print(cleanup.stdout,end="")
  if cleanup.stderr: print(cleanup.stderr,end="",file=sys.stderr)
 kv=parsekv(raw) if raw.is_file() else {}
 curpost=sha(cur); modelpost=sha(model)
 passed=cp.returncode==0 and kv.get("STATUS")=="PASS_D006_V2_REFINED_FROM_CURRENT" and curpost==cursha and modelpost==modelsha
 lease.update({"status":"RELEASED_AFTER_PASS" if passed else ("RELEASED_AFTER_FAILED_REFINEMENT" if curpost==cursha and modelpost==modelsha else "HOLD_UNSAFE_POST_STATE"),"released_utc":now(),"post_current_drawing_sha256":curpost,"post_source_model_sha256":modelpost,"current_drawing_invariant":curpost==cursha,"source_model_invariant":modelpost==modelsha,"candidate_root":str(candroot)})
 wr(repo/LEASE,lease)

 candidate=Path(kv.get("OUTPUT_DRAWING","")); pdf=Path(kv.get("OUTPUT_PDF","")); bmp=Path(kv.get("OUTPUT_BMP",""))
 rep={"schema":"k01.d006.v2_refined_authoring.current.v1","generated_utc":now(),"status":"PASS_NEW_D006_V2_REFINED_CANDIDATE__CURRENT_UNCHANGED" if passed else "HOLD_D006_V2_REFINED_AUTHORING","route":"CLONE_CURRENT_SEMANTIC_PASS_BASELINE__APPLY_CONTROLLED_RELEASE_DELTA","reason":"Drawing System fresh section creation is currently brittle for D006; current semantic-PASS D006 is the controlled baseline for one-off refinement.","source_current":{"path":str(cur),"sha256":cursha},"source_model":{"path":str(model),"sha256":modelsha},"candidate_root":str(candroot),"candidate":{"drawing":artifact(candidate) if candidate else None,"pdf":artifact(pdf) if pdf else None,"bmp":artifact(bmp) if bmp else None},"current_drawing_invariant":curpost==cursha,"source_model_invariant":modelpost==modelsha,"helper_returncode":cp.returncode,"raw":kv}
 wr(repo/REPORT,rep)
 defect={"schema":"k01.drawing_system.scoped_defect.current.v1","generated_utc":now(),"status":"SCOPED_DEFECT_RECORDED__D006_DELIVERY_ROUTE_BYPASS_ACTIVE","id":"DSV1-SECTION-CREATION-QA-D006","observed_failure":"section QA failed: zero face hatches; exterior duplicate rejected","scope":"fresh section creation for D006 V2 candidate","product_definition_impact":"NONE","current_drawing_impact":"NONE","source_model_impact":"NONE","delivery_route":"Use current semantic-PASS D006 as baseline; clone/refine only the released delta.","drawing_system_policy":"Do not redesign frozen Drawing System during D006 closure. Reopen system only if this defect blocks another drawing/current-refinement path or repeats as a release-wide capability blocker."}
 wr(repo/DEFECT,defect)
 if not passed:
  print(rep["status"]); print("LEASE:",lease["status"]); return 2

 # candidate manifest / lineage
 manifest={"schema":"k01.drawing_candidate.v2_refined","candidate_id":candroot.name,"drawing_id":"K01-D-006","part_id":"K01-P-007","created_utc":now(),"state":"GENERATED_REFINED_FROM_CURRENT","release":"HOLD","spec":{"path":str(SPEC).replace("\\","/"),"sha256":sha(repo/SPEC)},"source_current":{"path":str(cur),"sha256":cursha},"source_model":{"path":str(model),"sha256":modelsha},"paths":{"candidate_root":str(candroot),"generated":str(gen),"manual_finish":str(manual),"evidence":str(evidence)},"generated_artifacts":{"drawing":artifact(candidate),"pdf":artifact(pdf),"bmp":artifact(bmp)},"delta":["hide obsolete visible J2 surface engineering-review note","add released J2 Ra note","add assembled-J2 C12 acceptance note","add inspection-plan reference"],"release":"HOLD_SEMANTIC_QA_D8_PUBLICATION"}
 wr(candroot/"candidate_manifest.json",manifest)

 # move frontier to semantic/native QA
 f=rd(repo/FRONT); g=rd(repo/GATE); n=rd(repo/NEXT)
 blocker="D006-SEMANTIC-NATIVE-QA"; nid="K01-NA-D006-SEMANTIC-NATIVE-QA"; exp="PASS_D006_SEMANTIC_NATIVE_QA__READY_FOR_D8"
 text="Independently verify the refined D006 V2 candidate against promoted spec V2, released P007 Product Definition, inherited current semantic evidence, and source/current hash invariance. Read-only."
 authority=[str(REPORT).replace("\\","/"),str(SPEC).replace("\\","/"),"control/product_definition/K01_P007_PRODUCT_DEFINITION_RELEASE_CURRENT.json","reports/control/K01_DRAWING_CONTROL_CURRENT.json"]
 n.update({"schema":"k01.next_actions.current.v24_lifecycle","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"READ_ONLY_SEMANTIC_NATIVE_VERIFICATION","authority_set":authority,"release_blockers":[{"id":blocker,"state":"OPEN","role":"Independent semantic/native QA of refined V2 candidate","class":"L6_EXECUTABLE_BLOCKER"}]})
 g={"schema":"k01.active_step_gate.v8_lifecycle","state_epoch":n.get("state_epoch"),"generated_utc":now(),"step_id":"K01-STEP-D006-L6-SEMANTIC-NATIVE-QA","current_lifecycle_level":"L6","active_line":"K01-D006-RELEASE-PIPELINE","checkpoint_id":g.get("checkpoint_id"),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"READ_ONLY_DRAWING_SEMANTIC_NATIVE_VERIFICATION; NO NATIVE SAVE; NO CURRENT PUBLICATION","result_on_pass":exp,"required_files":authority}
 f.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":authority,"expected_closure":exp,"execution_mode":"READ_ONLY_SEMANTIC_NATIVE_VERIFICATION"}}); f.setdefault("timing",{})["ACTIVE_NOW"]=[blocker]; f["timing"]["WAITING_DEPENDENCY"]=["D006-D8-VISUAL-QA","D006-CURRENT-PUBLICATION"]
 wr(repo/NEXT,n); wr(repo/GATE,g); wr(repo/FRONT,f)
 c=rd(repo/CENTER) if (repo/CENTER).exists() else {}; c.update({"generated_utc":now(),"current_lifecycle_level":"L6","active_blocker":blocker,"next_action_id":nid,"drawing_system_defect":str(DEFECT).replace("\\","/")}); wr(repo/CENTER,c)
 subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
 subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
 print(rep["status"]); print("CANDIDATE:",candidate); print("NEXT: independent semantic/native QA.")
 return 0

if __name__=="__main__": raise SystemExit(main())
