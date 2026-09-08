@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 Gate04D-C2R1 - DRAWINGS V2 / MANUFACTURING-DRAFT QUALITY GATE
echo ================================================================================
echo Creates A3 first-angle native SLDDRW + PDF with:
echo side/end/isometric + longitudinal section, AutoDimension,
echo controlled critical-dimension table and document/title table.
echo A saved PDF is NOT automatically PASS; drawing quality is checked.
echo.
set "SWROOT=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS"
set "SLD=%SWROOT%\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%SWROOT%\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%SLD%" (echo ERROR: sldworks interop missing.&pause&exit /b 10)
if not exist "%CONST%" (echo ERROR: swconst interop missing.&pause&exit /b 11)
if not exist "%CSC%" (echo ERROR: csc.exe missing.&pause&exit /b 12)
if not exist "K01_GATE04D_C2R1_PARAMS_v1.json" (echo ERROR: parameter file missing.&pause&exit /b 13)
if not exist "bin" mkdir "bin"
copy /Y "K01_GATE04D_C2R1_PARAMS_v1.json" "bin\K01_GATE04D_C2R1_PARAMS_v1.json" >nul
echo [1/2] Compiling K01Gate04D_C2R1_DrawingsV2.cs...
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04D_C2R1_DrawingsV2.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01Gate04D_C2R1_DrawingsV2.cs"
if errorlevel 1 (echo COMPILE FAILED.&pause&exit /b 20)
copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul
echo [2/2] Running...
"bin\K01Gate04D_C2R1_DrawingsV2.exe"
set RC=%ERRORLEVEL%
echo.
echo Report: D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04D_C2R1_TYPED_DRAWINGS_V2.json
if %RC% EQU 0 echo DRAWING DRAFT QUALITY PASSED.
if %RC% EQU 2 echo DRAWINGS GENERATED BUT QUALITY GATE IS HOLD - review report/PDF.
pause
exit /b %RC%
