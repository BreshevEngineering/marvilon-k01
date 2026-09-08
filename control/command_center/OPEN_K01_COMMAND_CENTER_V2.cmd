@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 Engineering Control Center v2
echo ================================================================================
echo Starts LOCAL navigation/status server at 127.0.0.1:8765.
echo It does not modify CAD or Git.
echo Close this window to stop the server.
echo.
python cc_server.py
if errorlevel 1 (
  echo.
  echo Python launch failed. Try: py -3 cc_server.py
  pause
)
