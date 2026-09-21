@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\drawing_d1_authoring_plan_v11.py
if errorlevel 1 exit /b %errorlevel%
py -3 tools\medtas\d006_exemplar_prepare_v12.py
exit /b %errorlevel%
