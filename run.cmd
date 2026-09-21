@echo off
REM K01 CENTER ROUTES V1
if /I "%~1"=="--list" goto K01_CENTER_DISPATCH_V1
if /I "%~1"=="pds-status" goto K01_CENTER_DISPATCH_V1
if /I "%~1"=="pds-next" goto K01_CENTER_DISPATCH_V1
if /I "%~1"=="center-build" goto K01_CENTER_DISPATCH_V1
goto K01_ORIGINAL_DISPATCH_V1
:K01_CENTER_DISPATCH_V1
py -3 "%~dp0tools\cli\k01_center_routes.py" %*
exit /b %ERRORLEVEL%
:K01_ORIGINAL_DISPATCH_V1
@echo off



REM BEGIN K01 PRODUCT DEVELOPMENT SYSTEM
if /I "%~1"=="pds-status" (
  pushd "%~dp0"
  py -3 tools\pds\k01_pds.py --repo-root . status
  set RC=%ERRORLEVEL%
  popd
  exit /b %RC%
)
if /I "%~1"=="pds-next" (
  pushd "%~dp0"
  py -3 tools\pds\k01_pds.py --repo-root . next
  set RC=%ERRORLEVEL%
  popd
  exit /b %RC%
)
if /I "%~1"=="pds-report" (
  pushd "%~dp0"
  py -3 tools\pds\k01_pds.py --repo-root . report
  set RC=%ERRORLEVEL%
  popd
  exit /b %RC%
)
REM END K01 PRODUCT DEVELOPMENT SYSTEM









REM BEGIN K01 D006 DRAWING DISPATCH

if /I "%~1"=="drawing-d006" (

  pushd "%~dp0"

  py -3 tools\cad\d006_candidate_authoring.py --repo-root .

  set RC=%ERRORLEVEL%

  popd

  exit /b %RC%

)

REM END K01 D006 DRAWING DISPATCH



















REM BEGIN K01 GOVERNANCE DISPATCH



if /I "%~1"=="change-begin" (



  pushd "%~dp0"



  shift



  py -3 tools\governance\change_control.py --repo-root . begin %*



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="impact" (



  pushd "%~dp0"



  shift



  py -3 tools\governance\change_control.py --repo-root . impact %*



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="what-if" (



  pushd "%~dp0"



  shift



  py -3 tools\governance\change_control.py --repo-root . what-if %*



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="implementation" (



  pushd "%~dp0"



  py -3 tools\governance\change_control.py --repo-root . implementation



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="verify-change" (



  pushd "%~dp0"



  shift



  py -3 tools\governance\change_control.py --repo-root . verify %*



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="promote-change" (



  pushd "%~dp0"



  shift



  py -3 tools\governance\change_control.py --repo-root . promote %*



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="change-guard" (



  pushd "%~dp0"



  py -3 tools\governance\change_control.py --repo-root . guard



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="center-build" (



  pushd "%~dp0"



  py -3 tools\assurance\build_center_state.py --repo-root .



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



if /I "%~1"=="governance-test" (



  pushd "%~dp0"



  py -3 -m unittest discover -s tests\governance -p "test_*.py"



  if errorlevel 1 (



    set RC=%ERRORLEVEL%



    popd



    exit /b %RC%



  )



  py -3 -m unittest discover -s tests\assurance -p "test_*.py"



  set RC=%ERRORLEVEL%



  popd



  exit /b %RC%



)



REM END K01 GOVERNANCE DISPATCH























setlocal















for %%I in ("%~dp0.") do set "ROOT=%%~fI"















py -3 "%ROOT%\tools\cli\k01_cli.py" --repo-root "%ROOT%" %*















exit /b %ERRORLEVEL%















