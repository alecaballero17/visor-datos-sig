"""Consultas: consola SQL, conteos, tamanos, exportacion CSV y bitacoras."""
from __future__ import annotations

import csv
from datetime import datetime

from cli.core import sql, ui
from cli.core.paths import ARTIFACTS, asegurar, rel


def conteos() -> None:
    """Filas por tabla."""
    filas = sql.filas("""
        SELECT s.name + '.' + t.name, SUM(p.rows)
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id = t.schema_id
        JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
        GROUP BY s.name, t.name ORDER BY s.name, t.name""")
    ui.tabla(filas, ["Tabla", "Filas"])


def tamanos() -> None:
    """Espacio usado por tabla (datos + indices)."""
    filas = sql.filas("""
        SELECT TOP 30 s.name + '.' + t.name,
               SUM(CASE WHEN p.index_id IN (0,1) THEN p.rows ELSE 0 END),
               CAST(SUM(a.total_pages) * 8 / 1024.0 AS decimal(10,2)),
               CAST(SUM(a.used_pages) * 8 / 1024.0 AS decimal(10,2))
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id = t.schema_id
        JOIN sys.indexes i ON i.object_id = t.object_id
        JOIN sys.partitions p ON p.object_id = i.object_id AND p.index_id = i.index_id
        JOIN sys.allocation_units a ON a.container_id = p.partition_id
        GROUP BY s.name, t.name ORDER BY SUM(a.total_pages) DESC""")
    ui.tabla(filas, ["Tabla", "Filas", "Reservado MB", "Usado MB"])


def consola() -> None:
    """Consola SQL interactiva (termine cada sentencia con ';' o 'GO'; 'salir' para terminar)."""
    ui.info("Escriba T-SQL. Una linea con 'GO' o terminada en ';' ejecuta. 'salir' termina.")
    bufer: list[str] = []
    while True:
        try:
            linea = input(ui.c("sql› " if not bufer else "  … ", ui.C.CYAN))
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if linea.strip().lower() in ("salir", "exit", "quit") and not bufer:
            return
        if linea.strip().upper() != "GO":
            bufer.append(linea)
        if linea.strip().upper() == "GO" or linea.rstrip().endswith(";"):
            consulta = "\n".join(bufer).strip()
            bufer = []
            if consulta:
                try:
                    sql.ejecutar(consulta)
                except ui.Fallo as e:
                    ui.error(str(e))


def exportar_csv() -> None:
    """Exporta una tabla o consulta a CSV (artifacts/csv)."""
    origen = ui.preguntar("Tabla (ej. dbo.Usuarios) o SELECT completo")
    if not origen:
        return
    es_select = origen.lower().lstrip().startswith("select")
    consulta = origen if es_select else f"SELECT * FROM {origen}"
    nombre = "consulta" if es_select else origen.replace(".", "_")
    # Las geometrias se exportan como WKT
    tipos = sql.filas(f"SELECT name, system_type_name FROM sys.dm_exec_describe_first_result_set(N'{sql.lit(consulta)}', NULL, 0) ORDER BY column_ordinal")
    sel = ", ".join(f"{sql.ident(n)}.STAsText() AS {sql.ident(n)}" if t.startswith(("geography", "geometry")) else sql.ident(n)
                    for n, t in tipos)
    datos = sql.filas(f"SELECT {sel} FROM ({consulta}) AS q")
    asegurar(ARTIFACTS / "csv")
    destino = ARTIFACTS / "csv" / f"{nombre}-{datetime.now():%Y%m%d-%H%M%S}.csv"
    with destino.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([t[0] for t in tipos])
        w.writerows(datos)
    ui.ok(f"{len(datos)} filas → {rel(destino)}")


def bitacora_accesos() -> None:
    """Ultimos accesos al sistema."""
    filas = sql.filas("SELECT TOP 30 * FROM dbo.BitacoraAccesos ORDER BY 1 DESC")
    ui.tabla(filas)


def bitacora_migraciones() -> None:
    """Historial del migrador de capas."""
    ui.tabla(sql.filas("SELECT TOP 30 * FROM dbo.BitacoraMigraciones ORDER BY 1 DESC"))


def sesiones() -> None:
    """Conexiones activas a la base."""
    filas = sql.filas("""SELECT session_id, login_name, host_name, program_name, status,
               CONVERT(varchar(19), login_time, 120)
        FROM sys.dm_exec_sessions WHERE database_id = DB_ID() AND is_user_process = 1""")
    ui.tabla(filas, ["Sesion", "Login", "Equipo", "Programa", "Estado", "Desde"])
