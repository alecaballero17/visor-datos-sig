from cli.core.menu import Menu

from . import admin

MENU = Menu("bd", "Base de datos", "SQL Server: migraciones, scripts, respaldos, usuarios y capas SIG", orden=30)
MENU.agregar("estado", "Estado general de la base", admin.estado)
MENU.agregar("inicializar", "Inicializar TODO", admin.inicializar, "crear + migrar + importar capas")
MENU.agregar("crear", "Crear base vacia", admin.crear)
MENU.agregar("eliminar", "Eliminar base", admin.eliminar)
MENU.agregar("recrear", "Recrear base desde cero", admin.recrear, "desarrollo")
# Submenus: servidor/, migraciones/, scripts/, respaldos/, consultas/, usuarios/, capas/
MENU.descubrir(__package__)
