@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\sw_api_preflight_v1.py --repo-root "%CD%" --capability P007_DIMXPERT_WRITE_C02_C05
exit /b %ERRORLEVEL%
