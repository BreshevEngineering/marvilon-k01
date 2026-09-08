@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
echo ================================================================================
echo K01 - READ ONLY GIT STATUS
echo ================================================================================
git status --short
echo.
echo Typed Gate04C source should live under:
echo   cad_api\gate04c_typed
echo.
echo Do not add generated SLDPRT/SLDASM/SLDDRW binaries to ordinary Git unless
echo the CAD/PDM/LFS policy is explicitly changed.
pause
