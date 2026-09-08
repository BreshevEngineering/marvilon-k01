@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ================================================================================
echo MARVILON K01 Gate04C - A001 VERIFICATION
echo ================================================================================
echo Strongly typed C# SOLIDWORKS API. No Python COM. No VBA.
echo.

set "SWROOT=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS"
set "SLD=%SWROOT%\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%SWROOT%\api\redist\SolidWorks.Interop.swconst.dll"

if not exist "%SLD%" (
  echo Searching Program Files for SolidWorks.Interop.sldworks.dll...
  for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$p=Get-ChildItem -Path $env:ProgramFiles -Filter SolidWorks.Interop.sldworks.dll -Recurse -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty FullName; if($p){$p}"`) do set "SLD=%%F"
)
if not exist "%CONST%" (
  for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$p=Get-ChildItem -Path $env:ProgramFiles -Filter SolidWorks.Interop.swconst.dll -Recurse -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty FullName; if($p){$p}"`) do set "CONST=%%F"
)

if not exist "%SLD%" (
  echo ERROR: SolidWorks.Interop.sldworks.dll not found.
  exit /b 10
)
if not exist "%CONST%" (
  echo ERROR: SolidWorks.Interop.swconst.dll not found.
  exit /b 11
)

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo ERROR: .NET Framework C# compiler csc.exe not found.
  exit /b 12
)

if not exist "bin" mkdir "bin"

if not exist "K01_GATE04C_PARAMS_v1.json" (
  echo ERROR: K01_GATE04C_PARAMS_v1.json is missing from package folder:
  echo   %CD%
  exit /b 13
)
copy /Y "K01_GATE04C_PARAMS_v1.json" "bin\K01_GATE04C_PARAMS_v1.json" >nul
echo Parameters      : %CD%\K01_GATE04C_PARAMS_v1.json

echo SldWorks interop: %SLD%
echo swconst interop : %CONST%
echo Compiler        : %CSC%
echo.
echo [1/2] Compiling K01Gate04C_Verify.cs...
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04C_Verify.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01Gate04C_Verify.cs"
if errorlevel 1 (
  echo.
  echo COMPILE FAILED.
  echo Copy the compiler output and return it. Do not edit stable CAD manually.
  exit /b 20
)

copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul

echo.
echo [2/2] Running K01Gate04C_Verify.exe...
"bin\K01Gate04C_Verify.exe"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo STAGE FAILED / HOLD. Exit code=%RC%
  exit /b %RC%
)

echo.
echo STAGE PASSED.
exit /b 0
