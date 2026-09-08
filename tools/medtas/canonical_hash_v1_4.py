from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any

VOLATILE_KEYS={
    'generated','generated_at','timestamp','exported_at','created_at','modified_at','date_modified','last_saved',
    'native_path','source_sha256','binary_sha256','document_version','solidworks_revision','computer_name','user_name',
    'absolute_path','repo_root','cad_root'
}

def _norm_float(x: float, sig: int=12):
    if abs(x) < 1e-15: x=0.0
    # canonical numeric text is intentionally represented as a string to avoid platform-specific float serialization noise.
    return format(x,f'.{sig}g')

def canonicalize_json(obj: Any, sig: int=12, drop_keys=None):
    drops=VOLATILE_KEYS | set(drop_keys or [])
    if obj is None or isinstance(obj,(bool,str,int)): return obj
    if isinstance(obj,float): return _norm_float(obj,sig)
    if isinstance(obj,list): return [canonicalize_json(x,sig,drops) for x in obj]
    if isinstance(obj,dict):
        out={}
        for k in sorted(obj):
            if k in drops: continue
            out[k]=canonicalize_json(obj[k],sig,drops)
        return out
    return str(obj)

def canonical_json_bytes(obj: Any, sig: int=12, drop_keys=None)->bytes:
    c=canonicalize_json(obj,sig,drop_keys)
    return json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def canonical_json_hash(obj: Any, sig: int=12, drop_keys=None)->str:
    return hashlib.sha256(canonical_json_bytes(obj,sig,drop_keys)).hexdigest()

STEP_HEADER_RE=re.compile(r'HEADER;(?P<header>.*?)ENDSEC;',re.I|re.S)
FILE_SCHEMA_RE=re.compile(r'FILE_SCHEMA\s*\((.*?)\)\s*;',re.I|re.S)

def canonicalize_step_text(text: str)->str:
    """Header-normalized STEP artifact text.

    This removes volatile FILE_NAME/author/timestamp header content and preserves only FILE_SCHEMA from HEADER.
    It is an artifact-stability hash, NOT a proof of geometric equivalence: entity ordering/IDs can still differ across exporters.
    """
    t=text.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff')
    m=STEP_HEADER_RE.search(t)
    if m:
        sm=FILE_SCHEMA_RE.search(m.group('header'))
        schema=('FILE_SCHEMA('+sm.group(1).strip()+');') if sm else ''
        replacement='HEADER;\n'+schema+'\nENDSEC;'
        t=t[:m.start()]+replacement+t[m.end():]
    # Trim trailing spaces and blank-line noise. Do not rewrite DATA entity syntax/order.
    lines=[ln.rstrip() for ln in t.split('\n')]
    out=[]; prev_blank=False
    for ln in lines:
        blank=(ln.strip()=='')
        if blank and prev_blank: continue
        out.append(ln); prev_blank=blank
    return '\n'.join(out).strip()+'\n'

def canonical_step_hash(path: Path)->str:
    txt=path.read_text(encoding='utf-8',errors='replace')
    return hashlib.sha256(canonicalize_step_text(txt).encode('utf-8')).hexdigest()
