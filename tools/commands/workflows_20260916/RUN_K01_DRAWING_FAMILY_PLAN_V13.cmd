@echo off
setlocal
cd /d "%~dp0\..\..\.."
echo [1/2] Rebuild current Product Definition / drawing slice...
py -3 tools\medtas\product_definition_guard_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [2/2] Build reusable drawing-family view/routing plan...
py -3 tools\medtas\drawing_family_plan_v13.py
exit /b %ERRORLEVEL%
