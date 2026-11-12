from cli.core import shell
from cli.core.menu import Menu

from . import conexion, motor

MENU = Menu("servidor", "Servidor y conexion", "Conexion, SQL Server (Docker / mssql-server) y logins", orden=10)
MENU.agregar("probar", "Probar conexion", conexion.probar)
MENU.agregar("instalar", "Instalar / configurar SQL Server", motor.instalar, "Docker, nativo o remoto")
MENU.agregar("info", "Informacion del servidor", conexion.info_servidor)
MENU.agregar("bases", "Listar bases de datos", conexion.listar_bases)
MENU.agregar("login", "Crear login SQL para la app", conexion.crear_login_app, "no usar 'sa' en produccion")
MENU.agregar("elegir", "Cambiar servidor de la conexion", conexion.elegir_instancia, "guarda en .env")
MENU.agregar("docker-crear", "SQL Server en Docker: crear", motor.docker_crear, "volumen persistente")
MENU.agregar("docker-iniciar", "SQL Server en Docker: iniciar", motor.docker_iniciar)
MENU.agregar("docker-detener", "SQL Server en Docker: detener", motor.docker_detener)
MENU.agregar("docker-estado", "SQL Server en Docker: estado", motor.docker_estado)
MENU.agregar("docker-logs", "SQL Server en Docker: logs en vivo", motor.docker_logs)
MENU.agregar("docker-eliminar", "SQL Server en Docker: eliminar", motor.docker_eliminar)
if not shell.ES_WINDOWS:
    MENU.agregar("mssql-instalar", "mssql-server: instalar nativo", motor.nativo_instalar)
    MENU.agregar("mssql-estado", "mssql-server: estado", motor.servicio_estado)
    MENU.agregar("mssql-reiniciar", "mssql-server: reiniciar", motor.servicio_reiniciar)
    MENU.agregar("mssql-logs", "mssql-server: logs en vivo", motor.servicio_logs)
else:
    from . import localdb
    MENU.agregar("localdb-info", "LocalDB: instancias", localdb.info)
    MENU.agregar("localdb-iniciar", "LocalDB: iniciar", localdb.iniciar)
    MENU.agregar("localdb-detener", "LocalDB: detener", localdb.detener)
    MENU.agregar("localdb-crear", "LocalDB: crear instancia", localdb.crear)
    MENU.agregar("localdb-eliminar", "LocalDB: eliminar instancia", localdb.eliminar)
