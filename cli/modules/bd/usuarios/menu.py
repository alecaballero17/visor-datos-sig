from cli.core.menu import Menu

from . import usuarios

MENU = Menu("usuarios", "Usuarios y roles", "Cuentas del sistema (PBKDF2 como el backend)", orden=60)
MENU.agregar("listar", "Listar usuarios", usuarios.listar)
MENU.agregar("crear", "Crear usuario", usuarios.crear)
MENU.agregar("clave", "Restablecer contrasena", usuarios.cambiar_clave)
MENU.agregar("activar", "Activar / desactivar", usuarios.activar)
MENU.agregar("rol", "Asignar / quitar rol", usuarios.asignar_rol)
MENU.agregar("roles", "Listar roles", usuarios.roles)
