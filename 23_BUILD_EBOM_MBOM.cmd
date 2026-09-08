@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 computed EBOM + MBOM v1.9

echo CAD owns occurrences/quantities. control\product\parts.json owns metadata.
echo ============================================================
py -3 "tools\medtas\build_bom_v1_9.py" --repo-root "%CD%"
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%"
pause
