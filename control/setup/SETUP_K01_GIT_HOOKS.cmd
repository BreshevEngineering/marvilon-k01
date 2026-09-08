@echo off
setlocal EnableExtensions
cd /d "%~dp0"
git config core.hooksPath .githooks
echo Git hooks path set to .githooks
echo Current:
git config --get core.hooksPath
