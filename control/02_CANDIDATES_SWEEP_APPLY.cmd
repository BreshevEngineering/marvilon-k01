@echo off
cd /d "%~dp0.."
echo Close SOLIDWORKS first.
py -3.12 tools\K01_CANDIDATES_SWEEP_v5.py --apply
pause
