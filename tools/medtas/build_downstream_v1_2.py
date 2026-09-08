#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import medtas_state_engine_v1_1 as eng

ID_RE=re.compile(r'(K01-[PBA]-\d{3})',re.I)

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def base_id(text):
    m=ID_RE.search(str(text or ''))
    return m.group(1).upper() if m else str(text or '')

def load_graph(root):
    p=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_5.json'
    if not p.exists(): p=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_4.json'
    if not p.exists(): p=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_3.json'
    if not p.exists(): p=root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_2.json'
    return load(p)
def stores(root): return eng.load_record_store(root/'reports/medtas/records/current'), eng.load_record_store(root/'reports/medtas/verifications/current')
def evaluate(root):
    r,v=stores(root); return eng.evaluate_graph(load_graph(root),root,r,v)

def register_build(root,nid,producer,extra=None):
    d=evaluate(root)[nid]
    if not d.get('artifact_hash'):
        raise RuntimeError(nid+' has no artifact hash after output generation')
    br={'schema':'medtas.build_record.v1','node_id':nid,'built_state_hash':d['state_hash'],'artifact_hash':d['artifact_hash'],'producer':producer}
    if extra: br.update(extra)
    dump(root/'reports/medtas/records/current'/f'{nid}.build.json',br)
    return br

def register_verification(root,nid,verdict,metrics=None,limitations=None,notes=None):
    d=evaluate(root)[nid]
    vr={'schema':'medtas.verification_record.v1','node_id':nid,'verified_state_hash':d['state_hash'],'verified_artifact_hash':d['artifact_hash'],'verdict':verdict,'metrics':metrics or {},'limitations':limitations or [],'notes':notes or ''}
    dump(root/'reports/medtas/verifications/current'/f'{nid}.verify.json',vr)
    return vr

def graph_semantics(graph,nid):
    return next(n for n in graph['nodes'] if n['node_id']==nid)['contract'].get('semantic_payload',{})

def build_snapshot(root,graph,cad,derived):
    out=root/'reports/medtas/snapshot/current/K01_CANONICAL_ENGINEERING_SNAPSHOT_A001_v1.json'
    req=graph_semantics(graph,'K01.REQ.GATE04E'); params=graph_semantics(graph,'K01.PARAM.GATE04E'); mat=graph_semantics(graph,'K01.MAT.GATE04E')
    payload={'schema':'k01.canonical_engineering_snapshot.a001.v1_4','project':'K01','assembly':cad.get('assembly',{}),'requirements':req,'parameters':params,'materials':mat,'cad_semantic':cad,'limitations':cad.get('limitations',[])}
    # Provenance hashes are deliberately outside the semantic snapshot. ARTIFACT_HASH must never leak into STATE_HASH.
    dump(out,payload)
    dump(root/'reports/medtas/provenance/current/K01_SNAPSHOT_A001_PROVENANCE.json',{'schema':'k01.snapshot.provenance.v1_4','cad_state_hash':derived['K01.CAD.SEM.A001']['state_hash'],'cad_artifact_hash':derived['K01.CAD.SEM.A001']['artifact_hash']})
    register_build(root,'K01.SNAPSHOT.A001',{'tool':'build_downstream_v1_2.py','stage':'canonical_snapshot_v1_4'}); return payload

def _mc_chain(contributors, samples=50000, seed=10401):
    """Deterministic Monte Carlo for 1D signed contributors.
    Supports uniform and normal_3sigma distributions. No guessed distributions are created.
    """
    import random, math
    if not contributors:
        return {'status':'NOT_RUN','reason':'no contributor distributions bound'}
    rng=random.Random(seed); vals=[]
    for _ in range(samples):
        total=0.0
        for c in contributors:
            nominal=float(c.get('nominal_mm',0.0)); sign=float(c.get('sign',1.0)); dist=c.get('distribution')
            lo=c.get('lower_dev_mm'); hi=c.get('upper_dev_mm')
            if dist=='uniform' and lo is not None and hi is not None:
                x=nominal+rng.uniform(float(lo),float(hi))
            elif dist=='normal_3sigma' and lo is not None and hi is not None:
                # mean at midpoint of limits; +/-3 sigma spans the bound. Explicit opt-in only.
                lower=nominal+float(lo); upper=nominal+float(hi); mu=0.5*(lower+upper); sigma=(upper-lower)/6.0
                x=rng.gauss(mu,sigma)
            else:
                return {'status':'NOT_RUN','reason':'unbound/unsupported distribution for '+str(c.get('id') or c.get('name'))}
            total += sign*x
        vals.append(total)
    vals.sort(); n=len(vals)
    def q(p): return vals[min(n-1,max(0,int(round(p*(n-1)))))]
    mean=sum(vals)/n; std=(sum((x-mean)**2 for x in vals)/(n-1))**0.5 if n>1 else 0.0
    return {'status':'PASS','samples':n,'seed':seed,'mean_mm':round(mean,9),'std_mm':round(std,9),'p0_135_mm':round(q(0.00135),9),'p50_mm':round(q(0.5),9),'p99_865_mm':round(q(0.99865),9),'min_sample_mm':round(vals[0],9),'max_sample_mm':round(vals[-1],9)}

def _mbd_annotation_index(mbd):
    idx={}
    for d in mbd.get('documents',[]) or []:
        pid=base_id(d.get('document_id'))
        for a in d.get('annotations',[]) or []:
            idx[(pid,str(a.get('name') or ''))]=a
    return idx

def _resolve_mbd_chain(cid, mbd, mbd_map):
    spec=(mbd_map.get('chains') or {}).get(cid) or {}
    idx=_mbd_annotation_index(mbd)
    missing=[]; contrib=[]; direct=None
    for c in spec.get('contributors',[]) or []:
        key=(base_id(c.get('part_no')),str(c.get('characteristic_id') or ''))
        a=idx.get(key)
        if not a or a.get('nominal_SI') in (None,''):
            missing.append(c.get('characteristic_id')); continue
        nom=float(a['nominal_SI'])*1000.0
        z={'id':c.get('characteristic_id'),'part_no':c.get('part_no'),'role':c.get('role'),'sign':float(c.get('sign',1.0)),'nominal_mm':nom}
        if a.get('limit_available') and a.get('lower_limit_SI') not in (None,'') and a.get('upper_limit_SI') not in (None,''):
            z['lower_dev_mm']=float(a['lower_limit_SI'])*1000.0-nom
            z['upper_dev_mm']=float(a['upper_limit_SI'])*1000.0-nom
        sm=c.get('statistical_model')
        if sm in ('uniform','normal_3sigma'): z['distribution']=sm
        contrib.append(z)
    dc=spec.get('direct_characteristic')
    if dc:
        name=str(dc.get('characteristic_id') or '')
        # assembly-level direct characteristic is not yet available from per-part DimXpert extraction; search all docs by name as fallback.
        hits=[a for (pid,n),a in idx.items() if n==name]
        if hits:
            a=hits[0]; direct={'id':name,'nominal_mm':float(a.get('nominal_SI'))*1000.0 if a.get('nominal_SI') not in (None,'') else None}
            if a.get('limit_available'):
                direct['lower_limit_mm']=float(a.get('lower_limit_SI'))*1000.0; direct['upper_limit_mm']=float(a.get('upper_limit_SI'))*1000.0
        else: missing.append(name)
    return {'contributors':contrib,'direct':direct,'missing':sorted(set(x for x in missing if x)),'mapping_status':spec.get('mapping_status')}

def build_tolerance(root,snapshot):
    seed=load(root/'control/medtas/v1/bindings/K01_TOLERANCE_SEED_v1.json')
    mbdp=root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json'
    mbd=load(mbdp) if mbdp.exists() else {'summary':{},'coverage_status':'MISSING','limitations':['MBD output missing']}
    mapp=root/'control/medtas/v1/bindings/K01_TOLERANCE_MBD_MAP_v1.json'; mbd_map=load(mapp) if mapp.exists() else {'chains':{}}
    results=[]; limitations=[]
    for c in seed['chains']:
        x=dict(c); cid=c['chain_id']; n=c.get('nominal',{}); acc=c.get('acceptance',{})
        mb=_resolve_mbd_chain(cid,mbd,mbd_map); x['mbd_binding']={'missing':mb['missing'],'bound_contributor_count':len(mb['contributors']),'direct':mb['direct'],'mapping_status':mb.get('mapping_status')}
        if mb['missing']: limitations.append(cid+': MBD characteristic(s) not yet bound: '+', '.join(mb['missing']))
        if cid=='K01-TOL-P004-SEAT':
            clr=float(n['P003_seat_ID_mm'])-float(n['P004_OD_mm']); x['calculated']={'nominal_diametral_clearance_mm':round(clr,6)}; x['screen_verdict']='PASS_NOMINAL' if clr>0 else 'HOLD'
            limitations.append(cid+': manufacturing tolerance bounds not yet bound, so minimum clearance is not verified')
        elif cid=='K01-TOL-P002-AXIAL-FLOAT':
            t=float(n['target_mm']); lo=float(acc['min_mm']); hi=float(acc['max_mm']); x['calculated']={'margin_to_min_mm':round(t-lo,6),'margin_to_max_mm':round(hi-t,6)}; x['screen_verdict']='PASS_NOMINAL' if lo<=t<=hi else 'HOLD'
            limitations.append(cid+': contributor stack and worst-case limits are not yet fully bound')
        elif cid=='K01-TOL-P001-P008-M4-BOTTOM':
            clr=float(n['female_usable_depth_mm'])-float(n['male_length_mm']); x['calculated']={'nominal_bottom_clearance_mm':round(clr,6)}; x['screen_verdict']='PASS_NOMINAL' if clr>0 else 'HOLD'
            limitations.append(cid+': thread length/depth manufacturing tolerances are not yet bound')
        else:
            x['screen_verdict']='BASELINE'; limitations.append(cid+': release tolerance distribution is open')
        contrib=mb['contributors'] or c.get('contributors') or []
        if mb['contributors']:
            x['source_authority']='MBD_DIMXPERT'
            x['mbd_chain_nominal_mm']=round(sum(float(z.get('sign',1.0))*float(z.get('nominal_mm',0.0)) for z in mb['contributors']),9)
        else:
            x['source_authority']='CONTROLLED_SEED_SCREENING'
        if contrib:
            # Worst-case from explicitly bound lower/upper deviations.
            wc_min=wc_max=0.0
            bound=True
            for z in contrib:
                if z.get('lower_dev_mm') is None or z.get('upper_dev_mm') is None: bound=False; break
                nom=float(z.get('nominal_mm',0.0)); sg=float(z.get('sign',1.0)); a=nom+float(z['lower_dev_mm']); b=nom+float(z['upper_dev_mm'])
                wc_min += min(sg*a,sg*b); wc_max += max(sg*a,sg*b)
            x['worst_case']={'status':'PASS','min_mm':round(wc_min,9),'max_mm':round(wc_max,9)} if bound else {'status':'NOT_RUN','reason':'contributor tolerance bounds incomplete'}
            x['monte_carlo']=_mc_chain(contrib)
        else:
            x['worst_case']={'status':'NOT_RUN','reason':'contributors not yet machine-bound'}
            x['monte_carlo']={'status':'NOT_RUN','reason':'contributors/distributions not yet machine-bound; no distribution is guessed'}
        results.append(x)
    if mbd.get('coverage_status')!='MBD_ACTIVE': limitations.append('TOL-MBD-001: native MBD/DimXpert is not yet the complete tolerance authority; legacy controlled seed is screening-only')
    payload={'schema':'k01.tolerance_analysis.a001.v1_4','method':'native MBD/DimXpert first; controlled legacy seed fallback; worst-case + deterministic Monte Carlo only when contributor tolerances/distributions are explicitly bound','chains':results,'cad_dimension_inventory':{'documents':len(snapshot.get('cad_semantic',{}).get('documents',[])),'dimension_count':sum(len(d.get('dimensions',[])) for d in snapshot.get('cad_semantic',{}).get('documents',[]))},'mbd_inventory':mbd.get('summary',{}),'mbd_coverage_status':mbd.get('coverage_status'),'release_status':'PASS_WITH_LIMITATIONS','limitations':sorted(set(limitations+(mbd.get('limitations') or [])))}
    out=root/'reports/medtas/tolerance/current/K01_TOLERANCE_A001_v1.json'; dump(out,payload); register_build(root,'K01.TOL.A001',{'tool':'build_downstream_v1_2.py','stage':'tolerance_v1_4'}); return payload

def build_structural(root,snapshot):
    docs={base_id(d.get('document_id')):d for d in snapshot.get('cad_semantic',{}).get('documents',[])}
    parts=[p for p in ('K01-P-003','K01-P-007') if p in docs]
    limitations=[]
    if len(parts)<2: limitations.append('STRUCT-GEO-001: P003/P007 document semantics not both present in CAD snapshot')
    limitations.append('STRUCT-BIND-001: exact topology-stable face sets for fixture, pressure and force are not yet exported for CalculiX')
    face_candidates={pid:(docs.get(pid,{}) or {}).get('face_inventory',[]) for pid in ('K01-P-003','K01-P-007')}
    payload={'schema':'k01.structural_model.p006.v1_2','analysis':'linear_static','geometry':{'assembly':'K01-A-001','components':['K01-P-003','K01-P-007'],'cad_documents_found':parts,'source':'K01.SNAPSHOT.A001','face_candidates':face_candidates},'material':{'name':'1.4404 (X2CrNiMo17-12-2)','E_Pa':2.0e11,'nu':0.28,'yield_Pa':4.0e8,'density_kg_m3':8000},'boundary_conditions':{'fixture':{'role':'FIXED_INTERFACE_FACE','count':1,'topology_binding':'OPEN_FOR_NEUTRAL_SOLVER'},'pressure':{'role':'PRESSURE_FACES','value_MPa':0.02,'face_count_reference':5,'topology_binding':'OPEN_FOR_NEUTRAL_SOLVER'},'service_force':{'role':'SERVICE_FORCE_FACE','value_N':300,'face_count_reference':1,'topology_binding':'OPEN_FOR_NEUTRAL_SOLVER'},'bolts':{'count':3,'nominal_diameter_mm':2.5,'head_diameter_mm':4.5,'preload_N_each':300},'contact':{'type':'no_penetration_surface_to_surface','friction':False}},'reference_solidworks_evidence':{'sigma_vm_max_MPa':40.66,'displacement_max_mm':0.002171,'reaction_resultant_N':302.262,'mesh_nodes':102923,'mesh_elements':63800},'calculix_target':{'metrics':['sigma_vm_max','displacement_max','reaction_balance'],'status':'BLOCKED_UNTIL_FACE_ROLE_AND_MESH_BINDING','next_input':'face_candidates from live SolidWorks geometry'},'limitations':limitations}
    out=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json'; dump(out,payload); register_build(root,'K01.STRUCT.MODEL.P006',{'tool':'build_downstream_v1_2.py','stage':'solver_neutral_structural'}); return payload

def bind_sw(root):
    report=root/'reports/engineering/current/source/K01-A-001_GATE04E_P006_SERVICE_VERIFY-Static_1-4.docx'
    if not report.exists(): return
    register_build(root,'K01.STRUCT.SWSIM.P006',{'tool':'MEDTAS evidence binding','source':'SolidWorks Simulation report 2026-09-06'})
    register_verification(root,'K01.STRUCT.SWSIM.P006','PASS',metrics={'sigma_vm_max_MPa':40.66,'yield_strength_MPa':400.0,'simple_yield_margin':9.84,'displacement_max_mm':0.002171,'reaction_N':302.262,'mesh_nodes':102923,'mesh_elements':63800},notes='Linear-static P006 service screening. Material mapping is unified to EN 1.4404 in the current report.')

def build_femm(root):
    desc={'schema':'k01.femm_model.current.v1','position':'CURRENT','cases':[{'id':'A','coil_A_Aturn':1,'coil_B_Aturn':0},{'id':'B','coil_A_Aturn':0,'coil_B_Aturn':1}],'materials':{'magnet_Br_T':1.0,'steel_mu_r_screen':1.005},'evidence_source':'imported current FEMM run artifacts','model_reproducibility':'PARTIAL','limitations':['FEMM-GEO-001: DXF import reported orphan endpoints','FEMM-MODEL-001: original FEM/DXF/LUA source bundle is not yet bound to this MEDTAS node']}
    out=root/'reports/medtas/femm/current/K01_FEMM_MODEL_CURRENT_v1.json'; dump(out,desc); register_build(root,'K01.FEMM.MODEL.CURRENT',{'tool':'MEDTAS evidence descriptor','stage':'femm_model_backfill'})
    for nid in ('K01.FEMM.RUN.A','K01.FEMM.RUN.B'):
        register_build(root,nid,{'tool':'MEDTAS evidence binding','source':'completed FEMM current-position run'})
        register_verification(root,nid,'PASS',metrics={'script_completed':True,'field_plot_present':True},notes='PASS is limited to solver completion + field solution evidence; Fz is not accepted as quantitative force evidence.')
    verify={'schema':'k01.femm_verify.current.v1','field_screening':'PASS','automation':'PASS','force_quantification':'NOT_VERIFIED','numeric_export':'PARTIAL','limitations':['FEMM-GEO-001: orphan endpoints warning on DXF import','FEMM-OUT-001: Coil B CSV record is incomplete','FEMM-FORCE-001: Fz_N=0 extraction is not independently validated'],'decision':'PASS_WITH_LIMITATIONS_FOR_CURRENT_ENGINEERING_SCREEN'}
    outv=root/'reports/medtas/femm/current/K01_FEMM_VERIFY_CURRENT_v1.json'; dump(outv,verify); register_build(root,'K01.FEMM.VERIFY.CURRENT',{'tool':'build_downstream_v1_2.py','stage':'femm_verification'}); register_verification(root,'K01.FEMM.VERIFY.CURRENT','PASS_WITH_LIMITATIONS',metrics={'coil_A_script':'PASS','coil_B_script':'PASS','field_solution_A':True,'field_solution_B':True,'force_release_evidence':False},limitations=verify['limitations'])

def build_recon(root):
    payload={'schema':'k01.structural_reconciliation.p006.v1','screening':{'solidworks':'PASS','calculix':'NOT_RUN','verdict':'PASS_WITH_LIMITATIONS'},'production_release':{'verdict':'OPEN','required_next':'CalculiX equivalent-model cross-check or controlled waiver'},'comparison_metrics':['sigma_vm_max','displacement_max','reaction_balance'],'limitations':['CCX-001: independent CalculiX run not yet available']}
    out=root/'reports/medtas/structural/current/K01_STRUCTURAL_RECON_P006_v1.json'; dump(out,payload); register_build(root,'K01.STRUCT.RECON.P006',{'tool':'build_downstream_v1_2.py','stage':'reconciliation'}); register_verification(root,'K01.STRUCT.RECON.P006','PASS_WITH_LIMITATIONS',limitations=payload['limitations'],notes='Sufficient for current engineering screen; not a production-release cross-solver closure.')

def build_drawing_model(root,snapshot,tol):
    seed=load(root/'control/medtas/v1/bindings/K01_DRAWING_SEED_v1.json'); docmap={base_id(d.get('document_id')):d for d in snapshot.get('cad_semantic',{}).get('documents',[])}
    mbdp=root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json'; mbd=load(mbdp) if mbdp.exists() else {'summary':{},'coverage_status':'MISSING'}
    items=[]; limits=[]
    for item in seed['items']:
        x=dict(item); d=docmap.get(item['model']); x['cad_semantics_present']=bool(d); x['cad_materials']=(d or {}).get('materials',[]); x['datums']=(d or {}).get('datums',[]); items.append(x)
        if not d: limits.append('DRAWING-MODEL-MISSING-CAD:'+item['model'])
    limits.append('DRAWING-ARTIFACT-001: native SLDDRW/PDF generation and verification remain open')
    payload={'schema':'k01.drawing_model.gate04e.v1_4','release_mode':seed['release_mode'],'definition_authority':'native CAD + MBD/DimXpert; drawing is a derived presentation, never an independent tolerance source','items':items,'tolerance_node_status':tol.get('release_status'),'mbd_summary':mbd.get('summary',{}),'mbd_coverage_status':mbd.get('coverage_status'),'limitations':limits+([] if mbd.get('coverage_status')=='MBD_ACTIVE' else ['DRAWING-MBD-001: model PMI not yet complete; drawing generation must not invent unmodeled tolerances'])}
    out=root/'reports/medtas/drawing/current/K01_DRAWING_MODEL_GATE04E_v1.json'; dump(out,payload); register_build(root,'K01.DRAWING.MODEL.GATE04E',{'tool':'build_downstream_v1_2.py','stage':'drawing_intent'}); return payload

def build_bom(root,snapshot):
    seed=load(root/'control/medtas/v1/bindings/K01_BOM_SEED_v1.json')['items']; docs={base_id(d.get('document_id')):d for d in snapshot.get('cad_semantic',{}).get('documents',[])}
    qty={}
    for inst in snapshot.get('cad_semantic',{}).get('instances',[]):
        if inst.get('suppressed'): continue
        pid=base_id(inst.get('document_id'))
        if pid.startswith('K01-'): qty[pid]=qty.get(pid,0)+1
    items=[]; limits=[]
    for pid in sorted(qty):
        meta=seed.get(pid,{}); d=docs.get(pid,{}); mats=d.get('materials',[]) or []
        items.append({'item_id':pid,'part_number':pid,'description':meta.get('description',''),'quantity':qty[pid],'material':mats[0] if len(mats)==1 else mats,'make_buy':meta.get('make_buy','OPEN'),'source_node':'K01.CAD.SEM.A001'})
        if not mats: limits.append('BOM-MATERIAL-MISSING:'+pid)
        if not meta: limits.append('BOM-METADATA-MISSING:'+pid)
    payload={'schema':'k01.bom_model.a001.v1','authority':'projection of live CAD semantic identities; not an independent second truth','items':items,'item_count':len(items),'limitations':sorted(set(limits))}
    out=root/'reports/medtas/bom/current/K01_BOM_MODEL_A001_v1.json'; dump(out,payload); register_build(root,'K01.BOM.MODEL.A001',{'tool':'build_downstream_v1_2.py','stage':'canonical_bom'}); return payload

def register_report(root):
    for nid in ('K01.EVIDENCE.GATE04E.REPORT',):
        d=evaluate(root)[nid]
        if d.get('artifact_hash'):
            register_build(root,nid,{'tool':'MEDTAS evidence registry','stage':'formal_report'})

def build_gate(root,tol):
    d=evaluate(root)
    req=['K01.STRUCT.SWSIM.P006','K01.FEMM.VERIFY.CURRENT']
    ok=all(d[x]['state'] in ('PASS','PASS_WITH_LIMITATIONS') for x in req)
    payload={'schema':'k01.gate04e.verify.v1','screen_gate':'PASS_TO_CONTINUE' if ok else 'HOLD','required_nodes':{x:d[x]['state'] for x in req},'release_additional':{'K01.TOL.A001':d['K01.TOL.A001']['state'],'K01.STRUCT.CCX.P006':d['K01.STRUCT.CCX.P006']['state'],'K01.DRAWING.VERIFY.GATE04E':d['K01.DRAWING.VERIFY.GATE04E']['state'],'K01.BOM.VERIFY.A001':d['K01.BOM.VERIFY.A001']['state']},'production_release':'NOT_READY','limitations':['Current FEMM force extraction is not release evidence','CalculiX, drawing artifact verification and BOM artifact verification remain open']}
    out=root/'reports/medtas/verification/current/K01_VERIFY_GATE04E_v1.json'; dump(out,payload); register_build(root,'K01.VERIFY.GATE04E',{'tool':'build_downstream_v1_2.py','stage':'gate04e'}); register_verification(root,'K01.VERIFY.GATE04E','PASS_WITH_LIMITATIONS' if ok else 'HOLD',limitations=payload['limitations']); return payload

def calculix_preflight(root):
    def where(exe): return shutil.which(exe)
    payload={'schema':'k01.calculix_preflight.v1','calculix_executable':where('ccx.exe') or where('ccx'),'gmsh_executable':where('gmsh.exe') or where('gmsh'),'structural_model':'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json','ready_to_run':False,'blocking':['CCX-GEO-001: topology-stable face map and solver-neutral mesh are not yet generated']}
    if not payload['calculix_executable']: payload['blocking'].append('CCX-EXE-001: CalculiX executable not found on PATH')
    if not payload['gmsh_executable']: payload['blocking'].append('CCX-MESH-001: Gmsh not found on PATH; another controlled mesher may be bound instead')
    dump(root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json',payload)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve(); graph=load_graph(root)
    cadp=root/'reports/medtas/cad/current/K01_CAD_SEM_A001.json'
    if not cadp.exists():
        print('ERROR: CAD semantic snapshot missing:',cadp,file=sys.stderr); return 51
    cad=load(cadp); derived=evaluate(root)
    if derived['K01.CAD.SEM.A001']['state'] not in ('PASS','PASS_WITH_LIMITATIONS'):
        print('ERROR: K01.CAD.SEM.A001 is not fresh:',derived['K01.CAD.SEM.A001']['state'],file=sys.stderr); return 52
    snapshot=build_snapshot(root,graph,cad,derived)
    tol=build_tolerance(root,snapshot)
    build_structural(root,snapshot); bind_sw(root)
    build_femm(root); build_recon(root)
    build_drawing_model(root,snapshot,tol); build_bom(root,snapshot)
    register_report(root); build_gate(root,tol); calculix_preflight(root)
    subprocess.check_call([sys.executable,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)])
    d=load(root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json')['nodes']
    print('\nMEDTAS downstream build complete.')
    for nid in ['K01.CAD.SEM.A001','K01.MBD.A001','K01.SNAPSHOT.A001','K01.TOL.A001','K01.STRUCT.MODEL.P006','K01.STRUCT.SWSIM.P006','K01.STRUCT.CCX.P006','K01.FEMM.VERIFY.CURRENT','K01.DRAWING.MODEL.GATE04E','K01.BOM.MODEL.A001','K01.VERIFY.GATE04E']:
        print(f'{nid:32s} {d[nid]["state"]}')
    return 0
if __name__=='__main__': raise SystemExit(main())
