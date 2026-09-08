@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ================================================================================
echo MARVILON K01 Gate04C - READ ONLY MATE DIAGNOSTIC
echo ================================================================================
echo No CAD is saved or modified.
echo Reads stable A001 and the current Gate04C verification A001.
echo.

set "SWROOT=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS"
set "SLD=%SWROOT%\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%SWROOT%\api\redist\SolidWorks.Interop.swconst.dll"

if not exist "%SLD%" (
  for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$p=Get-ChildItem -Path $env:ProgramFiles -Filter SolidWorks.Interop.sldworks.dll -Recurse -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty FullName; if($p){$p}"`) do set "SLD=%%F"
)
if not exist "%CONST%" (
  for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$p=Get-ChildItem -Path $env:ProgramFiles -Filter SolidWorks.Interop.swconst.dll -Recurse -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty FullName; if($p){$p}"`) do set "CONST=%%F"
)

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"

if not exist "%SLD%" (
  echo ERROR: sldworks interop not found.
  pause
  exit /b 10
)
if not exist "%CONST%" (
  echo ERROR: swconst interop not found.
  pause
  exit /b 11
)
if not exist "%CSC%" (
  echo ERROR: csc.exe not found.
  pause
  exit /b 12
)

if not exist "bin" mkdir "bin"

echo [1/2] Compiling diagnostic...
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04C_MateDiag.exe" ^
  /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll ^
  "K01Gate04C_MateDiag.cs"

if errorlevel 1 (
  echo COMPILE FAILED.
  pause
  exit /b 20
)

copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul

echo.
echo [2/2] Running READ ONLY diagnostic...
"bin\K01Gate04C_MateDiag.exe"
set RC=%ERRORLEVEL%

echo.
echo Persistent output:
echo   D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04C_MATE_DIAG.json
echo   D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04C_MATE_DIAG_*.log
echo.
echo Upload those two files. No console copy is required.
pause
exit /b %RC%
