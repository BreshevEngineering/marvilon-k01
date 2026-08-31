@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo K01 SolidWorks API Gate 01 - v06 minimal
echo ============================================================
echo.

if not exist "cad_api\sw_api_probe_v06.py" (
  echo [ERROR] cad_api\sw_api_probe_v06.py not found.
  pause
  exit /b 2
)

py -3.12 --version
if errorlevel 1 (
  echo [ERROR] Python 3.12 launcher not available.
  pause
  exit /b 3
)

py -3.12 -c "import win32com.client; print('[PASS] pywin32 import OK')"
if errorlevel 1 (
  echo [ERROR] pywin32 unavailable.
  pause
  exit /b 4
)

echo.
echo Keep SOLIDWORKS 2026 running with native P016 active.
echo.

py -3.12 cad_api\sw_api_probe_v06.py
set RC=%ERRORLEVEL%

echo.
if %RC% EQU 0 (
  echo [PASS] Gate 01 completed.
  echo Send reports\CAD_SNAPSHOT_probe_v06.json.
) else (
  echo [FAIL] Gate 01 returned code %RC%.
)

pause
exit /b %RC%
