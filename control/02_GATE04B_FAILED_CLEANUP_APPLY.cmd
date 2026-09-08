@echo off
cd /d "%~dp0.."
echo SOLIDWORKS MUST BE CLOSED.
py -3.12 tools\K01_GATE04B_FAILED_CLEANUP_v1.py --apply
pause
