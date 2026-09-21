@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
py -3 -B "%~dp0app\build_ai_handoff.py"
set "RC=%ERRORLEVEL%"
echo Return code: %RC%
pause
exit /b %RC%
