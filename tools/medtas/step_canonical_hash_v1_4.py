import argparse
from pathlib import Path
from canonical_hash_v1_4 import canonical_step_hash
ap=argparse.ArgumentParser();ap.add_argument('step');a=ap.parse_args();p=Path(a.step)
if not p.exists(): raise SystemExit('STEP file not found: '+str(p))
print(canonical_step_hash(p))
