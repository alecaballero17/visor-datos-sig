"""
SQL Server T-SQL Migration Script Generator for VisorDatosSIG.
Generates INSERT / UPDATE statements with OGC geography::STGeomFromText('...', 4326).
"""
from typing import List, Optional, Any
from datetime import datetime
from sig_vector_studio.core.layer_manager import LayerManager
from sig_vector_studio.core.models import Feature
from sig_vector_studio.core.db_sync import (
    escape_sql_string, sql_int_or_null, sql_float_or_null,
    make_geography_expr, make_safe_id_mza_expr, make_safe_id_lote_expr
)

def generate_sql_migration(layer_manager: LayerManager, only_new_or_modified: bool = True) -> str:
    """
    Generates a transaction-safe T-SQL script ready to execute in SQL Server Management Studio (SSMS) or via sqlcmd.
    """
    lines = [
        "-- ===========================================================================",
        "-- SCRIPT DE ACTUALIZACIÓN GEOESPACIAL - VisorDatosSIG",
        f"-- Generado por: SIG Vector Studio el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-- Base de Datos: VisorDatosSIG (SRID: 4326 - geography)",
        "-- ===========================================================================",
        "SET QUOTED_IDENTIFIER ON;",
        "SET ANSI_NULLS ON;",
        "SET NOCOUNT ON;",
        "BEGIN TRANSACTION;",
        "BEGIN TRY",
        ""
    ]

    total_inserted = 0

    # 1. Manzanas
    mza_layer = layer_manager.get_layer("manzanas")
    if mza_layer:
        mza_feats = [f for f in mza_layer.features.values() if not only_new_or_modified or f.is_new or f.is_modified]
        if mza_feats:
            lines.append("-- --- INSERTAR / ACTUALIZAR MANZANAS ---")
            for f in mza_feats:
                uv_mza = escape_sql_string(f.properties.get("UV_MZA"))
                uv = escape_sql_string(f.properties.get("UV"))
                mza = escape_sql_string(f.properties.get("MZA"))
                id_orig = sql_int_or_null(f.properties.get("IdOrigen"))
                wkt = f.wkt
                if not wkt:
                    continue
                geom_expr = make_geography_expr("Polygon", wkt)
                sql = (
                    f"INSERT INTO dbo.Manzanas (IdOrigen, UV_MZA, UV, MZA, Geom) "
                    f"VALUES ({id_orig}, {uv_mza}, {uv}, {mza}, {geom_expr});"
                )
                lines.append(sql)
                total_inserted += 1
            lines.append("")

    # 2. Lotes
    lote_layer = layer_manager.get_layer("lotes")
    if lote_layer:
        lote_feats = [f for f in lote_layer.features.values() if not only_new_or_modified or f.is_new or f.is_modified]
        if lote_feats:
            lines.append("-- --- INSERTAR / ACTUALIZAR LOTES ---")
            for f in lote_feats:
                nro_lote = escape_sql_string(f.properties.get("NroLote"))
                id_orig = sql_int_or_null(f.properties.get("IdOrigen"))
                wkt = f.wkt
                if not wkt:
                    continue
                geom_expr = make_geography_expr("Polygon", wkt)
                safe_id_mza = make_safe_id_mza_expr(f.properties.get("IdManzana"), geom_expr)
                sql = (
                    f"INSERT INTO dbo.Lotes (IdOrigen, NroLote, IdManzana, Geom) "
                    f"VALUES ({id_orig}, {nro_lote}, {safe_id_mza}, {geom_expr});"
                )
                lines.append(sql)
                total_inserted += 1
            lines.append("")

    # 3. Códigos Fijos (Casas / Medidores de Agua)
    cf_layer = layer_manager.get_layer("codigosfijos")
    if cf_layer:
        cf_feats = [f for f in cf_layer.features.values() if not only_new_or_modified or f.is_new or f.is_modified]
        if cf_feats:
            lines.append("-- --- INSERTAR / ACTUALIZAR CÓDIGOS FIJOS (CASAS / AGUA) ---")
            for f in cf_feats:
                cod_f_sql = sql_int_or_null(f.properties.get("CodF_SQL"))
                cod_f_sig = escape_sql_string(f.properties.get("CodF_SIG"))
                cod_fijo = sql_int_or_null(f.properties.get("CodFijo"))
                nombre = escape_sql_string(f.properties.get("Nombre", "Propietario"))
                estado = sql_int_or_null(f.properties.get("Estado", 1))
                
                coord_lon = f.coordinates[0] if (f.coordinates and len(f.coordinates) > 0) else None
                coord_lat = f.coordinates[1] if (f.coordinates and len(f.coordinates) > 1) else None
                lon_str = sql_float_or_null(f.properties.get("Longitud", coord_lon))
                lat_str = sql_float_or_null(f.properties.get("Latitud", coord_lat))

                wkt = f.wkt
                if not wkt:
                    continue
                geom_expr = make_geography_expr("Point", wkt)
                safe_id_lote = make_safe_id_lote_expr(f.properties.get("IdLote"), geom_expr)
                sql = (
                    f"INSERT INTO dbo.CodigosFijos (CodF_SQL, CodF_SIG, CodFijo, Nombre, Estado, FechaCambioEstado, IdLote, Longitud, Latitud, Geom) "
                    f"VALUES ({cod_f_sql}, {cod_f_sig}, {cod_fijo}, {nombre}, {estado}, SYSDATETIME(), {safe_id_lote}, {lon_str}, {lat_str}, {geom_expr});"
                )
                lines.append(sql)
                total_inserted += 1
            lines.append("")

    # 4. Vías
    via_layer = layer_manager.get_layer("vias")
    if via_layer:
        via_feats = [f for f in via_layer.features.values() if not only_new_or_modified or f.is_new or f.is_modified]
        if via_feats:
            lines.append("-- --- INSERTAR / ACTUALIZAR VÍAS ---")
            for f in via_feats:
                obj_id = sql_int_or_null(f.properties.get("OBJECTID"))
                nombre = escape_sql_string(f.properties.get("Nombre", "Calle S/N"))
                tipo_via = escape_sql_string(f.properties.get("TipoVia", "Calle"))
                osmid = escape_sql_string(f.properties.get("OSMID", ""))
                wkt = f.wkt
                if not wkt:
                    continue
                geom_expr = make_geography_expr("LineString", wkt)
                sql = (
                    f"INSERT INTO dbo.Vias (OBJECTID, Nombre, TipoVia, OSMID, Geom) "
                    f"VALUES ({obj_id}, {nombre}, {tipo_via}, {osmid}, {geom_expr});"
                )
                lines.append(sql)
                total_inserted += 1
            lines.append("")

    # Spatial relationship recalculation & Commit
    lines.extend([
        "-- Re-sincronizar relaciones espaciales Lotes -> Manzanas",
        "UPDATE l",
        "   SET IdManzana = m.IdManzana",
        "  FROM dbo.Lotes l",
        "  JOIN dbo.Manzanas m ON l.Geom.STPointN(1).STIntersects(m.Geom) = 1",
        " WHERE l.IdManzana IS NULL AND l.Geom IS NOT NULL;",
        "",
        "-- Re-sincronizar relaciones espaciales CodigosFijos -> Lotes",
        "UPDATE c",
        "   SET IdLote = l.IdLote",
        "  FROM dbo.CodigosFijos c",
        "  JOIN dbo.Lotes l ON c.Geom.STIntersects(l.Geom) = 1",
        " WHERE c.IdLote IS NULL AND c.Geom IS NOT NULL;",
        "",
        "COMMIT TRANSACTION;",
        f"PRINT 'Actualización completada exitosamente. Registros procesados: {total_inserted}';",
        "END TRY",
        "BEGIN CATCH",
        "    ROLLBACK TRANSACTION;",
        "    DECLARE @ErrMsg NVARCHAR(4000) = ERROR_MESSAGE();",
        "    RAISERROR(@ErrMsg, 16, 1);",
        "END CATCH;"
    ])

    return "\n".join(lines)
