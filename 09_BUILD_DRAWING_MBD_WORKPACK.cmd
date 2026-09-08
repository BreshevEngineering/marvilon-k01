@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 "tools\medtas\build_mbd_authoring_candidates_v1_6.py" --repo-root "%CD%"
py -3 "tools\medtas\build_drawing_mbd_workpack_v1_6.py" --repo-root "%CD%"
set RC=%ERRORLEVEL%
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%"
pause
exit /b %RC%
