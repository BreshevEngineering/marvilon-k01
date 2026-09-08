@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 controlled SOLIDWORKS drawing-template discovery v1.8
echo Multiple candidates are never auto-selected.
echo ============================================================
py -3 "tools\medtas\discover_drawing_templates_v1_7.py" --repo-root "%CD%"
echo.
choice /C YN /N /M "Apply only if discovery found one unique controlled candidate? [Y/N] "
if errorlevel 2 goto :skip
py -3 "tools\medtas\discover_drawing_templates_v1_7.py" --repo-root "%CD%" --apply
:skip
py -3 "tools\medtas\build_product_definition_v1_8.py" --repo-root "%CD%"
py -3 "tools\medtas\build_drawing_release_plan_v1_8.py" --repo-root "%CD%"
py -3 "tools\medtas\build_release_priority_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\project_view_v1_8.py" --repo-root "%CD%" >nul 2>&1
pause
