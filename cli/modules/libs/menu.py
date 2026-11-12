from cli.core.menu import Menu

from . import modelos, paquetes, web

MENU = Menu("libs", "Librerias", "Librerias web offline, modelo IA y paquetes desactualizados", orden=25)
MENU.agregar("estado", "Estado de librerias web", web.estado)
MENU.agregar("descargar", "Descargar librerias web", web.descargar, "→ wwwroot/lib")
MENU.agregar("verificar", "Verificar hashes", web.verificar)
MENU.agregar("modo-local", "Usar librerias locales (offline)", web.modo_local)
MENU.agregar("modo-cdn", "Volver a CDN", web.modo_cdn)
MENU.agregar("modelo", "Descargar modelo IA (GGUF)", modelos.descargar)
MENU.agregar("modelo-movil", "Enviar modelo al telefono", modelos.enviar_dispositivo, "adb, build debug")
MENU.agregar("modelo-borrar", "Eliminar modelos descargados", modelos.eliminar)
MENU.agregar("obsoletos", "Paquetes desactualizados (todos)", paquetes.todos)
MENU.agregar("nuget", "NuGet desactualizados", paquetes.nuget)
MENU.agregar("pub", "pub desactualizados", paquetes.pub)
MENU.agregar("pip", "pip desactualizados", paquetes.pip)
