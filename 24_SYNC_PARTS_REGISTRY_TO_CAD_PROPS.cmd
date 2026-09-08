@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 parts registry -> SOLIDWORKS custom properties v2.0
echo One-way projection. Active A001 assembly is NOT required.
echo Native paths are resolved from the current raw CAD semantic snapshot.
echo No geometry or native material assignment is modified.
echo ============================================================
py -3 "tools\medtas\sync_parts_registry_to_cad_props_v2_0.py" --repo-root "%CD%"
echo.
set /p APPLY=Apply the reported property projection to current K01 part documents? [Y/N] 
if /I "%APPLY%"=="Y" py -3 "tools\medtas\sync_parts_registry_to_cad_props_v2_0.py" --repo-root "%CD%" --apply
pause
