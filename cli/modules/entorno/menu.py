from cli.core.menu import Menu

from . import env_file, sincronizar

MENU = Menu("entorno", "Configuracion (.env)",
            "Solo lo que usan backend y frontend: conexion SQL, puertos, URL publica y servidor", orden=10)
MENU.agregar("crear", "Asistente: crear .env", env_file.crear, "servidor Linux o desarrollo")
MENU.agregar("ver", "Ver configuracion", env_file.mostrar)
MENU.agregar("ver-todo", "Ver todo (incluye avanzadas)", env_file.mostrar_todo)
MENU.agregar("editar", "Editar un grupo", env_file.editar)
MENU.agregar("set", "Cambiar una variable", env_file.establecer)
MENU.agregar("validar", "Validar (y probar conexion SQL)", env_file.validar)
MENU.agregar("limpiar", "Quitar variables que no se usan", env_file.limpiar)
MENU.agregar("dotnet", "Ver variables que recibe .NET", sincronizar.mostrar_dotnet)
MENU.agregar("exportar", "Exportar a .setup/env.sh y env.ps1", sincronizar.exportar_shell)
MENU.agregar("movil", "Generar Movil/.env", sincronizar.movil, "URL publica de la API")
MENU.agregar("ejemplo", "Regenerar .env.example", env_file.generar_ejemplo)
MENU.agregar("restaurar", "Restaurar respaldo del .env", env_file.restaurar_respaldo)
