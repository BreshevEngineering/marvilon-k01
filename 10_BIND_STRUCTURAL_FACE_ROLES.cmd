@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 automatic SolidWorks Simulation face-role binding v1.7
echo No mouse selection is used. No CAD geometry is written.
echo ============================================================
py -3 "tools\medtas\auto_bind_structural_face_roles_v1_7.py" --repo-root "%CD%"
set RC=%ERRORLEVEL%
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_release_priority_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
pause
exit /b %RC%
