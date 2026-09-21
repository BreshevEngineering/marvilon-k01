@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo [1/5] Validate engineering-chain structure...
py -3 tools\medtas\engineering_chain_guard_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [2/5] Rebuild Product Definition / domain slices...
py -3 tools\medtas\product_definition_guard_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/5] Rebuild reusable drawing-family plan...
py -3 tools\medtas\drawing_family_plan_v13.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [4/5] Rebuild D1 claim-level authoring plan...
py -3 tools\medtas\drawing_d1_authoring_plan_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [5/5] Audit whole-project engineering-domain coverage...
py -3 tools\medtas\engineering_system_guard_v14.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
