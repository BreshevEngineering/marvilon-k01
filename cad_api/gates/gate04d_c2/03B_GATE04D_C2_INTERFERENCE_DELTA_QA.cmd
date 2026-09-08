@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 Gate04D-C2 - INTERFERENCE DELTA QA
echo ================================================================================
echo Compares stable A001 against C2 verification assembly.
echo P003/P006 M12x1 engagement passes only if its signature is unchanged.
echo.
set "SLD=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "bin" mkdir "bin"
"%CSC%" /nologo /platform:x64 /target:exe /out:"bin\K01Gate04D_C2_InterferenceDeltaQA.exe" /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll "K01Gate04D_C2_InterferenceDeltaQA.cs"
if errorlevel 1 (echo COMPILE FAILED.&pause&exit /b 20)
copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul
"bin\K01Gate04D_C2_InterferenceDeltaQA.exe"
set RC=%ERRORLEVEL%
echo.
echo Report: D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04D_C2_INTERFERENCE_DELTA.json
pause
exit /b %RC%
