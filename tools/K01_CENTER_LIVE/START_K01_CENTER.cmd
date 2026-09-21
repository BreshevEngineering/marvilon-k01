@echo off
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
echo K01 CENTER - English standalone edition
echo Application folder: %~dp0
echo Project settings: settings.json
echo.
if defined K01_PYTHON goto custom_python
where py >nul 2>nul
if not errorlevel 1 goto py_launcher
where python >nul 2>nul
if not errorlevel 1 goto python_launcher
echo ERROR: Python was not found. Install Python 3.10 or newer.
goto failed
:py_launcher
py -3 -B "%~dp0app\launch.py"
goto finished
:python_launcher
python -B "%~dp0app\launch.py"
goto finished
:custom_python
"%K01_PYTHON%" -B "%~dp0app\launch.py"
goto finished
:failed
set "CENTER_RC=2"
goto end
:finished
set "CENTER_RC=%ERRORLEVEL%"
:end
echo.
echo Center exit code: %CENTER_RC%
echo Startup log: %~dp0runtime\CENTER_STARTUP.log
pause
exit /b %CENTER_RC%
