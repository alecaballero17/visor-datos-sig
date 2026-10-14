@echo off
title SIG Vector Studio
cd /d "%~dp0"
echo Iniciando SIG Vector Studio...
python sig_vector_studio\main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error al iniciar la aplicacion.
    pause
)
