from __future__ import annotations
import hashlib,json,math,re
ID_RE=re.compile(r'(K01-[PBA]-\d{3})',re.I)

def base_id(x):
    m=ID_RE.search(str(x or ''));return m.group(1).upper() if m else str(x or '')

def q(x,nd=12):
    try:
        f=float(x)
        if abs(f)<1e-15:f=0.0
        return float(format(f,f'.{nd}g'))
    except:return x

def qarr(a):return [q(x) for x in (a or [])]

def canon_vec(v):
    v=[q(x) for x in (v or [])]
    if len(v)<3:return v
    n=math.sqrt(sum(float(x)**2 for x in v[:3]))
    if n>0:v=[q(float(x)/n) for x in v[:3]]+v[3:]
    for x in v[:3]:
        if abs(float(x))>1e-12:
            if float(x)<0:v=[q(-float(y)) for y in v]
            break
    return v

def primitive(face):
    typ=str(face.get('surface_type') or 'unknown').lower()
    if typ=='plane':
        a=qarr(face.get('plane_params'))
        if len(a)>=6:
            n=canon_vec(a[:3]);p=[float(x) for x in a[3:6]]
            # canonical plane distance; if normal flipped canon_vec made it positive orientation.
            d=q(sum(float(n[i])*p[i] for i in range(3)))
            return {'normal':n[:3],'offset_m':d}
    if typ=='cylinder':
        a=qarr(face.get('cylinder_params'))
        if len(a)>=7:
            o=[float(x) for x in a[:3]];axis=canon_vec(a[3:6])[:3];dot=sum(o[i]*float(axis[i]) for i in range(3));perp=[q(o[i]-dot*float(axis[i])) for i in range(3)]
            return {'axis':axis,'axis_perp_origin_m':perp,'radius_m':q(a[6])}
    if typ=='cone':
        a=qarr(face.get('cone_params'))
        if len(a)>=8:
            o=[float(x) for x in a[:3]];axis=canon_vec(a[3:6])[:3];dot=sum(o[i]*float(axis[i]) for i in range(3));perp=[q(o[i]-dot*float(axis[i])) for i in range(3)]
            return {'axis':axis,'axis_perp_origin_m':perp,'radius_m':q(a[6]),'half_angle':q(a[7])}
    if typ=='sphere':
        a=qarr(face.get('sphere_params'))
        if len(a)>=4:return {'center_m':a[:3],'radius_m':q(a[3])}
    if typ=='torus':
        a=qarr(face.get('torus_params'))
        if a:return {'params':a}
    return {}

def semantic_descriptor(part,face):
    return {'part':base_id(part or face.get('part_no')),'body':str(face.get('body') or ''),'surface_type':str(face.get('surface_type') or 'unknown').lower(),'primitive':primitive(face),'area_m2':q(face.get('area_m2')),'box_m':qarr(face.get('box_m')),'normal':canon_vec(face.get('normal')),'edge_count':face.get('edge_count')}

def signature(part,face):
    b=json.dumps(semantic_descriptor(part,face),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()

def distance(a,b):
    # Strict semantic distance for fallback matching. Primitive type and topology must agree.
    if str(a.get('surface_type'))!=str(b.get('surface_type')):return float('inf')
    if a.get('edge_count')!=b.get('edge_count'):return float('inf')
    def dif(x,y,scale=1.0):
        try:return abs(float(x)-float(y))/scale
        except:return 1e9
    score=dif(a.get('area_m2'),b.get('area_m2'),max(abs(float(a.get('area_m2') or 1)),1e-12))
    aa=a.get('box_m') or [];bb=b.get('box_m') or []
    if len(aa)==6 and len(bb)==6:score+=sum(dif(x,y,1e-6) for x,y in zip(aa,bb))*1e-6
    pa=a.get('primitive') or {};pb=b.get('primitive') or {}
    if set(pa)!=set(pb):return float('inf')
    score+=0 if pa==pb else 1e-3
    return score
