@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 "tools\medtas\build_release_priority_view_v1_8.py" --repo-root "%CD%"
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
pause
