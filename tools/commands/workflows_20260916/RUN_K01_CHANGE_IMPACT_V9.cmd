@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~1"=="" (
  echo USAGE: RUN_K01_CHANGE_IMPACT_V9.cmd ENTITY CHANGE_DOMAIN
  echo EXAMPLE: RUN_K01_CHANGE_IMPACT_V9.cmd K01-P-007 interface_geometry
  exit /b 2
)
if "%~2"=="" (
  echo USAGE: RUN_K01_CHANGE_IMPACT_V9.cmd ENTITY CHANGE_DOMAIN
  exit /b 2
)
py -3 tools\medtas\change_impact_v9.py --repo-root "%CD%" what-if --entity "%~1" --domain "%~2"
exit /b %ERRORLEVEL%
