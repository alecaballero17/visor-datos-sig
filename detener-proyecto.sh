#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/arquis-linux.sh"
WEB_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --solo-web) WEB_ONLY=true ;;
        --help|-h) echo 'Uso: ./detener-proyecto.sh [--solo-web]'; exit 0 ;;
        *) fail "Opción desconocida: $arg" ;;
    esac
done
lock_project
stop_web
if ! $WEB_ONLY && [[ -f "$SETUP/sql.env" ]]; then
    require docker
    compose stop sql
fi
echo 'Apagado completado. La base de datos y sus credenciales se conservan.'
