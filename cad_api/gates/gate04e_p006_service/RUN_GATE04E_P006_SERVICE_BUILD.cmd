@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ================================================================================
echo K01 Gate04E - P006 SERVICE DRIVE + FULL C2R1 ASSEMBLY VERIFY
echo Stable CAD is never a direct write target.
echo ================================================================================
set "SWROOT=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS"
set "SLD=%SWROOT%\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%SWROOT%\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%SLD%" (echo ERROR: SolidWorks.Interop.sldworks.dll missing.&pause&exit /b 10)
if not exist "%CONST%" (echo ERROR: SolidWorks.Interop.swconst.dll missing.&pause&exit /b 11)
if not exist "%CSC%" (echo ERROR: C# compiler missing.&pause&exit /b 12)
if not exist bin mkdir bin

echo [1/4] Compiling P006 candidate builder...
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04E_P006_ServiceDrive.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01Gate04E_P006_ServiceDrive.cs"
if errorlevel 1 (echo P006 BUILDER COMPILE FAILED.&pause&exit /b 20)

echo [2/4] Compiling full-assembly verifier...
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04E_P006_ServiceVerify.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01Gate04E_P006_ServiceVerify.cs"
if errorlevel 1 (echo P006 VERIFY COMPILE FAILED.&pause&exit /b 21)

copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul

echo [3/4] Building P006 service candidate...
"bin\K01Gate04E_P006_ServiceDrive.exe"
if errorlevel 1 (echo P006 CANDIDATE BUILD FAILED. Stop.&pause&exit /b 30)

echo [4/4] Creating full C2R1 + P006 verification assembly...
"bin\K01Gate04E_P006_ServiceVerify.exe"
if errorlevel 1 (echo FULL ASSEMBLY VERIFY FAILED. Candidate P006 was not promoted.&pause&exit /b 31)

echo.
echo ================================================================================
echo GATE04E CAD STAGE PASSED.
echo P006 candidate and full verification assembly are available.
echo Service-process qualification remains a separate release gate.
echo ================================================================================
echo Build report : D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04E_P006_SERVICE_BUILD.json
echo Verify report: D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04E_P006_SERVICE_VERIFY.json
echo Assembly     : D:\Marvilon\K01\cad\candidates\gate04e_p006_service\verification\K01-A-001_GATE04E_P006_SERVICE_VERIFY.SLDASM
pause
exit /b 0
