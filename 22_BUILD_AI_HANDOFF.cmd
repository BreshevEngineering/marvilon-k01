@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\ai_handoff_v2_0.py --repo-root "%CD%"
pause
