@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================================================
echo K01 Gate04C HOTFIX v1.4 -> v1.5
echo ================================================================================
echo This patches source text only, then starts the normal pipeline.
echo Stable CAD is not touched by this hotfix.
echo.

for %%F in (K01Gate04C_Build.cs K01Gate04C_Verify.cs K01Gate04C_Drawings.cs) do (
  if not exist "%%F" (
    echo ERROR: %%F not found in %CD%
    echo Put this HOTFIX CMD in the same folder as the Gate04C source files.
    pause
    exit /b 10
  )
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$files='K01Gate04C_Build.cs','K01Gate04C_Verify.cs','K01Gate04C_Drawings.cs';" ^
  "foreach($f in $files){$s=[IO.File]::ReadAllText((Join-Path (Get-Location) $f));" ^
  "$s=$s.Replace('System.System.Environment','global::System.Environment');" ^
  "$s=$s.Replace('System.Environment.CurrentDirectory','global::System.Environment.CurrentDirectory');" ^
  "$s=$s.Replace('System.Environment.NewLine','global::System.Environment.NewLine');" ^
  "$s=$s.Replace('global::global::System.Environment','global::System.Environment');" ^
  "[IO.File]::WriteAllText((Join-Path (Get-Location) $f),$s,[Text.UTF8Encoding]::new($false));}" ^
  "$vf=Join-Path (Get-Location) 'K01Gate04C_Verify.cs';" ^
  "$v=[IO.File]::ReadAllText($vf).Replace('ref mateError);','out mateError);');" ^
  "[IO.File]::WriteAllText($vf,$v,[Text.UTF8Encoding]::new($false));"

if errorlevel 1 (
  echo HOTFIX FAILED.
  pause
  exit /b 20
)

findstr /C:"System.System" K01Gate04C_Build.cs K01Gate04C_Verify.cs K01Gate04C_Drawings.cs >nul
if not errorlevel 1 (
  echo ERROR: System.System remains after patch.
  pause
  exit /b 21
)

echo Hotfix applied.
echo Starting normal Gate04C pipeline...
echo.
call "00_GATE04C_ALL.cmd"
exit /b %ERRORLEVEL%
