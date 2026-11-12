"""Conexion al servidor SQL: probar, elegir instancia, listar bases."""
from __future__ import annotations

from cli.core import env, shell, sql, ui


def probar() -> bool:
    """Prueba la conexion con el servidor y la base configurados."""
    cfg = env.cargar()
    ui.info(f"Servidor: {cfg['DB_SERVER']}  ·  Base: {cfg['DB_NAME']}  ·  Auth: {cfg['DB_AUTH']}")
    bien, detalle = sql.probar()
    if not bien:
        ui.error("No se pudo conectar al servidor.")
        ui.dim(detalle[-600:])
        if cfg["DB_SERVER"].lower().startswith("(localdb)"):
            ui.info("Pruebe: arquis bd servidor localdb-iniciar")
        elif not shell.ES_WINDOWS:
            ui.info("¿SQL Server en marcha? arquis bd servidor mssql-estado  |  docker-estado")
        return False
    ui.ok(f"Servidor accesible: SQL Server {detalle}")
    if sql.existe_base():
        ui.ok(f"La base '{cfg['DB_NAME']}' existe.")
    else:
        ui.warn(f"La base '{cfg['DB_NAME']}' no existe (arquis bd crear).")
    return True


def listar_bases() -> None:
    """Bases de datos del servidor con tamano y estado."""
    filas = sql.filas("""
        SELECT d.name, d.state_desc, d.recovery_model_desc,
               CAST(SUM(mf.size) * 8 / 1024.0 AS decimal(10,1)), CONVERT(varchar(16), d.create_date, 120)
        FROM sys.databases d JOIN sys.master_files mf ON mf.database_id = d.database_id
        WHERE d.database_id > 4 GROUP BY d.name, d.state_desc, d.recovery_model_desc, d.create_date
        ORDER BY d.name""", base="master")
    ui.tabla(filas, ["Base", "Estado", "Recuperacion", "MB", "Creada"])


def elegir_instancia() -> None:
    """Detecta servidores SQL locales y guarda el elegido en el .env."""
    import socket
    candidatas = []
    def abierto(puerto: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", puerto), timeout=1):
                return True
        except OSError:
            return False
    if abierto(1433):
        candidatas.append("localhost")
    if shell.ES_WINDOWS:
        loc = shell.which("SqlLocalDB", shell.LOCALDB_EXTRAS)
        if loc:
            candidatas += [rf"(localdb)\{n.strip()}" for n in shell.salida([loc, "info"]).splitlines() if n.strip()]
        texto = shell.salida(["reg", "query", r"HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL"])
        for linea in texto.splitlines():
            partes = linea.split()
            if len(partes) >= 3 and partes[1] == "REG_SZ":
                candidatas.append("." if partes[0] == "MSSQLSERVER" else rf".\{partes[0]}")
    candidatas = list(dict.fromkeys(candidatas)) + ["Otro servidor (escribir host[,puerto])"]
    i = ui.elegir("Servidor SQL Server", candidatas)
    servidor = candidatas[i] if i < len(candidatas) - 1 else ui.preguntar("Servidor (host[,puerto])")
    if not servidor:
        return
    valores = env.cargar()
    valores["DB_SERVER"] = servidor
    windows_auth = shell.ES_WINDOWS and (servidor.lower().startswith("(localdb)")
                                         or ui.confirmar("¿Autenticacion de Windows?", False))
    if windows_auth:
        valores.update(DB_AUTH="windows", DB_USER="", DB_PASSWORD="")
    else:
        valores["DB_AUTH"] = "sql"
        valores["DB_USER"] = ui.preguntar("Usuario", valores.get("DB_USER") or "sa")
        valores["DB_PASSWORD"] = ui.preguntar("Contrasena (Enter = conservar)", secreto=True) or valores.get("DB_PASSWORD", "")
    env.escribir(valores)
    ui.ok(f"DB_SERVER={servidor} guardado en .env")
    probar()


def info_servidor() -> None:
    """Version, edicion, colacion y rutas de datos del servidor."""
    filas = sql.filas("""
        SELECT 'Version', CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(100))
        UNION ALL SELECT 'Edicion', CAST(SERVERPROPERTY('Edition') AS nvarchar(100))
        UNION ALL SELECT 'Instancia', CAST(@@SERVERNAME AS nvarchar(100))
        UNION ALL SELECT 'Colacion', CAST(SERVERPROPERTY('Collation') AS nvarchar(100))
        UNION ALL SELECT 'Datos', CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS nvarchar(260))
        UNION ALL SELECT 'Respaldos', CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS nvarchar(260))
        UNION ALL SELECT 'Usuario', SUSER_SNAME()""", base="master")
    ui.tabla(filas, ["Propiedad", "Valor"])


def crear_login_app() -> None:
    """Crea un login SQL con permisos minimos (db_datareader/writer/ddladmin) para produccion."""
    cfg = env.cargar()
    login = ui.preguntar("Login a crear", "arquis_app")
    clave = ui.preguntar("Contrasena (min. 8, mayus/minus/numero)", secreto=True)
    if len(clave) < 8:
        raise ui.Fallo("Contrasena demasiado corta.")
    base = cfg["DB_NAME"]
    sql.ejecutar(f"""
        IF SUSER_ID(N'{sql.lit(login)}') IS NULL
            CREATE LOGIN {sql.ident(login)} WITH PASSWORD = N'{sql.lit(clave)}', CHECK_POLICY = ON;
        ELSE ALTER LOGIN {sql.ident(login)} WITH PASSWORD = N'{sql.lit(clave)}';""", base="master", mostrar=False)
    sql.ejecutar(f"""
        IF USER_ID(N'{sql.lit(login)}') IS NULL CREATE USER {sql.ident(login)} FOR LOGIN {sql.ident(login)};
        ALTER ROLE db_datareader ADD MEMBER {sql.ident(login)};
        ALTER ROLE db_datawriter ADD MEMBER {sql.ident(login)};
        ALTER ROLE db_ddladmin ADD MEMBER {sql.ident(login)};
        GRANT EXECUTE TO {sql.ident(login)};""", base=base, mostrar=False)
    ui.ok(f"Login '{login}' con acceso a {base}.")
    if ui.confirmar("¿Guardar en .env como credencial de la aplicacion (DB_AUTH=sql)?"):
        cfg.update(DB_AUTH="sql", DB_USER=login, DB_PASSWORD=clave)
        env.escribir(cfg)
        ui.ok(".env actualizado.")
