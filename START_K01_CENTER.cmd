@echo off
setlocal
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
py -3 "%ROOT%\center\selftest.py" "%ROOT%"
if errorlevel 1 (
  echo.
  echo HOLD: Center selftest failed.
  pause
  exit /b 1
)
py -3 "%ROOT%\center\server.py" --repo-root "%ROOT%"
endlocal
