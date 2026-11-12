"""Acceso a SQL Server mediante sqlcmd (sin dependencias de Python)."""
from __future__ import annotations

import re
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


def _args(base: str | None, cfg: dict[str, str]) -> list[str]:
    args = [sqlcmd(), "-S", cfg["DB_SERVER"], "-b", "-I", "-l", "30", "-f", "i:65001,o:65001"]
    if base:
        args += ["-d", base]
    if cfg.get("DB_AUTH", "sql").lower() == "sql":
        args += ["-U", cfg.get("DB_USER", ""), "-P", cfg.get("DB_PASSWORD", "")]
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
        raise ui.Fallo("Error SQL:\n" + texto[-2000:])
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
        raise ui.Fallo("Error SQL:\n" + ((p.stdout or "") + (p.stderr or "")).strip()[-2000:])
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
