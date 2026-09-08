from __future__ import annotations
import argparse, json, math
from pathlib import Path
from medtas_v16_common import load, dump, base_id, register_build, register_verify

ACCEPTED={'DEFINED_IN_MBD','VERIFIED_NATIVE_DATUM','VERIFIED_NATIVE_DIMENSION','VERIFIED_NATIVE_GEOMETRY','CONTROLLED_PARAMETER_VERIFIED','DERIVED_NON_DIMENSIONAL'}

DATUM_BINDINGS={
    'K01-D003-DATUM-A':('K01-P-003','K01_DATUM_A_MATING'),
    'K01-D003-DATUM-B':('K01-P-003','K01_DATUM_B_AXIS'),
}
INTERFACE_BINDINGS={
    'K01-D003-PILOT':['pilot_nominal_diameter_mm','pilot_fit'],
    'K01-D003-FASTENER-PATTERN':['fastener_count','fastener_thread','fastener_pcd_mm'],
    'K01-D006-LOCATOR':['pilot_nominal_diameter_mm','pilot_fit'],
}

# Characteristics whose nominal source exists but whose manufacturing tolerance/specification is explicitly still OPEN.
OPEN_TOLERANCE_IDS={'K01-CHAR-P003-SEAT-ID','K01-CHAR-P001-M4-MALE-LENGTH','K01-CHAR-A001-ROD-TRAVEL'}

def annotations(mbd):
    out=set()
    for d in mbd.get('documents',[]) or []:
        pid=base_id(d.get('document_id'))
        for a in d.get('annotations',[]) or []:
            n=a.get('name')
            if n: out.add((pid,str(n)))
    return out

def cad_docs(cad):return {base_id(d.get('document_id')):d for d in cad.get('documents',[]) or []}

def has_datum(doc,name):
    return any(str(d.get('name'))==name and not d.get('suppressed',False) for d in (doc or {}).get('datums',[]) or [])

def candidate_map(c):return {x.get('characteristic_id'):x for x in c.get('rows',[]) or []}

def tol_state(seed,cid):
    # Only characteristics currently used by the controlled tolerance seed are mapped here.
    chain_by_char={'K01-CHAR-P003-SEAT-ID':'K01-TOL-P004-SEAT','K01-CHAR-P001-M4-MALE-LENGTH':'K01-TOL-P001-P008-M4-BOTTOM','K01-CHAR-A001-ROD-TRAVEL':'K01-TOL-ROD-TRAVEL'}
    chain=chain_by_char.get(cid)
    if not chain:return None
    for x in seed.get('chains',[]) or []:
        if x.get('chain_id')==chain:return x.get('release_tolerance_state')
    return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    reg=load(r/'control/drawings/K01_DRAWING_CHARACTERISTICS_v1_7.json',{}) or {}
    cad=load(r/'reports/medtas/cad/current/K01_CAD_SEM_A001.json',{}) or {};docs=cad_docs(cad)
    mbd=load(r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',{}) or {};ann=annotations(mbd)
    cand=load(r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_7.json',{}) or {};cm=candidate_map(cand)
    iface=(load(r/'control/parameters/K01_J2_INTERFACE_PARAMETERS_v1_7.json',{}) or {}).get('interface',{})
    tseed=load(r/'control/medtas/v1/bindings/K01_TOLERANCE_SEED_v1.json',{}) or {}
    rows=[];blocking=[];accepted=0
    for dr in reg.get('drawings',[]) or []:
        pid=base_id(dr.get('model'));doc=docs.get(pid);drow={'drawing_no':dr.get('drawing_no'),'model':dr.get('model'),'title':dr.get('title'),'characteristics':[]}
        for c in dr.get('characteristics',[]) or []:
            cid=c.get('id');x=dict(c);x['definition_state']='SEMANTIC_BIND_REQUIRED';x['source']=None;x['evidence']={}
            if (pid,cid) in ann:
                x['definition_state']='DEFINED_IN_MBD';x['source']='native_mbd_annotation'
            elif c.get('status')=='OPEN_SPEC':
                x['definition_state']='OPEN_SPEC';x['source']=c.get('authority')
            elif c.get('authority') in ('material_state','canonical_bom') and c.get('status')=='DEFINED_IN_CONTROL':
                x['definition_state']='DERIVED_NON_DIMENSIONAL';x['source']=c.get('authority')
            elif cid in DATUM_BINDINGS:
                p,dn=DATUM_BINDINGS[cid];d=docs.get(base_id(p));x['evidence']={'datum_name':dn,'document':p,'present':has_datum(d,dn)}
                if has_datum(d,dn):x['definition_state']='VERIFIED_NATIVE_DATUM';x['source']='cad_semantic.datums'
            elif cid in INTERFACE_BINDINGS:
                keys=INTERFACE_BINDINGS[cid];vals={k:iface.get(k) for k in keys};complete=all(v not in (None,'') for v in vals.values())
                x['evidence']={'controlled_parameters':vals,'cad_model_present':bool(doc)}
                if complete and (bool(doc) or dr.get('model')=='K01-A-001'):x['definition_state']='CONTROLLED_PARAMETER_VERIFIED';x['source']='controlled_parameter+cad_presence'
            elif cid in cm:
                cc=cm[cid];st=cc.get('status');x['evidence']={'candidate_status':st,'candidates':cc.get('candidates',[])}
                if st=='CANDIDATE_UNIQUE':x['definition_state']='VERIFIED_NATIVE_DIMENSION';x['source']='cad_semantic.native_dimension'
                elif st=='GEOMETRY_CANDIDATE_UNIQUE':x['definition_state']='VERIFIED_NATIVE_GEOMETRY';x['source']='cad_semantic.face_geometry'
                elif st=='AMBIGUOUS':x['definition_state']='AMBIGUOUS';x['source']='candidate_discovery'
            # Manufacturing tolerance is a different layer than nominal/native ownership.
            ts=tol_state(tseed,cid);x['tolerance_release_state']=ts
            if x['definition_state'] in ACCEPTED and cid in OPEN_TOLERANCE_IDS and ts not in ('RELEASED','CONTROLLED'):
                x['definition_state']='OPEN_TOLERANCE_SPEC';x['source']=(x.get('source') or '')+'+tolerance_seed'
            x['accepted_for_drawing']=x['definition_state'] in ACCEPTED
            if x['accepted_for_drawing']:accepted+=1
            else:blocking.append(cid)
            drow['characteristics'].append(x)
        drow['ready_characteristics']=sum(1 for x in drow['characteristics'] if x['accepted_for_drawing'])
        drow['total_characteristics']=len(drow['characteristics'])
        drow['definition_verdict']='PASS' if drow['ready_characteristics']==drow['total_characteristics'] else 'HOLD'
        rows.append(drow)
    payload={'schema':'k01.product_definition.gate04e.v1_8','status':'PASS' if not blocking else 'PASS_WITH_LIMITATIONS','authority':'canonical product definition assembled from native CAD semantics, reviewed MBD when present, controlled parameters/material/BOM and explicit open-spec states','drawings':rows,'summary':{'characteristics':sum(x['total_characteristics'] for x in rows),'accepted':accepted,'blocking':len(set(blocking)),'drawings_ready':sum(1 for x in rows if x['definition_verdict']=='PASS'),'drawings_total':len(rows)},'blocking_characteristics':sorted(set(blocking)),'policy':'MBD is the preferred machine-readable carrier. Reviewed native semantic bindings are explicit transitional authority, never silent guessed values. OPEN tolerance/process/datum specifications remain blockers.'}
    out=r/'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json';dump(out,payload)
    register_build(r,'K01.PRODUCT.DEFINITION.GATE04E',{'tool':'build_product_definition_v1_8.py'})
    register_verify(r,'K01.PRODUCT.DEFINITION.GATE04E',payload['status'],metrics=payload['summary'],limitations=[] if not blocking else ['PRODUCT-DEFINITION-OPEN:'+x for x in sorted(set(blocking))])
    print('Product definition:',out);print(payload['summary']);return 0
if __name__=='__main__':raise SystemExit(main())
