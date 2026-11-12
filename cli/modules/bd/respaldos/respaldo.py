"""Respaldo y restauracion (.bak).

El archivo lo escribe el *proceso de SQL Server* (en Linux el usuario mssql),
por eso se usa la carpeta de respaldos del servidor (InstanceDefaultBackupPath,
p. ej. /var/opt/mssql/data) y el listado sale del historial de msdb: funciona
igual con SQL Server local, remoto o en Docker. Solo con LocalDB (Windows,
mismo usuario) se guarda en .setup/backups del proyecto.
"""
from __future__ import annotations

from datetime import datetime

from cli.core import env, sql, ui
from cli.core.paths import BACKUPS_DIR, asegurar


def _sep(ruta: str) -> str:
    return "\\" if "\\" in ruta or (len(ruta) > 1 and ruta[1] == ":") else "/"


def carpeta() -> str:
    """Carpeta (vista por el servidor SQL) donde se escriben los .bak."""
    if env.get("DB_SERVER").lower().startswith("(localdb)"):
        asegurar(BACKUPS_DIR)
        return str(BACKUPS_DIR)
    ruta = sql.escalar("SELECT CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS nvarchar(260))", base="master")
    return (ruta or "/var/opt/mssql/data").rstrip("/\\")


def respaldar(etiqueta: str = "manual") -> str | None:
    """BACKUP DATABASE verificado (comprimido si la edicion lo permite)."""
    base = env.get("DB_NAME")
    if not sql.existe_base(base):
        ui.warn(f"La base {base} no existe; nada que respaldar.")
        return None
    dir_ = carpeta()
    destino = f"{dir_}{_sep(dir_)}{base}-{datetime.now():%Y%m%d-%H%M%S}-{etiqueta}.bak"
    edicion = sql.escalar("SELECT CAST(SERVERPROPERTY('EngineEdition') AS int)", base="master")
    compresion = ", COMPRESSION" if edicion in ("2", "3", "8") else ""   # Standard / Enterprise / Managed
    ui.info(f"Respaldando {base} → {destino}  (ruta en el servidor SQL)")
    sql.ejecutar(f"BACKUP DATABASE {sql.ident(base)} TO DISK = N'{sql.lit(destino)}' "
                 f"WITH INIT, CHECKSUM, COPY_ONLY{compresion}, STATS = 25", base="master")
    sql.ejecutar(f"RESTORE VERIFYONLY FROM DISK = N'{sql.lit(destino)}' WITH CHECKSUM", base="master", mostrar=False)
    ui.ok(f"Respaldo verificado: {destino}")
    return destino


def _historial(base: str | None = None, limite: int = 30) -> list[list[str]]:
    filtro = f"AND s.database_name = N'{sql.lit(base)}'" if base else ""
    return sql.filas(f"""
        SELECT TOP {limite} m.physical_device_name, s.database_name,
               CONVERT(varchar(16), s.backup_finish_date, 120),
               CAST(COALESCE(s.compressed_backup_size, s.backup_size) / 1048576.0 AS decimal(10,1))
        FROM msdb.dbo.backupset s JOIN msdb.dbo.backupmediafamily m ON m.media_set_id = s.media_set_id
        WHERE s.type = 'D' {filtro} ORDER BY s.backup_finish_date DESC""", base="master")


def listar() -> None:
    """Respaldos completos registrados en el servidor (msdb)."""
    filas = _historial()
    ui.tabla([[f[0], f[1], f[2], f"{f[3]} MB"] for f in filas], ["Archivo (en el servidor)", "Base", "Fecha", "Tamano"])
    ui.dim(f"Carpeta de respaldos: {carpeta()}")


def restaurar(ruta: str | None = None) -> None:
    """Restaura un .bak sobre la base configurada (la reemplaza)."""
    base = env.get("DB_NAME")
    if ruta is None:
        hist = _historial(base, 15)
        opciones = [f"{f[2]}  {f[0]}" for f in hist] + ["Otra ruta (vista por el servidor)..."]
        i = ui.elegir("Respaldo a restaurar", opciones)
        ruta = hist[i][0] if i < len(hist) else ui.preguntar("Ruta del .bak en el servidor SQL")
    if not ruta or not ui.confirmar_peligro(f"Se REEMPLAZARA la base {base} con {ruta}.", base):
        return
    archivos = sql.filas(f"RESTORE FILELISTONLY FROM DISK = N'{sql.lit(ruta)}'", base="master")
    datos = sql.escalar("SELECT CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS nvarchar(260))", base="master")
    datos = (datos or "/var/opt/mssql/data").rstrip("/\\")
    s = _sep(datos)
    moves = [f"MOVE N'{sql.lit(f[0])}' TO N'{sql.lit(datos + s + base + ('_log.ldf' if f[2] == 'L' else '.mdf'))}'"
             for f in archivos]
    if sql.existe_base(base):
        sql.ejecutar(f"ALTER DATABASE {sql.ident(base)} SET SINGLE_USER WITH ROLLBACK IMMEDIATE", base="master", mostrar=False)
    try:
        sql.ejecutar(f"RESTORE DATABASE {sql.ident(base)} FROM DISK = N'{sql.lit(ruta)}' WITH REPLACE, "
                     f"{', '.join(moves)}, STATS = 25", base="master")
    finally:
        sql.ejecutar(f"IF DB_ID(N'{sql.lit(base)}') IS NOT NULL ALTER DATABASE {sql.ident(base)} SET MULTI_USER",
                     base="master", mostrar=False, check=False)
    ui.ok(f"Base {base} restaurada. Revise migraciones: arquis bd migraciones estado")


def purgar() -> None:
    """Borra el historial de msdb anterior a N dias (los archivos .bak se borran en el servidor)."""
    dias = int(ui.preguntar("Conservar historial de los ultimos N dias", "30") or "30")
    sql.ejecutar(f"DECLARE @f datetime = DATEADD(day, -{dias}, GETDATE()); EXEC msdb.dbo.sp_delete_backuphistory @f;",
                 base="master", mostrar=False)
    ui.ok("Historial purgado.")
    ui.info(f"Para liberar disco borre los .bak antiguos de {carpeta()} en el servidor SQL "
            f"(Linux: sudo find {carpeta()} -name '*.bak' -mtime +{dias} -delete).")
