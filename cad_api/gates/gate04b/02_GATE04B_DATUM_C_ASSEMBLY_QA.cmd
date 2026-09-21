@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================================================
echo K01 Gate04B DATUM C - CANDIDATE A001 ASSEMBLY QA
echo ================================================================================
echo Uses current Gate04B PASS report. Does NOT rebuild P003/P016/P017.
echo Canonical A001 is SHA-guarded and is never modified.
echo.
echo Candidate QA:
echo   - copy canonical A001
echo   - replace P003/P016 with current Gate04B candidates
echo   - add P017 as the 14th modeled occurrence
echo   - add nominal C-axis surrogate mate for P003/P016
echo   - constrain P017 press fit: concentric + locked rotation + 4-mm press depth
echo   - require P003/P016/P017 fully constrained and 0 active mate errors
echo   - run IN/MID/OUT interference sweep
echo   - re-prove moving-group propagation
echo   - save one verification A001 only
echo.

set "SLD=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll"
set "CONST=%ProgramFiles%\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.swconst.dll"
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"

if not exist "%SLD%" (echo ERROR: SolidWorks.Interop.sldworks.dll missing&pause&exit /b 10)
if not exist "%CONST%" (echo ERROR: SolidWorks.Interop.swconst.dll missing&pause&exit /b 11)
if not exist "%CSC%" (echo ERROR: csc.exe missing&pause&exit /b 12)

if not exist "bin" mkdir "bin"

echo [1/2] Compiling SW2018 verifier...
"%CSC%" /nologo /langversion:5 /platform:x64 /target:exe ^
 /out:"bin\K01Gate04B_DatumC_AssemblyQA.exe" ^
 /reference:"%SLD%" /reference:"%CONST%" /reference:System.Web.Extensions.dll ^
 "K01Gate04B_DatumC_AssemblyQA.cs"
if errorlevel 1 (
  echo.
  echo COMPILE FAILED. Canonical CAD remains untouched.
  pause
  exit /b 20
)

copy /Y "%SLD%" "bin\SolidWorks.Interop.sldworks.dll" >nul
copy /Y "%CONST%" "bin\SolidWorks.Interop.swconst.dll" >nul

echo.
echo [2/2] Running candidate A001 assembly QA...
"bin\K01Gate04B_DatumC_AssemblyQA.exe"
set "RC=%ERRORLEVEL%"

echo.
echo ================================================================================
echo Gate04B Datum-C candidate A001 QA finished - Return code %RC%
echo ================================================================================
echo Verification assembly:
echo   D:\Marvilon\K01\cad\candidates\gate04b_datumc\verification\K01-A-001_GATE04B_DATUMC_VERIFY.SLDASM
echo Report:
echo   D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04B_DATUM_C_ASSEMBLY_QA.json
echo Log:
echo   D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04B_DATUM_C_ASSEMBLY_QA_*.log
echo.
if "%RC%"=="0" (
  echo PASS: candidate assembly QA closed. Do NOT promote canonical yet.
  echo Next: review report, refresh handoff, then controlled promotion + EBOM delta.
) else (
  echo HOLD/FAIL: return the JSON + latest log. Do not open another engineering line.
)
echo.
pause
exit /b %RC%
