@echo off
setlocal
cd /d "%~dp0"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=study"
echo ================================================================================
echo K01 AUTOMATIC BOM - %MODE%
echo ================================================================================
set "SLD=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "bin" mkdir "bin"
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01_BOM_Extract.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01_BOM_Extract.cs"
if errorlevel 1 (echo COMPILE FAILED.&pause&exit /b 20)
copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul
"bin\K01_BOM_Extract.exe" "%MODE%"
set RC=%ERRORLEVEL%
echo Outputs: D:\BreshevEngineering\marvilon-k01\bom\
echo Audit: D:\BreshevEngineering\marvilon-k01\reports\bom\
pause
exit /b %RC%
