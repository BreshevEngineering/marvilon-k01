#!/usr/bin/env python3
"""Compatibility wrapper.

K01-TZ state sync is centralized in tools/state/k01_state_sync_v3.py.
Do not maintain a second navigation-state generator here.
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",required=True)
    a=ap.parse_args(); root=Path(a.repo_root).resolve()
    p=root/"tools/state/k01_state_sync_v3.py"
    if not p.is_file():
        print("HOLD: centralized state reducer missing:",p)
        return 2
    return subprocess.run([sys.executable,str(p),"--repo-root",str(root)],cwd=str(root)).returncode

if __name__=="__main__":
    raise SystemExit(main())
