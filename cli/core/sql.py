"""Acceso a SQL Server mediante sqlcmd (sin dependencias de Python)."""
from __future__ import annotations

import re
import socket
import time
from pathlib import Path

from . import env, shell, ui

SEP = "\x1f"   # separador de columnas improbable en los datos

SQLCMD_EXTRAS = [
    # Linux (paquetes mssql-tools18 / mssql-tools de Microsoft)
    "/opt/mssql-tools18/bin/sqlcmd",
    "/opt/mssql-tools/bin/sqlcmd",
    # Windows
    r"C:\Program Files\SqlCmd\sqlcmd.exe",
    r"C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\180\Tools\Binn\SQLCMD.EXE",
    r"C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\170\Tools\Binn\SQLCMD.EXE",
    r"C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\130\Tools\Binn\SQLCMD.EXE",
]


def sqlcmd() -> str:
    return shell.requerir("sqlcmd", SQLCMD_EXTRAS,
                          "Instalelo con: arquis deps instalar  (Linux: paquete mssql-tools18)")


# -- alcance rapido ----------------------------------------------------------------
# sqlcmd tarda lo que diga -l (antes 30 s) en rendirse si no hay servidor. Antes de
# llamarlo se prueba el puerto TCP (1.5 s) y se falla al instante con un mensaje util.
_ALCANZABLE: dict[str, tuple[bool, str]] = {}


def destino_tcp(servidor: str) -> tuple[str, int] | None:
    """(host, puerto) del servidor; None si es LocalDB / instancia con nombre (puerto dinamico)."""
    servidor = servidor.strip()
    if servidor.lower().startswith(("(localdb)", "np:", "lpc:")) or "\\" in servidor:
        return None
    host, _, puerto = re.sub(r"^tcp:", "", servidor, flags=re.I).partition(",")
    host = "127.0.0.1" if host.lower() in (".", "(local)", "localhost") else host
    return host, int(puerto or 1433)


def alcanzable(cfg: dict[str, str] | None = None, usar_cache: bool = True) -> tuple[bool, str]:
    """¿Hay algo escuchando en el servidor SQL configurado? (no valida usuario/clave)."""
    cfg = cfg or env.cargar()
    servidor = cfg["DB_SERVER"]
    if usar_cache and servidor in _ALCANZABLE:
        return _ALCANZABLE[servidor]
    destino = destino_tcp(servidor)
    if destino is None:
        r = (True, servidor)
    else:
        try:
            with socket.create_connection(destino, timeout=1.5):
                r = (True, f"{destino[0]}:{destino[1]}")
        except OSError:
            r = (False, f"nada responde en {destino[0]}:{destino[1]}")
    _ALCANZABLE[servidor] = r
    return r


def olvidar_alcance() -> None:
    _ALCANZABLE.clear()


def ayuda_sin_servidor(cfg: dict[str, str] | None = None) -> str:
    cfg = cfg or env.cargar()
    if cfg["DB_SERVER"].lower().startswith("(localdb)"):
        return "Inicie LocalDB: arquis bd servidor localdb-iniciar"
    opciones = ["arquis bd servidor instalar        (instalar SQL Server: Docker o nativo)"]
    if shell.which("docker"):
        opciones.insert(0, "arquis bd servidor docker-iniciar  (si ya creo el contenedor)")
    if not shell.ES_WINDOWS and shell.which("systemctl") and shell.salida(["systemctl", "list-unit-files", "mssql-server.service"]):
        opciones.insert(0, "arquis bd servidor mssql-reiniciar (servicio instalado pero detenido)")
    opciones.append("arquis entorno editar               (si el servidor es otro: DB_SERVER)")
    return "Opciones:\n    " + "\n    ".join(opciones)


def asegurar_servidor(cfg: dict[str, str] | None = None) -> None:
    """Falla al instante, con indicaciones, si SQL Server no responde."""
    cfg = cfg or env.cargar()
    bien, detalle = alcanzable(cfg)
    if not bien:
        raise ui.Fallo(f"SQL Server no esta disponible ({cfg['DB_SERVER']}): {detalle}.\n  {ayuda_sin_servidor(cfg)}")


def _resumir_error(texto: str) -> str:
    """Traduce los errores tipicos de sqlcmd a algo accionable."""
    t = texto.lower()
    if "login failed" in t or "error de inicio de sesi" in t:
        cuenta = "DB_ADMIN_USER / DB_ADMIN_PASSWORD" if env.get("DB_ADMIN_USER") else "DB_USER / DB_PASSWORD"
        return f"Usuario o contrasena incorrectos ({cuenta}). Corrija con: arquis entorno editar"
    if "cannot open database" in t or "no se puede abrir la base" in t:
        return f"La base {env.get('DB_NAME')} no existe. Creela con: arquis bd crear"
    if "certificate" in t or "certificado" in t:
        return "Certificado del servidor no confiable: DB_TRUST_CERT=true (arquis entorno set)"
    if "login timeout" in t or "tiempo de espera" in t or "0x2749" in t or "network-related" in t:
        cfg = env.cargar()
        abierto, donde = alcanzable(cfg, usar_cache=False)
        if abierto and destino_tcp(cfg["DB_SERVER"]):
            return (f"Algo escucha en {donde} pero no contesta como SQL Server "
                    "(esta arrancando, se cae al iniciar u otro programa ocupa el puerto). "
                    "Diagnostico: arquis bd servidor diagnostico")
        return "SQL Server no responde. " + ayuda_sin_servidor()
    return ""


def _args(base: str | None, cfg: dict[str, str]) -> list[str]:
    asegurar_servidor(cfg)
    args = [sqlcmd(), "-S", env.servidor_sql(cfg["DB_SERVER"]), "-b", "-I", "-l", "8", "-f", "i:65001,o:65001"]
    if base:
        args += ["-d", base]
    if cfg.get("DB_AUTH", "sql").lower() == "sql":
        usuario, clave = env.credenciales(cfg, admin=True)
        args += ["-U", usuario, "-P", clave]
    else:
        args.append("-E")
    if env.es_verdad("DB_TRUST_CERT", cfg) and _soporta_C():
        args.append("-C")
    return args


_C_CACHE: bool | None = None


def _soporta_C() -> bool:
    global _C_CACHE
    if _C_CACHE is None:
        ayuda = shell.salida([sqlcmd(), "-?"])
        _C_CACHE = bool(re.search(r"(^|\s)-C\b", ayuda))
    return _C_CACHE


def ejecutar(consulta: str, base: str | None = "__default__", mostrar: bool = True, check: bool = True) -> str:
    """Ejecuta T-SQL. Devuelve la salida de texto."""
    cfg = env.cargar()
    if base == "__default__":
        base = cfg["DB_NAME"]
    p = shell.run(_args(base, cfg) + ["-Q", consulta], capturar=True, silencioso=True, check=False)
    texto = ((p.stdout or "") + (p.stderr or "")).strip()
    if mostrar and texto:
        print(texto)
    if check and p.returncode != 0:
        raise ui.Fallo(_resumir_error(texto) or ("Error SQL:\n" + texto[-2000:]))
    return texto


def archivo(ruta: Path, base: str | None = "__default__", variables: dict[str, str] | None = None) -> str:
    cfg = env.cargar()
    if base == "__default__":
        base = cfg["DB_NAME"]
    args = _args(base, cfg) + ["-i", str(ruta)]
    for k, v in (variables or {}).items():
        args += ["-v", f"{k}={v}"]
    p = shell.run(args, capturar=True, silencioso=True, check=False)
    texto = ((p.stdout or "") + (p.stderr or "")).strip()
    if p.returncode != 0:
        raise ui.Fallo(f"Error ejecutando {ruta.name}:\n" + texto[-2500:])
    return texto


def filas(consulta: str, base: str | None = "__default__") -> list[list[str]]:
    """Devuelve filas como listas de texto (NULL -> '')."""
    cfg = env.cargar()
    if base == "__default__":
        base = cfg["DB_NAME"]
    q = "SET NOCOUNT ON; " + consulta
    args = _args(base, cfg) + ["-Q", q, "-h", "-1", "-W", "-s", SEP, "-w", "65535"]
    p = shell.run(args, capturar=True, silencioso=True, check=False)
    if p.returncode != 0:
        texto = ((p.stdout or "") + (p.stderr or "")).strip()
        raise ui.Fallo(_resumir_error(texto) or ("Error SQL:\n" + texto[-2000:]))
    res = []
    for linea in (p.stdout or "").splitlines():
        if not linea.strip():
            continue
        res.append([("" if v == "NULL" else v) for v in linea.split(SEP)])
    return res


def escalar(consulta: str, base: str | None = "__default__") -> str:
    f = filas(consulta, base)
    return f[0][0] if f and f[0] else ""


def probar(base: str | None = None) -> tuple[bool, str]:
    try:
        v = escalar("SELECT CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(50))+ ' - ' + "
                    "CAST(SERVERPROPERTY('Edition') AS nvarchar(100))", base=base or "master")
        return True, v
    except ui.Fallo as e:
        return False, str(e)


def existe_base(nombre: str | None = None) -> bool:
    nombre = nombre or env.get("DB_NAME")
    return escalar(f"SELECT CASE WHEN DB_ID(N'{lit(nombre)}') IS NULL THEN 0 ELSE 1 END", base="master") == "1"


def lit(texto: str) -> str:
    """Escapa un literal para N'...'."""
    return str(texto).replace("'", "''")


def ident(nombre: str) -> str:
    return "[" + str(nombre).replace("]", "]]") + "]"
