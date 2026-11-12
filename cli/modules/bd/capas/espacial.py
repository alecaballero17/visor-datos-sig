"""Mantenimiento espacial: vinculos catastrales, indices y validez de geometrias."""
from __future__ import annotations

from cli.core import sql, ui

from .capas import CAPAS


def vincular() -> None:
    """Vincula Codigos fijos→Lotes y Lotes→Manzanas por interseccion (como DbSeeder)."""
    ui.info("Vinculando entidades por interseccion espacial (puede tardar)...")
    sql.ejecutar("""
        UPDATE c SET c.IdLote = l.IdLote FROM dbo.CodigosFijos c
        JOIN dbo.Lotes l ON c.Geom.STIntersects(l.Geom) = 1 WHERE c.IdLote IS NULL;
        PRINT CONCAT('Codigos fijos vinculados: ', @@ROWCOUNT);
        UPDATE l SET l.IdManzana = m.IdManzana FROM dbo.Lotes l
        JOIN dbo.Manzanas m ON l.Geom.STIntersects(m.Geom) = 1 WHERE l.IdManzana IS NULL;
        PRINT CONCAT('Lotes vinculados: ', @@ROWCOUNT);""")
    ui.ok("Vinculacion terminada.")


def estadisticas() -> None:
    """Totales, sin geometria, invalidas y sin vinculo por capa."""
    filas = []
    for capa in CAPAS:
        try:
            r = sql.filas(f"""SELECT COUNT(*), SUM(CASE WHEN Geom IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN Geom IS NOT NULL AND Geom.STIsValid() = 0 THEN 1 ELSE 0 END)
                FROM {capa.tabla}""")[0]
        except ui.Fallo:
            filas.append([capa.clave, "-", "-", "-", "-"])
            continue
        sin_vinculo = "-"
        if capa.clave == "codigosfijos":
            sin_vinculo = sql.escalar("SELECT COUNT(*) FROM dbo.CodigosFijos WHERE IdLote IS NULL")
        elif capa.clave == "lotes":
            sin_vinculo = sql.escalar("SELECT COUNT(*) FROM dbo.Lotes WHERE IdManzana IS NULL")
        filas.append([capa.clave, r[0], r[1] or 0, r[2] or 0, sin_vinculo])
    ui.tabla(filas, ["Capa", "Total", "Sin geom", "Invalidas", "Sin vinculo"])


def reparar() -> None:
    """Aplica MakeValid a las geometrias invalidas."""
    for capa in CAPAS:
        sql.ejecutar(f"""UPDATE {capa.tabla} SET Geom = Geom.MakeValid() WHERE Geom IS NOT NULL AND Geom.STIsValid() = 0;
                         PRINT CONCAT('{capa.clave}: ', @@ROWCOUNT, ' reparadas');""")


def indices(usar_sp: bool | None = None) -> None:
    """Crea/reconstruye los indices espaciales."""
    existe_sp = sql.escalar("SELECT CASE WHEN OBJECT_ID(N'dbo.sp_OptimizarIndicesEspaciales', 'P') IS NULL THEN 0 ELSE 1 END") == "1"
    if usar_sp is None:
        usar_sp = existe_sp and ui.confirmar("Existe dbo.sp_OptimizarIndicesEspaciales. ¿Usarlo?", True)
    if usar_sp and existe_sp:
        sql.ejecutar("EXEC dbo.sp_OptimizarIndicesEspaciales;")
        ui.ok("Procedimiento ejecutado.")
        return
    for capa in CAPAS:
        nombre = f"SIX_{capa.tabla.split('.')[1]}_Geom"
        tipo = sql.escalar(f"SELECT TYPE_NAME(user_type_id) FROM sys.columns WHERE object_id = OBJECT_ID(N'{capa.tabla}') AND name = 'Geom'")
        if not tipo:
            continue
        grid = "GEOGRAPHY_AUTO_GRID" if tipo == "geography" else \
            "GEOMETRY_AUTO_GRID WITH (BOUNDING_BOX = (-62, -18, -60, -15))"
        sql.ejecutar(f"""
            IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'{nombre}' AND object_id = OBJECT_ID(N'{capa.tabla}'))
                ALTER INDEX {nombre} ON {capa.tabla} REBUILD;
            ELSE CREATE SPATIAL INDEX {nombre} ON {capa.tabla}(Geom) USING {grid};""", mostrar=False)
        ui.ok(f"{nombre} listo.")


def vaciar_capa() -> None:
    """Borra todas las filas de una capa."""
    i = ui.elegir("Capa a vaciar", [c.clave for c in CAPAS])
    capa = CAPAS[i]
    if ui.confirmar_peligro(f"Se borraran todas las filas de {capa.tabla}.", capa.clave):
        sql.ejecutar(f"DELETE FROM {capa.tabla}; PRINT CONCAT(@@ROWCOUNT, ' filas borradas');")
