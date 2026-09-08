@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===========================================================
echo K01-D-006 / P007 first exemplar release front v2.0
echo Live CAD geometry is checked before legacy draft values are used.
echo CalculiX is not involved.
echo ===========================================================
py -3 "tools\medtas\build_p007_geometry_authority_v2_0.py" --repo-root "%CD%"
if errorlevel 1 goto :end
py -3 "tools\medtas\build_p007_exemplar_plan_v2_0.py" --repo-root "%CD%"
:end
pause
