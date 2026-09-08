@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 structural face-map qualification v1.7
echo Test: exact Simulation mapping before/after no-op rebuild.
echo Ambiguity or mapping drift is HOLD.
echo ============================================================
py -3 "tools\medtas\qualify_structural_face_map_v1_7.py" --repo-root "%CD%"
set RC=%ERRORLEVEL%
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_release_priority_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
pause
exit /b %RC%
