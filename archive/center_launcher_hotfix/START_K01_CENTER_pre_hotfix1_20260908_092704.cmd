@echo off
setlocal
set "ROOT=%~dp0"
py -3 "%ROOT%center\selftest.py" "%ROOT%"
if errorlevel 1 (echo. & echo HOLD: Center selftest failed. & pause & exit /b 1)
py -3 "%ROOT%center\server.py" --repo-root "%ROOT%"
endlocal
