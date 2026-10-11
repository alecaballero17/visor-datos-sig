#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/arquis-linux.sh"
IMPORT=false
PREPARE=false
for arg in "$@"; do
    case "$arg" in
        --importar-capas) IMPORT=true ;;
        --preparar-base) PREPARE=true ;;
        --help|-h) echo 'Uso: ./levantar-proyecto.sh [--importar-capas] [--preparar-base]'; exit 0 ;;
        *) fail "Opción desconocida: $arg" ;;
    esac
done
lock_project
trap 'printf "Falló el arranque (línea %s). Revise .setup/*.log. Puede ejecutar ./detener-proyecto.sh para apagar los servicios.\n" "$LINENO" >&2' ERR
for tool in docker dotnet python3 curl sed awk grep setsid; do require "$tool"; done
[[ "$(dotnet --version)" == 10.* ]] || fail 'Se necesita el SDK .NET 10.'
[[ "$(docker info --format '{{.OSType}}')" == linux ]] || fail 'Inicie Docker Desktop con el motor Linux.'
if [[ ! -f "$SETUP/sql.env" ]]; then
    (umask 077; python3 - <<'PY'
from pathlib import Path
import secrets
Path('.setup/sql.env').write_text('ARQUIS_SQL_PASSWORD=Arquis1!' + secrets.token_hex(16) + '\n')
PY
    )
fi
load_password
compose up -d --quiet-pull sql
SQLCMD="$(compose exec -T sql sh -c 'if [ -x /opt/mssql-tools18/bin/sqlcmd ]; then echo /opt/mssql-tools18/bin/sqlcmd; else echo /opt/mssql-tools/bin/sqlcmd; fi' | tr -d '\r')"
printf 'Esperando a SQL Server…\n'
ready=false
for ((attempt=0; attempt<90; attempt++)); do
    if sql -l 2 -t 2 -Q "IF DB_ID(N'VisorDatosSIG') IS NULL SELECT 1; ELSE EXEC(N'USE VisorDatosSIG; SELECT 1;');" >/dev/null 2>&1; then ready=true; break; fi
    sleep 2
done
$ready || fail 'SQL Server no responde. Revise docker compose --env-file .setup/sql.env logs sql.'
new_db="$(sql_value "SELECT CASE WHEN DB_ID(N'VisorDatosSIG') IS NULL THEN 1 ELSE 0 END")"
if [[ "$new_db" == 1 ]]; then
    for file in 01_CrearBD.sql 04_Actualizar_CodigosFijos_Estado.sql 05_Optimizar_Relacion_CodigoFijo_Lote.sql 06_Agregar_Nombre_Vias.sql 07_Roles_Usuarios_Menu.sql 08_MenuOpciones_UsuarioMenu.sql 09_Arquis_Alfa.sql; do
        echo "Ejecutando $file"
        sql_file "$ROOT/02_BaseDatos/$file"
    done
    PREPARE=true
fi
schema_pending="$(sql_value "USE VisorDatosSIG; SELECT CASE WHEN COL_LENGTH('dbo.Usuarios','Email') IS NULL OR COL_LENGTH('dbo.CodigosFijos','EstadoVerificado') IS NULL OR OBJECT_ID('dbo.sp_ActualizarLoteCodigosFijos','P') IS NULL THEN 1 ELSE 0 END")"
[[ "$schema_pending" != 1 ]] || PREPARE=true
empty_layers="$(sql_value 'USE VisorDatosSIG; SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM dbo.Manzanas) OR NOT EXISTS(SELECT 1 FROM dbo.Lotes) OR NOT EXISTS(SELECT 1 FROM dbo.CodigosFijos) OR NOT EXISTS(SELECT 1 FROM dbo.Vias) THEN 1 ELSE 0 END')"
shopt -s nullglob
shapes=("$ROOT"/03_DatosPrueba/*.shp "$ROOT"/03_DatosPrueba/DatosSIG_Reproj/*.shp)
if $IMPORT || [[ "$empty_layers" == 1 && ${#shapes[@]} -gt 0 ]]; then
    [[ ${#shapes[@]} -gt 0 ]] || fail 'No hay capas SHP en 03_DatosPrueba.'
    # pip --target evita depender del módulo venv o modificar Python del sistema.
    if ! PYTHONPATH="$SETUP/pythonlibs" python3 -c 'import shapefile' 2>/dev/null; then
        if python3 -m pip --version >/dev/null 2>&1; then
            python3 -m pip install --no-deps --target "$SETUP/pythonlibs" pyshp
        else
            echo 'Python no tiene pip; instalando pyshp con un contenedor temporal.'
            require tar
            mkdir -p "$SETUP/pythonlibs"
            # Transferencia por stdout: no requiere compartir /mnt con Docker Desktop.
            docker run --rm python:3.12-slim sh -c \
                'python -m pip install --no-cache-dir --no-deps --target /tmp/pythonlibs pyshp >&2 && tar -C /tmp/pythonlibs -cf - .' \
                | tar --no-same-owner -xf - -C "$SETUP/pythonlibs"
        fi
    fi
    python3 "$ROOT/convertir-capas.py" --sqlcmd-batches
    echo 'Importando las tablas vacías; se conservan las capas ya cargadas.'
    sql < "$SETUP/capas-linux.sql"
    PREPARE=true
elif [[ "$empty_layers" == 1 ]]; then
    echo 'Aviso: hay tablas cartográficas vacías. Copie las cuatro capas y vuelva a ejecutar este script.'
fi
if $PREPARE; then
    # Completa también una preparación interrumpida sin borrar la base.
    for table in Manzanas Lotes CodigosFijos Vias; do
        sql -Q "USE VisorDatosSIG; IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.$table') AND name='SIX_${table}_Geom') CREATE SPATIAL INDEX SIX_${table}_Geom ON dbo.$table(Geom) USING GEOMETRY_GRID WITH (BOUNDING_BOX=(-180,-90,180,90));"
    done
    for file in 04_Actualizar_CodigosFijos_Estado.sql 05_Optimizar_Relacion_CodigoFijo_Lote.sql 06_Agregar_Nombre_Vias.sql 07_Roles_Usuarios_Menu.sql 08_MenuOpciones_UsuarioMenu.sql 09_Arquis_Alfa.sql 10_Asociacion_Indices_Espaciales.sql 11_Estado_Servicio_Verificado.sql 12_Indice_Codigos_Agua.sql 13_Registro_Email.sql; do
        echo "Ejecutando $file"
        sql_file "$ROOT/02_BaseDatos/$file"
    done
    sql -Q 'USE VisorDatosSIG; EXEC dbo.sp_ActualizarLoteCodigosFijos;'
fi
export DOTNET_CLI_HOME="$SETUP/dotnet"
export NUGET_PACKAGES="$SETUP/nuget"
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export ConnectionStrings__DefaultConnection="Server=127.0.0.1,14330;Database=VisorDatosSIG;User ID=sa;Password=$SQL_PASSWORD;TrustServerCertificate=True"
export ASPNETCORE_ENVIRONMENT=Development
for project in Backend Frontend; do
    if [[ "$project" == Backend ]]; then port=5080; probe=http://localhost:5080/health; expected=Arquis.Backend; else port=5180; probe=http://localhost:5180/; expected=Arquis; fi
    if owned_process "$project" && curl -fsS --max-time 3 "$probe" | grep -q "$expected"; then
        echo "Arquis.$project ya está activo."
        continue
    fi
    owned_process "$project" && fail "Arquis.$project está activo pero no responde. Ejecute detener-proyecto.sh."
    if python3 - "$port" <<'PY'
import socket, sys
with socket.socket() as s:
    s.settimeout(1)
    sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 1)
PY
    then fail "El puerto $port está ocupado por otro proceso."; fi
    echo "Compilando Arquis.$project…"
    dotnet build "$ROOT/src/Arquis.$project" --nologo > "$SETUP/$project.build.log" 2>&1 9>&- || { tail -n 30 "$SETUP/$project.build.log"; fail "No se pudo compilar Arquis.$project."; }
    ASPNETCORE_CONTENTROOT="$ROOT/src/Arquis.$project" ASPNETCORE_URLS="http://localhost:$port" nohup setsid dotnet "$ROOT/src/Arquis.$project/bin/Debug/net10.0/Arquis.$project.dll" > "$SETUP/$project.log" 2>&1 < /dev/null 9>&- &
    pid=$!
    born="$(awk '{print $22}' "/proc/$pid/stat")"
    printf '%s %s\n' "$pid" "$born" > "$SETUP/$project.linux.pid"
    ready=false
    for ((attempt=0; attempt<60; attempt++)); do
        kill -0 "$pid" 2>/dev/null || { tail -n 30 "$SETUP/$project.log"; fail "Arquis.$project terminó inesperadamente."; }
        if curl -fsS --max-time 2 "$probe" 2>/dev/null | grep -q "$expected"; then ready=true; break; fi
        sleep 1
    done
    $ready || fail "Arquis.$project no respondió. Revise .setup/$project.log."
done
printf '\nListo. Visor: http://localhost:5180\nAPI: http://localhost:5080/health\nCuenta inicial de una base nueva: admin / Admin123!\nApagar: ./detener-proyecto.sh\n'
