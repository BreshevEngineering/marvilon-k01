from __future__ import annotations
import json
from pathlib import Path

AUTHORITY_MAP = Path("control/project/K01_AUTHORITY_MAP_CURRENT.json")

class AuthorityError(RuntimeError):
    pass

def load_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception as e:
        raise AuthorityError(f"Cannot read authority JSON {path}: {e}") from e

def authority_map(root):
    root=Path(root).resolve(); p=root/AUTHORITY_MAP
    if not p.is_file(): raise AuthorityError(f"Authority map missing: {p}")
    return load_json(p)

def require_control_family(root, key):
    root=Path(root).resolve(); amap=authority_map(root)
    rec=(amap.get("control_families") or {}).get(key)
    if not isinstance(rec,dict): raise AuthorityError(f"Control family not declared: {key}")
    rel=rec.get("authority")
    if not isinstance(rel,str) or not rel.strip(): raise AuthorityError(f"Control family authority path missing: {key}")
    p=root/rel
    if not p.is_file(): raise AuthorityError(f"Declared control-family authority missing: {key} -> {p}")
    return p

def require_domain_authority(root, key):
    root=Path(root).resolve(); amap=authority_map(root)
    rel=(amap.get("authorities") or {}).get(key)
    if not isinstance(rel,str) or not rel.strip(): raise AuthorityError(f"Domain authority not declared: {key}")
    # Only path-valued domain authorities may be resolved by this helper.
    if any(x in rel for x in (" + ","->","→",";")) or rel.startswith("Canonical ") or rel.startswith("computed"):
        raise AuthorityError(f"Domain authority {key} is descriptive, not a path: {rel}")
    p=root/rel
    if not p.is_file(): raise AuthorityError(f"Declared domain authority missing: {key} -> {p}")
    return p
