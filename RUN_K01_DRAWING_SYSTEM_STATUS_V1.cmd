@echo off
pushd "%~dp0"
py -3 tools\medtas\drawing_system_status_v1.py --repo-root .
set RC=%ERRORLEVEL%
popd
exit /b %RC%
