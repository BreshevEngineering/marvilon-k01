@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 generic native CAD snapshot v07
echo ============================================================
if not exist "cad_api\sw_cad_snapshot_v07.py" (
  echo [ERROR] cad_api\sw_cad_snapshot_v07.py not found.
  pause
  exit /b 2
)
py -3.12 cad_api\sw_cad_snapshot_v07.py
set RC=%ERRORLEVEL%
echo.
if %RC% EQU 0 (
  echo [PASS] Snapshot completed.
) else (
  echo [FAIL] Snapshot returned code %RC%.
)
pause
exit /b %RC%
