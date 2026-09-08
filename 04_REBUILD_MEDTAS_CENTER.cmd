@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%"
py -3 "tools\medtas\project_structure_v1_7.py" --repo-root "%CD%"
py -3 "tools\medtas\build_release_priority_view_v1_8.py" --repo-root "%CD%"
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%"
echo.
echo Materialized views rebuilt. Start/open: OPEN_K01_COMMAND_CENTER_V11.cmd
pause
