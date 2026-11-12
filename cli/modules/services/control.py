"""Acciones sobre servicios instalados: instalar, iniciar, detener, detalles, logs."""
from __future__ import annotations

import time
from datetime import datetime

from cli.core import env, ui
from cli.core.menu import Menu

from . import definiciones as d
from . import logs
from .gestores import gestor


def _archivos(servicios: list[d.Servicio]) -> dict:
    archivos = {}
    for s in servicios:
        archivos[f"{s.clave}"] = s.log_out
        archivos[f"{s.clave}:err"] = s.log_err
        if s.clave == "nginx":
            archivos["nginx:access"] = d.dir_logs() / "nginx.access.log"
            archivos["nginx:error"] = d.dir_logs() / "nginx.error.log"
    return archivos


def esperar_salud(s: d.Servicio, segundos: int = 60) -> bool:
    for _ in range(segundos):
        bien, _ = d.salud(s)
        if bien:
            return True
        time.sleep(1)
    return False


# -- acciones por servicio ------------------------------------------------------
def instalar(s: d.Servicio) -> None:
    if not s.instalado_en_disco():
        if s.clave == "nginx":
            from .nginx import nginx as ng
            ng.instalar_binarios()
            s = d.obtener("nginx")
        else:
            ui.warn(f"Todavia no hay una version publicada ({s.carpeta}).")
            ui.info("Los servicios ejecutan la version publicada; el despliegue completo la publica,")
            ui.info("migra la base, configura nginx e instala y arranca los servicios.")
            if ui.confirmar("¿Ejecutar el despliegue completo ahora?", True):
                from ..deploy import pipeline
                pipeline.completo()
            return
    if s.clave == "nginx":
        from .nginx import nginx as ng
        ng.escribir_config()
    dependencias = [d.backend().nombre] if s.clave == "frontend" else None
    gestor(s).instalar(s, dependencias)


def desinstalar(s: d.Servicio) -> None:
    if ui.confirmar(f"¿Eliminar el servicio {s.nombre}?"):
        gestor(s).desinstalar(s)


def iniciar(s: d.Servicio, esperar: bool = True) -> bool:
    g = gestor(s)
    if not g.existe(s):
        raise ui.Fallo(f"{s.nombre} no esta instalado (arquis services {s.clave} instalar).")
    g.iniciar(s)
    if not esperar:
        return True
    ui.info(f"Esperando respuesta en {s.url} ...")
    if esperar_salud(s):
        ui.ok(f"{s.titulo} responde.")
        return True
    ui.error(f"{s.titulo} no responde. Ultimas lineas de error:")
    logs.mostrar_ultimas({s.clave: s.log_err, f"{s.clave}:out": s.log_out}, 15)
    return False


def detener(s: d.Servicio) -> None:
    gestor(s).detener(s)


def reiniciar(s: d.Servicio) -> bool:
    gestor(s).detener(s)
    time.sleep(1)
    return iniciar(s)


def actualizar_entorno(s: d.Servicio) -> None:
    """Reaplica las variables del .env al servicio y lo reinicia."""
    if s.clave == "nginx":
        from .nginx import nginx as ng
        ng.escribir_config()
        ng.recargar()
        return
    gestor(s).actualizar_entorno(s)
    if ui.confirmar("¿Reiniciar para aplicar los cambios?", True):
        reiniciar(s)


def detalles(s: d.Servicio) -> None:
    g = gestor(s)
    e = g.estado(s)
    bien, detalle_salud = d.salud(s)
    filas = [
        ["Servicio", s.nombre],
        ["Gestor", g.nombre],
        ["Estado", e.get("estado", "?")],
        ["Inicio", e.get("inicio", "")],
        ["PID", e.get("pid", "")],
        ["Proceso", e.get("proceso", "")],
        ["Memoria", f"{e['memoria_mb']} MB" if e.get("memoria_mb") else ""],
        ["En marcha desde", e.get("desde", "")],
        ["Puerto", f"{s.puerto} ({'abierto' if d.puerto_abierto(s.puerto) else 'cerrado'})"],
        ["Salud", ui.c(f"ok · {detalle_salud}", ui.C.GREEN) if bien else ui.c(detalle_salud, ui.C.RED)],
        ["URL", s.url],
        ["Carpeta", str(s.carpeta)],
        ["Ejecutable", f"{s.ejecutable} {' '.join(s.argumentos)}"],
    ]
    actual = d.dir_actual()
    if s.clave != "nginx" and actual.exists():
        filas.append(["Version activa", actual.resolve().name])
    for etiqueta, ruta in _archivos([s]).items():
        if ruta.exists():
            st = ruta.stat()
            filas.append([f"Log {etiqueta}", f"{ruta}  ({st.st_size / 1024:.0f} KB, "
                                             f"{datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M:%S})"])
    ui.tabla(filas, ["Propiedad", "Valor"])
    if s.entorno:
        ui.seccion("Variables de entorno")
        for k in s.entorno:
            ui.dim(k)
    logs.mostrar_ultimas({s.clave: s.log_out}, 10)


# -- fabrica de menus por servicio ------------------------------------------------
def menu_servicio(clave: str, titulo: str, orden: int) -> Menu:
    m = Menu(clave, titulo, f"Servicio del sistema: {titulo}", orden=orden)
    s = lambda: d.obtener(clave)   # se evalua al ejecutar (lee el .env actual)
    m.agregar("detalles", "Detalles del servicio", lambda: detalles(s()))
    m.agregar("iniciar", "Iniciar", lambda: iniciar(s()))
    m.agregar("detener", "Detener", lambda: detener(s()))
    m.agregar("reiniciar", "Reiniciar", lambda: reiniciar(s()))
    m.agregar("logs", "Logs en tiempo real", lambda: logs.seguir(_archivos([s()])), "Ctrl+C para salir")
    m.agregar("logs-filtro", "Logs en vivo con filtro", lambda: logs.seguir(_archivos([s()]), filtro=ui.preguntar("Regex")))
    m.agregar("ultimas", "Ultimas lineas del log", lambda: logs.mostrar_ultimas(_archivos([s()]), 60))
    m.agregar("errores", "Buscar errores en logs", lambda: logs.buscar_errores(_archivos([s()])))
    m.agregar("limpiar-logs", "Vaciar logs", lambda: logs.limpiar(_archivos([s()])))
    m.agregar("instalar", "Instalar / actualizar servicio", lambda: instalar(s()), "requiere administrador")
    m.agregar("env", "Reaplicar .env y reiniciar", lambda: actualizar_entorno(s()))
    m.agregar("desinstalar", "Desinstalar servicio", lambda: desinstalar(s()))
    return m


# -- acciones globales ---------------------------------------------------------------
def estado_general() -> None:
    """Tabla de estado de todos los servicios."""
    filas = []
    for s in d.todos(incluir_nginx=True):
        e = gestor(s).estado(s)
        bien, det = d.salud(s, timeout=2)
        estado = e.get("estado", "?")
        color = ui.C.GREEN if "running" in estado or "active" in estado else (ui.C.GRAY if "no instalado" in estado else ui.C.YELLOW)
        filas.append([s.clave, s.nombre, ui.c(estado, color), e.get("pid", ""),
                      f"{e['memoria_mb']} MB" if e.get("memoria_mb") else "", s.puerto,
                      ui.c("ok", ui.C.GREEN) if bien else ui.c("—", ui.C.GRAY)])
    ui.tabla(filas, ["Clave", "Servicio", "Estado", "PID", "Memoria", "Puerto", "Salud"])
    if not env.es_verdad("NGINX_ENABLED"):
        ui.dim("nginx deshabilitado (NGINX_ENABLED=false): no participa en iniciar/detener todo.")


def iniciar_todo() -> bool:
    """Inicia backend → frontend → nginx."""
    bien = True
    for s in d.todos():
        bien = iniciar(s) and bien
    return bien


def detener_todo() -> None:
    for s in reversed(d.todos()):
        detener(s)


def reiniciar_todo() -> bool:
    detener_todo()
    time.sleep(1)
    return iniciar_todo()


def instalar_todo() -> None:
    for s in d.todos():
        ui.seccion(s.titulo)
        instalar(s)


def desinstalar_todo() -> None:
    if not ui.confirmar_peligro("Se eliminaran todos los servicios de Arquis.", "SI"):
        return
    for s in reversed(d.todos(incluir_nginx=True)):
        if gestor(s).existe(s):
            gestor(s).desinstalar(s)


def logs_todos() -> None:
    """Sigue los logs de todos los servicios a la vez."""
    logs.seguir(_archivos(d.todos()))


def errores_todos() -> None:
    logs.buscar_errores(_archivos(d.todos()))
