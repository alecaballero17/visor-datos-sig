from cli.core.menu import Menu

from . import control

MENU = Menu("services", "Servicios", "Compilar, instalar como servicio, nginx, iniciar/detener y logs en vivo", orden=40)
MENU.agregar("estado", "Estado de todos los servicios", control.estado_general)
MENU.agregar("iniciar", "Iniciar todo", control.iniciar_todo, requiere=("root",))
MENU.agregar("detener", "Detener todo", control.detener_todo, requiere=("root",))
MENU.agregar("reiniciar", "Reiniciar todo", control.reiniciar_todo, requiere=("root",))
MENU.agregar("logs", "Logs de todo en tiempo real", control.logs_todos, "Ctrl+C para salir")
MENU.agregar("errores", "Buscar errores en todos los logs", control.errores_todos)
MENU.agregar("instalar", "Instalar todos los servicios", control.instalar_todo, "administrador", requiere=("root",))
MENU.agregar("desinstalar", "Desinstalar todos los servicios", control.desinstalar_todo, requiere=("root",))
# Submenus: build/, dev/, backend/, frontend/, nginx/
MENU.descubrir(__package__)
