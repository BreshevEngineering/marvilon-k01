@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\final_assembly_semantic_verify_v2_2.py --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
