@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ================================================================================
echo MARVILON MEDTAS - SOLIDWORKS LIVE BRIDGE v1
echo Read-only: SOLIDWORKS -> MEDTAS live state. No CAD writes.
echo ================================================================================
set "SWROOT=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS"
set "SLD=%SWROOT%\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%SWROOT%\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%SLD%" (echo ERROR: sldworks interop missing.&pause&exit /b 10)
if not exist "%CONST%" (echo ERROR: swconst interop missing.&pause&exit /b 11)
if not exist "%CSC%" (echo ERROR: C# compiler missing.&pause&exit /b 12)
if not exist bin mkdir bin
echo [1/2] Compiling bridge...
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01SolidWorksLiveBridge.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01SolidWorksLiveBridge.cs"
if errorlevel 1 (echo COMPILE FAILED.&pause&exit /b 20)
copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul
echo [2/2] Starting read-only watch...
"bin\K01SolidWorksLiveBridge.exe" --watch --interval-ms 2000
set RC=%ERRORLEVEL%
pause
exit /b %RC%
