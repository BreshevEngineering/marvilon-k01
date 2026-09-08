@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 BOM REFRESH - READ PRODUCT STRUCTURE, DO NOT PROJECT METADATA
echo ================================================================================
set "PIPE=%~dp0..\..\cad_api\bom\RUN_K01_BOM_PIPELINE_C2R1.cmd"
if not exist "%PIPE%" (
  echo ERROR: existing C2R1 BOM pipeline not found:
  echo %PIPE%
  pause
  exit /b 2
)
call "%PIPE%"
set RC=%ERRORLEVEL%
echo.
echo The BOM remains a valid product-structure artifact even if engineering metadata has HOLD fields.
pause
exit /b %RC%
