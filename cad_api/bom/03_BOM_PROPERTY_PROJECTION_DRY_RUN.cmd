@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ================================================================================
echo K01 BOM PROPERTY PROJECTION - DRY RUN
echo No CAD writes.
echo ================================================================================
call :compile
if errorlevel 1 (pause&exit /b %errorlevel%)
"bin\K01_BOM_PropertyProjection.exe"
set RC=%ERRORLEVEL%
echo.
echo Report: D:\BreshevEngineering\marvilon-k01\reports\bom\K01_BOM_PROPERTY_PROJECTION_CURRENT.json
pause
exit /b %RC%

:compile
set "SWROOT=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS"
set "SLD=%SWROOT%\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%SWROOT%\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%SLD%" exit /b 10
if not exist "%CONST%" exit /b 11
if not exist "%CSC%" exit /b 12
if not exist bin mkdir bin
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01_BOM_PropertyProjection.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01_BOM_PropertyProjection.cs"
if errorlevel 1 exit /b 20
copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul
exit /b 0
