@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo K01 SolidWorks API Gate 02 - FINAL v05
echo ============================================================
echo SAFETY: NEW UNSAVED Part + exactly one selected default plane.
echo.

if not exist "cad_api\sw_api_gate02_write_test_v05_final.py" (
  echo [ERROR] Python file not found.
  pause
  exit /b 2
)

py -3.12 -c "import win32com.client; print('[PASS] pywin32 import OK')"
if errorlevel 1 exit /b 4

pause
py -3.12 cad_api\sw_api_gate02_write_test_v05_final.py
set RC=%ERRORLEVEL%

echo.
if %RC% EQU 0 (
  echo [PASS] Gate 02 COMPLETE.
) else (
  echo [FAIL] Gate 02 returned code %RC%.
)
pause
exit /b %RC%
