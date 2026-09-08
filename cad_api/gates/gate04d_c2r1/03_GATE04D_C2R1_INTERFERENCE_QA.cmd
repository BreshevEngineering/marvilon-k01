@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 Gate04D-C2R1 - INTERFERENCE QA
echo ================================================================================
echo Read-only on C2R1 verification assembly. Treat coincidence as interference = OFF.
set "SLD=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "bin" mkdir "bin"
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04D_C2R1_InterferenceQA.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01Gate04D_C2R1_InterferenceQA.cs"
if errorlevel 1 (echo COMPILE FAILED.&pause&exit /b 20)
copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul
"bin\K01Gate04D_C2R1_InterferenceQA.exe"
set RC=%ERRORLEVEL%
echo Report: D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04D_C2R1_INTERFERENCE.json
pause
exit /b %RC%
