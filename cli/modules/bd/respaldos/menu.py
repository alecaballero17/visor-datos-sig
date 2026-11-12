from cli.core.menu import Menu

from . import respaldo

MENU = Menu("respaldos", "Respaldos", "BACKUP / RESTORE de la base", orden=40, requiere=("base",))
MENU.agregar("crear", "Crear respaldo", respaldo.respaldar)
MENU.agregar("listar", "Listar respaldos", respaldo.listar, requiere=("sql",))
MENU.agregar("restaurar", "Restaurar respaldo", respaldo.restaurar, requiere=("sql",))
MENU.agregar("purgar", "Purgar respaldos antiguos", respaldo.purgar, requiere=("sql",))