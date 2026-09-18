@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0levantar-proyecto.ps1" %*
set "ARQUIS_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %ARQUIS_EXIT%
