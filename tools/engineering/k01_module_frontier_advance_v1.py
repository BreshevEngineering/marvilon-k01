from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

DEFAULT=Path(r'D:\BreshevEngineering\marvilon-k01')
GOAL=Path('control/project/K01_GOAL_LOCK_CURRENT.json')
FRONT=Path('control/state/K01_COMPLETION_FRONTIER_CURRENT.json')
DEC=Path('control/decisions/EDR-053_P004_WAITING_EXTERNAL_MODULE_FRONTIER_ADVANCE.json')
PLAN=Path('control/project/K01_MODULE_COMPLETION_EXECUTION_PLAN_CURRENT.json')
PLAN_MD=Path('reports/control/K01_MODULE_COMPLETION_EXECUTION_PLAN_CURRENT.md')

def rd(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def unique(seq):
    out=[]
    for x in seq:
        if x not in out: out.append(x)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=str(DEFAULT)); a=ap.parse_args(); repo=Path(a.repo_root).resolve()
    gp=repo/GOAL; fp=repo/FRONT
    if not gp.is_file() or not fp.is_file():
        raise SystemExit('HOLD: Goal Lock / Completion Frontier missing')
    goal=rd(gp); front=rd(fp)
    blocker=(front.get('active_blocker') or {}).get('id') if isinstance(front.get('active_blocker'),dict) else front.get('active_blocker')
    if blocker != 'P004-EXTERNAL-EVIDENCE-ACQUISITION':
        raise SystemExit('HOLD: expected P004-EXTERNAL-EVIDENCE-ACQUISITION, got '+repr(blocker))
    if front.get('active_engineering_object')!='K01-P-004':
        raise SystemExit('HOLD: active object is not K01-P-004')
    if not (repo/'control/decisions/EDR-052_P004_PHYSICAL_EVIDENCE_ACQUISITION_PLAN.json').is_file():
        raise SystemExit('HOLD: EDR-052 missing')
    # Required T05 authorities must exist before routing.
    auth=[
      'control/analysis/K01_T05_LOCAL_FEA_DEFINITION.json',
      'reports/calculations/K01_T05_CLAMP_SCREEN_CURRENT.json',
      'control/workpacks/K01_T05_J2_CLAMP_STRENGTH_WORKPACKAGE_v1.json',
      'control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json'
    ]
    missing=[x for x in auth if not (repo/x).is_file()]
    if missing: raise SystemExit('HOLD: T05 authority missing: '+', '.join(missing))

    stamp=now()
    edr={
      'decision_id':'EDR-053',
      'title':'P004 external-evidence dependency classification and module completion frontier advance',
      'status':'ACCEPTED_PROGRAM_FRONTIER_ADVANCE__P004_WAITING_EXTERNAL__T05_ACTIVE',
      'date':'2026-09-18',
      'problem':'P004 physical evidence acquisition is externally dependent. Treating it as the only active project blocker incorrectly stops independent calibration-module design closure work.',
      'authority_rule':'This decision changes work routing only. It does not close P004 Product Definition, does not release any P004 tolerance, and does not change CAD geometry.',
      'decision':[
        'Keep K01-P-004 Product Definition OPEN and reclassify P004-EXTERNAL-EVIDENCE-ACQUISITION as WAITING_EXTERNAL.',
        'Change the active deliverable to K01-A-001 CALIBRATION MODULE DESIGN FREEZE at lifecycle L5.',
        'Activate exactly one executable WIP: T05 J2 local contact/separation FEA on final C2R1 P003/P007 geometry.',
        'Do not restart T07A global P007 static/buckling or the passed FEMM numerical candidate unless a stale trigger occurs.',
        'Continue independent executable module closures while physical qualification and user-controlled drawing work remain external.'
      ],
      'next_active':'J2-T05-LOCAL-CONTACT-FEA',
      'p004_state':'WAITING_EXTERNAL__PRODUCT_DEFINITION_NOT_READY',
      'native_mutation':'NONE',
      'generated_utc':stamp
    }
    wr(repo/DEC,edr)

    goal.update({
      'schema':'k01.goal_lock.current.v3_module_design_freeze',
      'current_deliverable':'K01-A-001 CALIBRATION MODULE DESIGN FREEZE',
      'deliverable_class':'MODULE DESIGN FREEZE / L5 CLOSURE',
      'wip_limit':1,
      'primary_objective':'Complete the K01 calibration module engineering definition and verification needed to reach L6 Candidate TPD without allowing external physical qualification tasks to stop independent design work.',
      'active_dependency':'T05 LOCAL CONTACT / SEPARATION VERIFICATION',
      'current_execution_mode':'MANUAL_CONTROLLED_SOLIDWORKS_SIMULATION__NO_GEOMETRY_MUTATION',
      'current_lifecycle_level':'L5',
      'active_engineering_object':'K01-J2 P003-P007 SERVICE JOINT',
      'generated_utc':stamp,
      'state_semantics':{
        'CURRENT_DELIVERABLE':'K01-A-001 CALIBRATION MODULE DESIGN FREEZE',
        'CURRENT_LIFECYCLE_LEVEL':'L5',
        'ACTIVE_ENGINEERING_OBJECT':'K01-J2 P003-P007 SERVICE JOINT',
        'ACTIVE_DEPENDENCY':'T05 LOCAL CONTACT / SEPARATION FEA',
        'rule':'P004 remains OPEN but WAITING_EXTERNAL; D006 remains user-controlled drawing branch; neither blocks independent module design-freeze work.'
      },
      'non_active_work':{
        'P004_external_evidence':'WAITING_EXTERNAL',
        'D006_drawing_branch':'WAITING_EXTERNAL_USER_CONTROLLED',
        'center_redesign':'SEPARATE_BRANCH_NOT_ACTIVE_HERE',
        'physical_qualification':'L7_L8_DOWNSTREAM',
        'git_cleanup':'RELEASE_DEPENDENCY_BACKLOG'
      },
      'current_artifact':goal.get('current_artifact') or {}
    })
    wr(gp,goal)

    oldtim=front.get('timing') or {}
    waiting_ext=unique([
      'P004-EXTERNAL-EVIDENCE-ACQUISITION — physical/FAI/metrology evidence; K01-P-004 remains OPEN',
      'K01-D-006 USER-CONTROLLED DRAWING FINALIZATION'
    ] + list(oldtim.get('WAITING_EXTERNAL') or []))
    later=unique([
      'P014 material / retention definition',
      'P015 production bobbin + winding + lead/driver definition',
      'B001 design-grade / magnetic-property specification for design freeze',
      'Final CFD OUT/MID/IN force envelope on frozen gas-wetted geometry',
      'FEMM design-candidate re-adjudication after P015/B001 freeze; rerun only if stale',
      'Independent structural FEM/CalculiX cross-check or controlled waiver',
      'EBOM/MBOM release reconciliation after component/process decisions',
      'All-node / all-joint Technical Filter closure',
      'L6 Candidate TPD integration'
    ])
    front.update({
      'schema':'k01.completion_frontier.current.v4_module_design_freeze',
      'current_lifecycle_level':'L5',
      'lifecycle_name':'Joints / Seals / Tolerances / Manufacturing Definition',
      'current_deliverable':'K01-A-001 CALIBRATION MODULE DESIGN FREEZE',
      'wip_limit':1,
      'active_engineering_object':'K01-J2 P003-P007 SERVICE JOINT',
      'active_dependency':'T05 LOCAL CONTACT / SEPARATION VERIFICATION',
      'active_blocker':{'id':'J2-T05-LOCAL-CONTACT-FEA','state':'OPEN','timing':'ACTIVE_NOW'},
      'next_allowed_action':{
        'id':'K01-NA-T05-J2-LOCAL-FEA',
        'text':'Execute T05 local J2 contact/separation FEA on the frozen final C2R1 P003/P007 geometry. Run 200 and 300 N preload per screw, seal-reaction sensitivity 0/300/600 N, +0.20 bar pressure, no-penetration metal contact, local mesh <=0.20 mm at fastener/gland/pilot/flange-root regions, then refine the critical case. Report P003/P007 von Mises stress, maximum face separation, contact pressure, bolt axial force and J2 datum-face displacement. Do not mutate CAD geometry. If LC2 with 600 N seal reaction passes, retain OD33; otherwise trigger local J2 redesign.',
        'authority_set':auth,
        'expected_closure':'PASS_T05_LOCAL_CONTACT_FEA__J2_GEOMETRY_RETAINED_OR_REDESIGN_TRIGGERED',
        'execution_mode':'MANUAL_CONTROLLED_SOLIDWORKS_SIMULATION__NO_GEOMETRY_MUTATION'
      },
      'timing':{
        'ACTIVE_NOW':['J2-T05-LOCAL-CONTACT-FEA'],
        'WAITING_EXTERNAL':waiting_ext,
        'WAITING_DEPENDENCY':[
          'Final BOM release waits for P014/P015/B001/J2 component/process decisions',
          'L6 Candidate TPD waits for executable L5 module closure fronts',
          'P004 completion waits for its external evidence/requirement inputs'
        ],
        'LATER':later,
        'DEBT':list(oldtim.get('DEBT') or [])
      },
      'generated_utc':stamp
    })
    wr(fp,front)

    plan={
      'schema':'k01.module_completion_execution_plan.v1',
      'generated_utc':stamp,
      'goal':'K01-A-001 CALIBRATION MODULE DESIGN FREEZE -> L6 Candidate TPD',
      'wip_rule':'Exactly one ACTIVE_NOW. Externally blocked work moves to WAITING_EXTERNAL and does not stop independent executable closure fronts.',
      'current_active':{
        'id':'J2-T05-LOCAL-CONTACT-FEA','object':'K01-J2 P003-P007 SERVICE JOINT','status':'ACTIVE_NOW',
        'closure':'PASS_T05_LOCAL_CONTACT_FEA__J2_GEOMETRY_RETAINED_OR_REDESIGN_TRIGGERED'
      },
      'analysis_status':{
        'CFD':'PARTIAL_CURRENT_EVIDENCE — OUT=0 mm controlled PASS; final canonical OUT/MID/IN envelope still needs closure/confirmation',
        'FEA_GLOBAL_P007':'PASS_ENGINEERING_SCREEN — T07A static + buckling; do not rerun without stale trigger',
        'FEA_LOCAL_J2':'OPEN — T05 READY_TO_RUN; active now',
        'FEM_INDEPENDENT':'OPEN — CalculiX not run; face-role/mesh/bolt equivalence/toolchain blockers remain',
        'FEMM':'PASS_NUMERICAL_DESIGN_CANDIDATE — rerun/re-adjudicate after P015/B001 design-spec freeze only if inputs change'
      },
      'bom_status':{
        'state':'HOLD_NOT_RELEASE_READY','modeled_occurrences':14,'ebom_items':16,'mbom_items':17,
        'hard_open_nonmodeled':['NM-J2-SEAL','NM-J2-CLAMP-SCREW','NM-J2-FASTENER-PROCESS'],
        'design_definition_gaps':['K01-B-001','K01-P-014','K01-P-015','K01-P-004 external dependency','K01-P-013 retention qualification','K01-P-016 production compatibility/process']
      },
      'ordered_closure_fronts':[
        {'order':1,'id':'T05','title':'J2 local contact/separation FEA','timing':'ACTIVE_NOW'},
        {'order':2,'id':'P014','title':'Freeze P014 material + retention definition','timing':'NEXT_AFTER_T05'},
        {'order':3,'id':'P015_B001','title':'Freeze P015 bobbin/winding/lead/driver design spec and B001 design magnetic spec','timing':'AFTER_P014'},
        {'order':4,'id':'CFD_FINAL','title':'Close final CFD OUT/MID/IN gas-force envelope on frozen geometry','timing':'AFTER_GEOMETRY_INPUT_FREEZE'},
        {'order':5,'id':'FEMM_ADJ','title':'Re-adjudicate passed FEMM numerical candidate against frozen P015/B001 inputs; rerun only if stale','timing':'AFTER_P015_B001'},
        {'order':6,'id':'FEM_CCX','title':'Independent structural FEM/CalculiX cross-check or explicit controlled waiver','timing':'VERIFICATION_FRONT'},
        {'order':7,'id':'BOM','title':'Close engineering EBOM/MBOM, materials, make/buy, purchased seal/screw/process rows and revisions','timing':'AFTER_COMPONENT_PROCESS_DECISIONS'},
        {'order':8,'id':'NODE_REVIEW','title':'Systematic all-parts/all-joints Technical Filter and interface closure','timing':'BEFORE_L6'},
        {'order':9,'id':'L6','title':'Build K01-A-001 Candidate TPD package','timing':'EXIT_L5'}
      ],
      'waiting_external':waiting_ext,
      'do_not_restart_without_stale':['T07A P007 global static/buckling','FEMM passed numerical candidate','Drawing System','Center development','closed EDRs']
    }
    wr(repo/PLAN,plan)

    md='''# K01 Calibration Module — controlled completion plan\n\n'''
    md+=f'Generated: `{stamp}`\n\n'
    md+='## Goal\nFinish **K01-A-001 Calibration Module Design Freeze** and exit L5 to **L6 Candidate TPD**.\n\n'
    md+='## Current WIP = 1\n**T05 — J2 local contact / separation FEA** on frozen C2R1 P003/P007 geometry.\n\n'
    md+='P004 physical evidence is **WAITING_EXTERNAL**. P004 is not READY and is not falsely closed, but it no longer stops independent module work.\n\n'
    md+='## Analysis reality\n- CFD: OUT=0 mm result is controlled; final OUT/MID/IN envelope still needs canonical closure/confirmation.\n- Global P007 FEA: T07A static + buckling PASS engineering screen; do not rerun without stale trigger.\n- Local J2 FEA: OPEN and executable now.\n- Independent FEM/CalculiX: NOT RUN; solver-equivalence/toolchain blockers remain.\n- FEMM: numerical design candidate PASS; physical qualification remains later; rerun only if P015/B001 input freeze makes it stale.\n\n'
    md+='## Ordered fronts\n1. T05 J2 local FEA.\n2. P014 material/retention definition.\n3. P015 production winding/bobbin/lead/driver + B001 design magnetic specification.\n4. Final CFD OUT/MID/IN.\n5. FEMM re-adjudication / rerun only if stale.\n6. Independent FEM/CalculiX cross-check or controlled waiver.\n7. EBOM/MBOM release closure.\n8. All-part / all-joint Technical Filter closure.\n9. L6 Candidate TPD.\n\n'
    md+='## BOM reality\nCurrent BOM is not absent, but it is **HOLD**, not release-ready: 14 modeled occurrences; 16 EBOM items; 17 MBOM items. Open purchased/process rows include J2 seal, J2 clamp screw and fastener process.\n'
    (repo/PLAN_MD).parent.mkdir(parents=True,exist_ok=True); (repo/PLAN_MD).write_text(md,encoding='utf-8')

    # Recompute navigation/coherence using existing state system.
    cmds=[
      [sys.executable,'tools/state/k01_lifecycle_state_reducer_v2.py','--repo-root',str(repo)],
      [sys.executable,'tools/state/k01_temporal_coherence_guard_v1.py','--repo-root',str(repo),'--write-report'],
      [sys.executable,'tools/state/k01_semantic_coherence_guard_v1.py','--repo-root',str(repo),'--write-report']]
    for c in cmds: subprocess.run(c,cwd=repo,check=True,text=True)
    print('PASS_MODULE_FRONTIER_ADVANCED__P004_WAITING_EXTERNAL__T05_ACTIVE')
    print('EDR: EDR-053')
    print('ACTIVE: J2-T05-LOCAL-CONTACT-FEA')
    print('NO CAD GEOMETRY MUTATION')
    return 0

if __name__=='__main__': raise SystemExit(main())
