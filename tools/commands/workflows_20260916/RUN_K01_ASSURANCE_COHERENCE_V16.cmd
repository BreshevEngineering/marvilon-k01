@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 -B tools\assurance\center_assurance_coherence.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
