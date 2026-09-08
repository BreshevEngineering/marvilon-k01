from __future__ import annotations
import argparse,shutil
from pathlib import Path
PAIRS=[
 ('control/medtas/v1/defaults/K01_DRAWING_GENERATION_BINDING_v1_7.default.json','control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json'),
 ('control/medtas/v1/defaults/K01_TOOLCHAIN_BINDING_v1_6.default.json','control/medtas/v1/bindings/K01_TOOLCHAIN_BINDING_v1_6.json'),
]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();created=[];kept=[]
 for src,dst in PAIRS:
  s=r/src;d=r/dst
  if d.exists():kept.append(dst);continue
  if not s.exists():print('HOLD missing default',src);return 2
  d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,d);created.append(dst)
 print('Runtime bindings: kept=',len(kept),'created=',len(created))
 for x in created:print(' CREATED',x)
 for x in kept:print(' PRESERVED',x)
 return 0
if __name__=='__main__':raise SystemExit(main())
