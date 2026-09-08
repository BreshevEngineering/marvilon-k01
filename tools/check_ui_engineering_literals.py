from pathlib import Path
import re,sys

ROOT=Path(__file__).resolve().parents[1]
files=[ROOT/"control/command_center/index.html",ROOT/"control/command_center/app.js"]
# Project engineering values that must come from controlled JSON, never UI source code.
forbidden=[
    r"\bOD\s*33\b", r"PCD\s*26[.,]5", r"14[.,]10", r"0[.,]930895",
    r"\bP007\s*L35\b", r"3[.,]1225", r"16\s*[×x]\s*1[.,]5"
]
bad=[]
for p in files:
    text=p.read_text(encoding="utf-8")
    for pat in forbidden:
        if re.search(pat,text,re.I):
            bad.append((str(p.relative_to(ROOT)),pat))
if bad:
    print("FAIL engineering literals found in UI source:")
    for x in bad: print(" ",x)
    sys.exit(2)
print("PASS no controlled engineering values hard-coded in UI source")
