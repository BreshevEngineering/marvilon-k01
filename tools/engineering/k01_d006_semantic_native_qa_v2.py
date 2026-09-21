from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
AUTH=Path("reports/drawing/current/K01-D-006_V2_REFINED_AUTHORING_CURRENT.json")
SPEC=Path("control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v2.json")
CS=Path("cad_api/solidworks_2018_proven/current/K01_D006_V2_REFINE_CURRENT/K01D006V2SemanticVerify.cs")
WORK=Path("reports/cad/d006_v2_semantic_verify")
REPORT=Path("reports/drawing/current/K01-D-006_V2_SEMANTIC_NATIVE_QA_CURRENT.json")
D8=Path("control/drawings/K01_D006_D8_WORKPACK_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json"); GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json"); FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json"); CENTER=Path("control/center/K01_CENTER_INPUT_CURRENT.json")

def rd(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def run(c,cwd=None,timeout=900): return subprocess.run(c,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)
def sw_running():
 cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30)
 return "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower()
def csc():
 w=Path(os.environ.get("WINDIR",r"C:\Windows"))
 for p in (w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"):
  if p.exists(): return p
 raise RuntimeError("csc missing")
def redist():
 for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
  if (p/"SolidWorks.Interop.sldworks.dll").exists(): return p
 raise RuntimeError("interop missing")

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root)
 if sw_running(): raise SystemExit("HOLD: close SolidWorks before read-only semantic/native QA.")
 for rel in (AUTH,SPEC,CS,NEXT,GATE,FRONT):
  if not (repo/rel).exists(): raise SystemExit("HOLD: missing "+str(rel))
 ar=rd(repo/AUTH); n=rd(repo/NEXT); spec=rd(repo/SPEC)
 if ar.get("status")!="PASS_NEW_D006_V2_REFINED_CANDIDATE__CURRENT_UNCHANGED": raise SystemExit("HOLD: refined authoring report not PASS.")
 if n.get("next_action_id")!="K01-NA-D006-SEMANTIC-NATIVE-QA": raise SystemExit("HOLD: frontier is not semantic/native QA.")
 candidate=Path((((ar.get("candidate") or {}).get("drawing") or {}).get("path") or "")); cur=Path((ar.get("source_current") or {}).get("path","")); model=Path((ar.get("source_model") or {}).get("path",""))
 if not candidate.is_file() or not cur.is_file() or not model.is_file(): raise SystemExit("HOLD: candidate/current/model missing.")
 cpre=sha(candidate)
 if sha(cur)!=(ar.get("source_current") or {}).get("sha256"): raise SystemExit("HOLD: current D006 changed since refined candidate authoring.")
 if sha(model)!=(ar.get("source_model") or {}).get("sha256"): raise SystemExit("HOLD: P007 model changed since refined candidate authoring.")

 rdll=redist();refs=[rdll/"SolidWorks.Interop.sldworks.dll",rdll/"SolidWorks.Interop.swconst.dll"];build=repo/WORK/"build";build.mkdir(parents=True,exist_ok=True);exe=build/"K01D006V2SemanticVerify.exe"
 cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]+["/reference:"+str(x) for x in refs]+[str(repo/CS)],cwd=repo)
 print(cp.stdout,end="");print(cp.stderr,end="",file=sys.stderr)
 if cp.returncode!=0: raise SystemExit("HOLD: semantic verifier compile failed.")
 for x in refs: shutil.copy2(x,build/x.name)
 raw=repo/WORK/"K01_D006_V2_SEMANTIC_NATIVE_RAW_CURRENT.txt"
 cp=run([str(exe),"--drawing",str(candidate),"--model",str(model),"--report",str(raw)],cwd=repo,timeout=900)
 print(cp.stdout,end="");print(cp.stderr,end="",file=sys.stderr)
 if cp.returncode!=0 or not raw.is_file() or "PASS_D006_V2_NATIVE_DELTA_QA" not in raw.read_text(encoding="utf-8-sig",errors="replace"): raise SystemExit("HOLD: native delta QA failed.")
 if sha(candidate)!=cpre: raise SystemExit("HOLD: read-only QA changed candidate hash.")

 # Reuse existing presentation audit for automated D8 precheck. It does not replace human D8.
 cmd=[sys.executable,"tools/medtas/drawing_presentation_audit_v1.py","--repo-root",str(repo),"--drawing-id","K01-D-006","--spec",str(SPEC).replace("\\","/"),"--drawing",str(candidate)]
 pa=run(cmd,cwd=repo,timeout=900); print(pa.stdout,end="");print(pa.stderr,end="",file=sys.stderr)
 presentation_ok=pa.returncode==0
 status="PASS_D006_SEMANTIC_NATIVE_QA__READY_FOR_D8" if presentation_ok else "HOLD_D006_PRESENTATION_PRECHECK"
 rep={"schema":"k01.d006.v2_semantic_native_qa.current.v1","generated_utc":now(),"status":status,"candidate":str(candidate),"candidate_sha256":cpre,"native_delta_qa":"PASS","presentation_precheck_returncode":pa.returncode,"presentation_precheck_stdout_tail":(pa.stdout or "")[-5000:],"current_drawing_invariant":sha(cur)==(ar.get("source_current") or {}).get("sha256"),"source_model_invariant":sha(model)==(ar.get("source_model") or {}).get("sha256"),"inherited_baseline":"Current D006 already had PASS_DRAWING_SYSTEM_V1 semantic status; refined candidate is a binary clone plus controlled note delta.","human_D8_required":True}
 wr(repo/REPORT,rep)
 if not presentation_ok:
  print(status); return 2

 d8={"schema":"k01.d006.d8_workpack.current.v1","generated_utc":now(),"status":"READY_FOR_MANUAL_CONTROLLED_D8","drawing_id":"K01-D-006","candidate":str(candidate),"candidate_sha256_before_d8":cpre,"allowed_changes":["move views/annotations/leaders for readability","resolve overlaps","update title/status fields to RELEASE CANDIDATE - NOT YET RELEASED","replace presentation-only review wording","regenerate candidate PDF/BMP"],"forbidden_changes":["no dimension/tolerance/GPS value changes","no datum reassignment","no surface value change","no C12 value change","no P007 source model save","no current D006 overwrite","no drawing-system redesign"],"checks":["A3 / FIRST ANGLE / scale readable","section and J2 end view readable","all released dimensions and FCFs readable","no text/leader overlap","J2 Ra note unambiguous","C12 note explicitly says assembled J2, not bare P007","title block K01-D-006 / Hermetic Magnetic Can / EN1.4404-AISI316L / RELEASE CANDIDATE - NOT YET RELEASED","PDF/BMP regenerated after manual finish"],"publication_boundary":"D8 PASS is still candidate evidence. current/ publication requires explicit controlled publication step."}
 wr(repo/D8,d8)

 f=rd(repo/FRONT);g=rd(repo/GATE);n=rd(repo/NEXT)
 blocker="D006-D8-VISUAL-QA";nid="K01-NA-D006-D8-VISUAL-QA";exp="PASS_D006_D8_VISUAL_QA__READY_FOR_PUBLICATION"
 text="Perform controlled manual D8 visual finish on the refined D006 V2 candidate under a native mutation lease; no engineering-value changes."
 auth=[str(REPORT).replace("\\","/"),str(D8).replace("\\","/"),str(SPEC).replace("\\","/")]
 n.update({"schema":"k01.next_actions.current.v25_lifecycle","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"MANUAL_CONTROLLED_D8_NATIVE_LEASE_REQUIRED","authority_set":auth,"release_blockers":[{"id":blocker,"state":"OPEN","role":"Controlled visual/presentation finish and human D8 approval","class":"L6_EXECUTABLE_BLOCKER"}]})
 g={"schema":"k01.active_step_gate.v9_lifecycle","state_epoch":n.get("state_epoch"),"generated_utc":now(),"step_id":"K01-STEP-D006-L6-D8","current_lifecycle_level":"L6","active_line":"K01-D006-RELEASE-PIPELINE","checkpoint_id":g.get("checkpoint_id"),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"NO NATIVE SAVE UNTIL D8 LEASE ACTIVE; PRESENTATION-ONLY CHANGES; NO ENGINEERING VALUES","result_on_pass":exp,"required_files":auth}
 f.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"MANUAL_CONTROLLED_D8_NATIVE_LEASE_REQUIRED"}});f.setdefault("timing",{})["ACTIVE_NOW"]=[blocker];f["timing"]["WAITING_DEPENDENCY"]=["D006-CURRENT-PUBLICATION"]
 wr(repo/NEXT,n);wr(repo/GATE,g);wr(repo/FRONT,f)
 c=rd(repo/CENTER) if (repo/CENTER).exists() else {};c.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"current_lifecycle_level":"L6"});wr(repo/CENTER,c)
 subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
 subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
 print(status);print("NEXT: controlled manual D8 visual QA.")
 return 0

if __name__=="__main__":raise SystemExit(main())
