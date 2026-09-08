from __future__ import annotations
import argparse,math,re
from pathlib import Path
from medtas_v16_common import load,dump,sha256_obj,register_build,register_verify

def f(x):
    try:return float(x)
    except Exception:return None

def span_x(face):
    b=face.get('box_m') or []
    return abs(f(b[3])-f(b[0])) if len(b)>=6 and f(b[3]) is not None and f(b[0]) is not None else None

def radius(face):
    p=face.get('cylinder_params') or []
    return abs(f(p[-1])) if p and f(p[-1]) is not None else None

def center_r(face):
    p=face.get('cylinder_params') or []
    if len(p)<3:return None
    y,z=f(p[1]),f(p[2])
    return math.hypot(y,z) if y is not None and z is not None else None

def near(a,b,tol=2e-6):return a is not None and abs(a-b)<=tol

def mm(x):return None if x is None else round(x*1000,6)

def unique(rows,label):
    if len(rows)==1:return rows[0],None
    if not rows:return None,label+':NOT_FOUND'
    return None,label+':AMBIGUOUS:'+str(len(rows))

def parse_nums(s):
    return [float(x.replace(',','.')) for x in re.findall(r'(?<![A-Za-z])\d+(?:[\.,]\d+)?',str(s or ''))]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    cad=load(r/'reports/medtas/cad/current/K01_CAD_SEM_A001.json',{}) or {};spec=load(r/'control/drawings/K01-D-006_P007_EXEMPLAR_v1_9.json',{}) or {};j2=load(r/'control/parameters/K01_J2_INTERFACE_PARAMETERS_v1_7.json',{}) or {}
    doc=next((d for d in cad.get('documents',[]) or [] if str(d.get('document_id','')).startswith('K01-P-007')),None)
    out=r/'reports/drawing/current/K01-D-006_P007_LIVE_GEOMETRY_CURRENT.json'
    if not doc:
        dump(out,{'schema':'k01.p007_live_geometry.v2_0','status':'HOLD','issues':['P007-CAD-SEMANTIC-MISSING']});print('HOLD P007 live geometry: CAD semantic document missing');return 2
    faces=doc.get('face_inventory',[]) or [];cyl=[x for x in faces if str(x.get('surface_type')).lower()=='cylinder'];issues=[]
    flange,e=unique([x for x in cyl if near(radius(x),0.0165)],'FLANGE_OD33');issues += [e] if e else []
    locator,e=unique([x for x in cyl if near(radius(x),0.00705) and (span_x(x) or 0)>.0005],'LOCATOR_D14P10');issues += [e] if e else []
    thin_od,e=unique([x for x in cyl if near(radius(x),0.005) and (span_x(x) or 0)>.02],'THIN_OD10');issues += [e] if e else []
    thin_id,e=unique([x for x in cyl if near(radius(x),0.0047) and (span_x(x) or 0)>.02],'THIN_ID9P4');issues += [e] if e else []
    holes=[x for x in cyl if near(radius(x),0.00145) and near(span_x(x),0.003,5e-6)]
    # overall X envelope from all face boxes
    xs=[]
    for x in faces:
        b=x.get('box_m') or []
        if len(b)>=6:
            for q in (b[0],b[3]):
                v=f(q)
                if v is not None:xs.append(v)
    live={
      'flange_od_mm':mm(2*radius(flange)) if flange else None,
      'flange_thickness_mm':mm(span_x(flange)) if flange else None,
      'locator_od_mm':mm(2*radius(locator)) if locator else None,
      'locator_length_mm':mm(span_x(locator)) if locator else None,
      'clearance_hole_count':len(holes),
      'clearance_hole_diameter_mm':mm(2*radius(holes[0])) if holes else None,
      'fastener_pcd_mm':mm(2*(sum(center_r(x) for x in holes if center_r(x) is not None)/len(holes))) if holes else None,
      'thin_can_od_mm':mm(2*radius(thin_od)) if thin_od else None,
      'thin_can_id_mm':mm(2*radius(thin_id)) if thin_id else None,
      'overall_length_mm':round((max(xs)-min(xs))*1000,6) if xs else None,
    }
    # controlled parameter reconciliation
    cp=(j2.get('interface') or {});recon=[]
    pairs=[('flange_od_mm','flange_od_mm'),('locator_od_mm','pilot_nominal_diameter_mm'),('fastener_pcd_mm','fastener_pcd_mm'),('overall_length_mm','p007_overall_length_mm')]
    for lk,pk in pairs:
        lv,pv=live.get(lk),cp.get(pk);ok=(lv is not None and pv is not None and abs(float(lv)-float(pv))<=0.001)
        recon.append({'live_key':lk,'parameter_key':pk,'live_mm':lv,'controlled_mm':pv,'status':'MATCH' if ok else 'MISMATCH'})
        if not ok:issues.append('P007-CONTROLLED-PARAM-MISMATCH:'+lk)
    # legacy draft candidate reconciliation; this is diagnostic only and never promotes the draft to authority.
    cmap={c.get('id'):c for c in spec.get('characteristics',[]) or []};checks=[]
    def add(cid,fields,vals):
        c=cmap.get(cid,{}) ; nums=parse_nums(c.get('candidate_spec'))
        # fields is sequence of (live key, index in parsed numeric list)
        details=[];ok=True
        for live_key,idx in fields:
            cand=nums[idx] if idx<len(nums) else None;lv=vals.get(live_key)
            same=lv is not None and cand is not None and abs(float(lv)-float(cand))<=0.001
            details.append({'live_key':live_key,'live':lv,'legacy_candidate':cand,'status':'MATCH' if same else 'MISMATCH'});ok &= same
        checks.append({'characteristic_id':cid,'source_candidate':c.get('candidate_spec'),'status':'MATCH' if ok else 'CONFLICT','details':details})
        if not ok:issues.append('P007-LEGACY-DRAFT-CONFLICT:'+cid)
    add('C02',[('locator_od_mm',0),('locator_length_mm',1)],live)
    # C04 contains semantic prefixes (3x, diameter, PCD). Parse by labels rather than positional number order.
    c04=cmap.get('C04',{});txt=str(c04.get('candidate_spec') or '')
    md=re.search(r'Ø\s*(\d+(?:[\.,]\d+)?)',txt);mp=re.search(r'PCD\s*(\d+(?:[\.,]\d+)?)',txt,re.I)
    details=[];ok=True
    for key,val in [('clearance_hole_diameter_mm', float(md.group(1).replace(',','.')) if md else None),('fastener_pcd_mm', float(mp.group(1).replace(',','.')) if mp else None)]:
        lv=live.get(key);same=lv is not None and val is not None and abs(float(lv)-float(val))<=0.001;details.append({'live_key':key,'live':lv,'legacy_candidate':val,'status':'MATCH' if same else 'MISMATCH'});ok &= same
    checks.append({'characteristic_id':'C04','source_candidate':txt,'status':'MATCH' if ok else 'CONFLICT','details':details})
    if not ok:issues.append('P007-LEGACY-DRAFT-CONFLICT:C04')
    add('C05',[('flange_od_mm',0),('flange_thickness_mm',2)],live)             # ±0.05 is parsed between them
    add('C06',[('overall_length_mm',0)],live)
    add('C07',[('thin_can_od_mm',0)],live)
    add('C08',[('thin_can_id_mm',0)],live)
    payload={'schema':'k01.p007_live_geometry.v2_0','status':'PASS_WITH_CONFLICTS' if issues else 'PASS','authority':'live canonical CAD semantic geometry; legacy drawing values are comparison candidates only','document_id':doc.get('document_id'),'live_geometry':live,'controlled_parameter_reconciliation':recon,'legacy_draft_reconciliation':checks,'issues':sorted(set(x for x in issues if x)),'semantic_payload_hash':sha256_obj({'live_geometry':live,'controlled_parameter_reconciliation':recon})}
    dump(out,payload)
    try:
        register_build(r,'K01.DRAWING.P007.LIVE.GEOMETRY',{'tool':'build_p007_geometry_authority_v2_0.py','authority':'live canonical CAD nominal geometry'})
        register_verify(r,'K01.DRAWING.P007.LIVE.GEOMETRY','PASS_WITH_LIMITATIONS' if payload['issues'] else 'PASS',metrics={'issues':len(payload['issues']),'live_geometry':live},limitations=payload['issues'])
    except Exception as e: print('WARN P007 live geometry record registration:',e)
    print('P007 live geometry:',payload['status']);print(' - flange OD/thickness =',live['flange_od_mm'],'/',live['flange_thickness_mm'],'mm');print(' - locator OD/length   =',live['locator_od_mm'],'/',live['locator_length_mm'],'mm');print(' - holes               =',live['clearance_hole_count'],'x',live['clearance_hole_diameter_mm'],'PCD',live['fastener_pcd_mm']);print(' - thin can OD/ID      =',live['thin_can_od_mm'],'/',live['thin_can_id_mm'],'mm');print(' - overall length      =',live['overall_length_mm'],'mm')
    for x in payload['issues']:print(' -',x)
    print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
