@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\build_inspection_characteristics_v1_9.py --repo-root "%CD%"
pause
