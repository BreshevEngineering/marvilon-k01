@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 CalculiX / Gmsh controlled toolchain discovery v1.7
echo Unique discoveries can be written to binding after confirmation.
echo ============================================================
py -3 "tools\medtas\discover_analysis_toolchain_v1_7.py" --repo-root "%CD%"
echo.
choice /C YN /N /M "Apply unique discovered executable paths to controlled binding? [Y/N] "
if errorlevel 2 goto :skip
py -3 "tools\medtas\discover_analysis_toolchain_v1_7.py" --repo-root "%CD%" --apply
:skip
py -3 "tools\medtas\calculix_preflight_v1_7.py" --repo-root "%CD%"
pause
