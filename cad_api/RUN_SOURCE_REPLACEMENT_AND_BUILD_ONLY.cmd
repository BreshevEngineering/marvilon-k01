@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================================================
echo K01 Gate04C - SOURCE REPLACEMENT v1.6b + BUILD ONLY
echo ================================================================================
echo This does NOT string-patch the current C# file.
echo It backs it up and replaces it with the complete corrected build source.
echo Stable CAD is not the write target.
echo.

if not exist "K01Gate04C_Build.cs" (
  echo ERROR: Run this CMD from the Gate04C source folder.
  echo Expected current file:
  echo   %CD%\K01Gate04C_Build.cs
  pause
  exit /b 10
)

if not exist "replacement\K01Gate04C_Build.cs" (
  echo ERROR: replacement source is missing.
  pause
  exit /b 11
)

if not exist "01_GATE04C_BUILD_ONLY.cmd" (
  echo ERROR: 01_GATE04C_BUILD_ONLY.cmd not found in %CD%
  pause
  exit /b 12
)

if not exist "history" mkdir "history"

for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set D=%%d%%b%%c
set T=%time::=%
set T=%T:.=%
set T=%T: =0%

copy /Y "K01Gate04C_Build.cs" "history\K01Gate04C_Build_before_v1_6b_%D%_%T%.cs" >nul
if errorlevel 1 (
  echo ERROR: Could not back up current build source.
  pause
  exit /b 20
)

copy /Y "replacement\K01Gate04C_Build.cs" "K01Gate04C_Build.cs" >nul
if errorlevel 1 (
  echo ERROR: Could not install corrected build source.
  pause
  exit /b 21
)

findstr /C:"bool reverse = plane.NormalX * desiredXSign > 0.0;" "K01Gate04C_Build.cs" >nul
if errorlevel 1 (
  echo ERROR: Correct cut-direction code not found after replacement.
  pause
  exit /b 22
)

echo Corrected full build source installed.
echo Running BUILD ONLY...
echo.

call "01_GATE04C_BUILD_ONLY.cmd"
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo ================================================================================
  echo BUILD PASSED.
  echo Next step: 02_GATE04C_VERIFY_ONLY.cmd
  echo ================================================================================
) else (
  echo ================================================================================
  echo BUILD STOPPED. Return the console output.
  echo No verification or drawing stage was run.
  echo ================================================================================
)

pause
exit /b %RC%
