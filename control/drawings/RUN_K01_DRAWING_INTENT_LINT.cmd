@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0K01_DRAWING_INTENT_LINT_v2.ps1"
set RC=%ERRORLEVEL%
echo.
echo Report: D:\BreshevEngineering\marvilon-k01\reports\drawings\K01_DRAWING_INTENT_LINT_CURRENT.json
pause
exit /b %RC%
