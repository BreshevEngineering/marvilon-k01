@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\product_definition_guard_v11.py
exit /b %ERRORLEVEL%
