from cli.core.menu import Menu

from . import compilar

MENU = Menu("build", "Compilacion", "Compilar y publicar backend, frontend y migrador", orden=10)
MENU.agregar("todo", "Compilar solucion", compilar.solucion)
MENU.agregar("backend", "Compilar backend", compilar.backend)
MENU.agregar("frontend", "Compilar frontend", compilar.frontend)
MENU.agregar("publicar", "Publicar backend + frontend", compilar.publicar_todo, "Release → artifacts/publish")
MENU.agregar("publicar-backend", "Publicar backend", compilar.publicar_backend)
MENU.agregar("publicar-frontend", "Publicar frontend", compilar.publicar_frontend)
MENU.agregar("migrador", "Publicar migrador WPF (.exe)", compilar.migrador)
MENU.agregar("limpiar", "Limpiar bin/obj", compilar.limpiar)
MENU.agregar("formato", "dotnet format", compilar.formato)
MENU.agregar("obsoletos", "Paquetes NuGet desactualizados", compilar.paquetes_obsoletos)
MENU.agregar("vulnerables", "Paquetes NuGet vulnerables", compilar.vulnerabilidades)
