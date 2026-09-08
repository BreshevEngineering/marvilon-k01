@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\drawing_qa_gate_v1_9.py --repo-root "%CD%"
pause
