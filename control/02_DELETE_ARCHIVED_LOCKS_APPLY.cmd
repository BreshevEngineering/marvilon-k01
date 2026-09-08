@echo off
cd /d "%~dp0.."
echo SOLIDWORKS MUST BE CLOSED.
py -3.12 tools\K01_DELETE_ARCHIVED_LOCKS_v1.py --apply
pause
