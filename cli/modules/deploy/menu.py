from cli.core.menu import Menu

from . import paquete, pipeline, releases

MENU = Menu("deploy", "Despliegue", "Despliegue completo con versiones y rollback automatico", orden=50)
MENU.agregar("plan", "Ver plan de despliegue", pipeline.plan, "que se hara con el .env actual")
MENU.agregar("completo", "DESPLIEGUE COMPLETO", pipeline.completo, "pruebas → publicar → BD → servicios → salud", requiere=("root",))
MENU.agregar("actualizar", "git pull + despliegue completo", pipeline.actualizar, requiere=("root",))
MENU.agregar("publicar", "Solo publicar version nueva", pipeline.solo_publicar, requiere=("root", "dotnet"))
MENU.agregar("activar", "Activar una version publicada", pipeline.activar, requiere=("root",))
MENU.agregar("rollback", "Volver a una version anterior", releases.rollback, requiere=("root",))
MENU.agregar("versiones", "Listar versiones instaladas", releases.listar)
MENU.agregar("historial", "Historial de despliegues", releases.historial)
MENU.agregar("purgar", "Borrar versiones antiguas", releases.purgar, requiere=("root",))
MENU.agregar("paquete", "Crear paquete portable (.zip)", paquete.crear, "servidor sin SDK", requiere=("dotnet", "ef"))
MENU.agregar("instalar-paquete", "Instalar desde paquete", paquete.instalar, "ejecutar en el servidor", requiere=("root", "sql"))