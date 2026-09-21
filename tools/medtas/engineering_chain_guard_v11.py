from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from control_authority import require_control_family

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / 'control/requirements/requirements.json'
ALLOC = ROOT / 'control/requirements/K01_REQUIREMENT_ALLOCATION_REGISTRY_v1.json'
DER = ROOT / 'control/engineering/K01_DERIVED_ENGINEERING_INPUTS_v1.json'
DEC = ROOT / 'control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json'
CTX = ROOT / 'control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json'
POL = ROOT / 'control/product_definition/K01_PRODUCT_DEFINITION_POLICY_CURRENT.json'
EXEC = ROOT / 'control/project/K01_ENGINEERING_EXECUTION_CONTRACT_CURRENT.json'
MFG = ROOT / 'control/manufacturing/K01_P007_MANUFACTURING_FEASIBILITY_CURRENT.json'
EFF = ROOT / 'control/configuration/K01_EFFECTIVITY_POLICY_v1.json'
BIND = ROOT / 'control/verification/K01_CAD_BINDING_INVARIANCE_POLICY_v1.json'
FBP = ROOT / 'control/change/K01_ENGINEERING_FEEDBACK_POLICY_v1.json'
FBR = ROOT / 'control/change/K01_ENGINEERING_FEEDBACK_REGISTRY_CURRENT.json'
GRAPH = None
DRAW_POLICY = ROOT / 'control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json'
DELIVERY = ROOT / 'control/drawings/K01_DRAWING_DELIVERY_CAPABILITY_CURRENT.json'
OUT = ROOT / 'reports/control/K01_ENGINEERING_CHAIN_READINESS_CURRENT.json'
OUT_MD = ROOT / 'reports/control/K01_ENGINEERING_CHAIN_READINESS_CURRENT.md'


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def now():
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    try:
        graph_authority = require_control_family(ROOT, 'engineering_build_graph')
    except Exception as exc:
        graph_authority = ROOT / 'control/project/__MISSING_ENGINEERING_BUILD_GRAPH_AUTHORITY__.json'
        issues = [f'GRAPH_AUTHORITY_RESOLUTION_FAILED:{exc}']
    else:
        issues = []
    required = [REQ, ALLOC, DER, DEC, CTX, POL, EXEC, MFG, EFF, BIND, FBP, FBR, graph_authority, DRAW_POLICY, DELIVERY]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        issues += [f'MISSING:{x}' for x in missing]
    if issues:
        data = {'schema':'k01.engineering_chain_readiness.current.v1','generated_utc':now(),'status':'HOLD_CHAIN_CONTROL','issues':issues}
        OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        print('STATUS: HOLD_CHAIN_CONTROL'); print('ISSUES:',len(issues)); return 2

    req, alloc, der, dec, ctx, pol, exe, mfg, eff, bind, fbp, fbr, graph, draw_policy, delivery = map(load, required)
    reqmap = {x['id']:x for x in req.get('requirements',[]) if x.get('id')}
    alloc_ids=set(); allocated_chars=set(); allocation_open=[]
    for a in alloc.get('allocations',[]):
        aid=a.get('id'); rid=a.get('requirement_id')
        if not aid or aid in alloc_ids: issues.append(f'ALLOCATION_ID_INVALID_OR_DUPLICATE:{aid}')
        alloc_ids.add(aid)
        if rid not in reqmap: issues.append(f'ALLOCATION_REQUIREMENT_MISSING:{aid}:{rid}')
        if not a.get('targets'): issues.append(f'ALLOCATION_TARGETS_EMPTY:{aid}')
        if not a.get('status'): issues.append(f'ALLOCATION_STATUS_MISSING:{aid}')
        if not a.get('revision') or not a.get('effective_from'): issues.append(f'ALLOCATION_CONFIGURATION_MISSING:{aid}')
        if not (a.get('share') or {}).get('mode'): issues.append(f'ALLOCATION_SHARE_MODE_MISSING:{aid}')
        for t in a.get('targets',[]):
            if not t.get('entity_id') or not t.get('responsibility'): issues.append(f'ALLOCATION_TARGET_ID_OR_RESPONSIBILITY_MISSING:{aid}')
        if 'OPEN' in str(a.get('status','')).upper() or 'PARTIAL' in str(a.get('status','')).upper(): allocation_open.append(aid)
        for t in a.get('targets',[]):
            if t.get('characteristic_id'): allocated_chars.add(t['characteristic_id'])

    derived_ids=set(); derived_open=[]; quantity_keys={}
    for x in der.get('inputs',[]):
        did=x.get('id'); q=x.get('quantity_kind')
        if not did or did in derived_ids: issues.append(f'DERIVED_ID_INVALID_OR_DUPLICATE:{did}')
        derived_ids.add(did)
        if not q: issues.append(f'DERIVED_QUANTITY_KIND_MISSING:{did}')
        if not x.get('source'): issues.append(f'DERIVED_SOURCE_MISSING:{did}')
        if not x.get('status'): issues.append(f'DERIVED_STATUS_MISSING:{did}')
        if not x.get('consumers'): issues.append(f'DERIVED_CONSUMERS_EMPTY:{did}')
        if not x.get('revision') or not x.get('effective_from'): issues.append(f'DERIVED_CONFIGURATION_MISSING:{did}')
        for rid in x.get('requirement_ids',[]):
            if rid not in reqmap: issues.append(f'DERIVED_REQUIREMENT_MISSING:{did}:{rid}')
            if rid not in {a.get("requirement_id") for a in alloc.get("allocations",[])}: issues.append(f'DERIVED_REQUIREMENT_UNALLOCATED:{did}:{rid}')
        if 'OPEN' in str(x.get('status','')).upper() or 'SCREENING' in str(x.get('status','')).upper() or x.get('release_authority') is False:
            derived_open.append(did)
        quantity_keys.setdefault((x.get('value'), x.get('unit')), []).append((did,q))
    # The known 300 N ambiguity must be represented by separate quantity identities.
    equal_300 = [(did,q) for (v,u),vals in quantity_keys.items() if v == 300.0 for did,q in vals]
    if len(equal_300) >= 2 and len({q for _,q in equal_300}) < len(equal_300):
        issues.append('DERIVED_EQUAL_VALUE_QUANTITY_IDENTITY_COLLISION')
    expected_300={'DER-K01-P006-SERVICE-NORMAL-FORCE-001','DER-K01-J2-BOLT-PRELOAD-SCREEN-001'}
    if not expected_300.issubset(derived_ids): issues.append('KNOWN_300N_DERIVED_INPUT_SPLIT_MISSING')

    decision_ids={x['id'] for x in dec.get('characteristics',[]) if x.get('id')}
    context_ids=set(ctx.get('characteristics',{}))
    missing_context=sorted(decision_ids-context_ids)
    if missing_context: issues.append('CHARACTERISTIC_CONTEXT_MISSING:'+','.join(missing_context))

    required_fields=set(pol.get('characteristic_required_fields',[]))
    for field in ['datum_reference_system','measurement_condition','inspection_strategy','revision_effectivity','binding_invariance','manufacturing_feasibility','requirement_allocation_ids','derived_input_ids']:
        if field not in required_fields: issues.append(f'POLICY_REQUIRED_FIELD_MISSING:{field}')

    stage_ids={x.get('id') for x in exe.get('stages',[])}
    for sid in ['S0A_REQUIREMENT_ALLOCATION','S1A_DERIVED_INPUTS','S1B_MANUFACTURING_SUPPLY_STRATEGY','S4A_PHYSICS_ANALYSIS','S4B_VARIATION_CAPABILITY','S7_CONFIGURATION_RELEASE_EFFECTIVITY']:
        if sid not in stage_ids: issues.append(f'EXEC_STAGE_MISSING:{sid}')
    if len(exe.get('feedback_loops',[])) < 5: issues.append('EXEC_FEEDBACK_LOOPS_INCOMPLETE')

    graph_nodes={x.get('node_id') for x in graph.get('nodes',[])}
    for nid in ['K01.DRAWING.PIPELINE.POLICY','K01.DRAWING.DELIVERY.CAPABILITY','K01.DRAWING.D006.D1.AUTHORING_PLAN','K01.REQ.ALLOCATION','K01.DERIVED.INPUTS','K01.PD.P007.CONTEXT.DATUM','K01.PD.P007.CONTEXT.MEASUREMENT','K01.PD.P007.CONTEXT.INSPECTION','K01.PD.P007.CONTEXT.MANUFACTURING','K01.PD.P007.CONTEXT.BINDING','K01.PD.P007.CONTEXT.CONFIGURATION','K01.PD.P007.DRAWING_SLICE','K01.PD.P007.VARIATION_SLICE','K01.PD.P007.INSPECTION_SLICE','K01.PD.P007.PHYSICS_SLICE','K01.MFG.P007.FEASIBILITY','K01.CONFIG.EFFECTIVITY']:
        if nid not in graph_nodes: issues.append(f'GRAPH_NODE_MISSING:{nid}')

    # Drawing D1-D9 chain is first-class: every current characteristic must expose claim-level authoring context.
    for cid in sorted(decision_ids):
        da = ctx.get('characteristics',{}).get(cid,{}).get('drawing_authoring')
        if not isinstance(da,dict) or not isinstance(da.get('targets'),list):
            issues.append(f'DRAWING_AUTHORING_CONTEXT_MISSING:{cid}')
    if draw_policy.get('lanes',{}).get('RELEASE_NATIVE_D1_D9',{}).get('release_eligible') is not True:
        issues.append('DRAWING_RELEASE_NATIVE_LANE_POLICY_INVALID')

    release_holds=[]
    if mfg.get('selection') == 'OPEN': release_holds.append('MANUFACTURING_ROUTE_OPEN')
    if 'OPEN' in str(ctx.get('configuration_scope',{}).get('effectivity_status','OPEN')): release_holds.append('CONFIGURATION_EFFECTIVITY_OPEN')
    if bind.get('current_p007_status') != 'PASS': release_holds.append('BINDING_INVARIANCE_NOT_COMPLETE')
    if allocation_open: release_holds.append('REQUIREMENT_ALLOCATION_PARTIAL_OR_OPEN')
    if derived_open: release_holds.append('DERIVED_INPUTS_SCREENING_OR_OPEN')

    status='PASS_CHAIN_CONTROLLED__HOLD_RELEASE' if not issues else 'HOLD_CHAIN_CONTROL'
    data={
      'schema':'k01.engineering_chain_readiness.current.v1','generated_utc':now(),'status':status,
      'structural_issues':issues,
      'release_holds':release_holds,
      'counts':{
        'requirements':len(reqmap),'allocations':len(alloc_ids),'derived_inputs':len(derived_ids),'characteristics':len(decision_ids),'feedback_records':len(fbr.get('records',[])),'graph_nodes':len(graph_nodes)
      },
      'known_300N_identity_check':{'status':'PASS' if not any(x.startswith('DERIVED_') for x in issues) else 'HOLD','records':sorted(expected_300)},
      'manufacturing_route':{'status':mfg.get('status'),'selection':mfg.get('selection')},
      'configuration_effectivity':ctx.get('configuration_scope',{}),
      'binding_invariance':{'status':bind.get('current_p007_status')},
      'feedback_policy':str(FBP.relative_to(ROOT)),
      'next':'Run Product Definition Guard V11; then use domain-slice fingerprints for drawing/variation/inspection/physics consumers. Release stays HOLD until release_holds close.'
    }
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md=['# K01 engineering chain readiness','',f'**Status:** `{status}`','', '## Release holds']
    md += [f'- {x}' for x in release_holds] or ['- None']
    md += ['', '## Structural issues'] + ([f'- {x}' for x in issues] or ['- None'])
    md += ['', '## Explicit separation', '- Requirement allocation is a separate object.', '- Derived engineering inputs are separate objects.', '- Product characteristics carry datum/measurement/inspection/configuration context.', '- Physics and variation/capability analyses are separate dependency domains.', '- Downstream problems return through EFR/change control, never silent edits.']
    OUT_MD.write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(f'STATUS: {status}')
    print(f'RELEASE_HOLDS: {len(release_holds)}')
    print(f'ALLOCATIONS: {len(alloc_ids)}')
    print(f'DERIVED_INPUTS: {len(derived_ids)}')
    print(f'KNOWN_300N_IDENTITY: {data["known_300N_identity_check"]["status"]}')
    print(f'REPORT: {OUT}')
    return 0 if not issues else 2

if __name__=='__main__':
    raise SystemExit(main())
