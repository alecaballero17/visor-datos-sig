#!/usr/bin/env sh
# Lanzador de la CLI de Arquis (Linux / macOS).
#
#   ./arquis.sh                      menu interactivo
#   sudo ./arquis.sh inicio servidor servidor desde cero
#   ./arquis.sh --list               todos los comandos
#
# Antes de abrir la CLI se asegura de que exista lo minimo para ejecutarla:
#   1. Python 3.10+         (lo instala con apt/dnf si falta)
#   2. entorno virtual .venv (lo crea; instala python3-venv si hace falta)
#   3. dependencias de cli/requirements/cli.txt (las reinstala cuando el archivo cambia)
# Todo lo demas (.NET, SQL Server, .env, base, nginx...) lo revisa la propia CLI:
#   ./arquis.sh inicio revisar   |   ./arquis.sh inicio preparar
set -eu

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
REQ="$ROOT/cli/requirements/cli.txt"
SELLO="$VENV/.arquis-requirements"

info()  { printf '  \033[36m·\033[0m %s\n' "$*"; }
falla() { printf '  \033[31m✖ %s\033[0m\n' "$*" >&2; exit 1; }

es_root() { [ "$(id -u)" -eq 0 ]; }

como_root() {
  if es_root; then "$@"
  elif command -v sudo >/dev/null 2>&1; then sudo "$@"
  else falla "Se necesita root para: $*  (instale sudo o ejecute como root)"; fi
}

# Con sudo, el .venv del repositorio se crea como el usuario original (no como root)
como_usuario() {
  if es_root && [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    sudo -u "$SUDO_USER" -H "$@"
  else "$@"; fi
}

instalar_paquetes() {
  if command -v apt-get >/dev/null 2>&1; then
    como_root apt-get update -qq
    como_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@"
  elif command -v dnf >/dev/null 2>&1; then como_root dnf install -y -q "$@"
  elif command -v yum >/dev/null 2>&1; then como_root yum install -y -q "$@"
  else falla "No hay apt ni dnf. Instale manualmente: $*"; fi
}

python_valido() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

buscar_python() {
  for c in python3 python3.13 python3.12 python3.11 python3.10 python; do
    p="$(command -v "$c" 2>/dev/null || true)"
    if [ -n "$p" ] && python_valido "$p"; then echo "$p"; return 0; fi
  done
  return 1
}

# ── 1. Python 3.10+ ──────────────────────────────────────────────────────────
PY="$(buscar_python || true)"
if [ -z "$PY" ]; then
  info "Python 3.10+ no encontrado: instalando..."
  if command -v apt-get >/dev/null 2>&1; then
    instalar_paquetes python3 python3-venv python3-pip
  else
    instalar_paquetes python3 python3-pip || true
    # RHEL/Rocky/Alma 8 traen 3.6: hace falta un paquete versionado
    buscar_python >/dev/null || instalar_paquetes python3.11 python3.11-pip || instalar_paquetes python3.12
  fi
  PY="$(buscar_python || true)"
  [ -n "$PY" ] || falla "No se pudo instalar Python 3.10 o superior."
fi

# ── 2. Entorno virtual ───────────────────────────────────────────────────────
crear_venv() {
  rm -rf "$VENV"
  como_usuario "$PY" -m venv "$VENV" >/dev/null 2>&1
}
if ! "$VENV/bin/python" -c 'import sys' >/dev/null 2>&1 || ! python_valido "$VENV/bin/python"; then
  info "Creando entorno virtual .venv"
  if ! crear_venv; then
    # Debian/Ubuntu separan venv/ensurepip en python3-venv (o python3.X-venv)
    VER="$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
    instalar_paquetes python3-venv >/dev/null 2>&1 || true
    instalar_paquetes "python${VER}-venv" >/dev/null 2>&1 || true
    crear_venv || falla "No se pudo crear .venv. Instale python3-venv y reintente."
  fi
  rm -f "$SELLO"
fi

# ── 3. Dependencias de la CLI (solo si cambiaron) ────────────────────────────
HUELLA="$(cksum < "$REQ")"
if [ ! -f "$SELLO" ] || [ "$(cat "$SELLO")" != "$HUELLA" ]; then
  info "Instalando dependencias de la CLI"
  como_usuario "$VENV/bin/python" -m pip install -q --disable-pip-version-check -r "$REQ" \
    || falla "pip no pudo instalar $REQ (¿sin internet?)."
  como_usuario sh -c 'printf "%s" "$1" > "$2"' _ "$HUELLA" "$SELLO"
fi

cd "$ROOT"
exec "$VENV/bin/python" -m cli "$@"
