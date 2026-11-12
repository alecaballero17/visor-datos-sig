"""Operaciones generales sobre la base: estado, crear, eliminar, inicializar."""
from __future__ import annotations

from cli.core import env, sql, ui

from .capas import importar as capas_importar
from .capas.capas import CAPAS, carpeta
from .migraciones import ef
from .respaldos import respaldo
from .servidor import conexion


def estado() -> None:
    """Resumen: conexion, tamano, migraciones y datos cargados."""
    cfg = env.cargar()
    if not conexion.probar():
        return
    base = cfg["DB_NAME"]
    if not sql.existe_base(base):
        return
    tam = sql.escalar("SELECT CAST(SUM(size) * 8 / 1024.0 AS decimal(10,1)) FROM sys.database_files")
    ui.info(f"Tamano: {tam} MB")
    hist = sql.escalar("SELECT CASE WHEN OBJECT_ID(N'dbo.__EFMigrationsHistory') IS NULL THEN '' ELSE "
                       "(SELECT TOP 1 MigrationId FROM dbo.__EFMigrationsHistory ORDER BY MigrationId DESC) END")
    ui.info(f"Ultima migracion aplicada: {hist or ui.c('ninguna', ui.C.YELLOW)}")
    filas = []
    for t in ["dbo.Usuarios", "dbo.Roles"] + [c.tabla for c in CAPAS] + ["dbo.RutasTrabajo", "dbo.TrackingPosiciones"]:
        n = sql.escalar(f"SELECT CASE WHEN OBJECT_ID(N'{t}') IS NULL THEN '-' ELSE "
                        f"CAST((SELECT SUM(rows) FROM sys.partitions WHERE object_id = OBJECT_ID(N'{t}') AND index_id IN (0,1)) AS varchar(20)) END")
        filas.append([t, n])
    ui.tabla(filas, ["Tabla", "Filas"])


def crear() -> None:
    """Crea la base vacia (si no existe)."""
    base = env.get("DB_NAME")
    if sql.existe_base(base):
        ui.info(f"La base {base} ya existe.")
        return
    sql.ejecutar(f"CREATE DATABASE {sql.ident(base)}", base="master", mostrar=False)
    ui.ok(f"Base {base} creada.")


def eliminar() -> None:
    """DROP DATABASE (ofrece respaldo previo)."""
    base = env.get("DB_NAME")
    if not sql.existe_base(base):
        ui.info("La base no existe.")
        return
    if not ui.confirmar_peligro(f"Se ELIMINARA la base {base} con todos sus datos.", base):
        return
    if ui.confirmar("¿Respaldar antes?", True):
        respaldo.respaldar("antes-de-eliminar")
    sql.ejecutar(f"ALTER DATABASE {sql.ident(base)} SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
                 f"DROP DATABASE {sql.ident(base)};", base="master", mostrar=False)
    ui.ok(f"Base {base} eliminada.")


def inicializar() -> None:
    """Todo en uno: crear base → migraciones → capas SIG → vinculos."""
    pasos = 4
    ui.paso(1, pasos, "Conexion")
    if not conexion.probar():
        raise ui.Fallo("Sin conexion al servidor.")
    ui.paso(2, pasos, "Crear base")
    crear()
    ui.paso(3, pasos, "Migraciones EF")
    ef.actualizar()
    ui.paso(4, pasos, "Capas SIG")
    if any((carpeta() / f"{c.archivo}.shp").exists() for c in CAPAS):
        capas_importar.importar(reemplazar=False)
    else:
        ui.warn("No hay shapefiles en SHP_DIR: el mapa quedara sin entidades (arquis bd capas copiar).")
    ui.ok("Base inicializada. Roles y usuarios iniciales se crean al arrancar el backend (DbSeeder).")


def recrear() -> None:
    """Elimina y vuelve a inicializar la base (desarrollo)."""
    base = env.get("DB_NAME")
    if sql.existe_base(base):
        eliminar()
        if sql.existe_base(base):
            return
    inicializar()
