"""Crear, editar, mostrar y validar el .env."""
from __future__ import annotations

import os
import re
import secrets
import shutil
import socket
import string
from datetime import datetime

from cli.core import env, ui
from cli.core.paths import ENV_EXAMPLE, ENV_FILE, SETUP_DIR, asegurar, rel


def _mascara(v: env.Variable, valor: str) -> str:
    if v.secreto and valor:
        return "•" * 8
    return valor


def _tabla(todas: bool) -> None:
    actuales = env.leer()
    grupo, filas = None, []
    for v in env.ESQUEMA:
        if v.avanzada and not todas and v.nombre not in actuales:
            continue
        if v.grupo != grupo:
            grupo = v.grupo
            filas.append([ui.c(grupo, ui.C.BLUE, ui.C.BOLD), "", "", ""])
        valor = env.cargar()[v.nombre]
        origen = "proceso" if v.nombre in os.environ else (".env" if v.nombre in actuales else "defecto")
        filas.append([f"  {v.nombre}", _mascara(v, valor) or ui.c("(vacio)", ui.C.GRAY),
                      ui.c(origen, ui.C.GRAY) if origen == "defecto" else origen, ui.c(v.usa, ui.C.GRAY)])
    ui.tabla(filas, ["Variable", "Valor", "Origen", "Lo usa"])


def mostrar() -> None:
    """Configuracion esencial (secretos ocultos)."""
    if not ENV_FILE.exists():
        ui.warn(f"No existe {rel(ENV_FILE)}: valores por defecto. Cree uno con: entorno crear")
    _tabla(False)
    ui.dim("Ver tambien las avanzadas: entorno ver-todo")


def mostrar_todo() -> None:
    """Configuracion completa, incluidas las variables avanzadas."""
    _tabla(True)
    ui.seccion("Cadena de conexion resultante")
    print("  " + re.sub(r"Password=[^;]*", "Password=••••", env.cadena_conexion()))


def _ip_local() -> str:
    return env.ip_local()


def crear() -> None:
    """Asistente: pregunta solo lo necesario para backend, frontend y servidor."""
    if ENV_FILE.exists() and not ui.confirmar(f"{rel(ENV_FILE)} ya existe. ¿Reemplazarlo? (se guarda respaldo)"):
        return
    _respaldar()
    v = env.cargar()
    ui.info("Enter acepta el valor entre corchetes.")

    ui.seccion("Uso")
    servidor = ui.elegir("¿Donde se usara esta configuracion?",
                         ["Servidor (produccion)", "Equipo de desarrollo"], 0 if not env.ES_WINDOWS else 1) == 0
    v["ARQUIS_ENV"] = "Production" if servidor else "Development"

    ui.seccion("Base de datos (SQL Server)")
    if env.ES_WINDOWS and not servidor and ui.confirmar("¿Usar LocalDB con su usuario de Windows?", True):
        v.update(DB_SERVER=r"(localdb)\MSSQLLocalDB", DB_AUTH="windows", DB_USER="", DB_PASSWORD="")
    else:
        v["DB_SERVER"] = ui.preguntar("Servidor (host o host,puerto)", "localhost" if v["DB_SERVER"].startswith("(localdb)") else v["DB_SERVER"])
        v["DB_AUTH"] = "sql"
        if env.ES_WINDOWS and ui.confirmar("¿Autenticacion de Windows en lugar de usuario SQL?", False):
            v["DB_AUTH"] = "windows"
        if v["DB_AUTH"] == "sql":
            v["DB_USER"] = ui.preguntar("Usuario", v["DB_USER"] or "sa")
            clave = ui.preguntar("Contrasena (Enter = conservar/generar)", secreto=True)
            v["DB_PASSWORD"] = clave or v["DB_PASSWORD"] or _generar_clave()
    v["DB_NAME"] = ui.preguntar("Nombre de la base", v["DB_NAME"])

    ui.seccion("Puertos internos")
    v["BACKEND_PORT"] = ui.preguntar("Puerto de la API", v["BACKEND_PORT"])
    v["FRONTEND_PORT"] = ui.preguntar("Puerto del visor", v["FRONTEND_PORT"])

    ui.seccion("Acceso publico")
    if servidor:
        v["NGINX_ENABLED"] = "true" if ui.confirmar("¿Publicar con nginx (recomendado)?", True) else "false"
    else:
        v["NGINX_ENABLED"] = "false"
    if env.es_verdad("NGINX_ENABLED", v):
        ui.info("Ejemplo: visor en sig.midominio.com y API para la app movil en api.midominio.com")
        web = ui.preguntar("Dominio del visor (_ = usar la IP del servidor)",
                           v["WEB_DOMAIN"] if v["WEB_DOMAIN"] != "_" else "").strip().lower() or "_"
        v["WEB_DOMAIN"] = web
        v["API_DOMAIN"] = ""
        v["HTTPS"] = "none"
        if web != "_":
            base = web.split(".", 1)[1] if web.count(".") >= 2 else web
            api = ui.preguntar("Subdominio de la API (vacio = API en el dominio del visor /api)",
                               v.get("API_DOMAIN") or f"api.{base}").strip().lower()
            v["API_DOMAIN"] = "" if api == web else api
            if ui.confirmar("¿Activar HTTPS gratis con Let's Encrypt?", True):
                v["HTTPS"] = "letsencrypt"
                v["LETSENCRYPT_EMAIL"] = ui.preguntar("Correo para avisos de vencimiento", v.get("LETSENCRYPT_EMAIL") or "")
        v["BACKEND_PUBLIC_URL"] = ""
        v["BACKEND_HOST"] = v["FRONTEND_HOST"] = "127.0.0.1"
    else:
        v["BACKEND_PUBLIC_URL"] = ""
        v["BACKEND_HOST"] = v["FRONTEND_HOST"] = "0.0.0.0" if servidor else "127.0.0.1"

    if servidor:
        ui.seccion("Instalacion")
        v["DEPLOY_DIR"] = ui.preguntar("Carpeta de instalacion", v["DEPLOY_DIR"])
        if not env.ES_WINDOWS:
            v["SERVICE_USER"] = ui.preguntar("Usuario de los servicios (se crea si no existe)", v["SERVICE_USER"] or "arquis")

    env.escribir({k: val for k, val in v.items() if k not in env.OBSOLETAS})
    ui.ok(f"Creado {rel(ENV_FILE)}" + ("" if env.ES_WINDOWS else " (permisos 600)"))
    ui.tabla([["Visor", env.url_publica("web", v)], ["API publica (app movil)", env.url_publica("api", v)],
              ["Frontend → backend", env.url_interna_api(v)]], ["", "URL"])
    if not ENV_EXAMPLE.exists():
        generar_ejemplo()
    validar()


def _generar_clave() -> str:
    alfabeto = string.ascii_letters + string.digits
    clave = "Aq9!" + "".join(secrets.choice(alfabeto) for _ in range(20))
    ui.info("Se genero una contrasena segura; queda guardada solo en el .env.")
    return clave


def editar() -> None:
    """Edita las variables de un grupo (Enter conserva el valor)."""
    valores = env.cargar()
    grupos = list(dict.fromkeys(v.grupo for v in env.ESQUEMA))
    g = ui.elegir("Grupo", grupos)
    for v in (x for x in env.ESQUEMA if x.grupo == grupos[g]):
        ayuda = f"{v.nombre} — {v.descripcion}" + (f" ({'/'.join(v.opciones)})" if v.opciones else "")
        actual = valores.get(v.nombre, "")
        nuevo = ui.preguntar(ayuda, None if v.secreto else actual, secreto=v.secreto) or actual
        if v.opciones and nuevo not in v.opciones:
            ui.warn(f"Valor no valido para {v.nombre}; se conserva '{actual}'.")
            nuevo = actual
        valores[v.nombre] = nuevo
    _respaldar()
    env.escribir(_solo_archivo(valores))
    ui.ok("Guardado.")


def establecer() -> None:
    """Cambia una variable."""
    nombre = ui.preguntar("Variable").strip().upper()
    if not nombre:
        return
    if nombre not in env.POR_NOMBRE:
        ui.warn(f"{nombre} no la usa el proyecto; se guardara en 'Otras'.")
    valores = env.cargar()
    v = env.POR_NOMBRE.get(nombre)
    valores[nombre] = ui.preguntar("Valor", None if v and v.secreto else valores.get(nombre, ""), secreto=bool(v and v.secreto))
    _respaldar()
    env.escribir(_solo_archivo(valores))
    ui.ok(f"{nombre} actualizado.")


def _solo_archivo(valores: dict[str, str]) -> dict[str, str]:
    """Evita volcar al .env valores que solo venian del entorno del proceso."""
    archivo = env.leer()
    return {k: (archivo.get(k, env.POR_NOMBRE[k].defecto if k in env.POR_NOMBRE else val)
                if k in os.environ and valores.get(k) == os.environ[k] else val)
            for k, val in valores.items()}


def revisar(cfg: dict[str, str] | None = None) -> tuple[list[str], list[str]]:
    """Errores y avisos del .env (sin imprimir nada)."""
    cfg = cfg or env.cargar()
    errores, avisos = [], []
    if not ENV_FILE.exists():
        avisos.append(f"No existe {rel(ENV_FILE)}; se usan valores por defecto")
    for v in env.ESQUEMA:
        if v.opciones and cfg[v.nombre] not in v.opciones:
            errores.append(f"{v.nombre}='{cfg[v.nombre]}' no es valido {v.opciones}")
    for p in ("BACKEND_PORT", "FRONTEND_PORT", "NGINX_PORT", "DEPLOY_KEEP_RELEASES",
              "VIEWER_DEFAULT_FEATURE_LIMIT", "VIEWER_MAX_FEATURE_LIMIT"):
        if not cfg[p].isdigit():
            errores.append(f"{p} debe ser un numero")
    if cfg["BACKEND_PORT"] == cfg["FRONTEND_PORT"]:
        errores.append("BACKEND_PORT y FRONTEND_PORT deben ser distintos")
    if cfg["DB_AUTH"] == "sql" and not (cfg["DB_USER"] and cfg["DB_PASSWORD"]):
        errores.append("DB_AUTH=sql requiere DB_USER y DB_PASSWORD")
    if cfg["DB_AUTH"] == "windows" and not env.ES_WINDOWS:
        errores.append("DB_AUTH=windows no esta disponible en Linux: use DB_AUTH=sql")
    if cfg["DB_SERVER"].lower().startswith("(localdb)") and not env.ES_WINDOWS:
        errores.append("LocalDB solo existe en Windows: use el host del SQL Server (p. ej. localhost)")
    if cfg["BACKEND_PUBLIC_URL"] and not re.match(r"^https?://", cfg["BACKEND_PUBLIC_URL"]):
        errores.append("BACKEND_PUBLIC_URL debe empezar con http:// o https:// (o quedar vacia = automatica)")
    if env.es_verdad("NGINX_ENABLED", cfg):
        from cli.modules.services.nginx.nginx import es_dominio
        for clave in ("WEB_DOMAIN", "API_DOMAIN"):
            valor = cfg.get(clave, "")
            if valor and valor != "_" and not es_dominio(valor):
                errores.append(f"{clave}='{valor}' no es un dominio valido")
        if cfg["API_DOMAIN"] and cfg["WEB_DOMAIN"] in ("", "_"):
            errores.append("API_DOMAIN requiere tambien WEB_DOMAIN (el dominio del visor)")
        if bool(cfg["NGINX_SSL_CERT"]) != bool(cfg["NGINX_SSL_KEY"]):
            errores.append("NGINX_SSL_CERT y NGINX_SSL_KEY van juntos")
        if cfg["HTTPS"] == "manual" and not cfg["NGINX_SSL_CERT"]:
            errores.append("HTTPS=manual requiere NGINX_SSL_CERT y NGINX_SSL_KEY")
        if cfg["HTTPS"] == "letsencrypt":
            if cfg["WEB_DOMAIN"] in ("", "_"):
                errores.append("Let's Encrypt necesita un dominio real en WEB_DOMAIN (no funciona con IP)")
            elif not cfg["NGINX_SSL_CERT"]:
                avisos.append("Certificado aun no emitido: arquis services nginx https")
        if cfg["HTTPS"] == "none" and cfg["ARQUIS_ENV"] == "Production" and cfg["WEB_DOMAIN"] not in ("", "_"):
            avisos.append("Sin HTTPS: las contrasenas viajan en claro (HTTPS=letsencrypt)")
    if cfg["ARQUIS_ENV"] == "Production":
        if cfg["DB_SERVER"].lower().startswith("(localdb)"):
            errores.append("Produccion con LocalDB: LocalDB solo vive mientras el usuario tiene sesion")
        if cfg["DB_USER"].lower() == "sa":
            avisos.append("Produccion con 'sa': cree un login propio (bd servidor login)")
        if "localhost" in env.url_publica("api", cfg) and not env.ES_WINDOWS:
            avisos.append("La URL publica de la API apunta a localhost: la app movil no llegara")
    obsoletas = sorted(set(env.leer()) & env.OBSOLETAS)
    if obsoletas:
        avisos.append("Variables que el proyecto no usa (se eliminan con 'entorno limpiar'): " + ", ".join(obsoletas))
    return errores, avisos


def validar(probar_bd: bool = True) -> bool:
    """Comprueba valores, coherencia y (opcional) la conexion a SQL Server."""
    errores, avisos = revisar()
    for e in errores:
        ui.error(e)
    for a in avisos:
        ui.warn(a)
    if errores:
        return False
    ui.ok("Valores correctos.")
    if probar_bd:
        from cli.core import sql
        try:
            bien, detalle = sql.probar()
        except ui.Fallo as e:
            bien, detalle = False, str(e)
        if bien:
            ui.ok(f"Conexion a SQL Server: {detalle}")
        else:
            ultima = detalle.strip().splitlines()[-1][:200] if detalle.strip() else "sin detalle"
            ui.warn(f"No se pudo conectar a SQL Server: {ultima}")
    return True


def limpiar() -> None:
    """Quita del .env variables que el proyecto no usa y avanzadas iguales al defecto."""
    actuales = env.leer()
    quitar = sorted(set(actuales) & env.OBSOLETAS)
    _respaldar()
    env.escribir({k: v for k, v in actuales.items() if k not in env.OBSOLETAS})
    ui.ok("Eliminadas: " + (", ".join(quitar) if quitar else "ninguna obsoleta") + ". Avanzadas por defecto compactadas.")


def generar_ejemplo() -> None:
    """Regenera .env.example (sin secretos) para git."""
    env.escribir({}, ENV_EXAMPLE, plantilla=True)
    ui.ok(f"Generado {rel(ENV_EXAMPLE)}")


def _respaldar() -> None:
    if ENV_FILE.exists():
        destino = SETUP_DIR / "env-backups"
        asegurar(destino)
        shutil.copy2(ENV_FILE, destino / f".env.{datetime.now():%Y%m%d-%H%M%S}")


def restaurar_respaldo() -> None:
    """Restaura una copia anterior del .env."""
    carpeta = SETUP_DIR / "env-backups"
    copias = sorted(carpeta.glob(".env.*"), reverse=True) if carpeta.exists() else []
    if not copias:
        ui.warn("No hay respaldos del .env.")
        return
    i = ui.elegir("Respaldo a restaurar", [c.name for c in copias[:15]])
    _respaldar()
    shutil.copy2(copias[i], ENV_FILE)
    ui.ok(f"Restaurado {copias[i].name}")
