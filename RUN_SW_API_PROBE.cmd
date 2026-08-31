@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo K01 SolidWorks API read-only probe
echo Working directory: %CD%
echo ============================================================

if not exist "cad_api\sw_api_probe.py" (
    echo [ERROR] cad_api\sw_api_probe.py not found.
    echo Extract/copy the complete repository starter into this folder first.
    pause
    exit /b 2
)

where py >nul 2>nul
if not errorlevel 1 (
    echo [INFO] Using Python Launcher: py -3.12
    py -3.12 --version
    py -3.12 -c "import win32com.client; print('[PASS] pywin32 import OK')" 2>nul
    if errorlevel 1 (
        echo [INFO] Installing pywin32 for Python 3.12...
        py -3.12 -m pip install --user pywin32
    )
    py -3.12 cad_api\sw_api_probe.py
    set RC=%ERRORLEVEL%
    echo.
    if %RC%==0 (
        echo [PASS] Probe completed.
        echo Send reports\CAD_SNAPSHOT_probe.json for engineering review.
    ) else (
        echo [FAIL] Probe returned error code %RC%.
    )
    pause
    exit /b %RC%
)

where python3.12 >nul 2>nul
if not errorlevel 1 (
    echo [INFO] Using python3.12
    python3.12 --version
    python3.12 -m pip install --user pywin32
    python3.12 cad_api\sw_api_probe.py
    set RC=%ERRORLEVEL%
    pause
    exit /b %RC%
)

echo [ERROR] A usable Python launcher was not found.
echo.
echo Recommended fix:
echo   Install official CPython 3.12 x64 from python.org
echo   Enable "Add python.exe to PATH"
echo   Enable "Install launcher for all users (recommended)"
echo.
echo Diagnostic commands:
echo   where python
echo   where py
echo   py -0p
pause
exit /b 3
