from cli.core.menu import Menu

from . import instalar, requisitos, restaurar

MENU = Menu("deps", "Dependencias", "Herramientas del sistema (apt/dnf/winget) y paquetes del proyecto", orden=20)
MENU.agregar("doctor", "Diagnostico de requisitos", requisitos.diagnostico)
MENU.agregar("servidor", "Instalar lo necesario para un servidor", instalar.instalar_servidor,
             ".NET 10, sqlcmd, python, nginx, fuentes")
MENU.agregar("instalar", "Instalar todo lo que falte", instalar.instalar_faltantes)
MENU.agregar("una", "Instalar una herramienta", instalar.instalar_una)
MENU.agregar("actualizar", "Actualizar paquetes del sistema", instalar.actualizar_sistema)
MENU.agregar("restaurar", "Restaurar dependencias del proyecto", restaurar.servidor, "NuGet + dotnet-ef + pyshp")
MENU.agregar("restaurar-todo", "Restaurar todo (incluye desarrollo)", restaurar.todo)
MENU.agregar("nuget", "dotnet restore", restaurar.nuget)
MENU.agregar("ef", "dotnet-ef (herramienta local)", restaurar.herramientas_dotnet)
MENU.agregar("venv", "Crear entorno virtual .venv", restaurar.crear_venv)
MENU.agregar("pip-cli", "pip: dependencias de la CLI", restaurar.python_cli)
MENU.agregar("pip-editor", "pip: editor de escritorio", restaurar.python_editor)
MENU.agregar("pub", "flutter pub get", restaurar.flutter_pub)
