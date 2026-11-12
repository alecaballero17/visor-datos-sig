from cli.core.menu import Menu

from . import consultas

MENU = Menu("consultas", "Consultas y datos", "Consola SQL, conteos y exportacion", orden=50, requiere=("base",))
MENU.agregar("conteos", "Filas por tabla", consultas.conteos)
MENU.agregar("tamanos", "Espacio por tabla", consultas.tamanos)
MENU.agregar("consola", "Consola SQL interactiva", consultas.consola)
MENU.agregar("csv", "Exportar tabla/consulta a CSV", consultas.exportar_csv)
MENU.agregar("accesos", "Bitacora de accesos", consultas.bitacora_accesos)
MENU.agregar("bitacora-migr", "Bitacora del migrador", consultas.bitacora_migraciones)
MENU.agregar("sesiones", "Sesiones activas", consultas.sesiones)
