@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo K01 controlled project-structure audit. Existing engineering files are NOT moved.
py -3 "tools\medtas\project_structure_v1_7.py" --repo-root "%CD%" --ensure-dirs
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_release_priority_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%"
pause
