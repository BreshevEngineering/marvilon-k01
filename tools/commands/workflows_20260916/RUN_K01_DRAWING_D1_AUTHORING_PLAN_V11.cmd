@echo off
setlocal
cd /d "%~dp0\..\..\.."
echo [1/3] Rebuild V11 Product Definition / drawing slice...
py -3 tools\medtas\product_definition_guard_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [2/3] Build V13 drawing-family view/routing plan...
py -3 tools\medtas\drawing_family_plan_v13.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [3/3] Build D1 claim-level PMI authoring plan...
py -3 tools\medtas\drawing_d1_authoring_plan_v11.py
exit /b %ERRORLEVEL%
