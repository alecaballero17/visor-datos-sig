#!/usr/bin/env bash
# Funciones compartidas: este archivo se carga desde los lanzadores.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SETUP="$ROOT/.setup"
mkdir -p "$SETUP"
chmod 700 "$SETUP"
cd "$ROOT"
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
require() { command -v "$1" >/dev/null || fail "Falta $1."; }
lock_project() {
    require flock
    exec 9>"$SETUP/linux.lock"
    flock -n 9 || fail 'Otro lanzador está trabajando en este proyecto.'
}
compose() { docker compose --project-directory "$ROOT" --env-file "$SETUP/sql.env" -f "$ROOT/compose.yaml" "$@"; }
load_password() {
    [[ -f "$SETUP/sql.env" ]] || fail 'No existe .setup/sql.env. Ejecute primero levantar-proyecto.sh.'
    SQL_PASSWORD="$(sed -n 's/^ARQUIS_SQL_PASSWORD=//p' "$SETUP/sql.env" | head -n 1 | tr -d '\r')"
    [[ -n "$SQL_PASSWORD" ]] || fail 'Falta ARQUIS_SQL_PASSWORD en .setup/sql.env.'
}
sql() { compose exec -T -e "SQLCMDPASSWORD=$SQL_PASSWORD" sql "$SQLCMD" -S localhost -U sa -C -I -x -b -r 1 -t 600 "$@"; }
sql_file() {
    local file="$1"
    if [[ "${file##*/}" == 05_Optimizar_Relacion_CodigoFijo_Lote.sql ]]; then
        # El cálculo se ejecuta al final, con el procedimiento e índices optimizados.
        sed '/^[[:space:]]*EXEC dbo.sp_ActualizarLoteCodigosFijos;[[:space:]]*$/d' "$file" | sql
    else
        sql < "$file"
    fi
}
sql_value() { sql -h -1 -W -Q "SET NOCOUNT ON; $1" | tr -d '\r' | sed '/^[[:space:]]*$/d'; }
# El PID y su instante de creación evitan detener otro proceso que reutilice el PID.
owned_process() {
    local project="$1" pid born current
    [[ -f "$SETUP/$project.linux.pid" ]] || return 1
    read -r pid born < "$SETUP/$project.linux.pid"
    [[ "$pid" =~ ^[0-9]+$ && -r "/proc/$pid/stat" ]] || return 1
    current="$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)" || return 1
    [[ "$current" == "$born" ]] || return 1
    tr '\0' '\n' < "/proc/$pid/cmdline" | grep -Fxq -- "$ROOT/src/Arquis.$project/bin/Debug/net10.0/Arquis.$project.dll"
}
stop_web() {
    local project pid born
    for project in Frontend Backend; do
        if owned_process "$project"; then
            read -r pid born < "$SETUP/$project.linux.pid"
            kill -TERM "$pid"
            for ((i=0; i<50; i++)); do
                owned_process "$project" || break
                sleep .2
            done
            if owned_process "$project"; then kill -KILL "$pid"; fi
            printf 'Arquis.%s detenido.\n' "$project"
        fi
        rm -f -- "$SETUP/$project.linux.pid"
    done
}
