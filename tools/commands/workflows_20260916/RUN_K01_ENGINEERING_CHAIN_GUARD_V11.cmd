@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\engineering_chain_guard_v11.py
exit /b %ERRORLEVEL%
