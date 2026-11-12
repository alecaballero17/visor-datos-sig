from cli.core.menu import Menu

from ..deploy import pipeline
from ..services import control
from ..services.dev import dev
from . import inicio, preparacion

MENU = Menu("inicio", "Inicio rapido", "Revisar, preparar y desplegar con un solo comando", orden=1)
MENU.agregar("revisar", "Revisar que falta", preparacion.revisar, "sistema, .env, dependencias, base, nginx...")
MENU.agregar("preparar", "Preparar todo lo que falte", preparacion.preparar, "arregla paso a paso")
MENU.agregar("servidor", "Servidor: preparar y desplegar", inicio.servidor, "sudo ./arquis.sh inicio servidor")
MENU.agregar("desarrollo", "Equipo de desarrollo: preparar y levantar", inicio.desarrollo)
MENU.agregar("dominios", "Dominios y HTTPS (nginx)", inicio.dominios, "visor + subdominio de la API")
MENU.agregar("levantar", "Levantar en modo desarrollo", dev.iniciar)
MENU.agregar("desplegar", "Despliegue completo", pipeline.completo)
MENU.agregar("estado", "Estado de servicios", control.estado_general)
