@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\canonical_hash_selftest_v1_5.py || goto :fail
py -3 tests\medtas\state_reducer_fixtures_v1_9.py || goto :fail
py -3 tools\medtas\registry_selftest_v1_9.py --repo-root "%CD%" || goto :fail
py -3 tools\medtas\status_model_selftest_v1_8.py --repo-root "%CD%" || goto :fail
py -3 tools\medtas\center_security_selftest_v2_0.py --repo-root "%CD%" || goto :fail
py -3 tools\medtas\center_action_launch_selftest_v2_0.py --repo-root "%CD%" || goto :fail
py -3 tools\medtas\center_server_regression_v2_0.py --repo-root "%CD%" || goto :fail
echo PASS MEDTAS v2.0 assurance suite
pause
exit /b 0
:fail
echo HOLD MEDTAS v2.0 assurance suite
pause
exit /b 1
