"""Requisitos de cada accion del menu.

Una accion declara lo que necesita (`requiere=("sql", "base")`). Antes de
ejecutarla, el menu lo comprueba en segundos y, si falta algo, explica que es,
como resolverlo y ofrece resolverlo; asi no se piden datos para luego fallar
tras un timeout.

Los requisitos se comprueban en orden y se detiene en el primero que falla,
porque los siguientes dependen de el (sin servidor no hay base).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from . import env, shell, ui


@dataclass
class Requisito:
    clave: str
    etiqueta: str                                  # texto corto que se muestra en el menu
    comprobar: Callable[[], tuple[bool, str]]      # (cumple, detalle)
    ayuda: str                                     # como resolverlo a mano
    resolver: Callable[[], object] | None = None   # resolverlo desde la CLI


# ── comprobaciones ──────────────────────────────────────────────────────────────
def _sqlcmd() -> tuple[bool, str]:
    from .sql import SQLCMD_EXTRAS
    exe = shell.which("sqlcmd", SQLCMD_EXTRAS)
    return (True, exe) if exe else (False, "sqlcmd no esta instalado")


def _dotnet() -> tuple[bool, str]:
    exe = shell.which("dotnet", shell.DOTNET_EXTRAS)
    return (True, exe) if exe else (False, ".NET SDK 10 no esta instalado")


def _env() -> tuple[bool, str]:
    from .paths import ENV_FILE
    return (True, "") if ENV_FILE.exists() else (False, "no existe el archivo .env")


def _sql() -> tuple[bool, str]:
    from . import sql
    bien, det = _sqlcmd()
    if not bien:
        return bien, det
    cfg = env.cargar()
    ok, detalle = sql.alcanzable(cfg, usar_cache=False)
    if not ok:
        return False, f"{cfg['DB_SERVER']}: {detalle}"
    if cfg.get("DB_AUTH", "sql") == "sql" and not env.credenciales(cfg, admin=True)[1]:
        return False, "falta la contrasena de SQL en el .env (DB_PASSWORD / DB_ADMIN_PASSWORD)"
    return True, detalle


def _base() -> tuple[bool, str]:
    from . import sql
    nombre = env.get("DB_NAME")
    try:
        return (True, nombre) if sql.existe_base(nombre) else (False, f"la base '{nombre}' no existe")
    except ui.Fallo as e:
        return False, str(e).splitlines()[0]


def _ef() -> tuple[bool, str]:
    from cli.modules.dependencias.restaurar import ef_rapido
    return ef_rapido()


def _docker() -> tuple[bool, str]:
    exe = shell.which("docker")
    if not exe:
        return False, "Docker no esta instalado"
    return True, exe


def _root() -> tuple[bool, str]:
    if shell.es_root():
        return True, ""
    if not shell.ES_WINDOWS and shell.which("sudo"):
        return True, "se usara sudo"
    return False, ("abra la terminal como Administrador" if shell.ES_WINDOWS else "ejecute con sudo")


def _linux() -> tuple[bool, str]:
    return (not shell.ES_WINDOWS, "") if not shell.ES_WINDOWS else (False, "solo disponible en Linux")


def _windows() -> tuple[bool, str]:
    return (True, "") if shell.ES_WINDOWS else (False, "el migrador WPF solo se compila en Windows")


def _shp() -> tuple[bool, str]:
    from cli.modules.bd.capas.capas import CAPAS, carpeta
    faltan = [c.archivo for c in CAPAS if not (carpeta() / f"{c.archivo}.shp").exists()]
    if len(faltan) == len(CAPAS):
        return False, f"no hay archivos SHP en {carpeta()} (copie el paquete de datos autorizado)"
    return True, str(carpeta())


def _pyshp() -> tuple[bool, str]:
    import importlib.util
    return (True, "") if importlib.util.find_spec("shapefile") else (False, "falta la libreria pyshp")


def _nginx() -> tuple[bool, str]:
    if shell.ES_WINDOWS:
        from cli.modules.services.definiciones import dir_nginx
        return ((dir_nginx() / "nginx.exe").exists(), "nginx no descargado")
    exe = shell.which("nginx", ["/usr/sbin/nginx"])
    return (True, exe) if exe else (False, "nginx no esta instalado")


def _flutter() -> tuple[bool, str]:
    return (True, "") if shell.which("flutter") else (False, "Flutter SDK no esta instalado (solo en equipos de desarrollo)")


# ── resolutores ─────────────────────────────────────────────────────────────────
def _instalar(clave: str) -> Callable[[], None]:
    def f() -> None:
        from cli.modules.dependencias import instalar
        from cli.modules.dependencias.requisitos import HERRAMIENTAS
        instalar._instalar([h for h in HERRAMIENTAS if h.clave == clave])
    return f


def _r_env() -> None:
    from cli.modules.entorno import env_file
    env_file.crear()


def _r_sql() -> None:
    from cli.modules.bd.servidor import motor
    motor.instalar()


def _r_base() -> None:
    from cli.modules.bd import admin
    admin.crear()


def _r_ef() -> None:
    from cli.modules.dependencias import restaurar
    restaurar.herramientas_dotnet()


def _r_pyshp() -> None:
    from cli.modules.dependencias import restaurar
    restaurar.python_cli()


def _r_nginx() -> None:
    from cli.modules.services.nginx import nginx
    nginx.instalar_binarios()


REQUISITOS: dict[str, Requisito] = {r.clave: r for r in [
    Requisito("env", ".env", _env, "arquis entorno crear", _r_env),
    Requisito("dotnet", ".NET", _dotnet, "arquis deps servidor", _instalar("dotnet")),
    Requisito("sqlcmd", "sqlcmd", _sqlcmd, "arquis deps servidor", _instalar("sqlcmd")),
    Requisito("sql", "SQL Server", _sql, "arquis bd servidor instalar  |  docker-iniciar  |  mssql-reiniciar", _r_sql),
    Requisito("base", "base", _base, "arquis bd crear", _r_base),
    Requisito("ef", "dotnet-ef", _ef, "arquis deps ef", _r_ef),
    Requisito("docker", "Docker", _docker, "arquis deps una → Docker", _instalar("docker")),
    Requisito("root", "admin", _root, "sudo ./arquis.sh ..."),
    Requisito("linux", "Linux", _linux, "esta accion es para servidores Linux"),
    Requisito("windows", "Windows", _windows, "ejecutela en un equipo Windows"),
    Requisito("shp", "SHP", _shp, "copie las capas a SHP_DIR (03_DatosPrueba/DatosSIG_Reproj)"),
    Requisito("pyshp", "pyshp", _pyshp, "arquis deps pip-cli", _r_pyshp),
    Requisito("nginx", "nginx", _nginx, "arquis services nginx descargar", _r_nginx),
    Requisito("flutter", "Flutter", _flutter, "instale Flutter SDK"),
]}

# Dependencias implicitas: pedir "base" implica comprobar antes "sql", etc.
_IMPLICA = {"sql": ("sqlcmd",), "base": ("sql",), "ef": ("dotnet",)}


def expandir(claves: tuple[str, ...]) -> list[str]:
    orden: list[str] = []

    def agregar(k: str) -> None:
        for previo in _IMPLICA.get(k, ()):
            agregar(previo)
        if k not in orden:
            orden.append(k)
    for k in claves:
        agregar(k)
    return orden


def etiqueta(claves: tuple[str, ...]) -> str:
    """Texto para el menu: 'necesita SQL Server, base'."""
    if not claves:
        return ""
    return "necesita " + ", ".join(REQUISITOS[k].etiqueta for k in claves if k in REQUISITOS)


def verificar(claves: tuple[str, ...]) -> bool:
    """Comprueba los requisitos; si falta alguno lo explica y ofrece resolverlo."""
    if not claves or os.environ.get("ARQUIS_SIN_REQUISITOS"):
        return True
    for k in expandir(claves):
        r = REQUISITOS[k]
        bien, detalle = r.comprobar()
        if bien:
            continue
        ui.error(f"Esta accion necesita {r.etiqueta}: {detalle}")
        if k == "sql":
            from . import sql
            ui.dim(sql.ayuda_sin_servidor())
        else:
            ui.dim(f"  Como resolverlo: {r.ayuda}")
        if r.resolver is None or not ui.confirmar(f"¿Resolver '{r.etiqueta}' ahora?", True):
            return False
        try:
            r.resolver()
        except ui.Fallo as e:
            ui.error(str(e))
            return False
        if k == "sql":
            from . import sql
            sql.olvidar_alcance()
        bien, detalle = r.comprobar()
        if not bien:
            ui.error(f"Sigue faltando {r.etiqueta}: {detalle}")
            return False
        ui.ok(f"{r.etiqueta}: listo")
    return True
