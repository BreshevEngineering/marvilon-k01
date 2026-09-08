@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================================================
echo K01 Gate04C HOTFIX v1.5 -> v1.6 : CUT DIRECTION
echo ================================================================================
echo Patches K01Gate04C_Build.cs only and runs BUILD ONLY.
echo Stable CAD is not the write target.
echo.

if not exist "K01Gate04C_Build.cs" (
  echo ERROR: K01Gate04C_Build.cs not found in %CD%
  pause
  exit /b 10
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p=Join-Path (Get-Location) 'K01Gate04C_Build.cs';" ^
  "$s=[IO.File]::ReadAllText($p);" ^
  "$names='CreateAnnularCut','CreateCircularCutSeed';" ^
  "foreach($name in $names){" ^
  "  $start=$s.IndexOf('static Feature '+$name);" ^
  "  if($start -lt 0){throw 'method not found: '+$name};" ^
  "  $next=$s.IndexOf([Environment]::NewLine+'        static ', $start+20);" ^
  "  if($next -lt 0){$next=$s.Length};" ^
  "  $block=$s.Substring($start,$next-$start);" ^
  "  $old='bool reverse = plane.NormalX * desiredXSign < 0.0;';" ^
  "  if(-not $block.Contains($old)){throw 'direction line not found in '+$name};" ^
  "  $block=$block.Replace($old,'bool reverse = plane.NormalX * desiredXSign > 0.0;');" ^
  "  $s=$s.Substring(0,$start)+$block+$s.Substring($next);" ^
  "};" ^
  "[IO.File]::WriteAllText($p,$s,[Text.UTF8Encoding]::new($false));"

if errorlevel 1 (
  echo HOTFIX FAILED.
  pause
  exit /b 20
)

echo Hotfix applied. Running BUILD ONLY...
echo.
call "01_GATE04C_BUILD_ONLY.cmd"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo BUILD PASSED.
  echo Next run 02_GATE04C_VERIFY_ONLY.cmd
) else (
  echo BUILD stopped. Return the console output.
)
pause
exit /b %RC%
