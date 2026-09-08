@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 "tools\medtas\build_p007_exemplar_plan_v1_9.py" --repo-root "%CD%"
py -3 "tools\medtas\build_drawing_release_plan_v1_9.py" --repo-root "%CD%"
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%"
pause
