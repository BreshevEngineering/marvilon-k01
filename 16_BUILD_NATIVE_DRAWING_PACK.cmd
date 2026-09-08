@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 "tools\medtas\build_product_definition_v1_8.py" --repo-root "%CD%"
py -3 "tools\medtas\build_drawing_release_plan_v1_8.py" --repo-root "%CD%"
py -3 "tools\medtas\build_native_drawing_pack_v1_8.py" --repo-root "%CD%"
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%"
pause
