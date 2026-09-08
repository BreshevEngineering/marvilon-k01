@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\build_release_program_v1_9.py --repo-root "%CD%"
pause
