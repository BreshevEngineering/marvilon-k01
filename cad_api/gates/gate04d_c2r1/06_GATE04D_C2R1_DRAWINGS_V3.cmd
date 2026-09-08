@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ================================================================================
echo K01 C2R1 DRAWING V3 - TPD / INTENT DRIVEN - NO AUTODIMENSION
echo ================================================================================
set "SWROOT=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS"
set "SLD=%SWROOT%\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%SWROOT%\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%SLD%" (echo ERROR missing SolidWorks interop&pause&exit /b 10)
if not exist "%CONST%" (echo ERROR missing swconst interop&pause&exit /b 11)
if not exist "K01_GATE04D_C2R1_PARAMS_v1.json" (echo ERROR missing params&pause&exit /b 12)
if not exist bin mkdir bin
copy /Y "K01_GATE04D_C2R1_PARAMS_v1.json" "bin\K01_GATE04D_C2R1_PARAMS_v1.json" >nul
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04D_C2R1_DrawingsV3.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01Gate04D_C2R1_DrawingsV3.cs"
if errorlevel 1 (echo COMPILE FAILED&pause&exit /b 20)
copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul
"bin\K01Gate04D_C2R1_DrawingsV3.exe"
set RC=%ERRORLEVEL%
echo.
echo IMPORTANT: native draft PASS still requires visual review and semantic linter.
pause
exit /b %RC%
