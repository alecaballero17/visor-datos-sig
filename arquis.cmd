@echo off
rem Lanzador de la CLI de Arquis (Windows). Uso: arquis [modulo] [submodulo] [accion] [--yes]
rem Asegura Python 3.10+, el entorno virtual .venv y las dependencias de la CLI antes de abrirla.
setlocal EnableExtensions
set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "VPY=%VENV%\Scripts\python.exe"
set "REQ=%ROOT%cli\requirements\cli.txt"
set "SELLO=%VENV%\.arquis-requirements"

rem 1. Python 3.10+
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
if not defined PY (
  echo   · Python 3.10+ no encontrado: instalando con winget...
  winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
  echo   Abra una terminal nueva y vuelva a ejecutar arquis.cmd
  exit /b 1
)

rem 2. Entorno virtual
"%VPY%" -c "import sys" >nul 2>nul || (
  echo   · Creando entorno virtual .venv
  if exist "%VENV%" rmdir /s /q "%VENV%"
  %PY% -m venv "%VENV%" || (echo   No se pudo crear .venv & exit /b 1)
  if exist "%SELLO%" del "%SELLO%"
)

rem 3. Dependencias de la CLI (solo si cambio el archivo)
fc /b "%REQ%" "%SELLO%" >nul 2>nul || (
  echo   · Instalando dependencias de la CLI
  "%VPY%" -m pip install -q --disable-pip-version-check -r "%REQ%" || (echo   pip fallo & exit /b 1)
  copy /y "%REQ%" "%SELLO%" >nul
)

pushd "%ROOT%"
"%VPY%" -m cli %*
set "CODE=%ERRORLEVEL%"
popd
exit /b %CODE%
