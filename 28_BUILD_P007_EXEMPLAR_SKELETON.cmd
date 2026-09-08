@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\build_p007_exemplar_skeleton_v1_9.py --repo-root "%CD%"
pause
