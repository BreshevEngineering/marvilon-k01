from __future__ import annotations
import hashlib,json,re,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
import medtas_state_engine_v1_1 as eng
ID_RE=re.compile(r'(K01-[PBA]-\d{3})',re.I)

_LOAD_SENTINEL=object()
def load(p, default=_LOAD_SENTINEL):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:
        if default is not _LOAD_SENTINEL:
            return default
        raise
def dump(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
def base_id(x):
    m=ID_RE.search(str(x or ''));return m.group(1).upper() if m else str(x or '')
def graph_path(root):
    root=Path(root)
    for n in ('K01_engineering_build_graph_v2_0.json','K01_engineering_build_graph_v1_9.json','K01_engineering_build_graph_v1_8.json','K01_engineering_build_graph_v1_7.json','K01_engineering_build_graph_v1_6.json','K01_engineering_build_graph_v1_5.json','K01_engineering_build_graph_v1_4.json','K01_engineering_build_graph_v1_3.json'):
        p=root/'control/medtas/v1/graph'/n
        if p.exists(): return p
    raise FileNotFoundError('MEDTAS graph missing')
def graph(root): return load(graph_path(root))
def stores(root):
    root=Path(root);return eng.load_record_store(root/'reports/medtas/records/current'),eng.load_record_store(root/'reports/medtas/verifications/current')
def evaluate(root):
    r,v=stores(root);return eng.evaluate_graph(graph(root),Path(root),r,v)
def register_build(root,nid,producer,limitations=None,extra=None):
    root=Path(root);d=evaluate(root)[nid]
    if not d.get('artifact_hash'): raise RuntimeError(nid+' has no artifact hash')
    br={'schema':'medtas.build_record.v1','node_id':nid,'built_state_hash':d['state_hash'],'artifact_hash':d['artifact_hash'],'producer':producer}
    if limitations: br['limitations']=limitations
    if extra: br.update(extra)
    dump(root/'reports/medtas/records/current'/f'{nid}.build.json',br);return br
def register_verify(root,nid,verdict,metrics=None,limitations=None,notes=''):
    root=Path(root);d=evaluate(root)[nid]
    vr={'schema':'medtas.verification_record.v1','node_id':nid,'verified_state_hash':d['state_hash'],'verified_artifact_hash':d['artifact_hash'],'verdict':verdict,'metrics':metrics or {},'limitations':limitations or [],'notes':notes}
    dump(root/'reports/medtas/verifications/current'/f'{nid}.verify.json',vr);return vr
def sha256_file(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha256_obj(o): return hashlib.sha256(canon(o).encode('utf-8')).hexdigest()
def face_signature(part,f):
    d={'part':base_id(part),'body':f.get('body'),'surface_type':f.get('surface_type'),'area_m2':f.get('area_m2'),'box_m':f.get('box_m'),'normal':f.get('normal'),'edge_count':f.get('edge_count')}
    return sha256_obj(d)
def tool_path(root,key,aliases):
    root=Path(root);bp=root/'control/medtas/v1/bindings/K01_TOOLCHAIN_BINDING_v1_6.json';explicit=''
    if bp.exists():
        try: explicit=str(load(bp).get(key) or '').strip()
        except Exception: explicit=''
    if explicit:
        p=Path(explicit)
        if p.exists(): return str(p)
    for a in aliases:
        q=shutil.which(a)
        if q:return q
    return None
