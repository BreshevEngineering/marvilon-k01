@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================================================
echo K01 Gate04C VERIFY V2 - TARGETED J2 MATE MIGRATION
echo ================================================================================
echo Candidate P003/P007 are already built. They are NOT rebuilt.
echo Stable A001 is NOT modified.
echo.

set "SLD=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"

if not exist "%SLD%" (echo ERROR: sldworks interop not found&pause&exit /b 10)
if not exist "%CONST%" (echo ERROR: swconst interop not found&pause&exit /b 11)
if not exist "%CSC%" (echo ERROR: csc.exe not found&pause&exit /b 12)

if not exist "bin" mkdir "bin"

echo [1/2] Compiling...
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04D_C2_Verify.exe" ^
 /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll ^
 "K01Gate04D_C2_Verify.cs"
if errorlevel 1 (echo COMPILE FAILED.&pause&exit /b 20)

copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul

echo.
echo [2/2] Running...
"bin\K01Gate04D_C2_Verify.exe"
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (echo VERIFY V2 PASSED.) else (echo VERIFY V2 HOLD/FAIL. Exit=%RC%)
echo.
echo Upload these files:
echo D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04D_C2_VERIFY.json
echo D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04D_C2_VERIFY_*.log
echo.
pause
exit /b %RC%
