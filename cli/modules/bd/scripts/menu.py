from cli.core.menu import Menu

from . import sql_scripts

MENU = Menu("scripts", "Scripts SQL (02_BaseDatos)", "Scripts manuales con control de ejecucion", orden=30, requiere=("base",))
MENU.agregar("listar", "Listar y ver estado", sql_scripts.listar)
MENU.agregar("pendientes", "Ejecutar pendientes", sql_scripts.pendientes)
MENU.agregar("uno", "Ejecutar un script", sql_scripts.uno)
MENU.agregar("archivo", "Ejecutar archivo .sql externo", sql_scripts.archivo_libre)
MENU.agregar("marcar", "Marcar como aplicado", sql_scripts.marcar)
MENU.agregar("nuevo", "Crear script nuevo", sql_scripts.nuevo, requiere=())
MENU.agregar("verificar", "Verificacion de estados (tests)", sql_scripts.verificacion_estados)
