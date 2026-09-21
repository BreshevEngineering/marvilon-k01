
from __future__ import annotations
from typing import Any, Dict, List
import re
from .dxf_stdlib import parse_ascii_dxf

def _contains(text_blob: str, token: str) -> bool:
    a = text_blob.replace(",", ".").replace(" ", "").lower()
    b = str(token).replace(",", ".").replace(" ", "").lower()
    return b in a

def _dimension_exists(dims, nominal, required_override_tokens=None, tol=0.015):
    required_override_tokens = required_override_tokens or []
    for d in dims:
        n = d.get("displayed_nominal")
        if n is None or abs(n - nominal) > tol:
            continue
        o = (d.get("override") or "").replace(" ", "").lower()
        if all(str(t).replace(" ", "").lower() in o for t in required_override_tokens):
            return True
    return False

def audit_dxf(contract: Dict[str, Any], dxf_path):
    parsed = parse_ascii_dxf(dxf_path)
    texts = parsed["texts"]
    blob = "\n".join(texts)
    dims = parsed["dimensions"]
    tol_entities = parsed["tolerance_entities"]

    checks: List[Dict[str,Any]] = []

    def add(cid, ok, detail, blocking=True):
        checks.append({
            "characteristic_id": cid,
            "status": "PASS" if ok else "HOLD",
            "detail": detail,
            "blocking": blocking,
        })

    for c in contract["characteristics"]:
        cid = c["id"]
        cls = c["semantic_class"]
        req = c["requirement"]
        proj = c["drawing_projection"]

        if proj == "PROHIBITED_UNTIL_RELEASED":
            # Current D005 has no released GTOL. Any native TOLERANCE entity is unauthorized.
            if cls.startswith("GTOL"):
                add(cid, len(tol_entities) == 0,
                    f'GTOL prohibited until released; DXF TOLERANCE entities={len(tol_entities)}')
            continue

        if proj != "REQUIRED":
            continue

        if cls == "THREAD_EXTERNAL":
            token = f'{req["designation"]}-{req["tolerance_class"]}'
            ok_text = _contains(blob, token)
            ok_len = _dimension_exists(dims, float(req["length_mm"])) or _contains(blob, f'{float(req["length_mm"]):.2f}')
            add(cid, ok_text and ok_len, f'thread={token}; length={req["length_mm"]}')

        elif cls == "DIAMETER_FIT_SHAFT":
            ok = _dimension_exists(dims, float(req["diameter_mm"]), [req["fit"]]) \
                 or (_contains(blob, f'{float(req["diameter_mm"]):.2f}') and _contains(blob, req["fit"]))
            add(cid, ok, f'Ø{req["diameter_mm"]:.2f} {req["fit"]}')

        elif cls == "DIAMETER_THROUGH":
            ok_nom = _dimension_exists(dims, float(req["diameter_mm"]), ["thru"]) \
                     or _contains(blob, f'Ø{float(req["diameter_mm"]):.2f}THRU')
            add(cid, ok_nom, f'Ø{req["diameter_mm"]:.2f} THRU')

        elif cls == "BLIND_HOLE_PATTERN":
            # SolidWorks DXF often carries the diameter symbol as DIMENSION semantics,
            # while the rendered anonymous block contains only the numeric value.
            diameter_ok = any(
                ("blind" in (d.get("override") or "").lower())
                and ("2×" in (d.get("override") or "") or "2x" in (d.get("override") or "").lower())
                for d in dims
            ) and _contains(blob, f'{req["diameter_mm"]:.2f}')
            tokens = [
                f'+{req["upper_tol_mm"]:.2f}/0',
                'BLIND',
                f'{req["depth_mm"]:.2f}',
                f'±{req["depth_sym_tol_mm"]:.2f}',
                f'{req["pcd_mm"]:.2f}',
                f'{int(req["angle_deg"])}°',
            ]
            missing = [t for t in tokens if not _contains(blob,t)]
            if not diameter_ok:
                missing.insert(0, f'DIAMETER_DIMENSION_{req["diameter_mm"]:.2f}')
            add(cid, not missing, 'missing=' + repr(missing))

        elif cls == "FUNCTIONAL_RELIEF":
            relief_dim_ok = any(
                ("×" in (d.get("override") or "") or "x" in (d.get("override") or "").lower())
                and f'{req["width_mm"]:.2f}' in (d.get("override") or "").replace(",",".")
                for d in dims
            ) and _contains(blob, f'{req["diameter_mm"]:.2f}')
            tokens = [
                f'{req["resulting_axial_float_mm"][0]:.2f}',
                f'{req["resulting_axial_float_mm"][1]:.2f}',
            ]
            missing = [t for t in tokens if not _contains(blob,t)]
            if not relief_dim_ok:
                missing.insert(0, f'RELIEF_DIMENSION_{req["diameter_mm"]:.2f}x{req["width_mm"]:.2f}')
            add(cid, not missing, 'missing=' + repr(missing))

        elif cls == "MATERIAL":
            mat = req["material"]
            add(cid, _contains(blob, mat), 'material=' + mat)

    # Document checks.
    scale = contract["document"]["scale"]
    add("DOC-SCALE", _contains(blob, "SCALE:"+scale) or _contains(blob, "SCALE: "+scale),
        "controlled sheet scale=" + scale)

    if contract["document"]["general_tolerance"]["state"] == "OPEN":
        # OPEN is not a generation failure, only release HOLD.
        checks.append({
            "characteristic_id":"DOC-GENERAL-TOLERANCE",
            "status":"OPEN",
            "detail":"general tolerance is explicitly OPEN in contract",
            "blocking":False
        })
    if contract["document"]["surface_texture"]["state"] == "OPEN":
        checks.append({
            "characteristic_id":"DOC-SURFACE-TEXTURE",
            "status":"OPEN",
            "detail":"surface texture is explicitly OPEN in contract",
            "blocking":False
        })

    hard_holds = [x for x in checks if x["blocking"] and x["status"] == "HOLD"]
    return {
        "schema":"marvilon.drawing_dxf_contract_qa.v2_stdlib",
        "drawing_id":contract["drawing_id"],
        "dxf_path":str(dxf_path),
        "status":"PASS_DXF_CONTRACT_QA" if not hard_holds else "HOLD_DXF_CONTRACT_QA",
        "checks":checks,
        "hard_holds":[x["characteristic_id"] for x in hard_holds],
        "parsed":{
            "text_entity_count":len(texts),
            "dimension_count":len(dims),
            "tolerance_entity_count":len(tol_entities),
        },
        "rule":"Stdlib-only runtime. OPEN requirements hold release but do not stop artifact generation."
    }
