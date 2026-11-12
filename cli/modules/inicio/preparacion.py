"""Chequeo de preparacion: detecta lo que falta y lo arregla en orden.

    arquis inicio revisar    tabla con el estado de cada requisito
    arquis inicio preparar   arregla lo pendiente, paso a paso (con --yes sin preguntar)

Cubre: paquetes del sistema, dependencias Python, .env, NuGet (backend y
frontend), dotnet-ef, SQL Server, base de datos, migraciones, capas, nginx,
HTTPS y servicios. No incluye Android/Flutter (no se compila en el servidor).
Al abrir el menu interactivo se ejecuta la version rapida y se avisa de lo pendiente.
"""
from __future__ import annotations

import importlib.util
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from cli.core import env, shell, sql, ui
from cli.core.paths import BACKEND, ENV_FILE, FRONTEND, rel

OK, FALTA, AVISO, NA = "ok", "falta", "aviso", "-"


@dataclass
class Chequeo:
    clave: str
    titulo: str
    probar: Callable[[], tuple[str, str]]     # (estado, detalle)
    arreglar: Callable[[], object] | None
    comando: str                              # como arreglarlo a mano
    rapido: bool = True                       # se usa en el aviso del menu
    solo_servidor: bool = False


def es_servidor(cfg: dict[str, str] | None = None) -> bool:
    cfg = cfg or env.cargar()
    return cfg.get("ARQUIS_ENV") == "Production"


# ── pruebas ─────────────────────────────────────────────────────────────────────
def _herramienta(clave: str) -> Callable[[], tuple[str, str]]:
    def probar() -> tuple[str, str]:
        from cli.modules.dependencias.requisitos import HERRAMIENTAS
        h = next(x for x in HERRAMIENTAS if x.clave == clave)
        if not h.aplica():
            return NA, "no aplica en este sistema"
        if not h.ruta():
            return FALTA, f"no instalado ({h.para})"
        ver = h.version()
        if h.minimo and not ver.startswith(h.minimo):
            return FALTA, f"version {ver}; se requiere {h.minimo}x"
        return OK, ver
    return probar


def _instalar_herramienta(*claves: str) -> Callable[[], None]:
    def arreglar() -> None:
        from cli.modules.dependencias import instalar
        from cli.modules.dependencias.requisitos import HERRAMIENTAS
        instalar._instalar([h for h in HERRAMIENTAS if h.clave in claves and not h.ruta()])
    return arreglar


def _p_python() -> tuple[str, str]:
    if importlib.util.find_spec("shapefile") is None:
        return FALTA, "falta pyshp (importador de capas)"
    return OK, shell.python()


def _p_env() -> tuple[str, str]:
    if not ENV_FILE.exists():
        return FALTA, f"no existe {rel(ENV_FILE)}"
    from cli.modules.entorno.env_file import revisar
    errores, avisos = revisar()
    if errores:
        return FALTA, errores[0] + (f" (+{len(errores) - 1})" if len(errores) > 1 else "")
    return (AVISO, avisos[0]) if avisos else (OK, env.get("ARQUIS_ENV"))


def _p_nuget() -> tuple[str, str]:
    pendientes = []
    for nombre, carpeta in (("backend", BACKEND), ("frontend", FRONTEND)):
        assets = carpeta / "obj" / "project.assets.json"
        csproj = next(carpeta.glob("*.csproj"), None)
        if not assets.exists() or (csproj and csproj.stat().st_mtime > assets.stat().st_mtime):
            pendientes.append(nombre)
    return (FALTA, "sin restaurar: " + ", ".join(pendientes)) if pendientes else (OK, "backend y frontend")


def _home_usuario() -> Path:
    usuario = shell.usuario_original()
    return Path(os.path.expanduser(f"~{usuario}")) if usuario else Path.home()


def _p_ef() -> tuple[str, str]:
    from cli.modules.dependencias.restaurar import DOTNET_TOOLS, MANIFIESTO
    if not MANIFIESTO.exists():
        return FALTA, "sin manifiesto .config/dotnet-tools.json"
    version = DOTNET_TOOLS["dotnet-ef"]
    nuget = Path(os.environ.get("NUGET_PACKAGES") or _home_usuario() / ".nuget" / "packages")
    if not (nuget / "dotnet-ef" / version).exists():
        return FALTA, f"dotnet-ef {version} sin restaurar"
    return OK, version


def _destino_sql(cfg: dict[str, str]) -> tuple[str, int] | None:
    servidor = cfg["DB_SERVER"].strip()
    if servidor.lower().startswith(("(localdb)", "np:", "lpc:")) or "\\" in servidor:
        return None   # instancia con nombre / LocalDB: sin puerto fijo
    host, _, puerto = servidor.replace("tcp:", "").partition(",")
    host = "127.0.0.1" if host in (".", "(local)", "localhost") else host
    return host, int(puerto or 1433)


_SOLO_PUERTO = False   # True solo en el aviso al abrir el menu


def _p_sql_rapido() -> tuple[str, str]:
    if not ENV_FILE.exists():
        return NA, "configure el .env primero"
    cfg = env.cargar()
    destino = _destino_sql(cfg)
    if destino is None:
        return _p_sql()
    try:
        with socket.create_connection(destino, timeout=1.5):
            pass
    except OSError:
        return FALTA, f"nada escucha en {destino[0]}:{destino[1]}"
    if _SOLO_PUERTO:
        return OK, f"{destino[0]}:{destino[1]} responde"
    return _p_sql()


def _p_sql() -> tuple[str, str]:
    if not shell.which("sqlcmd", sql.SQLCMD_EXTRAS):
        return NA, "falta sqlcmd"
    try:
        bien, detalle = sql.probar()
    except ui.Fallo as e:
        return FALTA, str(e)[:120]
    return (OK, detalle) if bien else (FALTA, " ".join(detalle.split())[:200] or "sin conexion")


def _p_base() -> tuple[str, str]:
    if _p_sql()[0] != OK:
        return NA, "sin conexion a SQL Server"
    nombre = env.get("DB_NAME")
    return (OK, nombre) if sql.existe_base() else (FALTA, f"la base {nombre} no existe")


def _p_login() -> tuple[str, str]:
    if _p_base()[0] != OK:
        return NA, "la base no existe"
    from cli.modules.bd.servidor.conexion import estado_login_app
    bien, detalle = estado_login_app()
    return (OK if bien else FALTA), detalle


def _a_login() -> None:
    from cli.modules.bd.servidor.conexion import asegurar_login_app
    asegurar_login_app()


def _migraciones_codigo() -> list[str]:
    carpeta = BACKEND / "Migrations"
    return sorted(p.stem for p in carpeta.glob("*.cs")
                  if not p.name.endswith(".Designer.cs") and "ModelSnapshot" not in p.name and p.stem[:14].isdigit())


def _p_migraciones() -> tuple[str, str]:
    if _p_base()[0] != OK:
        return NA, "la base no existe"
    codigo = _migraciones_codigo()
    try:
        aplicadas = {f[0] for f in sql.filas(
            "IF OBJECT_ID('dbo.__EFMigrationsHistory') IS NOT NULL SELECT MigrationId FROM dbo.__EFMigrationsHistory")}
    except ui.Fallo:
        aplicadas = set()
    pendientes = [m for m in codigo if m not in aplicadas]
    if pendientes:
        return FALTA, f"{len(pendientes)} pendientes de {len(codigo)} (ultima: {pendientes[-1][15:]})"
    return OK, f"{len(codigo)} aplicadas"


def _p_capas() -> tuple[str, str]:
    from cli.modules.bd.capas.capas import CAPAS, carpeta
    if _p_migraciones()[0] != OK:
        return NA, "faltan migraciones"
    hay_shp = any((carpeta() / f"{c.archivo}.shp").exists() for c in CAPAS)
    try:
        filas = int(sql.escalar("SELECT COUNT(*) FROM dbo.Manzanas") or 0)
    except (ui.Fallo, ValueError):
        filas = 0
    if filas:
        return OK, f"{filas} manzanas cargadas"
    if not hay_shp:
        return AVISO, f"base sin capas y sin SHP en {env.get('SHP_DIR')} (copie el paquete de datos autorizado)"
    return FALTA, "las capas SHP no estan importadas"


def _nginx_activo() -> bool:
    return env.es_verdad("NGINX_ENABLED") and es_servidor()


def _p_nginx() -> tuple[str, str]:
    if not _nginx_activo():
        return NA, "NGINX_ENABLED=false"
    from cli.modules.services.nginx import nginx
    if not shell.which("nginx", ["/usr/sbin/nginx"]) and not shell.ES_WINDOWS:
        return FALTA, "nginx no instalado"
    if not nginx.ruta_config().exists():
        return FALTA, "sin configuracion de Arquis"
    return OK, str(nginx.ruta_config())


def _p_https() -> tuple[str, str]:
    cfg = env.cargar()
    if not _nginx_activo() or cfg.get("HTTPS") == "none":
        return NA, "HTTPS=none"
    if not cfg.get("NGINX_SSL_CERT"):
        return FALTA, "certificado sin emitir"
    if not shell.ES_WINDOWS and not Path(cfg["NGINX_SSL_CERT"]).exists():
        return FALTA, f"no existe {cfg['NGINX_SSL_CERT']}"
    return OK, ", ".join(n for n in (cfg["WEB_DOMAIN"], cfg["API_DOMAIN"]) if n)


def _p_servicios() -> tuple[str, str]:
    from cli.modules.services import definiciones as d
    from cli.modules.services.gestores import gestor
    malos = []
    for s in d.todos(incluir_nginx=False):
        if not gestor(s).existe(s):
            malos.append(f"{s.clave} no instalado")
        elif not d.puerto_abierto(s.puerto):
            malos.append(f"{s.clave} detenido")
    return (FALTA, ", ".join(malos)) if malos else (OK, "backend y frontend en marcha")


# ── arreglos ────────────────────────────────────────────────────────────────────
def _a_env() -> None:
    from cli.modules.entorno import env_file
    if not ENV_FILE.exists():
        env_file.crear()
    else:
        env_file.validar(probar_bd=False)
        if ui.confirmar("¿Corregir el .env con el asistente?", True):
            env_file.crear()


def _a_sql() -> None:
    from cli.modules.bd.servidor import motor
    motor.instalar()


def _a_base() -> None:
    from cli.modules.bd import admin
    admin.crear()


def _a_migraciones() -> None:
    from cli.modules.bd.migraciones import ef
    ef.actualizar()


def _a_capas() -> None:
    from cli.modules.bd.capas import importar
    importar.importar(reemplazar=False)


def _a_nginx() -> None:
    from cli.modules.services.nginx import nginx
    nginx.instalar_binarios()
    nginx.escribir_config()


def _a_https() -> None:
    from cli.modules.services.nginx import nginx
    nginx.https()


def _a_servicios() -> None:
    from cli.modules.deploy import pipeline
    pipeline.completo()


def _a_python() -> None:
    from cli.modules.dependencias import restaurar
    restaurar.python_cli()
    ui.warn("Vuelva a abrir la CLI para cargar las dependencias nuevas.")


def _a_nuget() -> None:
    from cli.modules.dependencias import restaurar
    restaurar.nuget()


def _a_ef() -> None:
    from cli.modules.dependencias import restaurar
    restaurar.herramientas_dotnet()


CHEQUEOS: list[Chequeo] = [
    Chequeo("dotnet", ".NET SDK 10", _herramienta("dotnet"), _instalar_herramienta("dotnet"), "arquis deps servidor"),
    Chequeo("sqlcmd", "sqlcmd", _herramienta("sqlcmd"), _instalar_herramienta("sqlcmd"), "arquis deps servidor"),
    Chequeo("fuentes", "Fuentes (PDF)", _herramienta("fc-list"), _instalar_herramienta("fc-list"), "arquis deps servidor",
            solo_servidor=True),
    Chequeo("python", "Dependencias Python", _p_python, _a_python, "arquis deps pip-cli"),
    Chequeo("env", "Configuracion .env", _p_env, _a_env, "arquis entorno crear"),
    Chequeo("nuget", "Paquetes NuGet (backend/frontend)", _p_nuget, _a_nuget, "arquis deps nuget"),
    Chequeo("ef", "dotnet-ef (migraciones)", _p_ef, _a_ef, "arquis deps ef"),
    Chequeo("sql", "SQL Server", _p_sql_rapido, _a_sql, "arquis bd servidor instalar"),
    Chequeo("base", "Base de datos", _p_base, _a_base, "arquis bd crear", rapido=False),
    Chequeo("login", "Login SQL de la app", _p_login, _a_login, "arquis bd servidor login", rapido=False),
    Chequeo("migraciones", "Migraciones", _p_migraciones, _a_migraciones, "arquis bd migraciones aplicar", rapido=False),
    Chequeo("capas", "Capas SIG", _p_capas, _a_capas, "arquis bd capas importar", rapido=False),
    Chequeo("nginx", "nginx", _p_nginx, _a_nginx, "arquis services nginx dominios", solo_servidor=True),
    Chequeo("https", "HTTPS", _p_https, _a_https, "arquis services nginx https", solo_servidor=True),
    Chequeo("servicios", "Servicios (backend/frontend)", _p_servicios, _a_servicios, "sudo ./arquis.sh deploy completo",
            rapido=False, solo_servidor=True),
]


def _aplicables(rapido: bool = False, servicios: bool = True) -> list[Chequeo]:
    servidor = es_servidor()
    return [c for c in CHEQUEOS
            if (servidor or not c.solo_servidor) and (c.rapido or not rapido) and (servicios or c.clave != "servicios")]


def _progreso(texto: str = "") -> None:
    """Linea temporal 'Revisando ...' (solo en terminal) para que nunca parezca colgado."""
    import sys
    if not sys.stdout.isatty():
        return
    inicio_linea = chr(13)
    if texto:
        sys.stdout.write(inicio_linea + "  " + ui.c(texto.ljust(70), ui.C.GRAY))
    else:
        sys.stdout.write(inicio_linea + " " * 90 + inicio_linea)
    sys.stdout.flush()


def _ejecutar(c: Chequeo) -> tuple[str, str]:
    _progreso(f"· Revisando {c.titulo}...")
    try:
        return c.probar()
    except ui.Fallo as e:
        return FALTA, str(e).splitlines()[0][:120]
    except Exception as e:  # noqa: BLE001  (un chequeo nunca debe tumbar la CLI)
        return AVISO, f"no se pudo comprobar: {e}"[:120]
    finally:
        _progreso()


_COLOR = {OK: ui.C.GREEN, FALTA: ui.C.RED, AVISO: ui.C.YELLOW, NA: ui.C.GRAY}
_ICONO = {OK: "✔", FALTA: "✖", AVISO: "!", NA: "·"}


def revisar() -> bool:
    """Estado de todo lo necesario para que Arquis funcione."""
    ui.info("Modo: " + ("servidor (produccion)" if es_servidor() else "desarrollo"))
    filas, pendientes = [], 0
    for c in _aplicables():
        estado, detalle = _ejecutar(c)
        pendientes += estado == FALTA
        filas.append([ui.c(_ICONO[estado], _COLOR[estado]), c.titulo, detalle,
                      ui.c(c.comando, ui.C.GRAY) if estado == FALTA else ""])
    ui.tabla(filas, ["", "Requisito", "Estado", "Como arreglarlo"])
    if pendientes:
        ui.warn(f"{pendientes} pendientes. Arreglelos todos con: arquis inicio preparar")
        return False
    ui.ok("Todo listo.")
    return True


def preparar(servicios: bool = True, omitir: tuple[str, ...] = ()) -> bool:
    """Arregla, en orden, todo lo que falte (pregunta antes de cada paso)."""
    lista = [c for c in _aplicables(servicios=servicios) if c.clave not in omitir]
    arreglados, fallidos = [], []
    for i, c in enumerate(lista, 1):
        estado, detalle = _ejecutar(c)
        if estado != FALTA:
            continue
        ui.paso(i, len(lista), f"{c.titulo}: {detalle}")
        if c.arreglar is None or not ui.confirmar("¿Arreglarlo ahora?", True):
            fallidos.append(c.titulo)
            continue
        try:
            c.arreglar()
        except ui.Fallo as e:
            ui.error(str(e))
        estado, detalle = _ejecutar(c)
        if estado == FALTA:
            ui.error(f"{c.titulo} sigue pendiente: {detalle}")
            fallidos.append(c.titulo)
            if c.clave in ("dotnet", "env", "sql"):   # sin esto no tiene sentido seguir
                break
        else:
            ui.ok(f"{c.titulo}: {detalle}")
            arreglados.append(c.titulo)
    ui.seccion("Resultado")
    if arreglados:
        ui.ok("Arreglado: " + ", ".join(arreglados))
    if fallidos:
        ui.warn("Pendiente: " + ", ".join(fallidos))
        return False
    ui.ok("Todo listo.")
    return True


def aviso_inicial() -> None:
    """Chequeo rapido al abrir el menu (no consulta la base ni compila)."""
    global _SOLO_PUERTO
    _SOLO_PUERTO = True
    pendientes = [c.titulo for c in _aplicables(rapido=True) if _ejecutar(c)[0] == FALTA]
    if pendientes:
        ui.warn("Falta preparar: " + ", ".join(pendientes))
        ui.dim("    → Inicio rapido › Preparar todo   (o: arquis inicio preparar)")
