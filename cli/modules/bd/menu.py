from cli.core.menu import Menu

from . import admin

MENU = Menu("bd", "Base de datos", "SQL Server: migraciones, scripts, respaldos, usuarios y capas SIG", orden=30)
MENU.agregar("estado", "Estado general de la base", admin.estado, requiere=("sql",))
MENU.agregar("inicializar", "Inicializar TODO", admin.inicializar, "crear + migrar + importar capas", requiere=("sql", "ef"))
MENU.agregar("crear", "Crear base vacia", admin.crear, requiere=("sql",))
MENU.agregar("eliminar", "Eliminar base", admin.eliminar, requiere=("base",))
MENU.agregar("recrear", "Recrear base desde cero", admin.recrear, "desarrollo", requiere=("sql", "ef"))
# Submenus: servidor/, migraciones/, scripts/, respaldos/, consultas/, usuarios/, capas/
MENU.descubrir(__package__)
