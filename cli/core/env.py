"""Configuracion del proyecto: archivo .env y traduccion a variables de .NET.

El .env contiene solo lo que la aplicacion necesita de verdad:

  Backend  (Arquis.Backend)   ConnectionStrings:DefaultConnection, puerto (Kestrel),
                              Viewer:DefaultFeatureLimit / MaxFeatureLimit, entorno, log
  Frontend (Arquis.Frontend)  BackendBaseUrl, puerto
  Servidor (solo la CLI)      carpeta de instalacion, usuario del servicio, nginx

Al arrancar backend/frontend (modo dev o servicio systemd/NSSM) la CLI convierte
estos valores en las variables que ASP.NET Core ya lee
(ConnectionStrings__DefaultConnection, Kestrel__Endpoints__Http__Url, ...),
asi que no se edita appsettings.json ni se suben secretos a git.

Las variables "avanzadas" tienen un valor por defecto razonable y solo se
escriben en el .env si se cambian. Cualquier variable del entorno del proceso
tiene prioridad sobre el .env (util en CI:  DB_NAME=Pruebas ./arquis.sh bd estado).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .paths import ENV_FILE, ROOT

ES_WINDOWS = os.name == "nt"


class _PorSO(str):
    """Valor por defecto que depende del sistema; recuerda el de Linux para la plantilla."""
    linux: str


def _por_so(linux: str, windows: str) -> str:
    v = _PorSO(windows if ES_WINDOWS else linux)
    v.linux = linux
    return v


def defecto_linux(v: "Variable") -> str:
    """La plantilla .env.example documenta siempre un servidor Linux."""
    return getattr(v.defecto, "linux", v.defecto)


@dataclass(frozen=True)
class Variable:
    nombre: str
    defecto: str
    descripcion: str
    grupo: str
    secreto: bool = False
    opciones: tuple[str, ...] = ()
    avanzada: bool = False      # no se escribe en el .env salvo que difiera del defecto
    usa: str = ""               # que la consume (para documentar)


ESQUEMA: list[Variable] = [
    # ── Aplicacion ──────────────────────────────────────────────────────────
    Variable("ARQUIS_ENV", _por_so("Production", "Development"), "Entorno ASP.NET Core", "Aplicacion",
             opciones=("Production", "Development", "Staging"), usa="ASPNETCORE_ENVIRONMENT"),
    Variable("LOG_LEVEL", "Information", "Nivel de log", "Aplicacion", avanzada=True,
             opciones=("Trace", "Debug", "Information", "Warning", "Error"), usa="Logging:LogLevel:Default"),
    # ── Base de datos ───────────────────────────────────────────────────────
    Variable("DB_SERVER", _por_so("localhost", r"(localdb)\MSSQLLocalDB"), "Servidor SQL Server (host[,puerto])",
             "Base de datos", usa="ConnectionStrings:DefaultConnection"),
    Variable("DB_NAME", "VisorDatosSIG", "Nombre de la base", "Base de datos", usa="ConnectionStrings:DefaultConnection"),
    Variable("DB_AUTH", _por_so("sql", "windows"), "Autenticacion", "Base de datos", opciones=("sql", "windows"),
             usa="ConnectionStrings:DefaultConnection"),
    Variable("DB_USER", _por_so("sa", ""), "Usuario SQL (DB_AUTH=sql)", "Base de datos", usa="ConnectionStrings:DefaultConnection"),
    Variable("DB_PASSWORD", "", "Contrasena SQL (DB_AUTH=sql)", "Base de datos", secreto=True,
             usa="ConnectionStrings:DefaultConnection"),
    Variable("DB_ADMIN_USER", "", "Cuenta administradora que usa la CLI (crear base, migrar, respaldar); vacio = DB_USER",
             "Base de datos", avanzada=True),
    Variable("DB_ADMIN_PASSWORD", "", "Contrasena de la cuenta administradora", "Base de datos", secreto=True,
             avanzada=True),
    Variable("DB_TRUST_CERT", "true", "Aceptar certificado autofirmado del servidor", "Base de datos",
             opciones=("true", "false"), avanzada=True, usa="TrustServerCertificate"),
    # ── Backend ─────────────────────────────────────────────────────────────
    Variable("BACKEND_HOST", _por_so("127.0.0.1", "0.0.0.0"), "Interfaz de escucha de la API", "Backend",
             avanzada=True, usa="Kestrel:Endpoints:Http:Url"),
    Variable("BACKEND_PORT", "5080", "Puerto de la API", "Backend", usa="Kestrel:Endpoints:Http:Url"),
    Variable("VIEWER_DEFAULT_FEATURE_LIMIT", "1500", "Entidades por consulta del visor", "Backend",
             avanzada=True, usa="Viewer:DefaultFeatureLimit"),
    Variable("VIEWER_MAX_FEATURE_LIMIT", "5000", "Maximo de entidades por consulta", "Backend",
             avanzada=True, usa="Viewer:MaxFeatureLimit"),
    # ── Frontend ────────────────────────────────────────────────────────────
    Variable("FRONTEND_HOST", _por_so("127.0.0.1", "0.0.0.0"), "Interfaz de escucha del visor", "Frontend",
             avanzada=True, usa="ASPNETCORE_URLS"),
    Variable("FRONTEND_PORT", "5180", "Puerto del visor", "Frontend", usa="ASPNETCORE_URLS"),
    # ── Servidor (solo la CLI) ──────────────────────────────────────────────
    Variable("DEPLOY_DIR", _por_so("/opt/arquis", r"C:\Arquis"), "Carpeta de instalacion", "Servidor"),
    Variable("SERVICE_USER", _por_so("arquis", ""), "Usuario que ejecuta los servicios (vacio en Windows = LocalSystem)",
             "Servidor"),
    # ── Publicacion (nginx + dominios) ───────────────────────────────────────
    Variable("NGINX_ENABLED", _por_so("true", "false"), "Publicar detras de nginx", "Publicacion",
             opciones=("true", "false")),
    Variable("WEB_DOMAIN", "_", "Dominio del visor (ej. sig.midominio.com; _ = cualquiera / IP)", "Publicacion"),
    Variable("API_DOMAIN", "", "Subdominio de la API para la app movil (ej. api.midominio.com; vacio = solo WEB_DOMAIN/api)",
             "Publicacion"),
    Variable("HTTPS", "none", "Certificado HTTPS (cloudflare = certificado de origen, si el DNS pasa por Cloudflare)",
             "Publicacion", opciones=("none", "letsencrypt", "cloudflare", "manual")),
    Variable("LETSENCRYPT_EMAIL", "", "Correo para avisos de Let's Encrypt (HTTPS=letsencrypt)", "Publicacion"),
    Variable("NGINX_SSL_CERT", "", "Certificado (fullchain.pem); lo completa Let's Encrypt", "Publicacion", avanzada=True),
    Variable("NGINX_SSL_KEY", "", "Clave privada (privkey.pem); la completa Let's Encrypt", "Publicacion", avanzada=True),
    Variable("NGINX_PORT", "80", "Puerto HTTP publico", "Publicacion", avanzada=True),
    Variable("BACKEND_PUBLIC_URL", "", "URL publica de la API (vacio = automatica desde los dominios)", "Publicacion",
             avanzada=True, usa="Movil API_BASE_URL"),
    # ── Avanzadas de despliegue ─────────────────────────────────────────────
    Variable("DEPLOY_KEEP_RELEASES", "5", "Versiones anteriores a conservar", "Despliegue", avanzada=True),
    Variable("DEPLOY_RUN_TESTS", "true", "Ejecutar pruebas antes de desplegar", "Despliegue",
             opciones=("true", "false"), avanzada=True),
    Variable("DEPLOY_BACKUP_DB", "true", "Respaldar la base antes de migrar", "Despliegue",
             opciones=("true", "false"), avanzada=True),
    Variable("DEPLOY_AUTOSTART", "true", "Arrancar los servicios con el sistema", "Despliegue",
             opciones=("true", "false"), avanzada=True),
    Variable("DEPLOY_OPEN_FIREWALL", "false", "Abrir puertos en el firewall", "Despliegue",
             opciones=("true", "false"), avanzada=True),
    Variable("SERVICE_PREFIX", "Arquis", "Prefijo del nombre de los servicios", "Despliegue", avanzada=True),
    Variable("SERVICE_MANAGER", "auto", "Gestor de servicios", "Despliegue",
             opciones=("auto", "systemd", "nssm"), avanzada=True),
    Variable("NGINX_MAX_BODY", "50m", "Tamano maximo de subida", "Despliegue", avanzada=True),
    Variable("NGINX_VERSION", "1.26.2", "Version de nginx (solo Windows)", "Despliegue", avanzada=True),
    Variable("SHP_DIR", "03_DatosPrueba/DatosSIG_Reproj", "Carpeta con las capas SHP", "Despliegue", avanzada=True),
]

POR_NOMBRE = {v.nombre: v for v in ESQUEMA}
# Nombres antiguos que se leen con su nombre nuevo
ALIAS = {"NGINX_SERVER_NAME": "WEB_DOMAIN"}
OBSOLETAS = {"NGINX_SERVER_NAME", "DB_TIMEOUT", "CORS_ORIGINS", "MOVIL_API_URL_LOCAL", "MOVIL_API_URL_ANDROID", "ANDROID_DEVICE",
             "GEMINI_API_KEY", "LLM_MODEL_URL", "LLM_MODEL_FILE", "DEPLOY_BUILD_APK", "FRONTEND_PUBLIC_URL"}
_LINEA = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")


def _desescapar(valor: str) -> str:
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1].replace('\\"', '"')
    if " #" in valor:
        valor = valor.split(" #", 1)[0].rstrip()
    return valor


def leer(ruta: Path = ENV_FILE) -> dict[str, str]:
    datos: dict[str, str] = {}
    if not ruta.exists():
        return datos
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        m = _LINEA.match(linea)
        if m:
            datos[m.group(1)] = _desescapar(m.group(2))
    for viejo, nuevo in ALIAS.items():
        if viejo in datos and nuevo not in datos:
            datos[nuevo] = datos[viejo]
    return datos


def _formatear(valor: str) -> str:
    if valor and re.search(r"[\s#\"'$`\\;]", valor):
        return '"' + valor.replace('"', '\\"') + '"'
    return valor


def escribir(valores: dict[str, str], ruta: Path = ENV_FILE, plantilla: bool = False) -> None:
    """Escribe el .env: esenciales siempre, avanzadas solo si cambian.

    Con `plantilla` genera .env.example (sin secretos y con las avanzadas comentadas).
    """
    if plantilla:
        lineas = ["# Plantilla de configuracion de Arquis (sin secretos). Valores para un servidor Linux.",
                  "# Cree su .env con el asistente:  ./arquis.sh entorno crear   (Windows: arquis.cmd entorno crear)",
                  "# Las lineas comentadas son opcionales: su valor por defecto ya sirve."]
    else:
        lineas = ["# Configuracion de Arquis. Gestionar con: ./arquis.sh entorno",
                  "# Contiene credenciales: no subir a git."]
    grupo = None
    for v in ESQUEMA:
        val = defecto_linux(v) if plantilla else valores.get(v.nombre, v.defecto)
        if v.secreto and plantilla:
            val = ""
        if v.avanzada and not plantilla and val == v.defecto:
            continue
        if v.grupo != grupo:
            grupo = v.grupo
            lineas += ["", f"# ── {grupo} " + "─" * (44 - len(grupo))]
        extra = f"  [{' | '.join(v.opciones)}]" if v.opciones else ""
        lineas.append(f"# {v.descripcion}{extra}")
        prefijo = "# " if v.avanzada and plantilla else ""
        lineas.append(f"{prefijo}{v.nombre}={_formatear(val)}")
    extras = {k: v for k, v in valores.items() if k not in POR_NOMBRE and k not in OBSOLETAS}
    if extras and not plantilla:
        lineas += ["", "# ── Otras ────────────────────────────────────────"]
        lineas += [f"{k}={_formatear(v)}" for k, v in extras.items()]
    ruta.write_text("\n".join(lineas).lstrip() + "\n", encoding="utf-8", newline="\n")
    if not plantilla and not ES_WINDOWS:
        try:
            os.chmod(ruta, 0o600)
        except OSError:
            pass


def cargar() -> dict[str, str]:
    """Valores efectivos: defectos + .env + variables del proceso."""
    datos = {v.nombre: v.defecto for v in ESQUEMA}
    datos.update(leer())
    for v in ESQUEMA:
        if v.nombre in os.environ:
            datos[v.nombre] = os.environ[v.nombre]
    return datos


def get(nombre: str) -> str:
    return cargar().get(nombre, "")


def es_verdad(nombre: str, cfg: dict[str, str] | None = None) -> bool:
    return (cfg or cargar()).get(nombre, "").strip().lower() in ("1", "true", "si", "sí", "yes")


def ruta_proyecto(valor: str) -> Path:
    p = Path(valor)
    return p if p.is_absolute() else ROOT / p


# -- traducciones a .NET ----------------------------------------------------------
def credenciales(cfg: dict[str, str] | None = None, admin: bool = False) -> tuple[str, str]:
    """(usuario, contrasena). Con admin=True usa DB_ADMIN_* si estan definidas (tareas de la CLI)."""
    cfg = cfg or cargar()
    if admin and cfg.get("DB_ADMIN_USER"):
        return cfg["DB_ADMIN_USER"], cfg.get("DB_ADMIN_PASSWORD", "")
    return cfg.get("DB_USER", ""), cfg.get("DB_PASSWORD", "")


def cadena_conexion(cfg: dict[str, str] | None = None, base: str | None = None, admin: bool = False) -> str:
    cfg = cfg or cargar()
    partes = [f"Server={cfg['DB_SERVER']}", f"Database={base or cfg['DB_NAME']}"]
    if cfg.get("DB_AUTH", "sql").lower() == "sql":
        usuario, clave = credenciales(cfg, admin)
        partes += [f"User Id={usuario}", f"Password={clave}"]
    else:
        partes.append("Trusted_Connection=True")
    partes.append(f"TrustServerCertificate={'True' if es_verdad('DB_TRUST_CERT', cfg) else 'False'}")
    partes += ["Connect Timeout=30", "MultipleActiveResultSets=True"]
    return ";".join(partes) + ";"


def entorno_backend(cfg: dict[str, str] | None = None) -> dict[str, str]:
    cfg = cfg or cargar()
    return {
        "ASPNETCORE_ENVIRONMENT": cfg["ARQUIS_ENV"],
        "DOTNET_ENVIRONMENT": cfg["ARQUIS_ENV"],
        "ConnectionStrings__DefaultConnection": cadena_conexion(cfg),
        "Kestrel__Endpoints__Http__Url": f"http://{cfg['BACKEND_HOST']}:{cfg['BACKEND_PORT']}",
        "Viewer__DefaultFeatureLimit": cfg["VIEWER_DEFAULT_FEATURE_LIMIT"],
        "Viewer__MaxFeatureLimit": cfg["VIEWER_MAX_FEATURE_LIMIT"],
        "Logging__LogLevel__Default": cfg["LOG_LEVEL"],
    }


def entorno_frontend(cfg: dict[str, str] | None = None) -> dict[str, str]:
    cfg = cfg or cargar()
    return {
        "ASPNETCORE_ENVIRONMENT": cfg["ARQUIS_ENV"],
        "DOTNET_ENVIRONMENT": cfg["ARQUIS_ENV"],
        "ASPNETCORE_URLS": f"http://{cfg['FRONTEND_HOST']}:{cfg['FRONTEND_PORT']}",
        # El servidor del frontend (Blazor) llama a la API en la misma maquina
        "BackendBaseUrl": url_interna_api(cfg),
        # El JavaScript del navegador: con nginx, mismo origen ("/" → WEB_DOMAIN/api, /hubs)
        "PublicApiUrl": "/" if es_verdad("NGINX_ENABLED", cfg) else url_publica("api", cfg),
        "Logging__LogLevel__Default": cfg["LOG_LEVEL"],
    }


def url_local(servicio: str, cfg: dict[str, str] | None = None) -> str:
    cfg = cfg or cargar()
    puerto = cfg["BACKEND_PORT"] if servicio == "backend" else cfg["FRONTEND_PORT"]
    return f"http://localhost:{puerto}"


def ip_local() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))   # UDP: no envia paquetes
            return s.getsockname()[0]
    except OSError:
        return "localhost"


def esquema(cfg: dict[str, str] | None = None) -> str:
    cfg = cfg or cargar()
    return "https" if es_verdad("NGINX_ENABLED", cfg) and cfg.get("NGINX_SSL_CERT") else "http"


def url_interna_api(cfg: dict[str, str] | None = None) -> str:
    """URL con la que el frontend (en el mismo servidor) llega al backend."""
    cfg = cfg or cargar()
    host = cfg["BACKEND_HOST"] if cfg["BACKEND_HOST"] not in ("0.0.0.0", "*", "+", "") else "127.0.0.1"
    return f"http://{host}:{cfg['BACKEND_PORT']}"


def url_publica(cual: str, cfg: dict[str, str] | None = None) -> str:
    """URL publica del visor ('web') o de la API ('api').

    Con nginx: https?://API_DOMAIN para la API si hay subdominio; si no, WEB_DOMAIN.
    Sin nginx (desarrollo): los puertos internos.
    """
    cfg = cfg or cargar()
    if cual == "api" and cfg.get("BACKEND_PUBLIC_URL"):
        return cfg["BACKEND_PUBLIC_URL"].rstrip("/")
    if not es_verdad("NGINX_ENABLED", cfg):
        host = "localhost" if ES_WINDOWS or cfg["ARQUIS_ENV"] != "Production" else ip_local()
        return f"http://{host}:{cfg['BACKEND_PORT' if cual == 'api' else 'FRONTEND_PORT']}"
    dominio = cfg.get("API_DOMAIN") if cual == "api" and cfg.get("API_DOMAIN") else cfg.get("WEB_DOMAIN", "_")
    if dominio in ("", "_"):
        dominio = ip_local()
    esq = esquema(cfg)
    puerto = cfg.get("NGINX_PORT", "80")
    sufijo = "" if esq == "https" or puerto == "80" else f":{puerto}"
    return f"{esq}://{dominio}{sufijo}"


def url_api_movil(cfg: dict[str, str] | None = None, android: bool = True) -> str:
    """La app movil usa la API publica (API_DOMAIN); en el emulador Android localhost es 10.0.2.2."""
    cfg = cfg or cargar()
    base = url_publica("api", cfg)
    if android:
        base = re.sub(r"//(localhost|127\.0\.0\.1)", "//10.0.2.2", base)
    return base + "/api"
