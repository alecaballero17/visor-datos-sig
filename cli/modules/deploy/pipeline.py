"""Despliegue completo en un comando, con rollback automatico.

    arquis deploy completo [--yes]

 1. Verificaciones previas (herramientas, .env, permisos, conexion SQL)
 2. Pruebas automaticas (DEPLOY_RUN_TESTS)
 3. Publicacion de una version nueva en <DEPLOY_DIR>/releases/<id>
 4. Respaldo de la base (DEPLOY_BACKUP_DB)
 5. Base de datos: crear si falta + migraciones EF + capas SIG si estan vacias
 6. nginx (NGINX_ENABLED): binarios + configuracion
 7. Servicios: registrar/actualizar (backend, frontend, nginx)
 8. Activar la version y arrancar; si la salud falla → vuelve a la anterior
 9. Extras: firewall y limpieza de versiones antiguas
"""
from __future__ import annotations

import shutil
import time

from cli.core import env, shell, sql, ui

from ..bd import admin as bd_admin
from ..bd.capas import importar as capas
from ..bd.capas.capas import CAPAS, carpeta
from ..bd.migraciones import ef
from ..bd.respaldos import respaldo
from ..dependencias.requisitos import requerir_obligatorias
from ..entorno.env_file import validar
from ..services import control
from ..services import definiciones as d
from ..services.gestores import gestor, requerir_admin
from ..services.nginx import nginx
from . import releases


def _verificaciones() -> None:
    from ..inicio import preparacion
    # instala/configura lo que falte; nginx y HTTPS se hacen en su propio paso (no bloquean)
    if not preparacion.preparar(servicios=False, omitir=("nginx", "https")):
        raise ui.Fallo("Hay requisitos pendientes (arquis inicio revisar).")
    requerir_obligatorias()
    if not validar():
        raise ui.Fallo("Corrija el .env (arquis entorno editar) antes de desplegar.")
    if gestor().nombre in ("nssm", "systemd"):
        requerir_admin()
    shell.requerir_escritura(d.dir_instalacion())
    bien, detalle = sql.probar()
    if not bien:
        raise ui.Fallo("Sin conexion a SQL Server:\n" + detalle[-400:])
    ui.ok(f"SQL Server {detalle}")
    if not ef_disponible():
        raise ui.Fallo("Falta dotnet-ef: arquis deps ef")
    ui.info(f"Destino: {d.dir_instalacion()}  ·  Entorno: {env.get('ARQUIS_ENV')}")


def ef_disponible() -> bool:
    from ..dependencias.restaurar import ef_disponible as f
    return f()


def _pruebas() -> None:
    from ..test import pruebas
    if not pruebas.rapidas():
        raise ui.Fallo("Las pruebas fallaron; despliegue cancelado (DEPLOY_RUN_TESTS=false para omitirlas).")


def _base_de_datos() -> str | None:
    cfg = env.cargar()
    copia = None
    if sql.existe_base() and env.es_verdad("DEPLOY_BACKUP_DB", cfg):
        copia = respaldo.respaldar("pre-deploy")
    bd_admin.crear()
    ef.actualizar()
    if any((carpeta() / f"{c.archivo}.shp").exists() for c in CAPAS):
        capas.importar(reemplazar=False)
    return str(copia) if copia else None


def _nginx() -> None:
    if not env.es_verdad("NGINX_ENABLED"):
        ui.info("nginx deshabilitado; se omite.")
        return
    nginx.instalar_binarios()
    cfg = env.cargar()
    nginx.escribir_config()          # primero HTTP: el sitio queda accesible aunque HTTPS falle
    if cfg.get("HTTPS") in ("letsencrypt", "cloudflare") and not cfg.get("NGINX_SSL_CERT"):
        try:
            nginx.https()
        except ui.Fallo as e:
            ui.warn(f"HTTPS no se pudo activar ({str(e).splitlines()[0]}); se continua en HTTP.")
            ui.info("Reintente luego con: arquis services nginx https")


def _servicios() -> None:
    for s in d.todos():
        dependencias = [d.backend().nombre] if s.clave == "frontend" else None
        gestor(s).instalar(s, dependencias)


def completo() -> None:
    """Despliegue completo con rollback automatico."""
    pasos = [
        ("Verificaciones previas", _verificaciones),
        ("Pruebas", _pruebas if env.es_verdad("DEPLOY_RUN_TESTS") else None),
        ("Publicar version nueva", None),
        ("Base de datos (respaldo + migraciones + capas)", None),
        ("nginx", _nginx),
        ("Registrar servicios", None),
        ("Activar version y arrancar", None),
        ("Extras y limpieza", None),
    ]
    total = len(pasos)
    inicio = time.time()
    anterior = releases.activa()
    nueva = None
    copia_bd = None

    ui.paso(1, total, pasos[0][0])
    _verificaciones()

    ui.paso(2, total, pasos[1][0])
    if pasos[1][1]:
        _pruebas()
    else:
        ui.info("Omitidas (DEPLOY_RUN_TESTS=false).")

    ui.paso(3, total, pasos[2][0])
    destino = releases.crear()
    nueva = destino.name

    try:
        ui.paso(4, total, pasos[3][0])
        copia_bd = _base_de_datos()

        ui.paso(5, total, pasos[4][0])
        _nginx()

        ui.paso(6, total, pasos[5][0])
        control.detener_todo()
        releases.activar_ruta(destino)
        _servicios()

        ui.paso(7, total, pasos[6][0])
        if not control.iniciar_todo():
            raise ui.Fallo("La version nueva no paso la comprobacion de salud.")
    except (Exception, KeyboardInterrupt) as e:  # noqa: BLE001
        ui.error(f"Despliegue fallido: {e}")
        if anterior and anterior != nueva:
            ui.warn(f"Rollback automatico a {anterior}...")
            try:
                releases.cambiar_a(anterior)
                releases.registrar({"accion": "deploy", "version": nueva, "resultado": "rollback", "detalle": str(e)[:200]})
            except Exception as e2:  # noqa: BLE001
                ui.error(f"El rollback tambien fallo: {e2}")
                releases.registrar({"accion": "deploy", "version": nueva, "resultado": "fallo", "detalle": str(e2)[:200]})
        else:
            releases.registrar({"accion": "deploy", "version": nueva, "resultado": "fallo", "detalle": str(e)[:200]})
        if copia_bd:
            ui.info(f"Respaldo de la base previo al despliegue: {copia_bd}")
        raise ui.Fallo("Despliegue cancelado.") from e

    ui.paso(8, total, pasos[7][0])
    if env.es_verdad("DEPLOY_OPEN_FIREWALL"):
        _firewall()
    releases.purgar()
    releases.registrar({"accion": "deploy", "version": nueva, "resultado": "ok",
                        "detalle": f"{time.time() - inicio:.0f}s"})
    _resumen(nueva, time.time() - inicio)


def _firewall() -> None:
    if env.es_verdad("NGINX_ENABLED"):
        nginx.firewall()
        return
    for p in (env.get("BACKEND_PORT"), env.get("FRONTEND_PORT")):
        if shell.ES_WINDOWS:
            shell.run(["netsh", "advfirewall", "firewall", "add", "rule", f"name=Arquis {p}", "dir=in",
                       "action=allow", "protocol=TCP", f"localport={p}"], check=False)
        elif shell.which("ufw"):
            shell.run(["ufw", "allow", f"{p}/tcp"], check=False)



def _resumen(version: str, segundos: float) -> None:
    cfg = env.cargar()
    ui.titulo("Despliegue completado")
    ui.tabla([
        ["Version", version],
        ["Duracion", f"{segundos:.0f} s"],
        ["Visor", env.url_publica("web", cfg)],
        ["API (app movil)", env.url_api_movil(cfg, android=False)],
        ["Salud", env.url_publica("api", cfg) + "/health"],
        ["Instalacion", str(d.dir_instalacion())],
        ["Logs en vivo", "arquis services logs"],
        ["Volver atras", "arquis deploy rollback"],
    ])


def actualizar() -> None:
    """git pull + despliegue completo."""
    if not shell.which("git"):
        raise ui.Fallo("git no esta instalado.")
    from cli.core.paths import ROOT
    if shell.salida(["git", "status", "--porcelain"], cwd=ROOT):
        if not ui.confirmar("Hay cambios locales sin commit. ¿Continuar igualmente?"):
            return
    shell.run(["git", "pull", "--ff-only"], cwd=ROOT)
    completo()


def solo_publicar() -> None:
    """Publica una version nueva sin activarla."""
    releases.crear()


def activar() -> None:
    """Activa una version ya publicada (cambia current y reinicia)."""
    ids = releases.listar_ids()
    if not ids:
        raise ui.Fallo("No hay versiones publicadas.")
    i = ui.elegir("Version a activar", ids, 0)
    bien = releases.cambiar_a(ids[i])
    releases.registrar({"accion": "activar", "version": ids[i], "resultado": "ok" if bien else "fallo"})


def plan() -> None:
    """Muestra que hara el despliegue con la configuracion actual (sin ejecutar nada)."""
    cfg = env.cargar()
    s = lambda k: ui.c("si", ui.C.GREEN) if env.es_verdad(k, cfg) else ui.c("no", ui.C.GRAY)
    ui.tabla([
        ["Destino", cfg["DEPLOY_DIR"]],
        ["Entorno", cfg["ARQUIS_ENV"]],
        ["Base", f"{cfg['DB_SERVER']} / {cfg['DB_NAME']} ({cfg['DB_AUTH']})"],
        ["Gestor de servicios", gestor().nombre],
        ["Version activa", releases.activa() or "-"],
        ["Pruebas", s("DEPLOY_RUN_TESTS")],
        ["Respaldo BD", s("DEPLOY_BACKUP_DB")],
        ["nginx", s("NGINX_ENABLED") + (f" (puerto {cfg['NGINX_PORT']})" if env.es_verdad("NGINX_ENABLED", cfg) else "")],
        ["Inicio automatico", s("DEPLOY_AUTOSTART")],
        ["Firewall", s("DEPLOY_OPEN_FIREWALL")],
        ["Versiones a conservar", cfg["DEPLOY_KEEP_RELEASES"]],
        ["Dominio visor", cfg["WEB_DOMAIN"]],
        ["Dominio API", cfg["API_DOMAIN"] or "(el del visor, /api)"],
        ["HTTPS", cfg["HTTPS"]],
        ["URL visor", env.url_publica("web", cfg)],
        ["URL API (movil)", env.url_api_movil(cfg, android=False)],
    ], ["Ajuste", "Valor"])
    ui.dim("Cambie los valores con: arquis entorno editar  (grupo Despliegue / Servicios del sistema)")
