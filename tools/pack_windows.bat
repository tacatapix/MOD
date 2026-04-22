@echo off
REM Pack @PackFazupix_KOTH using the official DayZ Tools AddonBuilder.
REM Batch wrapper for pack_windows.ps1 - double-clickable from Explorer.

pushd "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pack_windows.ps1"
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
