@echo off
setlocal
cd /d "%~dp0\..\..\.."
where py >nul 2>nul
if errorlevel 1 (
  echo STATUS: HOLD_PRODUCT_DEFINITION_GUARD_V8
  echo ERROR: Python launcher 'py' not found.
  exit /b 2
)
py -3 tools\medtas\product_definition_guard_v8.py
exit /b %errorlevel%
