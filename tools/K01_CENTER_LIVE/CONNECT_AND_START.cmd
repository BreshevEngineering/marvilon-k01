@echo off
cd /d "%~dp0"
py -3 -B "%~dp0integration\connect.py"
if errorlevel 1 goto failed
call "%~dp0START_K01_CENTER.cmd"
exit /b %ERRORLEVEL%
:failed
pause
exit /b 2
