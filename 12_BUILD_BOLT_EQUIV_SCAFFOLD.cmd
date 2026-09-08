@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 "tools\medtas\build_bolt_equiv_scaffold_v1_7.py" --repo-root "%CD%"
set RC=%ERRORLEVEL%
py -3 "tools\medtas\calculix_preflight_v1_7.py" --repo-root "%CD%"
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_release_priority_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
pause
exit /b %RC%
