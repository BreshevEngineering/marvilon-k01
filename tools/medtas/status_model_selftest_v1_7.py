from __future__ import annotations
import argparse
from pathlib import Path
from status_model_v1_7 import load_status_model,selftest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    m=load_status_model(root);e=selftest(m)
    if e:
        print('K01 STATUS MODEL SELFTEST HOLD');[print(' -',x) for x in e];return 1
    print('K01 STATUS MODEL SELFTEST PASS');print('mapped raw statuses=',len(m.get('map',{})),'buckets=',len(m.get('buckets',{})));return 0
if __name__=='__main__':raise SystemExit(main())
