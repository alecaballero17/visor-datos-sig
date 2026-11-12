from cli.core.menu import Menu

from . import dev

MENU = Menu("dev", "Modo desarrollo", "Ejecutar desde el codigo fuente (sin instalar servicios)", orden=20)
MENU.agregar("iniciar", "Iniciar backend + frontend", dev.iniciar)
MENU.agregar("detener", "Detener", dev.detener)
MENU.agregar("reiniciar", "Reiniciar", dev.reiniciar)
MENU.agregar("estado", "Estado", dev.estado)
MENU.agregar("logs", "Logs en tiempo real", dev.logs_vivo)
MENU.agregar("watch", "dotnet watch (hot reload)", dev.watch, "ventanas nuevas")
MENU.agregar("abrir", "Abrir el visor en el navegador", dev.abrir_navegador)
