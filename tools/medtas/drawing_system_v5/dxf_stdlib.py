
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Any
import math, re

def decode_dxf_text(s: str) -> str:
    s = s or ""
    s = s.replace(r"\U+00D7", "×").replace(r"\U+00D8", "Ø")
    s = s.replace("%%c", "Ø").replace("%%d", "°")
    s = s.replace(r"\P", "\n")
    s = re.sub(r"\\[ACFHQTW][^;]*;", "", s)
    return s

def _pairs(path):
    lines = Path(path).read_text(encoding="latin-1", errors="replace").splitlines()
    if len(lines) % 2:
        lines = lines[:-1]
    return [(lines[i].strip(), lines[i+1].rstrip("\r\n")) for i in range(0, len(lines), 2)]

def parse_ascii_dxf(path):
    """
    Minimal ASCII-DXF parser sufficient for drawing QA:
    TEXT, MTEXT, TOLERANCE, DIMENSION and DIMSTYLE/DIMLFAC.
    It intentionally does not try to be a CAD kernel.
    """
    pairs = _pairs(path)
    dimlfac: Dict[str, float] = {}
    dimdec: Dict[str, int] = {}
    texts: List[str] = []
    dims: List[Dict[str, Any]] = []
    tolerance_entities: List[str] = []

    section = None
    i = 0
    current_table = None
    while i < len(pairs):
        code, val = pairs[i]

        if code == "0" and val == "SECTION":
            if i+1 < len(pairs) and pairs[i+1][0] == "2":
                section = pairs[i+1][1]
                i += 2
                continue
        if code == "0" and val == "ENDSEC":
            section = None
            current_table = None

        # Parse DIMSTYLE entries in TABLES.
        if section == "TABLES" and code == "0" and val == "TABLE":
            if i+1 < len(pairs) and pairs[i+1] == ("2","DIMSTYLE"):
                current_table = "DIMSTYLE"
        if section == "TABLES" and current_table == "DIMSTYLE" and code == "0" and val == "DIMSTYLE":
            rec = {}
            j = i+1
            while j < len(pairs) and pairs[j][0] != "0":
                rec[pairs[j][0]] = pairs[j][1]
                j += 1
            name = rec.get("2")
            if name:
                try: dimlfac[name] = float(rec.get("144","1"))
                except: dimlfac[name] = 1.0
                try: dimdec[name] = int(float(rec.get("271","2")))
                except: dimdec[name] = 2
            i = j
            continue

        if section in {"ENTITIES","BLOCKS"} and code == "0" and val in {"TEXT","MTEXT","TOLERANCE","DIMENSION"}:
            etype = val
            fields: List[Tuple[str,str]] = []
            j = i+1
            while j < len(pairs) and pairs[j][0] != "0":
                fields.append(pairs[j])
                j += 1

            if etype in {"TEXT","TOLERANCE"}:
                for c,v in fields:
                    if c == "1":
                        txt = decode_dxf_text(v)
                        texts.append(txt)
                        if etype == "TOLERANCE" and section == "ENTITIES":
                            tolerance_entities.append(txt)
                        break
            elif etype == "MTEXT":
                chunks = [v for c,v in fields if c in {"1","3"}]
                if chunks:
                    texts.append(decode_dxf_text("".join(chunks)))
            elif etype == "DIMENSION" and section == "ENTITIES":
                f = {}
                for c,v in fields:
                    f.setdefault(c, []).append(v)
                style = (f.get("3") or ["STANDARD"])[0]
                override = decode_dxf_text((f.get("1") or [""])[0])
                measurement = None
                if "42" in f:
                    try: measurement = float(f["42"][0])
                    except: pass
                lfac = dimlfac.get(style, 1.0)
                displayed = measurement * lfac if measurement is not None else None
                dims.append({
                    "style": style,
                    "override": override,
                    "measurement": measurement,
                    "dimlfac": lfac,
                    "displayed_nominal": displayed,
                    "decimals": dimdec.get(style, 2),
                })
                if override:
                    texts.append(override)
            i = j
            continue

        i += 1

    return {
        "texts": texts,
        "dimensions": dims,
        "tolerance_entities": tolerance_entities,
        "dimstyles": {k: {"dimlfac":dimlfac[k], "decimals":dimdec.get(k,2)} for k in dimlfac},
    }

def write_semantic_schedule_dxf(contract, manifest, output_path):
    """
    Writes a deliberately non-geometric prebuild schedule as plain ASCII DXF R12.
    It is NOT called a drawing preview: geometry authority remains native SolidWorks.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    def pair(c,v):
        lines.extend([str(c), str(v)])
    def text(x,y,h,s):
        pair(0,"TEXT"); pair(8,"TEXT"); pair(10,x); pair(20,y); pair(30,0)
        pair(40,h); pair(1,s)

    pair(0,"SECTION"); pair(2,"HEADER"); pair(9,"$ACADVER"); pair(1,"AC1009"); pair(0,"ENDSEC")
    pair(0,"SECTION"); pair(2,"ENTITIES")

    text(15, 280, 4, f'{contract["drawing_id"]} PREBUILD SEMANTIC SCHEDULE - NOT A DRAWING')
    text(15, 272, 3, f'{contract["part_id"]} / {contract["document"]["title"]}')
    text(15, 264, 2.5, f'FAMILY: {contract["drawing_family"]}')

    y = 252
    text(15,y,3,"PUBLISHED VIEWS:"); y -= 7
    for v in contract["views"]:
        if v["published"]:
            text(20,y,2.5,f'{v["id"]} | {v["kind"]} | {v["role"]}'); y -= 6

    y -= 3
    text(15,y,3,"CONTROLLED CHARACTERISTICS:"); y -= 7
    for c in contract["characteristics"]:
        req = c["requirement"]
        text(20,y,2.2,f'{c["id"]} | {c["semantic_class"]} | {c["state"]} | {req}')
        y -= 6
        if y < 55: break

    y2 = 252
    text(220,y2,3,"DOCUMENT / RELEASE STATE:"); y2 -= 7
    for name in ["general_tolerance","surface_texture","revision"]:
        b = contract["document"][name]
        text(225,y2,2.4,f'{name}: {b["state"]}'); y2 -= 6
    y2 -= 3
    for b in contract["release"]["blockers"]:
        text(225,y2,2.2,"HOLD_RELEASE: "+b); y2 -= 6

    pair(0,"ENDSEC"); pair(0,"EOF")
    out.write_text("\n".join(lines) + "\n", encoding="latin-1", errors="replace")
    return str(out)
