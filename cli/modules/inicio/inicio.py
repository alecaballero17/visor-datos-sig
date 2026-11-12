"""Flujos guiados de un solo comando."""
from __future__ import annotations

from cli.core import env, ui

from . import preparacion


def servidor() -> None:
    """Servidor Linux desde cero: paquetes → .env → dependencias → SQL Server → base →
    migraciones → capas → nginx + HTTPS → servicios.  Ejecutar: sudo ./arquis.sh inicio servidor
    """
    if env.get("ARQUIS_ENV") != "Production":
        ui.warn("El .env esta en modo desarrollo: el asistente (entorno crear) permite elegir 'Servidor'.")
    preparacion.preparar(servicios=True)
    from ..services.nginx import nginx
    if env.es_verdad("NGINX_ENABLED"):
        ui.seccion("URLs")
        nginx.resumen_urls()


def desarrollo() -> None:
    """Equipo de desarrollo: prepara lo que falte y levanta backend + frontend."""
    if not preparacion.preparar(servicios=False):
        ui.warn("Quedaron pasos pendientes; se intenta levantar igualmente.")
    from ..entorno import sincronizar
    from ..services.dev import dev
    sincronizar.movil()
    dev.iniciar()
    ui.ok("Listo. Usuario inicial: admin / Admin123! (cambielo: arquis bd usuarios clave)")


def dominios() -> None:
    """Dominio del visor, subdominio de la API y HTTPS."""
    from ..services.nginx import nginx
    nginx.dominios()
